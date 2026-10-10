"""
=============================================================
 FAVORIS : synchroniser les réactions ⭐ de Discord
=============================================================
Sous chaque alerte Discord, je peux réagir avec ⭐ :
l'article devient alors un de mes favoris.

Ce script :
  1. lit les messages récents du salon des alertes,
  2. repère ceux qui ont une réaction ⭐,
  3. met à jour la colonne "favori" de la base
     (ajout si j'ai mis ⭐, retrait si je l'ai enlevée),
  4. recopie les nouveaux favoris dans le salon #favoris.
Le site affiche ensuite l'onglet "Favoris" (via generer_site.py).

Pourquoi un BOT ? Un webhook sait seulement ÉCRIRE dans un salon.
Pour LIRE les réactions, il faut un bot Discord avec un jeton
secret (DISCORD_BOT_TOKEN). Il n'a que deux droits : voir le
salon et lire l'historique (principe du moindre privilège).

Pour le lancer :  py favoris.py
=============================================================
"""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from alerte_discord import PAUSE_ENTRE_MESSAGES, creer_carte, envoyer_sur_discord
from base import ouvrir_base


# ---------- Réglages ----------

# L'emoji qui veut dire "favori"
EMOJI_FAVORI = "⭐"

# On regarde les messages des X derniers jours
FENETRE_JOURS = 30

# Sécurité : 10 pages de 100 messages maximum par salon
MAX_PAGES = 10

API_DISCORD = "https://discord.com/api/v10"

# Discord impose ce format de "User-Agent" pour les bots
USER_AGENT_BOT = "DiscordBot (https://github.com/mohamed-ali-akir/veille-ia, 1.0)"


# ---------- Fonctions ----------

def lire_messages(canal_id, jeton):
    """
    Lit les messages du salon, du plus récent au plus ancien, page par page
    (100 messages par page), jusqu'à dépasser FENETRE_JOURS.
    """
    limite = datetime.now(timezone.utc) - timedelta(days=FENETRE_JOURS)
    messages = []
    avant = None  # identifiant du dernier message lu (pour demander la page suivante)

    for _ in range(MAX_PAGES):
        url = f"{API_DISCORD}/channels/{canal_id}/messages?limit=100"
        if avant:
            url += f"&before={avant}"
        requete = urllib.request.Request(url, headers={
            "Authorization": f"Bot {jeton}",
            "User-Agent": USER_AGENT_BOT,
        })
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            page = json.load(reponse)

        for message in page:
            if datetime.fromisoformat(message["timestamp"]) < limite:
                return messages  # trop ancien : on s'arrête là
            messages.append(message)

        if len(page) < 100:
            break  # dernière page
        avant = page[-1]["id"]

    return messages


def a_une_etoile(message):
    """Renvoie True si le message a au moins une réaction ⭐."""
    for reaction in message.get("reactions", []):
        if reaction["emoji"]["name"] == EMOJI_FAVORI and reaction["count"] > 0:
            return True
    return False


def calculer_changements(messages, favori_par_message):
    """
    Compare les réactions Discord avec la base.
    favori_par_message : {identifiant du message: 0 ou 1} pour les articles envoyés.
    Renvoie deux listes d'identifiants de messages : (ajouts, retraits).
    """
    ajouts = []
    retraits = []
    for message in messages:
        if message["id"] not in favori_par_message:
            continue  # message qui n'est pas une alerte d'article (ex : synthèse)
        etoile = a_une_etoile(message)
        deja_favori = favori_par_message[message["id"]] == 1
        if etoile and not deja_favori:
            ajouts.append(message["id"])
        elif not etoile and deja_favori:
            retraits.append(message["id"])
    return ajouts, retraits


# ---------- Programme principal ----------

def main():
    jeton = os.environ.get("DISCORD_BOT_TOKEN")
    if not jeton:
        print("Pas de variable DISCORD_BOT_TOKEN : favoris Discord ignorés.")
        return

    connexion = ouvrir_base()
    lignes = connexion.execute(
        "SELECT discord_message_id, discord_canal_id, favori FROM articles "
        "WHERE discord_message_id IS NOT NULL"
    ).fetchall()
    favori_par_message = {ligne["discord_message_id"]: ligne["favori"] for ligne in lignes}
    canaux = {ligne["discord_canal_id"] for ligne in lignes}  # set = sans doublon

    ajouts = []
    retraits = []
    for canal_id in canaux:
        try:
            messages = lire_messages(canal_id, jeton)
        except urllib.error.HTTPError as erreur:
            # 401 = jeton invalide ; 403 = le bot n'a pas accès au salon
            print(f"Erreur Discord {erreur.code} : vérifie le jeton du bot "
                  "et qu'il a bien accès au salon des alertes.")
            connexion.close()
            return
        except urllib.error.URLError as erreur:
            print(f"Discord injoignable : {erreur}")
            connexion.close()
            return
        nouveaux, enleves = calculer_changements(messages, favori_par_message)
        ajouts += nouveaux
        retraits += enleves

    for message_id in ajouts:
        connexion.execute("UPDATE articles SET favori = 1 WHERE discord_message_id = ?", (message_id,))
    for message_id in retraits:
        connexion.execute("UPDATE articles SET favori = 0 WHERE discord_message_id = ?", (message_id,))
    connexion.commit()

    total = connexion.execute("SELECT COUNT(*) FROM articles WHERE favori = 1").fetchone()[0]
    print(f"Favoris : {len(ajouts)} ajouté(s), {len(retraits)} retiré(s), {total} au total.")

    # Recopie les nouveaux favoris dans le salon #favoris
    url_favoris = os.environ.get("DISCORD_WEBHOOK_FAVORIS")
    if url_favoris:
        for message_id in ajouts:
            article = connexion.execute(
                "SELECT titre, url, source, tags, resume, note FROM articles "
                "WHERE discord_message_id = ?", (message_id,)
            ).fetchone()
            envoyer_sur_discord(url_favoris, {"username": "Veille IA", "embeds": [creer_carte(article)]})
            time.sleep(PAUSE_ENTRE_MESSAGES)

    connexion.close()


if __name__ == "__main__":
    main()
