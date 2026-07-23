"""
Brique 1 — Collecte d'entreprises.
==================================
Source : API Recherche d'Entreprises de la DINUM (gratuite, ouverte, sans clé).
    Base : https://recherche-entreprises.api.gouv.fr/search
    Limite : 7 requêtes/s par IP.

Mémoire anti-doublons : les fonctions charger_siren_vus / sauver_siren_vus
permettent à l'orchestrateur d'ignorer les entreprises déjà collectées, pour
ne ramener que des prospects NOUVEAUX à chaque exécution.

Diversité des recherches : prochain_departement() fait tourner le département
ciblé à chaque exécution (voir DEPARTEMENTS_CIBLE dans config/cibles.py), et
collecter() explore les pages de résultats de l'API dans un ordre mélangé plutôt
que toujours 1, 2, 3... pour ne pas retomber sur les mêmes fiches en tête de liste.

NB : les dirigeants renvoyés sont les mandataires sociaux (président, gérant...),
PAS le contact DRH/DAF -> c'est l'objet de la brique 2 (enrichissement).
"""

import os
import json
import time
import random
import requests

from src.referentiels import (TRANCHES_EFFECTIF, FORMES_JURIDIQUES, SECTIONS, secteur_prioritaire,
                              libelle_idcc, lien_legifrance_idcc, suggestion_idcc_pour_naf)

BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
USER_AGENT = "G2S-prospection-agent/1.0 (contact: a-completer@g2s.fr)"
PER_PAGE = 25            # plafond imposé par l'API
PAUSE_SECONDES = 0.25    # ~4 req/s, sous la limite de 7 req/s


