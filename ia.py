"""
=============================================================
 MODULE PARTAGÉ : appeler une IA (Gemini ou Mistral)
=============================================================
Utilisé par tri.py (analyse de chaque article) et par
essentiel.py (synthèse de la semaine).

Le code qui "parle" à l'IA est écrit ici UNE seule fois :
chaque script fournit seulement sa consigne (le prompt) et
le format de réponse attendu (le schéma JSON).

La clé est lue dans une variable d'environnement
(jamais écrite dans le code, car le dépôt est public) :
  - GEMINI_API_KEY  -> Google Gemini   (utilisée en priorité)
  - MISTRAL_API_KEY -> Mistral AI      (si pas de clé Gemini)
=============================================================
"""

import json
import os
import urllib.request


# ---------- Réglages ----------

MODELE_GEMINI = "gemini-flash-lite-latest"
MODELE_MISTRAL = "mistral-small-latest"


# ---------- Fonctions ----------

def envoyer_requete(url, corps, entetes):
    """Envoie une requête POST en JSON et renvoie la réponse décodée."""
    requete = urllib.request.Request(
        url,
        data=json.dumps(corps).encode("utf-8"),
        headers={"Content-Type": "application/json", **entetes},
        method="POST",
    )
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return json.load(reponse)


def appeler_gemini(consigne, cle, schema):
    """Envoie la consigne à Google Gemini. Renvoie la réponse (un dictionnaire)."""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODELE_GEMINI}:generateContent")
    corps = {
        "contents": [{"parts": [{"text": consigne}]}],
        "generationConfig": {
            "temperature": 0.2,  # réponses plus stables, moins "créatives"
            # On IMPOSE le format de la réponse : un JSON qui respecte le schéma
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    # La clé passe dans un en-tête, pas dans l'URL (elle n'apparaît pas dans les logs)
    donnees = envoyer_requete(url, corps, {"x-goog-api-key": cle})
    texte = donnees["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(texte)


def appeler_mistral(consigne, cle, schema):
    """Envoie la consigne à Mistral AI. Renvoie la réponse (un dictionnaire)."""
    # Mistral n'utilise pas le schéma : le format est décrit dans la consigne
    url = "https://api.mistral.ai/v1/chat/completions"
    corps = {
        "model": MODELE_MISTRAL,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": consigne}],
        "response_format": {"type": "json_object"},  # réponse en JSON obligatoire
    }
    donnees = envoyer_requete(url, corps, {"Authorization": f"Bearer {cle}"})
    texte = donnees["choices"][0]["message"]["content"]
    return json.loads(texte)


def choisir_ia():
    """Choisit l'IA selon la clé disponible. Renvoie (nom, fonction, clé)."""
    if os.environ.get("GEMINI_API_KEY"):
        return "Gemini", appeler_gemini, os.environ["GEMINI_API_KEY"]
    if os.environ.get("MISTRAL_API_KEY"):
        return "Mistral", appeler_mistral, os.environ["MISTRAL_API_KEY"]
    return None, None, None
