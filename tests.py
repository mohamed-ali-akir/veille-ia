"""
=============================================================
 TESTS AUTOMATIQUES
=============================================================
Vérifient que les fonctions importantes font bien ce qu'on
attend, SANS internet et SANS clé d'API.
Ils sont lancés automatiquement par GitHub Actions avant
chaque veille : si un test échoue, la veille ne tourne pas.

Pour les lancer :  py -m unittest -v tests
=============================================================
"""

import unittest

import feedparser

import collecte
import essentiel
import generer_site
import tri


class TestNettoyage(unittest.TestCase):
    """Étape 1 : nettoyage des textes reçus des flux RSS."""

    def test_enleve_les_balises_html(self):
        self.assertEqual(collecte.nettoyer_texte("<p>Bonjour <b>tout</b> le monde</p>"),
                         "Bonjour tout le monde")

    def test_decode_les_caracteres_speciaux(self):
        self.assertEqual(collecte.nettoyer_texte("Python &amp; SQL"), "Python & SQL")

    def test_texte_vide(self):
        self.assertIsNone(collecte.nettoyer_texte(None))

    def test_limite_a_1000_caracteres(self):
        self.assertEqual(len(collecte.nettoyer_texte("a" * 5000)), 1000)


class TestAge(unittest.TestCase):
    """Étape 1 : les articles trop anciens sont ignorés."""

    def test_article_ancien(self):
        self.assertTrue(collecte.est_trop_ancien("2020-01-01T00:00:00+00:00"))

    def test_date_inconnue_gardee(self):
        self.assertFalse(collecte.est_trop_ancien(None))


class TestMotsCles(unittest.TestCase):
    """Étape 2, phase 1 : le filtre par mots-clés."""

    @classmethod
    def setUpClass(cls):
        cls.motifs = tri.charger_motifs()

    def test_trouve_un_mot_cle(self):
        self.assertIn("ChatGPT", tri.trouver_mots_cles("Nouvelle version de ChatGPT", self.motifs))

    def test_insensible_aux_majuscules(self):
        self.assertIn("machine learning",
                      tri.trouver_mots_cles("Intro au Machine Learning", self.motifs))

    def test_sigle_en_majuscules(self):
        self.assertIn("AI", tri.trouver_mots_cles("A new AI tool for developers", self.motifs))

    def test_j_ai_n_est_pas_un_sigle(self):
        # Le piège : "ai" dans "j'ai" ne doit PAS être pris pour "AI"
        self.assertEqual(tri.trouver_mots_cles("J'ai acheté un vélo", self.motifs), [])

    def test_mot_entier_seulement(self):
        # "IA" ne doit pas être trouvé dans "via" ou "média"
        self.assertEqual(tri.trouver_mots_cles("Envoyé via les médias", self.motifs), [])


class TestValidationIA(unittest.TestCase):
    """Étape 2, phase 2 : on ne fait jamais confiance aveuglément à l'IA."""

    def test_reponse_correcte(self):
        resultat = tri.valider_resultat({"resume": "Un résumé.", "tags": ["LLM"], "note": 4,
                                         "justification": "Nouveau modèle utile."})
        self.assertEqual(resultat, {"resume": "Un résumé.", "tags": ["LLM"], "note": 4,
                                    "justification": "Nouveau modèle utile."})

    def test_justification_absente_remplacee_par_texte_vide(self):
        resultat = tri.valider_resultat({"resume": "R", "tags": [], "note": 3})
        self.assertEqual(resultat["justification"], "")

    def test_justification_trop_longue_coupee(self):
        resultat = tri.valider_resultat({"resume": "R", "tags": [], "note": 3,
                                         "justification": "x" * 1000})
        self.assertEqual(len(resultat["justification"]), 250)

    def test_tag_invente_supprime(self):
        resultat = tri.valider_resultat({"resume": "R", "tags": ["LLM", "Tag inventé"], "note": 3})
        self.assertEqual(resultat["tags"], ["LLM"])

    def test_maximum_3_tags_sans_doublon(self):
        resultat = tri.valider_resultat({"resume": "R", "note": 3,
                                         "tags": ["LLM", "LLM", "Recherche", "Sécurité", "Robotique"]})
        self.assertEqual(resultat["tags"], ["LLM", "Recherche", "Sécurité"])

    def test_note_trop_grande_ramenee_a_5(self):
        self.assertEqual(tri.valider_resultat({"resume": "R", "tags": [], "note": 12})["note"], 5)

    def test_note_negative_ramenee_a_0(self):
        self.assertEqual(tri.valider_resultat({"resume": "R", "tags": [], "note": -3})["note"], 0)

    def test_note_pas_un_nombre(self):
        self.assertIsNone(tri.valider_resultat({"resume": "R", "tags": [], "note": "super"}))

    def test_resume_vide(self):
        self.assertIsNone(tri.valider_resultat({"resume": "  ", "tags": [], "note": 3}))

    def test_reponse_pas_un_dictionnaire(self):
        self.assertIsNone(tri.valider_resultat(["pas", "un", "objet"]))


