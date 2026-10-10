# Préparation de l'épreuve — Veille IA

Fiche personnelle pour présenter et défendre le projet devant le jury.

---

## 1. Présenter le projet en 1 minute

> « Ma veille porte sur l'intelligence artificielle du point de vue d'un développeur.
> Plutôt que de lire des dizaines de sites à la main, j'ai automatisé la chaîne complète :
> un programme Python récupère chaque jour les articles de 16 sources grâce aux flux RSS,
> garde ceux qui parlent d'IA, les fait résumer et noter par une IA, les stocke dans une
> base SQLite et les publie sur un site web avec recherche instantanée. Tout tourne seul,
> deux fois par jour, grâce à GitHub Actions, et les articles les plus importants
> m'arrivent sur Discord. »

## 2. Déroulé de la démo (≈ 5 minutes)

1. **Le site** : ouvrir https://mohamed-ali-akir.github.io/veille-ia/
   - Montrer **« L'essentiel de la semaine »** (synthèse en 5 points, chaque point a sa source).
   - Montrer « À la une », les étoiles, les tags, le badge « Nouveau ».
   - Déplier un **« Pourquoi 4/5 ? »** : l'IA justifie sa note.
2. **Le défi des 30 secondes** : demander un mot-clé au jury, le taper.
   - Les résultats s'affichent **pendant la frappe**, le mot est **surligné**.
   - Montrer qu'on peut écrire sans accent (« securite » trouve « sécurité »).
   - Cliquer sur un tag, changer la note minimale, la période.
3. **Discord** : montrer le salon avec les alertes des articles notés 4 et 5.
4. **L'automatisation** : sur GitHub, onglet *Actions*, montrer l'historique des lancements
   et cliquer sur **« Run workflow »** pour en lancer un en direct.
