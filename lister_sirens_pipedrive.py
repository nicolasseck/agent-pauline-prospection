"""
Utilitaire — liste les SIREN déjà présents dans Pipedrive.
============================================================
Affiche en console, sous forme de tableau, les organisations Pipedrive qui ont
le champ SIREN renseigné. Utile pour vérifier manuellement le contenu du CRM
(brique 4 — déduplication, voir src/deduplication.py : reste à câbler cette
liste en amont de la collecte pour ne jamais reproposer un SIREN déjà présent).

Usage (depuis la racine du projet) :
    python lister_sirens_pipedrive.py

Ne fait PAS partie de l'exécution normale de l'agent (main.py) : lecture seule,
n'injecte ni ne modifie rien dans Pipedrive.
"""

import os
from src.pipedrive import Pipedrive, charger_token

RACINE = os.path.dirname(os.path.abspath(__file__))


def _imprimer_tableau(lignes, entetes):
    if not lignes:
        print("Aucune organisation avec un SIREN renseigné dans Pipedrive.")
        return

    largeurs = [max(len(str(entetes[i])), max(len(str(ligne[i])) for ligne in lignes))
               for i in range(len(entetes))]

    def formater(valeurs):
        return [value[1] for value in enumerate(valeurs) ]

    print("  ".join("-" * l for l in largeurs))

    print ([(formater(ligne)[1]) for ligne in lignes] )
    print(f"\n{len(lignes)} organisation(s) avec SIREN.")


def main():
    try:
        pd = Pipedrive(charger_token(RACINE))
        lignes = pd.lister_organisations_siren()
    except Exception as e:
        print(f"[!] Impossible de récupérer les SIREN depuis Pipedrive : {e}")
        return
    _imprimer_tableau(lignes, ("Raison sociale", "SIREN"))


if __name__ == "__main__":
    main()