# --- Mémoire des SIREN déjà collectés -------------------------------------------
def charger_siren_vus(chemin):
    """Charge l'ensemble des SIREN déjà collectés lors des runs précédents."""
    if os.path.exists(chemin):
        try:
            with open(chemin, encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            print(f"  [!] {chemin} illisible, on repart d'une mémoire vide.")
    return set()


def sauver_siren_vus(siren_set, chemin):
    """Enregistre la mémoire mise à jour."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(sorted(siren_set), f, ensure_ascii=False)


# --- Rotation géographique (diversité des recherches) ---------------------------
def charger_rotation(chemin):
    """Index du dernier département utilisé (-1 si aucun run précédent)."""
    if os.path.exists(chemin):
        try:
            with open(chemin, encoding="utf-8") as f:
                return json.load(f).get("dernier_index", -1)
        except (json.JSONDecodeError, ValueError):
            print(f"  [!] {chemin} illisible, on repart du premier département.")
    return -1


def sauver_rotation(index, chemin):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"dernier_index": index}, f)


def prochain_departement(departements, chemin):
    """Fait tourner la cible géographique à chaque exécution (round-robin) : deux
    recherches successives ne portent jamais sur le même département, ce qui évite
    d'épuiser le même vivier et varie les prospects proposés d'un run à l'autre.
    Renvoie None si `departements` est vide (comportement inchangé : pas de filtre
    département)."""
    if not departements:
        return None
    index = (charger_rotation(chemin) + 1) % len(departements)
    sauver_rotation(index, chemin)
    return departements[index]


# --- Collecte -------------------------------------------------------------------
def _appeler(params, tentatives=3):
    """Un appel GET à l'API, avec réessai en cas de limite de débit (429)."""
    for _ in range(tentatives):
        reponse = requests.get(BASE_URL, params=params,
                               headers={"User-Agent": USER_AGENT}, timeout=30)
        if reponse.status_code == 429:
            attente = int(reponse.headers.get("Retry-After", 2))
            print(f"  [429] Limite atteinte, pause {attente}s...")
            time.sleep(attente)
            continue
        reponse.raise_for_status()
        return reponse
    reponse.raise_for_status()
    return reponse


def collecter(filtres, max_resultats=50, siren_exclus=None):
    """Renvoie jusqu'à `max_resultats` entreprises NOUVELLES (SIREN absent de
    `siren_exclus`), en explorant les pages de résultats de l'API dans un ordre
    MÉLANGÉ (et non 1, 2, 3... toujours dans le même ordre) : l'API renvoyant un
    classement stable pour un même filtre, parcourir les pages dans le même ordre
    à chaque exécution reviendrait à toujours échantillonner la même tranche du
    vivier -> des prospects moins variés d'une recherche à l'autre."""
    siren_exclus = siren_exclus or set()
    resultats = []
    vus_ce_run = set()

    params = dict(filtres)
    params["page"] = 1
    params["per_page"] = PER_PAGE
    premiere = _appeler(params).json()
    total_pages = premiere.get("total_pages", 1)

    pages = list(range(1, total_pages + 1))
    random.shuffle(pages)

    lots_par_page = {1: premiere.get("results", [])}
    for page in pages:
        if len(resultats) >= max_resultats:
            break
        if page in lots_par_page:
            lot = lots_par_page.pop(page)
        else:
            params = dict(filtres)
            params["page"] = page
            params["per_page"] = PER_PAGE
            lot = _appeler(params).json().get("results", [])
            time.sleep(PAUSE_SECONDES)

        for entreprise in lot:
            siren = entreprise.get("siren")
            if not siren or siren in siren_exclus or siren in vus_ce_run:
                continue
            vus_ce_run.add(siren)
            resultats.append(entreprise)
            if len(resultats) >= max_resultats:
                break

    return resultats


# --- Mise en forme d'une fiche --------------------------------------------------
def _conventions(entreprise):
    """Codes IDCC : priorité aux compléments, sinon siège + établissements."""
    complements = entreprise.get("complements") or {}
    idcc = list(complements.get("liste_idcc") or [])
    if not idcc:
        siege = entreprise.get("siege") or {}
        idcc += siege.get("liste_idcc") or []
        for etab in entreprise.get("matching_etablissements") or []:
            idcc += etab.get("liste_idcc") or []
    return sorted(set(c for c in idcc if c))


def _conventions_infos(codes_idcc):
    """Texte à afficher pour les conventions collectives : la description
    complète de chaque convention si connue (referentiels.libelle_idcc, chargé
    depuis data/convetions_c/convention.json), sinon le code brut — plusieurs
    conventions sont jointes par "; ". `url` liste, dans le même ordre et avec
    le même séparateur, le lien Légifrance de CHAQUE convention reconnue (un
    code inconnu de la table n'a simplement pas de lien, jamais inventé)."""
    textes, liens = [], []
    for code in codes_idcc:
        label, lien = libelle_idcc(code), lien_legifrance_idcc(code)
        textes.append(label or code)
        if lien:
            liens.append(lien)
    return {"texte": "; ".join(textes), "url": "; ".join(liens) if liens else None}


def _suggestion_conv_infos(code_naf):
    """Quand l'entreprise n'a AUCUNE CCN officiellement déclarée : suggestion
    statistique (source DARES, table code APE -> IDCC) de la convention la
    plus fréquente pour son secteur, TOUJOURS avec le % de salariés du secteur
    concernés affiché, pour que ce soit lu comme une indication et non une
    certitude. Pas de suggestion possible (code APE non diffusable/inconnu de
    la table) -> texte vide, comme avant."""
    suggestion = suggestion_idcc_pour_naf(code_naf)
    if not suggestion:
        return {"texte": "", "url": None}
    code_idcc, intitule_dares, pct = suggestion
    texte = f"Suggestion secteur, non confirmée ({pct:.0f}% des salariés du secteur) : {intitule_dares}"
    return {"texte": texte, "url": lien_legifrance_idcc(code_idcc)}


def _chiffre_affaires(entreprise):
    """CA du dernier bilan disponible."""
    finances = entreprise.get("finances") or {}
    if not finances:
        return None
    return (finances[max(finances.keys())] or {}).get("ca")


def _departement_depuis_code_postal(code_postal):
    """Dérive le département depuis un code postal (repli quand le champ
    'departement' est absent — observé dans matching_etablissements)."""
    if not code_postal:
        return None
    cp = str(code_postal).strip()
    return cp[:3] if cp[:2] in ("97", "98") else cp[:2]


def _etablissement_pertinent(entreprise):
    """Établissement dont on affiche l'adresse. L'API filtre (ex. departement)
    au niveau ÉTABLISSEMENT, pas siège : une entreprise dont le siège est à
    Paris peut matcher un filtre "département 971" via une antenne en
    Guadeloupe — matching_etablissements liste alors cette antenne. On y
    cherche le premier établissement ACTIF qui n'est PAS le siège (c'est celui
    qui a réellement fait matcher la recherche) ; sinon on retombe sur le
    siège, comme avant."""
    for etab in entreprise.get("matching_etablissements") or []:
        if etab.get("etat_administratif") == "A" and not etab.get("est_siege"):
            return etab
    return entreprise.get("siege") or {}


def _dirigeants(entreprise):
    """Dirigeants personnes physiques (exclut personnes morales et CAC)."""
    noms = []
    for d in entreprise.get("dirigeants") or []:
        if d.get("type_dirigeant") != "personne physique":
            continue
        qualite = d.get("qualite") or ""
        if "commissaire aux comptes" in qualite.lower():
            continue
        nom = f"{d.get('prenoms', '')} {d.get('nom', '')}".strip()
        if nom:
            noms.append(f"{nom} ({qualite})" if qualite else nom)
    return "; ".join(noms[:3])


def aplatir(entreprise):
    """Transforme un résultat brut de l'API en fiche propre et exploitable."""
    siege = entreprise.get("siege") or {}
    etab = _etablissement_pertinent(entreprise)
    complements = entreprise.get("complements") or {}
    code_tranche = entreprise.get("tranche_effectif_salarie")
    code_forme = entreprise.get("nature_juridique")
    idcc = _conventions(entreprise)
    conv = _conventions_infos(idcc) if idcc else _suggestion_conv_infos(entreprise.get("activite_principale"))
    sec = secteur_prioritaire(entreprise.get("activite_principale"))
    secteur_lib = sec[0] if sec else SECTIONS.get(entreprise.get("section_activite_principale"), "")
    return {
        "siren": entreprise.get("siren"),
        "siret": siege.get("siret"),  # SIRET du siège (pour le champ Pipedrive « SIRET »)
        "raison_sociale": entreprise.get("nom_complet") or entreprise.get("nom_raison_sociale"),
        "naf": entreprise.get("activite_principale"),
        "section": entreprise.get("section_activite_principale"),  # technique (scoring)
        "secteur_activite": secteur_lib,  # libellé lisible (pour le champ Pipedrive)
        "forme_juridique": FORMES_JURIDIQUES.get(code_forme, f"Code {code_forme}"),
        "categorie": entreprise.get("categorie_entreprise"),
        "nb_etablissements": entreprise.get("nombre_etablissements"),  # technique (scoring multi-sites)
        "tranche_effectif": TRANCHES_EFFECTIF.get(code_tranche, "Inconnu"),
        "tranche_effectif_code": code_tranche,  # technique (scoring)
        "chiffre_affaires": _chiffre_affaires(entreprise),
        "conventions_idcc": conv["texte"],
        "conventions_idcc_url": conv["url"],  # technique (lien Légifrance direct si CCN unique et reconnue)
        "conv_renseignee": "Oui" if complements.get("convention_collective_renseignee") else "Non",
        "etat": entreprise.get("etat_administratif"),
        # Adresse de l'établissement pertinent (peut différer du siège — voir
        # _etablissement_pertinent), pas systématiquement celle du siège.
        "adresse": etab.get("adresse"),
        "code_postal": etab.get("code_postal"),
        "ville": etab.get("libelle_commune") or etab.get("commune"),
        "departement": etab.get("departement") or _departement_depuis_code_postal(etab.get("code_postal")),
        "dirigeants": _dirigeants(entreprise),  # mandataires sociaux, PAS le DRH/DAF
    }
