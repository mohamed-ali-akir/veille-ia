"""
=============================================================
 ÉTAPE 5 : préparer la SYNTHÈSE MENSUELLE
=============================================================
Crée un brouillon de synthèse pour un mois donné dans le
dossier syntheses/ (format Markdown, lisible sur GitHub) :
  - les chiffres du mois,
  - les tags les plus fréquents (= les tendances),
  - les 10 articles les mieux notés,
  - une partie "Mon analyse" à compléter À LA MAIN.

Le script ne remplace jamais une synthèse existante,
pour ne pas effacer l'analyse déjà écrite.

Pour le lancer :  py synthese.py            -> mois en cours
                  py synthese.py 2026-10    -> mois choisi
=============================================================
"""

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from base import ouvrir_base


# ---------- Réglages ----------

DOSSIER_SYNTHESES = Path(__file__).parent / "syntheses"
NOMBRE_ARTICLES = 10

MOIS_EN_FRANCAIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                    "août", "septembre", "octobre", "novembre", "décembre"]


# ---------- Programme principal ----------

def main():
    # Mois demandé (ex : "2026-10"), sinon le mois en cours
    mois = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m")
    annee, numero_mois = mois.split("-")
    nom_du_mois = f"{MOIS_EN_FRANCAIS[int(numero_mois) - 1]} {annee}"

    fichier = DOSSIER_SYNTHESES / f"{mois}.md"
    if fichier.exists():
        print(f"{fichier.name} existe déjà : je ne l'écrase pas.")
        return

    connexion = ouvrir_base()
    # LIKE '2026-10%' = toutes les dates qui commencent par "2026-10"
    articles = connexion.execute(
        """
        SELECT titre, url, source, tags, resume, note FROM articles
        WHERE note >= 1 AND date_publication LIKE ?
        ORDER BY note DESC, date_publication DESC
        """,
        (f"{mois}%",),
    ).fetchall()
    connexion.close()

    if not articles:
        print(f"Aucun article pertinent pour {nom_du_mois}.")
        return

    # Compte combien de fois chaque tag apparaît
    compteur_tags = Counter()
    for article in articles:
        for tag in (article["tags"] or "").split(", "):
            if tag:
                compteur_tags[tag] += 1

    lignes = [
        f"# Synthèse de veille IA — {nom_du_mois}",
        "",
        f"**{len(articles)} articles pertinents** ce mois-ci, "
        f"dont **{sum(1 for a in articles if a['note'] >= 4)}** notés 4 ou 5.",
        "",
        "## Les tendances du mois (tags les plus fréquents)",
        "",
    ]
    for tag, nombre in compteur_tags.most_common(5):
        lignes.append(f"- **{tag}** : {nombre} articles")

    lignes += ["", f"## Les {NOMBRE_ARTICLES} articles marquants", ""]
    for article in articles[:NOMBRE_ARTICLES]:
        etoiles = "★" * article["note"] + "☆" * (5 - article["note"])
        lignes.append(f"### [{article['titre']}]({article['url']})")
        lignes.append(f"{etoiles} · {article['source']} · {article['tags']}")
        lignes.append("")
        lignes.append(article["resume"] or "")
        lignes.append("")

    lignes += [
        "## Mon analyse",
        "",
        "> À compléter : ce que je retiens de ce mois, ce qui change pour un",
        "> développeur, et mon avis personnel.",
        "",
    ]

    DOSSIER_SYNTHESES.mkdir(exist_ok=True)
    fichier.write_text("\n".join(lignes), encoding="utf-8")
    print(f"Brouillon créé : syntheses/{fichier.name} ({len(articles)} articles)")


if __name__ == "__main__":
    main()
