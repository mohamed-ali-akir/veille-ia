"""
=============================================================
 BONUS : ALERTES sur Discord
=============================================================
Envoie sur un salon Discord les articles les plus importants
(note 4 ou 5) qui n'ont pas encore été envoyés.

Discord fournit un "webhook" : une adresse web secrète.
Quand on envoie un message JSON à cette adresse, il apparaît
dans le salon. L'adresse est lue dans la variable
d'environnement DISCORD_WEBHOOK_URL (jamais dans le code :
n'importe qui pourrait écrire dans le salon avec).

Chaque article est envoyé dans un message SÉPARÉ, dont on garde
l'identifiant : si je réagis avec ⭐ sous le message, favoris.py
saura de quel article il s'agit.

Pour le lancer :  py alerte_discord.py
=============================================================
"""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from base import ouvrir_base


# ---------- Réglages ----------

# Note minimale pour qu'un article soit envoyé
NOTE_MINIMALE = 4

# Nombre maximum d'articles envoyés à chaque lancement
MAX_ARTICLES = 10

# On n'envoie que les articles collectés depuis moins de X jours
# (évite d'envoyer de vieux articles la première fois)
AGE_MAX_JOURS = 2

# Pause (en secondes) entre deux messages : Discord limite le nombre
# de messages qu'un webhook peut envoyer en peu de temps
PAUSE_ENTRE_MESSAGES = 1

# Adresse du site, ajoutée dans les messages
URL_SITE = "https://mohamed-ali-akir.github.io/veille-ia/"

# Couleur de la carte selon la note (format hexadécimal converti en nombre)
COULEURS = {5: 0xE8590C, 4: 0x1C7ED6}


# ---------- Fonctions ----------

def lire_articles_a_envoyer(connexion):
    """Renvoie les articles importants, récents et pas encore envoyés."""
    limite = (datetime.now(timezone.utc) - timedelta(days=AGE_MAX_JOURS)).isoformat()
    return connexion.execute(
        """
        SELECT id, titre, url, source, tags, resume, note FROM articles
        WHERE note >= ? AND alerte_envoyee = 0 AND date_collecte >= ?
        ORDER BY note DESC, date_publication DESC
        LIMIT ?
        """,
        (NOTE_MINIMALE, limite, MAX_ARTICLES),
    ).fetchall()


def creer_carte(article):
    """
    Transforme un article en "carte" Discord (un embed).
    Aussi utilisée par favoris.py pour le salon #favoris.
    """
    etoiles = "★" * article["note"] + "☆" * (5 - article["note"])
    return {
        "author": {"name": "Veille IA", "url": URL_SITE},
        "title": article["titre"][:250],
        "url": article["url"],
        "description": (article["resume"] or "")[:1000],
        "color": COULEURS.get(article["note"], 0x868E96),
        "fields": [
            {"name": "Note", "value": etoiles, "inline": True},
            {"name": "Source", "value": article["source"], "inline": True},
            {"name": "Tags", "value": article["tags"] or "-", "inline": True},
        ],
    }


def envoyer_sur_discord(url_webhook, message):
    """
    Envoie un message (dictionnaire) sur un webhook Discord.
    "?wait=true" demande à Discord de répondre avec le message créé
    (dont son identifiant). Renvoie ce message, ou None en cas d'erreur.
    Aussi utilisée par essentiel.py et favoris.py.
    """
    requete = urllib.request.Request(
        url_webhook + "?wait=true",
        data=json.dumps(message).encode("utf-8"),
        # Discord refuse les requêtes sans "User-Agent" (carte d'identité du programme)
        headers={"Content-Type": "application/json",
                 "User-Agent": "VeilleIA/1.0 (projet etudiant BTS SIO)"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            return json.load(reponse)
    except urllib.error.HTTPError as erreur:
        print(f"Erreur Discord {erreur.code} : {erreur.read().decode()[:200]}")
    except urllib.error.URLError as erreur:
        print(f"Discord injoignable : {erreur}")
    return None


# ---------- Programme principal ----------

def main():
    url_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url_webhook:
        print("Pas de variable DISCORD_WEBHOOK_URL : alertes Discord ignorées.")
        return

    connexion = ouvrir_base()
    articles = lire_articles_a_envoyer(connexion)

    envoyes = 0
    for numero, article in enumerate(articles, start=1):
        if numero > 1:
            time.sleep(PAUSE_ENTRE_MESSAGES)

        carte = creer_carte(article)
        carte["footer"] = {"text": "Réagis avec ⭐ pour l'ajouter à tes favoris"}
        message_envoye = envoyer_sur_discord(url_webhook, {"username": "Veille IA", "embeds": [carte]})
        if message_envoye is None:
            break  # Discord a un problème : on réessaiera au prochain lancement

        # On garde l'identifiant du message et du salon, pour lire les réactions plus tard,
        # et on note l'article comme envoyé pour ne jamais le renvoyer
        connexion.execute(
            """
            UPDATE articles
            SET alerte_envoyee = 1, discord_message_id = ?, discord_canal_id = ?
            WHERE id = ?
            """,
            (message_envoye["id"], message_envoye["channel_id"], article["id"]),
        )
        connexion.commit()
        envoyes += 1

    if articles:
        print(f"{envoyes} article(s) envoyé(s) sur Discord.")
    else:
        print("Aucun nouvel article important à envoyer sur Discord.")
    connexion.close()


if __name__ == "__main__":
    main()
