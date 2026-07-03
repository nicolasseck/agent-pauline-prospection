"""
Orchestrateur de l'agent de prospection G2S.
=============================================
Point d'entrée. Lancer DEPUIS LA RACINE du projet :

    python main.py

Chaîne complète : collecte (1) -> exclusion procédures collectives (BODACC) ->
liens contact (2) -> scoring (3) -> injection Pipedrive (5, si activée) ->
export Excel -> notification (6).
"""

import os
from datetime import date

from config.cibles import (FILTRES_CIBLE, OBJECTIF_PAR_RUN, SEUIL_RETENTION,
                           INJECTER_PIPEDRIVE, EXCLURE_PROCEDURE_COLLECTIVE, NOTIFIER)
from src.collecte import charger_siren_vus, sauver_siren_vus, collecter, aplatir
from src.enrichissement import liens_recherche
from src.scoring import scorer
from src.export_excel import exporter_xlsx

RACINE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_MEMOIRE = os.path.join(RACINE, "data", "memoire", "siren_vus.json")
DOSSIER_SORTIES = os.path.join(RACINE, "data", "sorties")


def main():
    stats = {"collectes": 0, "exclus_pc": 0, "injection": None}

    # --- Brique 1 : Collecte (avec mémoire anti-doublons) -----------------------
    siren_vus = charger_siren_vus(CHEMIN_MEMOIRE)
    print(f"Mémoire : {len(siren_vus)} entreprise(s) déjà collectée(s) (ignorées).")

    print("Brique 1 — Collecte (API Recherche d'Entreprises, gratuite)...")
    brut = collecter(FILTRES_CIBLE, max_resultats=OBJECTIF_PAR_RUN, siren_exclus=siren_vus)
    fiches = [aplatir(e) for e in brut]
    stats["collectes"] = len(fiches)

    nouveaux = {f["siren"] for f in fiches if f["siren"]}
    siren_vus |= nouveaux
    sauver_siren_vus(siren_vus, CHEMIN_MEMOIRE)

    # --- Exclusion des procédures collectives (BODACC) --------------------------
    if EXCLURE_PROCEDURE_COLLECTIVE and fiches:
        from src.bodacc import filtrer, journaliser_exclusions
        print("Vérification BODACC (procédures collectives)...")
        fiches, exclus = filtrer(fiches)
        stats["exclus_pc"] = len(exclus)
        if exclus:
            chemin_log = os.path.join(RACINE, "data", "exclusions", "procedures_collectives.csv")
            journaliser_exclusions(exclus, chemin_log)
            print(f"  {len(exclus)} entreprise(s) en procédure collective exclue(s) "
                  f"— tracée(s) dans data/exclusions/procedures_collectives.csv")

    # --- Brique 2 (partielle) : liens de recherche du contact DRH/DAF -----------
    for f in fiches:
        f.update(liens_recherche(f))

    # --- Brique 3 : Scoring + tri par pertinence --------------------------------
    print("Brique 3 — Scoring par règles (grille Pauline)...")
    for f in fiches:
        f["score"], f["score_raison"] = scorer(f)
    fiches.sort(key=lambda f: f["score"], reverse=True)

    if SEUIL_RETENTION is not None:
        avant = len(fiches)
        fiches = [f for f in fiches if f["score"] >= SEUIL_RETENTION]
        print(f"  Rétention >= {SEUIL_RETENTION} : {len(fiches)}/{avant} prospects conservés.")

    # --- Brique 5 : Injection Pipedrive (si activée) ----------------------------
    if INJECTER_PIPEDRIVE:
        from src.pipedrive import Pipedrive, charger_token
        print("Brique 5 — Injection dans Pipedrive...")
        try:
            pd = Pipedrive(charger_token(RACINE))
            stats["injection"] = pd.injecter(fiches)
            r = stats["injection"]
            print(f"  Pipedrive : {r['crees']} créé(s), "
                  f"{r['ignores']} doublon(s) ignoré(s), {r['erreurs']} erreur(s).")
        except Exception as e:
            print(f"  [!] Injection non effectuée : {e}")

    # --- Sortie Excel -----------------------------------------------------------
    sortie = os.path.join(DOSSIER_SORTIES, f"prospects_{date.today():%Y%m%d}.xlsx")
    exporter_xlsx(fiches, sortie)

    # --- Brique 6 : Notification ------------------------------------------------
    if NOTIFIER:
        from src.notification import notifier
        notifier(stats, fiches, DOSSIER_SORTIES, RACINE)

    if len(nouveaux) < OBJECTIF_PAR_RUN:
        print("[i] Cible en cours d'épuisement — changez de département/NAF dans config/cibles.py.")


if __name__ == "__main__":
    main()
