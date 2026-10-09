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
- Je travaille **chez moi, sur mon PC Windows** (plus besoin de Codespaces).

Règles pour m'aider :
1. **Réponds et commente le code en français**, avec des mots simples.
2. **Explique ce que tu fais et pourquoi** avant de modifier un fichier, puis résume
   après coup ce qui a changé. Avance par petites étapes que je peux tester.
3. Garde le code **simple et lisible** : pas d'abstraction inutile, pas de framework
   lourd, noms de variables et de fonctions en français (comme dans le code existant).
4. **Teste** ce que tu écris (lance les scripts et `py -m unittest -v tests`) avant de
   dire que c'est fini.
5. Après chaque étape terminée, propose-moi le **commit git** avec un message clair,
   et indique **ce que je dois savoir expliquer au jury** sur cette étape.
6. **Ne mets jamais de secret** (clé API, mot de passe, webhook) dans un fichier du dépôt :
   le dépôt est **public**. Les secrets passent par des variables d'environnement.
7. Si une demande est ambiguë ou a plusieurs solutions possibles, **pose-moi la question**
   au lieu de deviner.

## 2. Contraintes techniques importantes

- **PC Windows** : la commande Python est **`py`** (`python` ouvre le Microsoft Store).
  Python 3.12 et Git sont installés.
- Le code doit aussi marcher sous **Linux** (GitHub Actions) : toujours
  `open(..., encoding="utf-8")` et des chemins construits avec `pathlib`.
- **100 % gratuit** : aucun service payant, aucune carte bancaire.
- IA : **API Gemini, offre gratuite** (modèle `gemini-flash-lite-latest`), quotas limités.
  Toujours gérer l'erreur 429 proprement. **Mistral** (`mistral-small-latest`, offre
  gratuite) est prévu en secours si `MISTRAL_API_KEY` existe et pas `GEMINI_API_KEY`.
- Clés sur le PC : `setx NOM "valeur"` (variables d'environnement Windows de l'utilisateur).
  Clés pour GitHub Actions : Settings > Secrets and variables > Actions.
