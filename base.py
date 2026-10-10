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
            justification    TEXT,     -- une phrase de l'IA : "pourquoi cette note ?"

            -- Colonnes remplies par alerte_discord.py
            alerte_envoyee   INTEGER NOT NULL DEFAULT 0,  -- 1 = déjà envoyé sur Discord
            discord_message_id TEXT,   -- identifiant du message Discord de l'alerte
            discord_canal_id   TEXT,   -- identifiant du salon où il a été envoyé

            -- Colonne remplie par favoris.py
            favori           INTEGER NOT NULL DEFAULT 0  -- 1 = réaction ⭐ sur Discord
        )
    """)

    # Synthèses "L'essentiel de la semaine" (remplie par essentiel.py)
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS essentiels (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            date_creation TEXT NOT NULL,
            debut         TEXT NOT NULL,  -- début de la période résumée
            fin           TEXT NOT NULL,  -- fin de la période résumée
            introduction  TEXT NOT NULL,  -- la grande tendance de la semaine
            points        TEXT NOT NULL   -- les points clés, au format JSON
        )
    """)

    # MIGRATION : "CREATE TABLE IF NOT EXISTS" ne modifie pas une table qui
    # existe déjà. Les colonnes ajoutées après coup doivent donc être
    # ajoutées à la main dans les bases existantes, avec ALTER TABLE.
    ajouter_colonne_si_absente(connexion, "articles", "justification", "TEXT")
    ajouter_colonne_si_absente(connexion, "articles", "discord_message_id", "TEXT")
    ajouter_colonne_si_absente(connexion, "articles", "discord_canal_id", "TEXT")
    ajouter_colonne_si_absente(connexion, "articles", "favori", "INTEGER NOT NULL DEFAULT 0")

    connexion.commit()
    return connexion


def ajouter_colonne_si_absente(connexion, table, colonne, type_sql):
    """Ajoute une colonne à une table, seulement si elle n'existe pas encore."""
    # PRAGMA table_info renvoie une ligne par colonne de la table
    colonnes = [ligne["name"] for ligne in connexion.execute(f"PRAGMA table_info({table})")]
    if colonne not in colonnes:
        connexion.execute(f"ALTER TABLE {table} ADD COLUMN {colonne} {type_sql}")
        print(f"Base mise à jour : colonne '{colonne}' ajoutée à la table '{table}'.")
