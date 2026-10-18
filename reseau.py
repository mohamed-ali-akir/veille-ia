"""
=============================================================
 MODULE PARTAGÉ : les erreurs réseau
=============================================================
Sur Internet, une requête peut échouer de plein de façons :
site injoignable, délai dépassé, connexion coupée en plein
milieu, réponse tronquée... Python les range dans des
familles différentes : si on en oublie une, le script plante
et toute la veille s'arrête.

Ce module les regroupe à UN SEUL endroit, et sait refaire
une requête quand l'erreur est passagère.
=============================================================
"""

import http.client
import json
import time
import urllib.error
import urllib.request

# Toutes les erreurs réseau "normales" :
#   - OSError regroupe URLError (site injoignable), HTTPError (code 4xx/5xx),
#     TimeoutError et ConnectionResetError (connexion coupée) ;
#   - http.client.HTTPException regroupe IncompleteRead (réponse tronquée)
#     et les réponses mal formées, qui ne sont PAS des OSError.
ERREURS_RESEAU = (OSError, http.client.HTTPException)

# Nombre d'essais pour une requête, et pause avant le 2e essai (doublée ensuite)
NOMBRE_ESSAIS = 3
PAUSE_INITIALE = 2


def est_passagere(erreur):
    """
    Renvoie True si l'erreur vaut la peine de réessayer : panne du serveur (5xx)
    ou problème de connexion. Une erreur 4xx (requête refusée, quota 429...)
    ne s'arrangera pas en réessayant tout de suite.
    """
    if isinstance(erreur, urllib.error.HTTPError):
        return erreur.code >= 500
    return isinstance(erreur, ERREURS_RESEAU)


def lire_json(requete, timeout, attendre=time.sleep):
    """
    Envoie la requête et renvoie la réponse JSON décodée.
    Réessaie jusqu'à NOMBRE_ESSAIS fois si l'erreur est passagère,
    sinon laisse remonter l'erreur à l'appelant.
    """
    pause = PAUSE_INITIALE
    for essai in range(1, NOMBRE_ESSAIS + 1):
        try:
            with urllib.request.urlopen(requete, timeout=timeout) as reponse:
                return json.load(reponse)
        except ERREURS_RESEAU as erreur:
            if essai == NOMBRE_ESSAIS or not est_passagere(erreur):
                raise
            print(f"  Erreur passagère ({erreur}), nouvel essai dans {pause} s...")
            attendre(pause)
            pause *= 2