5. **La méthodologie** : page « Méthodologie » (schéma + chiffres de l'entonnoir).
   Cliquer sur **« Flux RSS »** : « ma veille est elle-même une source qu'on peut suivre ».
6. **Le code** : ouvrir `tri.py`, montrer la consigne envoyée à l'IA et `valider_resultat()`.

**Plan B si internet ne marche pas** : `py -m http.server --directory docs` (site en local)
ou `py chercher.py mot` (recherche en ligne de commande).

## 3. Points techniques à savoir expliquer

| Notion | Où | Ce qu'il faut dire |
|---|---|---|
| **Flux RSS** | `collecte.py` | Format XML standard publié par les sites ; `feedparser` le lit pour moi. |
| **Pipeline / ETL** | tout le projet | *Extract* (collecte), *Transform* (tri), *Load* (base + JSON). Chaque script a un seul rôle. |
| **Doublons** | `base.py` | La colonne `url` est `UNIQUE` + `INSERT OR IGNORE` : SQLite refuse lui-même un article déjà connu. |
| **Injection SQL** | partout | Requêtes **paramétrées** (`?`) : les valeurs ne sont jamais collées dans le texte SQL. |
| **Regex** | `tri.py` | `\b` = limite de mot (« IA » ne matche pas « via ») ; sigles sensibles à la casse (« AI » ≠ « j'ai »). |
| **API REST** | `tri.py` | Requête HTTP POST en JSON avec `urllib`, clé dans un en-tête (pas dans l'URL). |
| **Prompt** | `tri.py` | Consigne précise : résumé en français, tags dans une liste fixe, barème de note expliqué. |
| **Ne pas faire confiance à l'IA** | `valider_resultat()` | L'IA peut inventer un tag ou donner 12/5 : le programme corrige ou rejette. |
| **Quotas / erreur 429** | `tri.py` | Offre gratuite limitée : pause de 5 s, 50 articles max, arrêt propre sur 429, reprise au lancement suivant. |
| **Secrets** | variables d'environnement | Dépôt public → aucune clé dans le code. `setx` sur le PC, *Secrets* sur GitHub. |
| **JSON** | `generer_site.py` | Format d'échange standard entre Python et JavaScript (le même que les API). |
| **Séparation données / présentation** | `docs/` | Python produit les données, HTML/CSS/JS les affichent. Proche du principe MVC. |
| **Recherche côté client** | `app.js` | Le JSON est chargé une fois ; à chaque touche (`input`), `filter()` sur le tableau → instantané, sans serveur. |
| **Faille XSS** | `app.js` | Texte inséré avec `textContent` et jamais `innerHTML` : un titre contenant `<script>` ne s'exécute pas. |
| **Responsive** | `style.css` | `@media (max-width: 640px)` + grille CSS ; mode sombre avec `prefers-color-scheme`. |
| **CI/CD** | `veille.yml` | GitHub Actions : déclenchement `cron` + bouton manuel, tests d'abord, puis la veille, puis `git push`. |
| **Tests unitaires** | `tests.py` | 31 tests `unittest`, lancés avant chaque veille ; si un test échoue, rien n'est publié. |
| **Migration de base** | `base.py` | `CREATE TABLE IF NOT EXISTS` ne modifie pas une table existante : la colonne `justification` est ajoutée avec `ALTER TABLE`, seulement si `PRAGMA table_info` montre qu'elle manque. |
| **Module partagé (DRY)** | `ia.py`, `base.py` | Le code d'appel à l'IA est écrit une fois et utilisé par `tri.py` et `essentiel.py` : seuls la consigne et le schéma changent. |
| **IA explicable** | `tri.py` | L'IA justifie chaque note en une phrase : on peut comprendre (et contester) sa décision. |
| **Anti-hallucination** | `valider_essentiel()` | La synthèse cite des numéros d'articles : un numéro qui n'a pas été fourni à l'IA est supprimé, chaque point reste vérifiable. |
| **Produire un flux RSS** | `generer_site.py` | `xml.etree.ElementTree` construit le XML et échappe `<` et `&` tout seul ; testé en relisant le flux avec `feedparser`. |
| **Cache HTTP** | `app.js` | GitHub Pages fait garder les fichiers 10 min par le navigateur : `fetch(..., { cache: "no-cache" })` force la vérification de la dernière version. |
| **Webhook** | `alerte_discord.py` | URL secrète ; un POST JSON = un message dans le salon. Colonne `alerte_envoyee` pour ne jamais envoyer deux fois. |
| **Windows / Linux** | partout | `encoding="utf-8"` obligatoire, sinon les accents sont abîmés sous Windows. |

## 4. Questions probables du jury

**Pourquoi des flux RSS et pas du « scraping » ?**
Le RSS est fait pour ça : format stable, autorisé par les sites, léger. Le scraping casse
dès que le site change son HTML et peut être interdit par les conditions d'utilisation.

**Pourquoi SQLite et pas MySQL ?**
Un seul fichier, aucun serveur à installer, inclus dans Python. Suffisant pour quelques
milliers d'articles, et le fichier peut être versionné dans Git pour l'automatisation.

**Pourquoi filtrer par mots-clés avant l'IA ?**
Pour économiser le quota gratuit de l'API : environ un quart des articles sont éliminés
gratuitement, sans appel à l'IA.

**L'IA peut se tromper, non ?**
Oui. C'est pour ça que (1) la réponse est validée par le programme, (2) le lien vers
l'article d'origine est toujours affiché, (3) la page Méthodologie le dit clairement.

**Pourquoi pas de framework (React, Flask…) ?**
Le besoin est simple : un framework ajouterait de la complexité sans rien apporter.
Un site statique est gratuit à héberger, rapide et marche même si l'API est en panne.

**Que se passe-t-il si une source est en panne ?**
Elle est signalée « [ERREUR] » dans le journal et les autres sources continuent.
Un délai d'attente de 20 s évite qu'un site bloque tout le programme.

**Que se passe-t-il si le quota de l'IA est atteint ?**
Erreur 429 → le script s'arrête proprement, les articles déjà analysés sont enregistrés
(commit après chaque article), les autres seront traités au lancement suivant.

**Comment ajouter une source ?**
Trois lignes dans `sources.yml`, sans toucher au code.

**Pourquoi la base est-elle dans le dépôt Git ?**
GitHub Actions repart d'une machine vierge à chaque lancement : la base doit être
récupérée depuis le dépôt puis renvoyée dedans, sinon on perdrait l'historique.

**La synthèse de la semaine peut-elle inventer des choses ?**
C'est le risque principal (« hallucination »). Trois protections : (1) la consigne interdit
d'utiliser autre chose que les articles fournis, (2) chaque point doit citer le numéro d'un
article fourni, sinon il est supprimé par le programme, (3) chaque point affiche un lien vers
sa source pour vérifier.

**Pourquoi ne pas faire un chatbot « pose une question à ta veille » ?**
Le site est statique : pour appeler l'IA depuis le navigateur, il faudrait mettre la clé
dans le JavaScript, donc la rendre publique. Il faudrait un serveur intermédiaire : c'est
une piste d'évolution, pas un oubli.

**Combien ça coûte ?**
Rien : GitHub Actions et GitHub Pages sont gratuits pour un dépôt public, l'API Gemini
a une offre gratuite, Discord est gratuit.

## 5. Ce que la veille m'a appris (à compléter moi-même)

- Les grandes tendances observées (agents IA, modèles open source, outils de code…) :
- Ce qui change pour un développeur :
- Un article marquant et pourquoi :
- Mon avis personnel :
