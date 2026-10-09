"""
=============================================================
 ÉTAPE 3 : EXPORTER les articles pour le site web
=============================================================
Un navigateur ne sait pas lire une base SQLite.
Ce script transforme donc les articles pertinents (note >= 1)
en un fichier JSON : docs/articles.json

Le site (docs/index.html + style.css + app.js) est écrit une
fois pour toutes. Il lit ce fichier JSON et affiche les articles.
=> Séparation des DONNÉES (Python) et de la PRÉSENTATION (HTML/CSS/JS).

Pour le lancer :  py generer_site.py
=============================================================
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from base import ouvrir_base


# ---------- Réglages ----------

FICHIER_JSON = Path(__file__).parent / "docs" / "articles.json"


# ---------- Fonctions ----------

def en_liste(texte):
    """Transforme "LLM, Outils dev" en ["LLM", "Outils dev"]."""
    if not texte:
        return []
    return [morceau.strip() for morceau in texte.split(",") if morceau.strip()]


def lire_articles(connexion):
    """Renvoie la liste des articles à afficher sur le site."""
    lignes = connexion.execute(
        """
        SELECT id, titre, url, source, categorie, date_publication,
               date_collecte, tags, mots_cles, resume, note
        FROM articles
        WHERE note >= 1
        ORDER BY COALESCE(date_publication, date_collecte) DESC
        """
    ).fetchall()

    articles = []
    for ligne in lignes:
        articles.append({
            "id": ligne["id"],
            "titre": ligne["titre"],
            "url": ligne["url"],
            "source": ligne["source"],
            "categorie": ligne["categorie"],
            # Si la date de publication est inconnue, on prend la date de collecte
            "date": ligne["date_publication"] or ligne["date_collecte"],
            "collecte": ligne["date_collecte"],
            "tags": en_liste(ligne["tags"]),
            "mots_cles": en_liste(ligne["mots_cles"]),
            "resume": ligne["resume"],
            "note": ligne["note"],
        })
    return articles


def lire_statistiques(connexion):
    """Compte les articles à chaque étape (affiché sur la page Méthodologie)."""
    def compter(condition):
        return connexion.execute(
            f"SELECT COUNT(*) FROM articles WHERE {condition}"
        ).fetchone()[0]

    return {
        "collectes": compter("1 = 1"),
        "gardes_mots_cles": compter("mots_cles != ''"),
        "analyses_ia": compter("resume IS NOT NULL"),
        "affiches": compter("note >= 1"),
    }


# ---------- Programme principal ----------

def main():
    connexion = ouvrir_base()
    articles = lire_articles(connexion)
    statistiques = lire_statistiques(connexion)
    connexion.close()

    donnees = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "statistiques": statistiques,
        "articles": articles,
    }

    FICHIER_JSON.parent.mkdir(exist_ok=True)
    with open(FICHIER_JSON, "w", encoding="utf-8") as fichier:
        # ensure_ascii=False : garde les accents lisibles (é au lieu de é)
        json.dump(donnees, fichier, ensure_ascii=False, indent=1)

    print(f"{len(articles)} article(s) exporté(s) dans {FICHIER_JSON.name}")
    print(f"Statistiques : {statistiques}")


if __name__ == "__main__":
    main()
