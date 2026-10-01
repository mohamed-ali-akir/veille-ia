"""
=============================================================
 ÉTAPE 1 : RÉCUPÉRER et STOCKER les articles
=============================================================
Ce script :
  1. lit la liste des sources dans le fichier sources.yml
  2. télécharge le flux RSS de chaque source
  3. enregistre chaque nouvel article dans une base SQLite
     (data/veille.db)
  4. ignore les articles déjà enregistrés (pas de doublons)

Pour le lancer :  python collecte.py
=============================================================
"""

import html
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import feedparser  # bibliothèque qui sait lire les flux RSS
import yaml        # bibliothèque qui sait lire le fichier sources.yml


# ---------- Réglages ----------

# Dossier où se trouve ce script
DOSSIER = Path(__file__).parent

# Fichier qui contient la liste des sources
FICHIER_SOURCES = DOSSIER / "sources.yml"

# Fichier de la base de données (créé automatiquement)
FICHIER_BDD = DOSSIER / "data" / "veille.db"

# "Carte d'identité" envoyée aux sites. Certains sites, comme Reddit,
# refusent les programmes qui ne se présentent pas.
USER_AGENT = "VeilleIA/1.0 (projet etudiant BTS SIO)"


# ---------- Fonctions ----------

def creer_base(connexion):
    """Crée la table 'articles' si elle n'existe pas encore."""
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            titre            TEXT NOT NULL,
            url              TEXT NOT NULL UNIQUE,  -- UNIQUE = pas de doublon
            source           TEXT NOT NULL,
            categorie        TEXT,
            date_publication TEXT,
            date_collecte    TEXT NOT NULL,
            description      TEXT,

            -- Colonnes vides pour l'instant,
            -- elles seront remplies à l'étape 2 (tri et IA)
            mots_cles        TEXT,
            tags             TEXT,
            resume           TEXT,
            note             INTEGER
        )
    """)
    connexion.commit()


def charger_sources():
    """Lit le fichier sources.yml et renvoie la liste des sources."""
    with open(FICHIER_SOURCES, encoding="utf-8") as fichier:
        contenu = yaml.safe_load(fichier)
    return contenu["sources"]


def nettoyer_texte(texte):
    """Enlève les balises HTML d'un texte et le raccourcit."""
    if not texte:
        return None
    texte = re.sub(r"<[^>]+>", " ", texte)   # supprime les balises <...>
    texte = html.unescape(texte)             # transforme &amp; en &, etc.
    texte = re.sub(r"\s+", " ", texte).strip()  # supprime les espaces en trop
    return texte[:1000]                      # garde 1000 caractères maximum


def date_de_publication(entree):
    """Renvoie la date de publication de l'article au format texte."""
    date = entree.get("published_parsed") or entree.get("updated_parsed")
    if date:
        return datetime(*date[:6], tzinfo=timezone.utc).isoformat()
    return None


def collecter_source(connexion, source):
    """
    Télécharge le flux d'une source et enregistre ses nouveaux articles.
    Renvoie le nombre de nouveaux articles, ou None en cas d'erreur.
    """
    flux = feedparser.parse(source["url"], agent=USER_AGENT)

    # Si le flux n'a renvoyé aucun article, c'est qu'il y a un problème
    if not flux.entries:
        return None

    nouveaux = 0
    maintenant = datetime.now(timezone.utc).isoformat()

    for entree in flux.entries:
        url = entree.get("link")
        titre = entree.get("title")
        if not url or not titre:
            continue  # article incomplet, on passe au suivant

        # "INSERT OR IGNORE" : si l'URL existe déjà, SQLite ignore l'article
        curseur = connexion.execute(
            """
            INSERT OR IGNORE INTO articles
                (titre, url, source, categorie,
                 date_publication, date_collecte, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nettoyer_texte(titre),
                url,
                source["nom"],
                source.get("categorie"),
                date_de_publication(entree),
                maintenant,
                nettoyer_texte(entree.get("summary")),
            ),
        )
        nouveaux += curseur.rowcount  # 1 si ajouté, 0 si déjà présent

    connexion.commit()
    return nouveaux


# ---------- Programme principal ----------

def main():
    # Crée le dossier "data" s'il n'existe pas
    FICHIER_BDD.parent.mkdir(exist_ok=True)

    connexion = sqlite3.connect(FICHIER_BDD)
    creer_base(connexion)

    sources = charger_sources()
    print(f"Collecte de {len(sources)} sources...\n")

    total_nouveaux = 0
    sources_en_erreur = []

    for source in sources:
        resultat = collecter_source(connexion, source)
        if resultat is None:
            print(f"  [ERREUR] {source['nom']} : flux introuvable ou vide")
            sources_en_erreur.append(source["nom"])
        else:
            print(f"  [OK]     {source['nom']} : {resultat} nouvel(s) article(s)")
            total_nouveaux += resultat

    total_base = connexion.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    connexion.close()

    print("\n----------------------------------------")
    print(f"Nouveaux articles ajoutés : {total_nouveaux}")
    print(f"Total dans la base        : {total_base}")
    if sources_en_erreur:
        print(f"Sources à vérifier        : {', '.join(sources_en_erreur)}")
    print("----------------------------------------")


# Lance main() seulement si on exécute ce fichier directement
if __name__ == "__main__":
    main()
