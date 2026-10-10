/* =============================================================
   APPLICATION DU SITE DE VEILLE (JavaScript sans framework)
   -------------------------------------------------------------
   1. Au chargement : on télécharge articles.json UNE seule fois
      et on garde tous les articles en mémoire.
   2. À chaque touche tapée ou filtre changé : on filtre cette
      liste et on réaffiche les résultats. Pas de serveur à
      interroger => la recherche est instantanée.
   ============================================================= */

// ---------- Réglages ----------

const NOMBRE_PAR_PAGE = 30;   // articles affichés avant "Afficher plus"
const UN_JOUR = 24 * 60 * 60 * 1000;  // un jour en millisecondes

// ---------- Éléments de la page ----------

const champRecherche = document.getElementById("champ-recherche");
const filtreSource = document.getElementById("filtre-source");
const filtrePeriode = document.getElementById("filtre-periode");
const filtreNote = document.getElementById("filtre-note");
const filtreTri = document.getElementById("filtre-tri");
const listeTags = document.getElementById("liste-tags");
const listeArticles = document.getElementById("liste-articles");
const compteur = document.getElementById("compteur");
const boutonPlus = document.getElementById("bouton-plus");
const boutonEffacer = document.getElementById("bouton-effacer");
const sectionUne = document.getElementById("a-la-une");
const listeUne = document.getElementById("liste-une");

// ---------- État de l'application ----------

let tousLesArticles = [];          // tous les articles du fichier JSON
let tagActif = "";                 // tag cliqué ("" = aucun)
let nombreAffiches = NOMBRE_PAR_PAGE;


// =============================================================
//  OUTILS
// =============================================================

