"""
=============================================================
 Recherche rapide dans la base (version provisoire)
=============================================================
En attendant le site web de l'étape 3, ce petit script permet
de retrouver un article en quelques secondes.

Exemples :
    python chercher.py              -> les 10 derniers articles
    python chercher.py agent        -> les articles qui parlent d'"agent"
    python chercher.py "open source"
=============================================================
"""

import sqlite3
import sys
from pathlib import Path

FICHIER_BDD = Path(__file__).parent / "data" / "veille.db"


def main():
    if not FICHIER_BDD.exists():
        print("La base n'existe pas encore. Lance d'abord : python collecte.py")
        return

    connexion = sqlite3.connect(FICHIER_BDD)

    # sys.argv contient ce qu'on a tapé après "python chercher.py"
    if len(sys.argv) > 1:
        mot = " ".join(sys.argv[1:])
        print(f'Recherche de "{mot}"...\n')
        # LIKE '%mot%' = "contient le mot", sans tenir compte des majuscules
        articles = connexion.execute(
            """
            SELECT titre, source, date_publication, url FROM articles
            WHERE titre LIKE ? OR description LIKE ?
            ORDER BY date_publication DESC
            LIMIT 20
            """,
            (f"%{mot}%", f"%{mot}%"),
        ).fetchall()
    else:
        print("Les 10 derniers articles :\n")
        articles = connexion.execute(
            """
            SELECT titre, source, date_publication, url FROM articles
            ORDER BY date_publication DESC
            LIMIT 10
            """
        ).fetchall()

    connexion.close()

    if not articles:
        print("Aucun article trouvé.")
        return

    for titre, source, date, url in articles:
        jour = date[:10] if date else "date inconnue"
        print(f"- [{jour}] {titre}")
        print(f"  {source} | {url}\n")

    print(f"{len(articles)} article(s) affiché(s).")


if __name__ == "__main__":
    main()
