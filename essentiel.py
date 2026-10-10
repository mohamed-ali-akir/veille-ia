"""
=============================================================
 BONUS : L'ESSENTIEL DE LA SEMAINE
=============================================================
Tous les 7 jours, l'IA lit les articles les mieux notés des
7 derniers jours et écrit une synthèse en 5 points.
Chaque point renvoie vers l'article d'origine : on peut
toujours vérifier ce que l'IA affirme.

La synthèse est :
  - enregistrée dans la base (table "essentiels"),
  - affichée en haut du site (exportée par generer_site.py),
  - envoyée sur Discord (si DISCORD_WEBHOOK_URL existe).

Pour le lancer :  py essentiel.py           -> seulement si la dernière
                                               synthèse a plus de 7 jours
                  py essentiel.py --forcer  -> tout de suite (pour la démo)
=============================================================
"""

import json
import os
import sys
import urllib.error
from datetime import datetime, timedelta, timezone

from alerte_discord import URL_SITE, envoyer_sur_discord
from base import ouvrir_base
from ia import choisir_ia


# ---------- Réglages ----------

# Une synthèse tous les X jours, qui résume les X derniers jours
JOURS = 7

# Articles donnés à l'IA : les mieux notés de la période
NOTE_MINIMALE = 3
MAX_ARTICLES = 25

# Nombre de points dans la synthèse
NOMBRE_POINTS = 5

# Format de réponse IMPOSÉ à l'IA (utilisé par Gemini)
SCHEMA_ESSENTIEL = {
    "type": "OBJECT",
    "properties": {
        "introduction": {"type": "STRING"},
        "points": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "texte": {"type": "STRING"},
                    "id": {"type": "INTEGER"},
                },
                "required": ["texte", "id"],
            },
        },
    },
    "required": ["introduction", "points"],
}


# ---------- Fonctions ----------

def derniere_synthese_recente(connexion):
    """Renvoie True si la dernière synthèse a été écrite il y a moins de JOURS jours."""
    derniere = connexion.execute(
        "SELECT date_creation FROM essentiels ORDER BY date_creation DESC LIMIT 1"
    ).fetchone()
    if derniere is None:
        return False
    # Marge de 2 heures : les lancements automatiques n'ont jamais lieu
    # exactement à la même minute d'une semaine à l'autre
    limite = datetime.now(timezone.utc) - timedelta(days=JOURS) + timedelta(hours=2)
    return datetime.fromisoformat(derniere["date_creation"]) > limite


def lire_articles(connexion, debut):
    """Renvoie les articles les mieux notés publiés depuis la date de début."""
    return connexion.execute(
        """
        SELECT id, titre, url, source, note, resume FROM articles
        WHERE note >= ? AND COALESCE(date_publication, date_collecte) >= ?
        ORDER BY note DESC, date_publication DESC
        LIMIT ?
        """,
        (NOTE_MINIMALE, debut.isoformat(), MAX_ARTICLES),
    ).fetchall()


def construire_consigne(articles):
    """Écrit la consigne envoyée à l'IA, avec la liste numérotée des articles."""
    liste = "\n".join(
        f"[{article['id']}] {article['titre']} ({article['source']}, "
        f"note {article['note']}/5) : {article['resume']}"
        for article in articles
    )
    return f"""Tu aides un étudiant en BTS SIO option SLAM (développement d'applications)
à faire sa veille technologique sur l'intelligence artificielle.

Voici les articles les plus importants des {JOURS} derniers jours, chacun avec son numéro entre crochets.
Écris « L'essentiel de la semaine » et réponds UNIQUEMENT avec un objet JSON contenant :
- "introduction" : une ou deux phrases en français sur la grande tendance de la semaine ;
- "points" : exactement {NOMBRE_POINTS} objets, du plus important au moins important, avec :
    "texte" : une ou deux phrases en français qui expliquent le sujet et pourquoi il compte pour un développeur ;
    "id" : le numéro de l'article qui parle de ce sujet.
Si plusieurs articles parlent du même sujet, fais-en un seul point.
N'invente rien : utilise seulement les informations des articles ci-dessous.

{liste}"""


