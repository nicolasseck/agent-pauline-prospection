"""
Vérification BODACC — exclusion (tracée) des entreprises en procédure collective.
=================================================================================
Source : API ouverte et gratuite du BODACC (DILA), via Opendatasoft.
    https://bodacc-datadila.opendatasoft.com

Pour chaque SIREN, on cherche une annonce de la famille « Procédures collectives »
(sauvegarde, redressement, liquidation). Si oui, l'entreprise est exclue — mais elle
est AUSSI consignée dans un registre cumulatif (data/exclusions/procedures_collectives.csv)
pour ne pas la perdre de vue.

Remarques :
    - Exclusion large : toute annonce de procédure collective écarte l'entreprise.
    - Fail-open : si le BODACC est indisponible, on n'exclut pas (message dans la console).
    - Gratuit ; ajoute une requête par entreprise (courte pause entre chaque).
"""

import os
import csv
import json
import time
import datetime
import unicodedata
import requests

BASE = "https://bodacc-datadila.opendatasoft.com/api/records/1.0/search/"
DATASET = "annonces-commerciales"
PAUSE_SECONDES = 0.2


def _sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


def _type_jugement(fields):
    """Essaie d'extraire le type de jugement (ex. « Liquidation judiciaire »)."""
    j = fields.get("jugement")
    if not j:
        return ""
    if isinstance(j, str):
        try:
            j = json.loads(j)
        except Exception:
            return ""
    if isinstance(j, dict):
        return j.get("type") or j.get("nature") or j.get("famille") or ""
    return ""


def _annonces_procedure(siren):
    """Liste des annonces de procédure collective pour ce SIREN (vide si aucune)."""
    if not siren:
        return []
    try:
        params = {"dataset": DATASET, "q": f'"{siren}"', "rows": 50}
        r = requests.get(BASE, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 2)))
            r = requests.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        annonces = []
        for rec in r.json().get("records", []):
            fields = rec.get("fields", {})
            famille = _sans_accents(fields.get("familleavis_lib") or "").lower()
            if "procedure" in famille:
                annonces.append({"date": fields.get("dateparution") or "",
                                 "type": _type_jugement(fields) or "Procédure collective"})
        return annonces
    except Exception as e:
        print(f"  [i] BODACC indisponible pour {siren} ({e}) — entreprise non exclue par précaution.")
        return []


def en_procedure_collective(siren):
    """True si au moins une annonce de procédure collective existe pour ce SIREN."""
    return len(_annonces_procedure(siren)) > 0


def filtrer(fiches):
    """Renvoie (fiches conservées, liste des exclusions détaillées)."""
    gardes, exclus = [], []
    for fiche in fiches:
        annonces = _annonces_procedure(fiche.get("siren"))
        if annonces:
            recent = sorted(annonces, key=lambda a: a.get("date") or "", reverse=True)[0]
            exclus.append({
                "siren": fiche.get("siren"),
                "raison_sociale": fiche.get("raison_sociale"),
                "ville": fiche.get("ville") or "",
                "motif": recent.get("type"),
                "date_annonce": recent.get("date"),
            })
        else:
            gardes.append(fiche)
        time.sleep(PAUSE_SECONDES)
    return gardes, exclus


def journaliser_exclusions(exclus, chemin):
    """Ajoute les entreprises exclues à un registre CSV cumulatif (sans doublon de SIREN)."""
    if not exclus:
        return
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    deja = set()
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8-sig") as f:
            for ligne in csv.DictReader(f, delimiter=";"):
                deja.add(ligne.get("siren"))
    nouveau = not os.path.exists(chemin)
    with open(chemin, "a", newline="", encoding="utf-8-sig" if nouveau else "utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if nouveau:
            w.writerow(["date_run", "siren", "raison_sociale", "ville", "motif", "date_annonce"])
        auj = datetime.date.today().isoformat()
        for e in exclus:
            if e["siren"] in deja:
                continue
            w.writerow([auj, e["siren"], e["raison_sociale"], e["ville"], e["motif"], e["date_annonce"]])
            deja.add(e["siren"])