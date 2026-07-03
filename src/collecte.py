"""
Brique 1 — Collecte d'entreprises.
==================================
Source : API Recherche d'Entreprises de la DINUM (gratuite, ouverte, sans clé).
    Base : https://recherche-entreprises.api.gouv.fr/search
    Limite : 7 requêtes/s par IP.

Mémoire anti-doublons : les fonctions charger_siren_vus / sauver_siren_vus
permettent à l'orchestrateur d'ignorer les entreprises déjà collectées, pour
ne ramener que des prospects NOUVEAUX à chaque exécution.

NB : les dirigeants renvoyés sont les mandataires sociaux (président, gérant...),
PAS le contact DRH/DAF -> c'est l'objet de la brique 2 (enrichissement).
"""

import os
import json
import time
import requests

from src.referentiels import TRANCHES_EFFECTIF, FORMES_JURIDIQUES, SECTIONS, secteur_prioritaire

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


# --- Collecte -------------------------------------------------------------------
def collecter(filtres, max_resultats=50, siren_exclus=None):
    """Renvoie jusqu'à `max_resultats` entreprises NOUVELLES (SIREN absent de
    `siren_exclus`), en paginant l'API."""
    siren_exclus = siren_exclus or set()
    resultats = []
    vus_ce_run = set()
    page = 1
    while len(resultats) < max_resultats:
        params = dict(filtres)
        params["page"] = page
        params["per_page"] = PER_PAGE
        reponse = requests.get(BASE_URL, params=params,
                               headers={"User-Agent": USER_AGENT}, timeout=30)
        if reponse.status_code == 429:
            attente = int(reponse.headers.get("Retry-After", 2))
            print(f"  [429] Limite atteinte, pause {attente}s...")
            time.sleep(attente)
            continue
        reponse.raise_for_status()
        data = reponse.json()

        lot = data.get("results", [])
        if not lot:
            break

        for entreprise in lot:
            siren = entreprise.get("siren")
            if not siren or siren in siren_exclus or siren in vus_ce_run:
                continue
            vus_ce_run.add(siren)
            resultats.append(entreprise)
            if len(resultats) >= max_resultats:
                break

        if page >= data.get("total_pages", page):
            break
        page += 1
        time.sleep(PAUSE_SECONDES)

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


def _chiffre_affaires(entreprise):
    """CA du dernier bilan disponible."""
    finances = entreprise.get("finances") or {}
    if not finances:
        return None
    return (finances[max(finances.keys())] or {}).get("ca")


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
    complements = entreprise.get("complements") or {}
    code_tranche = entreprise.get("tranche_effectif_salarie")
    code_forme = entreprise.get("nature_juridique")
    idcc = _conventions(entreprise)
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
        "conventions_idcc": "; ".join(idcc),
        "conv_renseignee": "Oui" if complements.get("convention_collective_renseignee") else "Non",
        "etat": entreprise.get("etat_administratif"),
        "adresse": siege.get("adresse"),
        "code_postal": siege.get("code_postal"),
        "ville": siege.get("libelle_commune") or siege.get("commune"),
        "departement": siege.get("departement"),
        "dirigeants": _dirigeants(entreprise),  # mandataires sociaux, PAS le DRH/DAF
    }
