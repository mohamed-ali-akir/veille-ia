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
     et les articles trop anciens (plus de 30 jours)

Pour le lancer :  py collecte.py   (Windows)
                  python collecte.py   (Linux / GitHub Actions)
=============================================================
"""

import html
import re
import socket
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser  # bibliothèque qui sait lire les flux RSS
import yaml        # bibliothèque qui sait lire le fichier sources.yml

from base import ouvrir_base  # notre module partagé (base.py)


# ---------- Réglages ----------

# Fichier qui contient la liste des sources
FICHIER_SOURCES = Path(__file__).parent / "sources.yml"

# "Carte d'identité" envoyée aux sites. Certains sites, comme Reddit,
# refusent les programmes qui ne se présentent pas.
USER_AGENT = "VeilleIA/1.0 (projet etudiant BTS SIO)"

# On ignore les articles publiés il y a plus de X jours.
# Sans cette limite, certains flux (OpenAI, Hugging Face) envoient
# toutes leurs archives : plus de 2000 vieux articles !
AGE_MAX_JOURS = 30

# Pause (en secondes) entre deux sources, pour ne pas être bloqué
# par les sites qui limitent les requêtes trop rapides (Reddit)
PAUSE_ENTRE_SOURCES = 1

# Temps maximum (en secondes) pour attendre la réponse d'un site.
# Sans ça, un site en panne pourrait bloquer le script indéfiniment.
socket.setdefaulttimeout(20)


# ---------- Fonctions ----------

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


def est_trop_ancien(date_texte):
    """Renvoie True si l'article a été publié il y a plus de AGE_MAX_JOURS."""
    if date_texte is None:
        return False  # date inconnue : on garde l'article par prudence
    date = datetime.fromisoformat(date_texte)
    limite = datetime.now(timezone.utc) - timedelta(days=AGE_MAX_JOURS)
    return date < limite


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

        date = date_de_publication(entree)
        if est_trop_ancien(date):
            continue  # article trop vieux, on passe au suivant

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
                date,
                maintenant,
                nettoyer_texte(entree.get("summary")),
            ),
        )
        nouveaux += curseur.rowcount  # 1 si ajouté, 0 si déjà présent

    connexion.commit()
    return nouveaux


# ---------- Programme principal ----------

def main():
    connexion = ouvrir_base()

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
        time.sleep(PAUSE_ENTRE_SOURCES)

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
