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

Le script écrit aussi docs/flux.xml : un flux RSS des articles
importants (4 et 5 étoiles). Ma veille devient elle-même une
source qu'on peut suivre dans n'importe quel lecteur RSS !

Pour le lancer :  py generer_site.py
=============================================================
"""

import json
import xml.etree.ElementTree as ET  # bibliothèque XML intégrée à Python
from datetime import datetime, timezone
from email.utils import format_datetime  # format de date imposé par le RSS
from pathlib import Path

from base import ouvrir_base


# ---------- Réglages ----------

FICHIER_JSON = Path(__file__).parent / "docs" / "articles.json"
FICHIER_FLUX = Path(__file__).parent / "docs" / "flux.xml"

URL_SITE = "https://mohamed-ali-akir.github.io/veille-ia/"

# Le flux RSS contient seulement les articles importants, les plus récents
NOTE_MINIMALE_FLUX = 4
NOMBRE_ARTICLES_FLUX = 30


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
               date_collecte, tags, mots_cles, resume, note, justification
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
            "justification": ligne["justification"],
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


def creer_flux_rss(articles):
    """
    Fabrique le flux RSS (format XML) des articles importants.
    ElementTree échappe automatiquement les caractères spéciaux
    (< > &) : un titre bizarre ne peut pas "casser" le fichier XML.
    """
    rss = ET.Element("rss", version="2.0")
    canal = ET.SubElement(rss, "channel")
    ET.SubElement(canal, "title").text = "Veille IA : les articles importants"
    ET.SubElement(canal, "link").text = URL_SITE
    ET.SubElement(canal, "description").text = (
        "Actualité de l'intelligence artificielle pour les développeurs, "
        "résumée et notée par une IA (articles notés 4 ou 5 sur 5).")
    ET.SubElement(canal, "language").text = "fr"
    ET.SubElement(canal, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))

    importants = [article for article in articles if article["note"] >= NOTE_MINIMALE_FLUX]
    for article in importants[:NOMBRE_ARTICLES_FLUX]:
        etoiles = "★" * article["note"] + "☆" * (5 - article["note"])
        item = ET.SubElement(canal, "item")
        ET.SubElement(item, "title").text = article["titre"]
        ET.SubElement(item, "link").text = article["url"]
        # guid = identifiant unique : les lecteurs RSS s'en servent contre les doublons
        ET.SubElement(item, "guid").text = article["url"]
        ET.SubElement(item, "pubDate").text = format_datetime(
            datetime.fromisoformat(article["date"]))
        ET.SubElement(item, "description").text = (
            f"{article['resume']}\n\n{etoiles} · {article['source']}")
        for tag in article["tags"]:
            ET.SubElement(item, "category").text = tag

    ET.indent(rss)  # met en forme le XML (retours à la ligne, indentation)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode")


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
        # ensure_ascii=False : garde les accents lisibles (é au lieu de \u00e9)
        json.dump(donnees, fichier, ensure_ascii=False, indent=1)

    FICHIER_FLUX.write_text(creer_flux_rss(articles), encoding="utf-8")

    print(f"{len(articles)} article(s) exporté(s) dans {FICHIER_JSON.name}")
    print(f"Flux RSS mis à jour : {FICHIER_FLUX.name}")
    print(f"Statistiques : {statistiques}")


if __name__ == "__main__":
    main()
