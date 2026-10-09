"""
=============================================================
 Recherche rapide dans la base (en ligne de commande)
=============================================================
Le site web est l'outil principal pour retrouver un article.
Ce petit script reste utile comme solution de secours
(par exemple si internet ne marche pas pendant la démo).

Exemples :
    py chercher.py              -> les 10 derniers articles pertinents
    py chercher.py agent        -> les articles qui parlent d'"agent"
    py chercher.py "open source"
=============================================================
"""

import sys

from base import FICHIER_BDD, ouvrir_base


def main():
    if not FICHIER_BDD.exists():
        print("La base n'existe pas encore. Lance d'abord : py collecte.py")
        return

    connexion = ouvrir_base()

    # sys.argv contient ce qu'on a tapé après "py chercher.py"
    if len(sys.argv) > 1:
        mot = " ".join(sys.argv[1:])
        print(f'Recherche de "{mot}"...\n')
        motif = f"%{mot}%"  # LIKE '%mot%' = "contient le mot"
        articles = connexion.execute(
            """
            SELECT titre, source, date_publication, url, note, resume FROM articles
            WHERE (note IS NULL OR note >= 1)
              AND (titre LIKE ? OR description LIKE ? OR resume LIKE ? OR tags LIKE ?)
            ORDER BY date_publication DESC
            LIMIT 20
            """,
            (motif, motif, motif, motif),
        ).fetchall()
    else:
        print("Les 10 derniers articles pertinents :\n")
        articles = connexion.execute(
            """
            SELECT titre, source, date_publication, url, note, resume FROM articles
            WHERE note >= 1
            ORDER BY date_publication DESC
            LIMIT 10
            """
        ).fetchall()

    connexion.close()

    if not articles:
        print("Aucun article trouvé.")
        return

    for article in articles:
        jour = (article["date_publication"] or "date inconnue")[:10]
        note = f"{article['note']}/5" if article["note"] else "pas encore noté"
        print(f"- [{jour}] {article['titre']}  ({note})")
        if article["resume"]:
            print(f"  {article['resume']}")
        print(f"  {article['source']} | {article['url']}\n")

    print(f"{len(articles)} article(s) affiché(s).")


if __name__ == "__main__":
    main()
