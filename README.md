# Veille IA

Outil de veille technologique automatisée sur l'intelligence artificielle,
réalisé dans le cadre du BTS SIO option SLAM.

## Fonctionnement

1. **Récupérer** : `collecte.py` lit les flux RSS listés dans `sources.yml`.
2. **Stocker** : les articles sont enregistrés dans une base SQLite (`data/veille.db`), sans doublons.
3. **Trier** *(étape 2, à venir)* : filtre par mots-clés, résumé, tags et note par une IA.
4. **Retrouver** *(étape 3, à venir)* : site web avec recherche instantanée.

## Utilisation

```bash
pip install -r requirements.txt   # installe les bibliothèques (une seule fois)
python collecte.py                # récupère les nouveaux articles
python chercher.py                # affiche les 10 derniers articles
python chercher.py agent          # cherche les articles contenant "agent"
```

## Ajouter une source

Ouvre `sources.yml` et ajoute un bloc :

```yaml
  - nom: Nom du site
    url: https://adresse-du-flux-rss
    categorie: Actualité FR
```
