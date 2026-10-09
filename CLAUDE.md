# CLAUDE.md — Projet « Veille IA »

Ce fichier donne à Claude Code tout le contexte du projet. Il est lu automatiquement
au démarrage de chaque session. **Mets à jour la section « Journal de progression »
à la fin de chaque séance de travail.**

---

## 1. Qui je suis et comment m'aider

- Étudiant en **BTS SIO 2e année, option SLAM** (développement).
- Ce projet est ma **veille technologique** pour l'épreuve du BTS : je devrai l'expliquer
  et la défendre devant un jury. Je dois donc **comprendre chaque ligne de code**.
- **Débutant en Python.**
- Je travaille **à la maison** et **au lycée**, toujours dans **GitHub Codespaces**.

Règles pour m'aider :
1. **Réponds et commente le code en français**, avec des mots simples.
2. **Explique ce que tu fais et pourquoi** avant de modifier un fichier, puis résume
   après coup ce qui a changé. Avance par petites étapes que je peux tester.
3. Garde le code **simple et lisible** : pas d'abstraction inutile, pas de framework
   lourd, noms de variables et de fonctions en français (comme dans le code existant).
4. **Teste** ce que tu écris (lance les scripts) avant de dire que c'est fini.
5. Après chaque étape terminée, propose-moi le **commit git** avec un message clair,
   et indique **ce que je dois savoir expliquer au jury** sur cette étape.
6. **Ne mets jamais de secret** (clé API, mot de passe, webhook) dans un fichier du dépôt :
   le dépôt est **public**. Les secrets passent par des variables d'environnement.
7. Si une demande est ambiguë ou a plusieurs solutions possibles, **pose-moi la question**
   au lieu de deviner.

## 2. Contraintes techniques importantes

- **Au lycée, le réseau passe par un proxy avec authentification (erreur 407)** :
  Python et pip ne peuvent pas accéder à internet depuis le PC du lycée. C'est pour ça
  que tout se fait dans **GitHub Codespaces** (le code tourne sur les serveurs de GitHub).
  Ne propose pas de contourner le proxy du lycée.
- Environnement : Codespaces = Linux, Python 3, commande `python`.
- **100 % gratuit** : aucun service payant, aucune carte bancaire.
- IA : **API Gemini, offre gratuite** (modèle `gemini-flash-lite-latest`), quotas limités
  (requêtes par minute et par jour). Toujours gérer l'erreur 429 proprement.
- Le dépôt est public : la base `data/veille.db` est **volontairement versionnée**
  (nécessaire pour l'automatisation de l'étape 4).

## 3. Objectif du projet

Une veille sur **l'intelligence artificielle** (point de vue développeur / SLAM) qui doit :

1. **Récupérer** automatiquement des articles (flux RSS)
2. **Trier** (mots-clés + analyse IA : résumé, tags, note de pertinence)
3. **Stocker** (base SQLite)
4. **Retrouver n'importe quel article en moins de 30 secondes** (site web avec recherche instantanée)

Et **impressionner le jury** : démonstration prévue = le jury donne un mot-clé,
je le tape dans la barre de recherche et l'article apparaît avec son résumé et ses tags.

## 4. Architecture actuelle

```
veille-ia/
├── CLAUDE.md          ce fichier
├── README.md          présentation du projet
├── requirements.txt   bibliothèques : feedparser, pyyaml
├── .gitignore
├── sources.yml        liste des flux RSS (nom, url, categorie)
├── mots_cles.yml      mots-clés du filtre (liste "mots_cles")
├── collecte.py        ÉTAPE 1 : récupère les flux RSS → SQLite (sans doublons)
├── tri.py             ÉTAPE 2 : filtre mots-clés puis analyse Gemini
├── chercher.py        recherche en ligne de commande (provisoire)
└── data/veille.db     base SQLite (créée par collecte.py)
```

### Table `articles` (SQLite)

| Colonne | Contenu |
|---|---|
| id | clé primaire auto-incrémentée |
| titre | titre nettoyé |
| url | **UNIQUE** → évite les doublons (`INSERT OR IGNORE`) |
| source, categorie | viennent de `sources.yml` |
| date_publication | ISO 8601 UTC (peut être NULL) |
| date_collecte | ISO 8601 UTC |
| description | extrait nettoyé du HTML, 1000 caractères max |
| mots_cles | NULL = pas encore filtré ; `''` = hors sujet ; sinon liste séparée par `, ` |
| tags | tags IA séparés par `, `, pris dans une **liste fixe** (`TAGS_AUTORISES` dans tri.py) |
| resume | résumé IA en français (NULL = pas encore analysé) |
| note | 0 = hors sujet ; 1 à 5 = pertinence donnée par l'IA ; NULL = pas encore noté |

