"""
=============================================================
 ÉTAPE 2 : TRIER les articles
=============================================================
Ce script travaille en deux phases :

  PHASE 1 - Filtre par mots-clés (rapide, gratuit, hors ligne)
    Cherche les mots de mots_cles.yml dans le titre et l'extrait
    de chaque nouvel article. Aucun mot trouvé = hors sujet (note 0).

  PHASE 2 - Analyse par une IA (Gemini ou Mistral)
    Pour chaque article gardé, l'IA écrit :
      - un résumé en français,
      - 1 à 3 tags (pris dans une liste fixe),
      - une note de pertinence de 0 à 5.
    La réponse de l'IA est VÉRIFIÉE avant d'être enregistrée.

La clé de l'API est lue dans une variable d'environnement
(jamais écrite dans le code, car le dépôt est public) :
  - GEMINI_API_KEY  -> Google Gemini   (utilisée en priorité)
  - MISTRAL_API_KEY -> Mistral AI      (si pas de clé Gemini)

Pour le lancer :  py tri.py
=============================================================
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from base import ouvrir_base


# ---------- Réglages ----------

FICHIER_MOTS_CLES = Path(__file__).parent / "mots_cles.yml"

# Nombre maximum d'articles envoyés à l'IA à chaque lancement
# (l'offre gratuite limite le nombre de requêtes par jour)
MAX_ARTICLES_IA = 50

# Pause (en secondes) entre deux appels à l'IA
# (l'offre gratuite limite aussi le nombre de requêtes par minute)
PAUSE_ENTRE_APPELS = 5

# Modèles utilisés
MODELE_GEMINI = "gemini-flash-lite-latest"
MODELE_MISTRAL = "mistral-small-latest"

# Liste FIXE des tags : l'IA doit choisir dedans.
# Une liste fixe permet de filtrer les articles par tag sur le site
# (sinon l'IA inventerait "LLM", "llm", "Grands modèles"... pour la même chose).
TAGS_AUTORISES = [
    "LLM",
    "Agents IA",
    "Outils dev",
    "Open source",
    "Recherche",
    "Sécurité",
    "Régulation",
    "Éthique & société",
    "Entreprises",
    "Matériel & GPU",
    "Image & vidéo",
    "Audio & voix",
    "Robotique",
    "Éducation",
]


# =============================================================
#  PHASE 1 : filtre par mots-clés
# =============================================================

def charger_motifs():
    """
    Lit mots_cles.yml et prépare une "expression régulière" (regex)
    pour chaque mot. Renvoie une liste de couples (mot, motif).
    """
    with open(FICHIER_MOTS_CLES, encoding="utf-8") as fichier:
        contenu = yaml.safe_load(fichier)

    motifs = []
    for mot in contenu["mots_cles"]:
        # \b = limite de mot : "IA" ne doit pas être trouvé dans "via"
        # re.IGNORECASE = sans tenir compte des majuscules
        motif = re.compile(r"\b" + re.escape(mot) + r"\b", re.IGNORECASE)
        motifs.append((mot, motif))
    for sigle in contenu["sigles"]:
        # Pas de re.IGNORECASE ici : "AI" oui, "j'ai" non
        motif = re.compile(r"\b" + re.escape(sigle) + r"\b")
        motifs.append((sigle, motif))
    return motifs


def trouver_mots_cles(texte, motifs):
    """Renvoie la liste des mots-clés présents dans le texte."""
    trouves = []
    for mot, motif in motifs:
        if motif.search(texte):
            trouves.append(mot)
    return trouves


def phase_1_mots_cles(connexion):
    """Filtre tous les articles qui n'ont pas encore été filtrés."""
    motifs = charger_motifs()
    articles = connexion.execute(
        "SELECT id, titre, description FROM articles WHERE mots_cles IS NULL"
    ).fetchall()

    gardes = 0
    for article in articles:
        texte = article["titre"] + " " + (article["description"] or "")
        trouves = trouver_mots_cles(texte, motifs)

        if trouves:
            gardes += 1
            connexion.execute(
                "UPDATE articles SET mots_cles = ? WHERE id = ?",
                (", ".join(trouves), article["id"]),
            )
        else:
            # Aucun mot-clé : hors sujet, note 0
            connexion.execute(
                "UPDATE articles SET mots_cles = '', note = 0 WHERE id = ?",
                (article["id"],),
            )

    connexion.commit()
    print(f"Phase 1 : {len(articles)} article(s) filtré(s), "
          f"{gardes} gardé(s), {len(articles) - gardes} hors sujet.")


# =============================================================
#  PHASE 2 : analyse par l'IA
# =============================================================

def construire_consigne(article):
    """Écrit la consigne (le "prompt") envoyée à l'IA pour un article."""
    return f"""Tu aides un étudiant en BTS SIO option SLAM (développement d'applications)
à faire sa veille technologique sur l'intelligence artificielle.

Analyse l'article ci-dessous et réponds UNIQUEMENT avec un objet JSON contenant :
- "resume" : un résumé en français, en 2 ou 3 phrases simples, même si l'article est en anglais ;
- "tags" : une liste de 1 à 3 tags choisis UNIQUEMENT dans cette liste : {", ".join(TAGS_AUTORISES)} ;
- "note" : la pertinence pour un développeur qui suit l'actualité de l'IA, nombre entier de 0 à 5 :
    0 = l'article ne parle pas vraiment d'intelligence artificielle
    1 = anecdotique, 2 = peu utile, 3 = intéressant, 4 = important,
    5 = incontournable (nouveau modèle, outil ou technique qui change la façon de développer).

Titre : {article["titre"]}
Source : {article["source"]}
Extrait : {article["description"] or "(pas d'extrait)"}"""


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


