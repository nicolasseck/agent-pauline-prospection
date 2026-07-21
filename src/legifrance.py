"""
Convention collective (CCN) EN DIRECT via l'API officielle Légifrance (PISTE).
===============================================================================
Remplace la source figée data/convetions_c/convention.json (export ponctuel,
408 IDCC) par une consultation LIVE de l'API Légifrance (DILA) : nom usuel et
lien légifrance.gouv.fr toujours à jour, pour n'importe quel code IDCC — plus
seulement ceux présents dans l'export du jour où il a été généré.

Authentification : compte PISTE (https://piste.gouv.fr), gratuit, application
« Légifrance » souscrite. Identifiants lus via LEGIFRANCE_CLIENT_ID /
LEGIFRANCE_CLIENT_SECRET (variable d'environnement ou fichier .env — voir
.env.example). Sans identifiants, ce module ne fait rien (fail-open, voir
src/referentiels.py qui se replie alors sur l'export statique).

Endpoint utilisé : POST /consult/kaliContIdcc {"idcc": "<code>"} — renvoie le
conteneur Légifrance (KALICONT...) de la convention collective correspondant à
cet IDCC, dont le titre et l'identifiant permettent de reconstruire l'URL
publique "https://www.legifrance.gouv.fr/conv_coll/id/<KALICONT...>" (même
format que les liens déjà présents dans data/convetions_c/convention.json).
⚠️ Schéma basé sur la documentation publique de l'API ; le nom exact des champs
de la réponse (titre/id) est vérifié de façon tolérante (plusieurs variantes
essayées) et à confirmer une fois un compte PISTE réel branché — voir README.

Cache : chaque IDCC résolu avec succès (ou confirmé inexistant, réponse 404)
est mémorisé dans data/convetions_c/cache_idcc.json, pour ne plus jamais
rappeler l'API pour ce code -> gratuit, rapide, résilient à une panne/quota
temporaire (dans ce cas, rien n'est mis en cache : on réessaiera au run
suivant).
"""

import os
import json
import time
import requests

OAUTH_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
API_BASE = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
URL_PUBLIQUE = "https://www.legifrance.gouv.fr/conv_coll/id/{}"

_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHEMIN_CACHE = os.path.join(_RACINE, "data", "convetions_c", "cache_idcc.json")

_jeton = {"valeur": None, "expire_a": 0}
_cache = None


def _lire_env(cle, racine=_RACINE):
    val = os.environ.get(cle)
    if val:
        return val.strip()
    chemin = os.path.join(racine, ".env")
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne.startswith(cle) and "=" in ligne:
                    return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _obtenir_jeton():
    """Jeton OAuth2 (client_credentials), mis en cache jusqu'à expiration. None
    si LEGIFRANCE_CLIENT_ID / LEGIFRANCE_CLIENT_SECRET ne sont pas configurés."""
    if _jeton["valeur"] and time.time() < _jeton["expire_a"]:
        return _jeton["valeur"]
    client_id = _lire_env("LEGIFRANCE_CLIENT_ID")
    client_secret = _lire_env("LEGIFRANCE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    reponse = requests.post(OAUTH_URL, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "openid",
    }, timeout=20)
    reponse.raise_for_status()
    data = reponse.json()
    _jeton["valeur"] = data["access_token"]
    _jeton["expire_a"] = time.time() + int(data.get("expires_in", 3600)) - 60
    return _jeton["valeur"]


def _charger_cache():
    global _cache
    if _cache is not None:
        return _cache
    _cache = {}
    if os.path.exists(_CHEMIN_CACHE):
        try:
            with open(_CHEMIN_CACHE, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            print(f"  [!] {_CHEMIN_CACHE} illisible — cache IDCC repart vide.")
            _cache = {}
    return _cache


def _sauver_cache():
    os.makedirs(os.path.dirname(_CHEMIN_CACHE), exist_ok=True)
    with open(_CHEMIN_CACHE, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)


def _extraire_titre_id(data):
    """Lecture tolérante de la réponse /consult/kaliContIdcc : essaie les
    variantes de noms de champs documentées pour le conteneur KALI (titre,
    identifiant), sans jamais inventer de valeur si absente."""
    conteneur = data.get("conteneur") or data.get("kaliCont") or data
    titre = conteneur.get("titre") or conteneur.get("title") or conteneur.get("nomIdcc")
    identifiant = conteneur.get("id") or conteneur.get("cid")
    if not titre or not identifiant:
        return None
    return (titre, URL_PUBLIQUE.format(identifiant))


def _interroger_api(code_idcc):
    """Un appel /consult/kaliContIdcc. Renvoie (titre, url), ou None si
    l'IDCC est confirmé inconnu de Légifrance (réponse 404 / réponse sans
    titre ni identifiant exploitable) — cette absence est cacheable."""
    jeton = _obtenir_jeton()
    if not jeton:
        return None
    reponse = requests.post(f"{API_BASE}/consult/kaliContIdcc",
                            headers={"Authorization": f"Bearer {jeton}"},
                            json={"idcc": str(code_idcc)}, timeout=20)
    if reponse.status_code == 404:
        return None
    reponse.raise_for_status()
    return _extraire_titre_id(reponse.json())


def infos_idcc(code_idcc):
    """(titre, url Légifrance) pour un code IDCC, via l'API Légifrance en
    direct — avec cache local (data/convetions_c/cache_idcc.json).
    Renvoie None si le code est confirmé inconnu, OU si l'API est
    inaccessible (identifiants absents, panne, quota) : dans ce dernier cas,
    RIEN n'est mis en cache (on réessaiera au run suivant) et c'est à
    l'appelant (src/referentiels.py) de se replier sur l'export statique."""
    code = str(code_idcc).strip().zfill(4)
    cache = _charger_cache()
    if code in cache:
        return tuple(cache[code]) if cache[code] else None
    try:
        resultat = _interroger_api(code)
    except Exception as e:
        print(f"  [i] API Légifrance indisponible pour IDCC {code} ({e}) "
              f"— repli sur l'export statique pour ce run.")
        return None
    cache[code] = list(resultat) if resultat else None
    _sauver_cache()
    return resultat