### Fonctionnement de `tri.py`
- **Phase 1** : cherche les mots de `mots_cles.yml` (regex avec `\b`, insensible à la casse)
  dans titre + description. Aucun mot → `mots_cles = ''` et `note = 0`.
- **Phase 2** : pour les articles gardés sans résumé, appel à Gemini (REST via `urllib`,
  clé dans l'en-tête `x-goog-api-key`, réponse JSON imposée par `responseSchema`).
  `valider_resultat()` vérifie la réponse (tags hors liste supprimés, note ramenée entre 1 et 5).
  Max 40 articles par lancement, pause de 5 s entre deux appels, arrêt propre sur 429.
- La clé est lue dans la variable d'environnement **`GEMINI_API_KEY`**
  (secret Codespaces ; pour GitHub Actions ce sera un secret de dépôt séparé).

### Conventions du code existant
- Commentaires et noms en français, docstring en tête de chaque script expliquant son rôle.
- Requêtes SQL **toujours paramétrées** (`?`) → protection contre l'injection SQL.
- Configuration dans des fichiers YAML séparés du code.
- Réglages modifiables regroupés en haut de chaque script.

## 5. Feuille de route

### ✅ Étape 1 — Récupérer + stocker (`collecte.py`) — code écrit et testé
### ✅ Étape 2 — Trier (`tri.py`) — code écrit et testé avec une fausse IA
À vérifier en conditions réelles avec la vraie clé Gemini (voir journal).

### ⬜ Étape 3 — Retrouver : site web avec recherche instantanée
Idée prévue (à valider avec moi) :
- Script `generer_site.py` qui exporte les articles pertinents (note > 0) de la base
  vers `docs/articles.json` et génère `docs/index.html`.
- Site **statique** (HTML + CSS + JavaScript sans framework), publié avec **GitHub Pages**
  depuis le dossier `docs/`.
- **Recherche instantanée** pendant la frappe (titre, résumé, tags, mots-clés, source),
  filtres par **tag**, **source**, **période** et **note minimale**, tri par date ou par note.
- Chaque article : titre cliquable, source, date, étoiles, tags, résumé.
- Une page ou section **« Méthodologie »** : sources, fréquence, fonctionnement, schéma.
- Responsive (lisible sur téléphone), propre et sobre.

### ⬜ Étape 4 — Automatiser
- **GitHub Actions** : workflow planifié (cron, 1 fois par jour) qui lance
  `collecte.py` → `tri.py` → `generer_site.py`, puis commit/push de `data/veille.db` et `docs/`.
- Secret de dépôt `GEMINI_API_KEY` (Settings > Secrets and variables > Actions).
- Option : envoi sur un **webhook Discord** des articles notés 4 ou 5
  (secret `DISCORD_WEBHOOK_URL`).
- Bouton « Run workflow » manuel (`workflow_dispatch`) pour la démo.

### ⬜ Étape 5 — Préparer l'épreuve
- README complet avec schéma de l'architecture (Mermaid).
- Synthèses mensuelles de la veille (articles marquants + mon analyse).
- Liste des points techniques à savoir expliquer (SQLite, doublons, injection SQL,
  quotas API, validation des réponses de l'IA, secrets, CI/CD).

## 6. Commandes utiles

```bash
pip install -r requirements.txt   # installer les dépendances (nouveau Codespace)
python collecte.py                # récupérer les nouveaux articles
python tri.py                     # filtrer + analyser par l'IA
python chercher.py mot            # chercher un article
git add . && git commit -m "message" && git push   # sauvegarder sur GitHub
```

## 7. Journal de progression

> À mettre à jour à la fin de chaque séance (date, ce qui a été fait, ce qui reste,
> problèmes rencontrés). C'est ce qui permet de reprendre au lycée là où je me suis
> arrêté à la maison, et inversement.

- **01/10/2026** — Étapes 1 et 2 écrites et testées (hors ligne). Problème du proxy du lycée
  (erreur 407) → passage à GitHub Codespaces.
- **10/10/2026** — Reprise à la maison avec Claude Code. État à vérifier en début de séance :
  dépôt créé ? fichiers des étapes 1 et 2 présents ? `python collecte.py` lancé ?
  clé Gemini créée et ajoutée en secret Codespaces ? `python tri.py` testé avec la vraie clé ?
