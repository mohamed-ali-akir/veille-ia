"""
=============================================================
 MODULE PARTAGÉ : la base de données SQLite
=============================================================
Tous les scripts du projet (collecte, tri, generer_site,
alerte_discord, chercher) ouvrent la base avec la fonction
ouvrir_base() de ce fichier.

Avantage : la structure de la table "articles" n'est écrite
qu'à UN SEUL endroit. Si on ajoute une colonne, on la
modifie ici et tous les scripts en profitent.
=============================================================
"""

import sqlite3
from pathlib import Path

# Fichier de la base de données (créé automatiquement)
FICHIER_BDD = Path(__file__).parent / "data" / "veille.db"


def ouvrir_base():
    """Ouvre la base (et la crée si besoin), puis renvoie la connexion."""
    # Crée le dossier "data" s'il n'existe pas
    FICHIER_BDD.parent.mkdir(exist_ok=True)

    connexion = sqlite3.connect(FICHIER_BDD)

    # Permet d'écrire article["titre"] au lieu de article[1]
    connexion.row_factory = sqlite3.Row

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

            -- Colonnes remplies par tri.py (étape 2)
            mots_cles        TEXT,     -- NULL = pas encore filtré, '' = hors sujet
            tags             TEXT,     -- tags choisis par l'IA, séparés par ", "
            resume           TEXT,     -- résumé en français écrit par l'IA
            note             INTEGER,  -- 0 = hors sujet, 1 à 5 = pertinence

            -- Colonne remplie par alerte_discord.py
            alerte_envoyee   INTEGER NOT NULL DEFAULT 0  -- 1 = déjà envoyé sur Discord
        )
    """)
    connexion.commit()
    return connexion