def appeler_gemini(consigne, cle):
    """Demande l'analyse à Google Gemini. Renvoie un dictionnaire."""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODELE_GEMINI}:generateContent")
    corps = {
        "contents": [{"parts": [{"text": consigne}]}],
        "generationConfig": {
            "temperature": 0.2,  # réponses plus stables, moins "créatives"
            # On IMPOSE le format de la réponse (un JSON avec ces 3 champs)
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "resume": {"type": "STRING"},
                    "tags": {"type": "ARRAY",
                             "items": {"type": "STRING", "enum": TAGS_AUTORISES}},
                    "note": {"type": "INTEGER"},
                },
                "required": ["resume", "tags", "note"],
            },
        },
    }
    # La clé passe dans un en-tête, pas dans l'URL (elle n'apparaît pas dans les logs)
    donnees = envoyer_requete(url, corps, {"x-goog-api-key": cle})
    texte = donnees["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(texte)


def appeler_mistral(consigne, cle):
    """Demande l'analyse à Mistral AI. Renvoie un dictionnaire."""
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


def valider_resultat(resultat):
    """
    Vérifie la réponse de l'IA : on ne lui fait JAMAIS confiance aveuglément.
    Renvoie un dictionnaire propre, ou None si la réponse est inutilisable.
    """
    if not isinstance(resultat, dict):
        return None

    # Le résumé doit être un texte non vide
    resume = resultat.get("resume")
    if not isinstance(resume, str) or not resume.strip():
        return None

    # La note doit être un nombre entier, ramené entre 0 et 5
    try:
        note = int(resultat.get("note"))
    except (TypeError, ValueError):
        return None
    note = max(0, min(5, note))

    # Les tags : on garde seulement ceux de la liste autorisée, sans doublon, 3 max
    tags = []
    for tag in resultat.get("tags") or []:
        if tag in TAGS_AUTORISES and tag not in tags:
            tags.append(tag)

    return {"resume": resume.strip()[:800], "tags": tags[:3], "note": note}


def choisir_ia():
    """Choisit l'IA selon la clé disponible. Renvoie (nom, fonction, clé)."""
    if os.environ.get("GEMINI_API_KEY"):
        return "Gemini", appeler_gemini, os.environ["GEMINI_API_KEY"]
    if os.environ.get("MISTRAL_API_KEY"):
        return "Mistral", appeler_mistral, os.environ["MISTRAL_API_KEY"]
    return None, None, None


def phase_2_ia(connexion):
    """Fait analyser par l'IA les articles gardés qui n'ont pas de résumé."""
    nom_ia, appeler_ia, cle = choisir_ia()
    if appeler_ia is None:
        print("Phase 2 : aucune clé d'API trouvée "
              "(GEMINI_API_KEY ou MISTRAL_API_KEY). Analyse IA ignorée.")
        return

    # Les plus récents d'abord : le site affiche en priorité l'actualité fraîche
    articles = connexion.execute(
        """
        SELECT id, titre, source, description FROM articles
        WHERE mots_cles != '' AND resume IS NULL
        ORDER BY date_publication DESC
        LIMIT ?
        """,
        (MAX_ARTICLES_IA,),
    ).fetchall()
    print(f"Phase 2 : {len(articles)} article(s) à analyser avec {nom_ia}...")

    analyses = 0
    for numero, article in enumerate(articles, start=1):
        if numero > 1:
            time.sleep(PAUSE_ENTRE_APPELS)

        try:
            resultat = appeler_ia(construire_consigne(article), cle)
        except urllib.error.HTTPError as erreur:
            if erreur.code == 429:
                # 429 = "Too Many Requests" : quota de l'offre gratuite atteint.
                # On s'arrête proprement, les articles restants seront
                # analysés au prochain lancement.
                print("  Quota de l'API atteint (erreur 429) : arrêt, "
                      "on reprendra au prochain lancement.")
                break
            print(f"  [ERREUR {erreur.code}] {article['titre'][:60]}")
            continue
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError,
                json.JSONDecodeError) as erreur:
            print(f"  [ERREUR] {article['titre'][:60]} : {erreur}")
            continue

        propre = valider_resultat(resultat)
        if propre is None:
            print(f"  [RÉPONSE INVALIDE] {article['titre'][:60]}")
            continue

        connexion.execute(
            "UPDATE articles SET resume = ?, tags = ?, note = ? WHERE id = ?",
            (propre["resume"], ", ".join(propre["tags"]), propre["note"], article["id"]),
        )
        connexion.commit()  # on enregistre après chaque article : rien n'est perdu si ça plante
        analyses += 1
        print(f"  [{propre['note']}/5] {article['titre'][:70]}")

    restants = connexion.execute(
        "SELECT COUNT(*) FROM articles WHERE mots_cles != '' AND resume IS NULL"
    ).fetchone()[0]
    print(f"Phase 2 : {analyses} article(s) analysé(s), {restants} en attente.")


# ---------- Programme principal ----------

def main():
    connexion = ouvrir_base()
    phase_1_mots_cles(connexion)
    phase_2_ia(connexion)
    connexion.close()


if __name__ == "__main__":
    main()