/** Met un texte en minuscules et sans accents : "Sécurité" -> "securite". */
function normaliser(texte) {
    return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** Crée un élément HTML. Le texte est inséré avec textContent :
 *  même si un titre contient "<script>", il s'affiche comme du texte
 *  et ne s'exécute jamais (protection contre la faille XSS). */
function creerElement(balise, classe, texte) {
    const element = document.createElement(balise);
    if (classe) element.className = classe;
    if (texte !== undefined) element.textContent = texte;
    return element;
}

/** Ajoute le texte dans l'élément en surlignant (<mark>) les mots cherchés.
 *  La comparaison ignore les accents : "securite" surligne "sécurité". */
function ajouterTexteSurligne(element, texte, mots) {
    if (mots.length === 0) {
        element.textContent = texte;
        return;
    }

    // 1. Version normalisée du texte, en retenant la position d'origine de chaque lettre
    let texteNormalise = "";
    const positionOrigine = [];
    for (let i = 0; i < texte.length; i++) {
        for (const lettre of normaliser(texte[i])) {
            texteNormalise += lettre;
            positionOrigine.push(i);
        }
    }

    // 2. On marque chaque lettre d'origine qui fait partie d'un mot trouvé
    const aSurligner = new Array(texte.length).fill(false);
    for (const mot of mots) {
        let debut = texteNormalise.indexOf(mot);
        while (debut !== -1) {
            for (let k = debut; k < debut + mot.length; k++) {
                aSurligner[positionOrigine[k]] = true;
            }
            debut = texteNormalise.indexOf(mot, debut + mot.length);
        }
    }

    // 3. On découpe le texte en morceaux normaux et morceaux surlignés
    let morceau = "";
    for (let i = 0; i <= texte.length; i++) {
        const finDuMorceau = i === texte.length || (i > 0 && aSurligner[i] !== aSurligner[i - 1]);
        if (finDuMorceau && morceau) {
            if (aSurligner[i - 1]) {
                element.appendChild(creerElement("mark", "", morceau));
            } else {
                element.appendChild(document.createTextNode(morceau));
            }
            morceau = "";
        }
        if (i < texte.length) morceau += texte[i];
    }
}

/** "2026-10-09T17:15:00+00:00" -> "9 oct. 2026" */
function formaterDate(dateTexte) {
    return new Date(dateTexte).toLocaleDateString("fr-FR", {
        day: "numeric", month: "short", year: "numeric",
    });
}

/** 4 -> "★★★★☆" */
function etoiles(note) {
    return "★".repeat(note) + "☆".repeat(5 - note);
}


// =============================================================
//  FILTRAGE
// =============================================================

/** Lit la barre de recherche et renvoie la liste des mots cherchés. */
function motsCherches() {
    return normaliser(champRecherche.value).split(/\s+/).filter(mot => mot !== "");
}

/** Renvoie la liste des articles qui passent TOUS les filtres, triée. */
function filtrerArticles() {
    const mots = motsCherches();
    const source = filtreSource.value;
    const noteMinimale = Number(filtreNote.value);
    const jours = Number(filtrePeriode.value);
    const dateLimite = Date.now() - jours * UN_JOUR;

    const resultats = tousLesArticles.filter(article =>
        // Chaque mot tapé doit apparaître quelque part dans l'article
        mots.every(mot => article.texteRecherche.includes(mot))
        && (source === "" || article.source === source)
        && (tagActif === "" || article.tags.includes(tagActif))
        && article.note >= noteMinimale
        && (jours === 0 || new Date(article.date).getTime() >= dateLimite)
    );

    if (filtreTri.value === "note") {
        // Mieux notés d'abord ; à note égale, le plus récent d'abord
        resultats.sort((a, b) => b.note - a.note || b.date.localeCompare(a.date));
    } else {
        resultats.sort((a, b) => b.date.localeCompare(a.date));
    }
    return resultats;
}

/** Vrai si l'utilisateur a tapé un mot ou choisi un filtre. */
function filtresActifs() {
    return champRecherche.value.trim() !== "" || filtreSource.value !== ""
        || filtrePeriode.value !== "0" || filtreNote.value !== "1" || tagActif !== "";
}


// =============================================================
//  AFFICHAGE
// =============================================================

/** Fabrique la "carte" HTML d'un article. */
function creerCarte(article, mots) {
    const carte = creerElement("article", "article");

    // Ligne du haut : date · source · étoiles · badge "Nouveau"
    const meta = creerElement("div", "article-meta");
    meta.appendChild(creerElement("span", "", formaterDate(article.date)));
    meta.appendChild(creerElement("span", "", "·"));
    const source = creerElement("span", "");
    ajouterTexteSurligne(source, article.source, mots);
    meta.appendChild(source);
    const note = creerElement("span", "etoiles", etoiles(article.note));
    note.title = `Pertinence : ${article.note}/5`;
    meta.appendChild(note);
    if (Date.now() - new Date(article.collecte).getTime() < UN_JOUR) {
        meta.appendChild(creerElement("span", "badge-nouveau", "Nouveau"));
    }
    carte.appendChild(meta);

    // Titre cliquable (ouvre l'article d'origine dans un nouvel onglet)
    const titre = creerElement("h3", "article-titre");
    const lien = creerElement("a");
    lien.href = article.url;
    lien.target = "_blank";
    lien.rel = "noopener";
    ajouterTexteSurligne(lien, article.titre, mots);
    titre.appendChild(lien);
    carte.appendChild(titre);

    // Résumé écrit par l'IA
    const resume = creerElement("p", "article-resume");
    ajouterTexteSurligne(resume, article.resume || "", mots);
    carte.appendChild(resume);

    // Tags cliquables
    const tags = creerElement("div", "article-tags");
    for (const tag of article.tags) {
        const bouton = creerElement("button", "tag", tag);
        bouton.type = "button";
        bouton.addEventListener("click", () => choisirTag(tag));
        tags.appendChild(bouton);
    }
    carte.appendChild(tags);

    return carte;
}

/** Réaffiche toute la liste selon la recherche et les filtres. */
function afficher() {
    const mots = motsCherches();
    const resultats = filtrerArticles();

    // Compteur
    const recherche = champRecherche.value.trim();
    let texteCompteur = `${resultats.length} article${resultats.length > 1 ? "s" : ""}`;
    if (recherche) texteCompteur += ` pour « ${recherche} »`;
    compteur.textContent = texteCompteur;
    boutonEffacer.hidden = !filtresActifs();

    // Section "À la une" : seulement quand on ne cherche rien
    afficherALaUne();

    // Liste des articles (seulement les N premiers)
    listeArticles.replaceChildren();
    if (tousLesArticles.length === 0) {
        listeArticles.appendChild(creerElement("p", "vide",
            "La veille démarre : les articles apparaîtront après leur première analyse par l'IA."));
    } else if (resultats.length === 0) {
        listeArticles.appendChild(creerElement("p", "vide",
            "Aucun article ne correspond. Essaie un autre mot ou retire un filtre."));
    }
    for (const article of resultats.slice(0, nombreAffiches)) {
        listeArticles.appendChild(creerCarte(article, mots));
    }
    boutonPlus.hidden = resultats.length <= nombreAffiches;

    // Boutons de tags : on met en valeur le tag actif
    for (const bouton of listeTags.querySelectorAll(".tag")) {
        bouton.setAttribute("aria-pressed", bouton.dataset.tag === tagActif);
    }

    memoriserDansAdresse();
}

/** Affiche les 3 derniers articles notés 5/5 de la semaine (inspiré de Techmeme). */
function afficherALaUne() {
    const ilYA7Jours = Date.now() - 7 * UN_JOUR;
    const une = tousLesArticles
        .filter(article => article.note === 5 && new Date(article.date).getTime() >= ilYA7Jours)
        .sort((a, b) => b.date.localeCompare(a.date))
        .slice(0, 3);

    sectionUne.hidden = filtresActifs() || une.length === 0;
    listeUne.replaceChildren(...une.map(article => creerCarte(article, [])));
}

/** Crée les boutons de tags, avec le nombre d'articles de chaque tag. */
function creerBoutonsTags() {
    const compte = {};
    for (const article of tousLesArticles) {
        for (const tag of article.tags) {
            compte[tag] = (compte[tag] || 0) + 1;
        }
    }
    const tagsTries = Object.keys(compte).sort((a, b) => compte[b] - compte[a]);

    for (const tag of tagsTries) {
        const bouton = creerElement("button", "tag", tag);
        bouton.type = "button";
        bouton.dataset.tag = tag;
        bouton.appendChild(creerElement("span", "tag-nombre", compte[tag]));
        bouton.addEventListener("click", () => choisirTag(tag));
        listeTags.appendChild(bouton);
    }
}

/** Remplit la liste déroulante des sources. */
function remplirSources() {
    const sources = [...new Set(tousLesArticles.map(article => article.source))].sort();
    for (const source of sources) {
        const option = creerElement("option", "", source);
        option.value = source;
        filtreSource.appendChild(option);
    }
}

/** Clic sur un tag : on l'active, ou on le désactive s'il l'était déjà. */
function choisirTag(tag) {
    tagActif = tagActif === tag ? "" : tag;
    nombreAffiches = NOMBRE_PAR_PAGE;
    afficher();
    window.scrollTo({ top: document.querySelector(".recherche").offsetTop, behavior: "smooth" });
}

/** Garde la recherche dans l'adresse de la page (?q=agent) :
 *  on peut copier le lien et retrouver la même recherche. */
function memoriserDansAdresse() {
    const parametres = new URLSearchParams();
    if (champRecherche.value.trim()) parametres.set("q", champRecherche.value.trim());
    if (tagActif) parametres.set("tag", tagActif);
    const adresse = parametres.toString() ? `?${parametres}` : location.pathname;
    history.replaceState(null, "", adresse);
}


// =============================================================
//  DÉMARRAGE
// =============================================================

async function demarrer() {
    try {
        // "no-cache" : le navigateur vérifie toujours s'il existe une version plus
        // récente (sinon GitHub Pages lui fait garder l'ancienne pendant 10 minutes)
        const reponse = await fetch("articles.json", { cache: "no-cache" });
        const donnees = await reponse.json();
        tousLesArticles = donnees.articles;

        // Texte de recherche préparé une seule fois par article (plus rapide)
        for (const article of tousLesArticles) {
            article.texteRecherche = normaliser([
                article.titre, article.resume || "", article.source,
                article.tags.join(" "), article.mots_cles.join(" "),
            ].join(" "));
        }

        const nombreSources = new Set(tousLesArticles.map(article => article.source)).size;
        const miseAJour = new Date(donnees.genere_le).toLocaleString("fr-FR", {
            day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
        });
        document.getElementById("infos-maj").textContent =
            `${tousLesArticles.length} articles · ${nombreSources} sources · mis à jour le ${miseAJour}`;
    } catch (erreur) {
        compteur.textContent = "Impossible de charger les articles.";
        listeArticles.appendChild(creerElement("p", "vide",
            "Le fichier articles.json est introuvable. En local, lance un serveur : " +
            "py -m http.server --directory docs"));
        return;
    }

    remplirSources();
    creerBoutonsTags();

    // Reprend la recherche contenue dans l'adresse (ex : ?q=agent)
    const parametres = new URLSearchParams(location.search);
    champRecherche.value = parametres.get("q") || "";
    tagActif = parametres.get("tag") || "";

    afficher();
    champRecherche.focus();
}

// ---------- Événements ----------

// "input" = à chaque touche tapée : c'est la recherche instantanée
champRecherche.addEventListener("input", () => {
    nombreAffiches = NOMBRE_PAR_PAGE;
    afficher();
});

for (const filtre of [filtreSource, filtrePeriode, filtreNote, filtreTri]) {
    filtre.addEventListener("change", () => {
        nombreAffiches = NOMBRE_PAR_PAGE;
        afficher();
    });
}

boutonPlus.addEventListener("click", () => {
    nombreAffiches += NOMBRE_PAR_PAGE;
    afficher();
});

boutonEffacer.addEventListener("click", () => {
    champRecherche.value = "";
    filtreSource.value = "";
    filtrePeriode.value = "0";
    filtreNote.value = "1";
    tagActif = "";
    nombreAffiches = NOMBRE_PAR_PAGE;
    afficher();
    champRecherche.focus();
});

// Raccourcis clavier : "/" pour aller dans la recherche, "Échap" pour l'effacer
document.addEventListener("keydown", evenement => {
    if (evenement.key === "/" && document.activeElement !== champRecherche) {
        evenement.preventDefault();
        champRecherche.focus();
    } else if (evenement.key === "Escape" && document.activeElement === champRecherche) {
        champRecherche.value = "";
        afficher();
    }
});

demarrer();