def valider_essentiel(resultat, articles_par_id):
    """
    Vérifie la réponse de l'IA. Chaque point doit renvoyer vers un article
    qu'on lui a VRAIMENT donné : un numéro inventé est supprimé.
    Renvoie un dictionnaire propre, ou None si la réponse est inutilisable.
    """
    if not isinstance(resultat, dict):
        return None

    introduction = resultat.get("introduction")
    if not isinstance(introduction, str) or not introduction.strip():
        return None

    points = []
    ids_utilises = []
    for point in resultat.get("points") or []:
        if not isinstance(point, dict):
            continue
        texte = point.get("texte")
        try:
            numero = int(point.get("id"))
        except (TypeError, ValueError):
            continue
        # Texte vide, article inconnu ou déjà utilisé : on ignore ce point
        if not isinstance(texte, str) or not texte.strip():
            continue
        if numero not in articles_par_id or numero in ids_utilises:
            continue

        article = articles_par_id[numero]
        ids_utilises.append(numero)
        points.append({
            "texte": texte.strip()[:400],
            "id": numero,
            "titre": article["titre"],
            "url": article["url"],
            "source": article["source"],
        })

    # Moins de 3 points valables : la synthèse n'est pas assez fiable
    if len(points) < 3:
        return None
    return {"introduction": introduction.strip()[:400], "points": points[:NOMBRE_POINTS]}


def creer_message_discord(essentiel, debut, fin):
    """Transforme la synthèse en message Discord (une grande carte)."""
    lignes = [essentiel["introduction"], ""]
    for numero, point in enumerate(essentiel["points"], start=1):
        # [texte](adresse) = lien cliquable dans Discord
        lignes.append(f"**{numero}.** {point['texte']} [→ {point['source']}]({point['url']})")
    return {
        "username": "Veille IA",
        "embeds": [{
            "title": "📰 L'essentiel de la semaine IA",
            "url": URL_SITE,
            "description": "\n".join(lignes)[:4000],  # limite Discord : 4096 caractères
            "color": 0x3B5BDB,
            "footer": {"text": f"Du {debut:%d/%m} au {fin:%d/%m/%Y} · résumé écrit par une IA"},
        }],
    }


# ---------- Programme principal ----------

def main():
    forcer = "--forcer" in sys.argv
    connexion = ouvrir_base()

    if not forcer and derniere_synthese_recente(connexion):
        print(f"La dernière synthèse a moins de {JOURS} jours : rien à faire.")
        connexion.close()
        return

    nom_ia, appeler_ia, cle = choisir_ia()
    if appeler_ia is None:
        print("Aucune clé d'API trouvée : synthèse de la semaine ignorée.")
        connexion.close()
        return

    fin = datetime.now(timezone.utc)
    debut = fin - timedelta(days=JOURS)
    articles = lire_articles(connexion, debut)
    if len(articles) < NOMBRE_POINTS:
        print(f"Seulement {len(articles)} article(s) noté(s) {NOTE_MINIMALE}+ : pas de synthèse.")
        connexion.close()
        return

    print(f"Synthèse de {len(articles)} articles avec {nom_ia}...")
    try:
        resultat = appeler_ia(construire_consigne(articles), cle, SCHEMA_ESSENTIEL)
    except urllib.error.HTTPError as erreur:
        print(f"Erreur de l'API ({erreur.code}) : synthèse reportée au prochain lancement.")
        connexion.close()
        return
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError,
            json.JSONDecodeError) as erreur:
        print(f"Erreur : {erreur}. Synthèse reportée au prochain lancement.")
        connexion.close()
        return

    essentiel = valider_essentiel(resultat, {article["id"]: article for article in articles})
    if essentiel is None:
        print("Réponse de l'IA invalide : synthèse reportée au prochain lancement.")
        connexion.close()
        return

    connexion.execute(
        """
        INSERT INTO essentiels (date_creation, debut, fin, introduction, points)
        VALUES (?, ?, ?, ?, ?)
        """,
        (fin.isoformat(), debut.isoformat(), fin.isoformat(), essentiel["introduction"],
         json.dumps(essentiel["points"], ensure_ascii=False)),
    )
    connexion.commit()
    connexion.close()

    print(f"\n{essentiel['introduction']}\n")
    for numero, point in enumerate(essentiel["points"], start=1):
        print(f"  {numero}. {point['texte']}\n     -> {point['source']}")

    url_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if url_webhook and envoyer_sur_discord(url_webhook, creer_message_discord(essentiel, debut, fin)):
        print("\nSynthèse envoyée sur Discord.")


if __name__ == "__main__":
    main()