class TestExport(unittest.TestCase):
    """Étape 3 : conversion pour le fichier JSON."""

    def test_en_liste(self):
        self.assertEqual(generer_site.en_liste("LLM, Outils dev"), ["LLM", "Outils dev"])

    def test_en_liste_vide(self):
        self.assertEqual(generer_site.en_liste(None), [])


class TestEssentiel(unittest.TestCase):
    """Bonus : vérification de la synthèse de la semaine écrite par l'IA."""

    # Les articles qu'on a VRAIMENT donnés à l'IA (numéros 1 à 4)
    ARTICLES = {numero: {"titre": f"Titre {numero}", "url": f"https://exemple.fr/{numero}",
                         "source": "Test"} for numero in [1, 2, 3, 4]}

    def reponse(self, ids):
        return {"introduction": "Semaine chargée.",
                "points": [{"texte": f"Point {numero}", "id": numero} for numero in ids]}

    def test_reponse_correcte(self):
        resultat = essentiel.valider_essentiel(self.reponse([1, 2, 3]), self.ARTICLES)
        self.assertEqual(len(resultat["points"]), 3)
        self.assertEqual(resultat["points"][0]["url"], "https://exemple.fr/1")

    def test_numero_invente_supprime(self):
        # L'IA cite l'article 99 qui n'existe pas : ce point est supprimé
        resultat = essentiel.valider_essentiel(self.reponse([1, 99, 2, 3]), self.ARTICLES)
        self.assertEqual([point["id"] for point in resultat["points"]], [1, 2, 3])

    def test_meme_article_pas_deux_fois(self):
        resultat = essentiel.valider_essentiel(self.reponse([1, 1, 2, 3]), self.ARTICLES)
        self.assertEqual([point["id"] for point in resultat["points"]], [1, 2, 3])

    def test_pas_assez_de_points(self):
        self.assertIsNone(essentiel.valider_essentiel(self.reponse([1, 2]), self.ARTICLES))

    def test_introduction_vide(self):
        reponse = self.reponse([1, 2, 3])
        reponse["introduction"] = ""
        self.assertIsNone(essentiel.valider_essentiel(reponse, self.ARTICLES))


class TestFluxRSS(unittest.TestCase):
    """Étape 3 : le flux RSS produit par la veille."""

    @classmethod
    def setUpClass(cls):
        def article(titre, note):
            return {"titre": titre, "url": f"https://exemple.fr/{note}", "note": note,
                    "date": "2026-10-09T12:00:00+00:00", "resume": "Résumé.",
                    "source": "Test", "tags": ["LLM"]}
        articles = [
            article("Un titre piège <script> & co", 5),
            article("Article important", 4),
            article("Article moyen", 3),
        ]
        # On relit notre propre flux avec feedparser, comme un vrai lecteur RSS
        cls.flux = feedparser.parse(generer_site.creer_flux_rss(articles))

    def test_xml_valide(self):
        self.assertFalse(self.flux.bozo)  # bozo = 1 si le XML est mal formé

    def test_seulement_les_articles_importants(self):
        self.assertEqual(len(self.flux.entries), 2)  # l'article noté 3 est exclu

    def test_caracteres_speciaux_conserves(self):
        self.assertEqual(self.flux.entries[0].title, "Un titre piège <script> & co")


if __name__ == "__main__":
    unittest.main()