- Le dépôt est public : la base `data/veille.db` est **volontairement versionnée**
  (nécessaire pour l'automatisation). **Faire `git pull` avant de travailler**, car
  GitHub Actions modifie la base deux fois par jour (un fichier binaire ne se fusionne pas).

## 3. Objectif du projet

Une veille sur **l'intelligence artificielle** (point de vue développeur / SLAM) qui doit :

1. **Récupérer** automatiquement des articles (flux RSS)
2. **Trier** (mots-clés + analyse IA : résumé, tags, note de pertinence)
3. **Stocker** (base SQLite)
4. **Retrouver n'importe quel article en moins de 30 secondes** (site web avec recherche instantanée)

Et **impressionner le jury** : démonstration prévue = le jury donne un mot-clé,
je le tape dans la barre de recherche et l'article apparaît avec son résumé et ses tags.

## 4. Architecture

```
veille-ia/
├── CLAUDE.md, README.md, EPREUVE.md (préparation de l'oral)
├── requirements.txt   bibliothèques : feedparser, pyyaml
├── sources.yml        liste des flux RSS (nom, url, categorie)
├── mots_cles.yml      "mots_cles" (sans casse) + "sigles" (casse respectée : AI ≠ j'ai)
├── base.py            ouvrir_base() : connexion + CREATE TABLE (partagé par tous)
├── collecte.py        ÉTAPE 1 : flux RSS → SQLite (sans doublons, < 30 jours)
├── tri.py             ÉTAPE 2 : filtre mots-clés puis analyse IA (Gemini ou Mistral)
├── generer_site.py    ÉTAPE 3 : SQLite → docs/articles.json (note >= 1)
├── alerte_discord.py  BONUS : articles notés 4-5 → webhook Discord
├── chercher.py        recherche en ligne de commande (secours pour la démo)
├── tests.py           tests unittest (sans internet ni clé)
├── data/veille.db     base SQLite
├── docs/              site statique publié par GitHub Pages
│   ├── index.html, methodologie.html, style.css, app.js  (écrits à la main)
│   └── articles.json  (SEUL fichier généré)
└── .github/workflows/veille.yml   tests → collecte → tri → site → Discord → commit/push
```

**Choix d'architecture (option B, validée)** : Python ne génère que les données
(`articles.json`) ; le HTML/CSS/JS est écrit une fois. Séparation données / présentation.
La recherche se fait dans le navigateur (JavaScript), sans serveur.

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
| tags | tags IA séparés par `, `, pris dans `TAGS_AUTORISES` (tri.py) |
| resume | résumé IA en français (NULL = pas encore analysé) |
| note | 0 = hors sujet (mots-clés OU jugé par l'IA) ; 1 à 5 = pertinence ; NULL = pas encore noté |
| alerte_envoyee | 0/1 : déjà envoyé sur Discord |

### Fonctionnement de `tri.py`
- **Phase 1** : regex `\b` sur titre + description. `mots_cles` insensibles à la casse,
  `sigles` sensibles. Aucun mot → `mots_cles = ''` et `note = 0`.
- **Phase 2** : articles gardés sans résumé, les plus récents d'abord, 50 max par
  lancement, pause de 5 s, arrêt propre sur 429. Gemini : `responseSchema` impose le JSON.
  Mistral : `response_format: json_object`. `valider_resultat()` vérifie tout
  (tags hors liste supprimés, 3 max, note ramenée entre 0 et 5).

### Conventions du code
- Commentaires et noms en français, docstring en tête de chaque script expliquant son rôle.
- Requêtes SQL **toujours paramétrées** (`?`) → protection contre l'injection SQL.
- Site : texte inséré avec `textContent` (jamais `innerHTML`) → protection contre XSS.
- Configuration dans des fichiers YAML séparés du code ; réglages en haut de chaque script.

## 5. Feuille de route

- ✅ Étape 1 — Récupérer + stocker (`collecte.py`, `base.py`)
- ✅ Étape 2 — Trier (`tri.py`) — testé hors ligne ; **à tester avec la vraie clé Gemini**
- ✅ Étape 3 — Site (`generer_site.py`, `docs/`) — testé en local avec des données simulées
- ✅ Étape 4 — GitHub Actions + Discord — écrits ; **à activer** (secrets + GitHub Pages)
- ⬜ Étape 5 — Préparer l'épreuve : relire `EPREUVE.md`, synthèses mensuelles, répétition de la démo

## 6. Commandes utiles (PC Windows)

```bash
git pull                                # TOUJOURS en premier
py -m pip install -r requirements.txt   # installer les dépendances
py collecte.py                          # récupérer les nouveaux articles
py tri.py                               # filtrer + analyser par l'IA
py generer_site.py                      # mettre à jour le site
py alerte_discord.py                    # alertes Discord
py -m unittest -v tests                 # tests
py -m http.server --directory docs      # voir le site : http://localhost:8000
git add . && git commit -m "message" && git push
```

## 7. Journal de progression

- **01/10/2026** — `collecte.py`, `chercher.py`, `sources.yml` écrits (dans Codespaces,
  à cause du proxy du lycée, erreur 407).
- **10/10/2026** — Séance avec Claude Code sur le PC (Codespaces abandonné).
  - `base.py` créé (structure de la table à un seul endroit, + colonne `alerte_envoyee`).
  - `collecte.py` : limite 30 jours (OpenAI et Hugging Face envoyaient 2000+ vieux
    articles), délai d'attente 20 s, pause 1 s entre sources. 5 sources ajoutées (16 au total).
  - `mots_cles.yml` + `tri.py` écrits (Gemini, Mistral en secours).
  - `generer_site.py` + site `docs/` (recherche instantanée sans accents, surlignage,
    filtres, tags cliquables, « À la une », mode sombre, mobile, page Méthodologie).
  - `alerte_discord.py`, `tests.py` (21 tests), workflow GitHub Actions, README, EPREUVE.md.
  - Problème : compte Google bloqué pour AI Studio (vérification d'âge) → clé Gemini
    pas encore créée. `GEMINI_API_KEY` contenait le texte d'exemple au lieu de la clé.
  - **Reste à faire** : vraie clé Gemini (PC + secret GitHub), webhook Discord,
    dépôt en public + GitHub Pages (main /docs), premier « Run workflow ».
