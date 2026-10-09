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

Pour le lancer :  py alerte_discord.py
=============================================================
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from base import ouvrir_base


# ---------- Réglages ----------

# Note minimale pour qu'un article soit envoyé
NOTE_MINIMALE = 4

# Discord accepte 10 "cartes" (embeds) maximum par message
MAX_ARTICLES = 10

# On n'envoie que les articles collectés depuis moins de X jours
# (évite d'envoyer de vieux articles la première fois)
AGE_MAX_JOURS = 2

# Adresse du site, ajoutée dans le message
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
    Les textes sont raccourcis : Discord refuse un message dont
    les cartes dépassent 6000 caractères au total.
    """
    etoiles = "★" * article["note"] + "☆" * (5 - article["note"])
    return {
        "title": article["titre"][:200],
        "url": article["url"],
        "description": (article["resume"] or "")[:300],
        "color": COULEURS.get(article["note"], 0x868E96),
        "fields": [
            {"name": "Note", "value": etoiles, "inline": True},
            {"name": "Source", "value": article["source"], "inline": True},
            {"name": "Tags", "value": article["tags"] or "-", "inline": True},
        ],
    }


def envoyer_message(url_webhook, articles):
    """Envoie un message avec une carte par article. Renvoie True si ça a marché."""
    message = {
        "username": "Veille IA",
        "content": f"**{len(articles)} article(s) important(s) dans la veille IA** · {URL_SITE}",
        "embeds": [creer_carte(article) for article in articles],
    }
    requete = urllib.request.Request(
        url_webhook,
        data=json.dumps(message).encode("utf-8"),
        # Discord refuse les requêtes sans "User-Agent" (carte d'identité du programme)
        headers={"Content-Type": "application/json",
                 "User-Agent": "VeilleIA/1.0 (projet etudiant BTS SIO)"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(requete, timeout=30):
            return True
    except urllib.error.HTTPError as erreur:
        print(f"Erreur Discord {erreur.code} : {erreur.read().decode()[:200]}")
    except urllib.error.URLError as erreur:
        print(f"Discord injoignable : {erreur}")
    return False


# ---------- Programme principal ----------

def main():
    url_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url_webhook:
        print("Pas de variable DISCORD_WEBHOOK_URL : alertes Discord ignorées.")
        return

    connexion = ouvrir_base()
    articles = lire_articles_a_envoyer(connexion)

    if not articles:
        print("Aucun nouvel article important à envoyer sur Discord.")
    elif envoyer_message(url_webhook, articles):
        # On note les articles comme envoyés pour ne jamais les renvoyer
        for article in articles:
            connexion.execute(
                "UPDATE articles SET alerte_envoyee = 1 WHERE id = ?", (article["id"],)
            )
        connexion.commit()
        print(f"{len(articles)} article(s) envoyé(s) sur Discord.")

    connexion.close()


if __name__ == "__main__":
    main()
