"""
Paramètres de ciblage — §7 du cahier des charges + grille Pauline (v1.0).
=========================================================================
C'EST LE FICHIER À ÉDITER pour changer qui l'agent va chercher.
À affiner avec Pauline en fonction des retours terrain.
"""

# Filtres de collecte envoyés à l'API Recherche d'Entreprises.
# Sections couvrant les secteurs prioritaires de Pauline :
#   E = déchets · F = BTP · H = transport-logistique · I = HCR
#   N = intérim/propreté/sécurité/services aux entreprises · Q = santé & médico-social
# (Le scoring affine ensuite au niveau du code NAF précis.)
FILTRES_CIBLE = {
    "section_activite_principale": "E,F,H,I,N,Q",
    "tranche_effectif_salarie": "21,22,31,32,41,42,51,52,53",  # 50 salariés et plus (500+ inclus)
    "categorie_entreprise": "PME,ETI,GE",                       # GE inclus : Pauline priorise les grands comptes
    "etat_administratif": "A",                                   # entreprises actives uniquement
    # "departement" est ajouté automatiquement par main.py à partir de DEPARTEMENTS_CIBLE
    # (rotation géographique, voir plus bas) — ne pas le fixer ici.
    # "convention_collective_renseignee": True,                  # ne garder que les CC connues
    # "ca_min": 5_000_000,                                        # proxy de masse salariale
}

# Rotation géographique : départements parcourus tour à tour, un par exécution, pour
# que deux recherches successives ne portent jamais sur le même bassin d'entreprises
# et que les prospects proposés soient plus variés (au lieu de rester bloqué sur "75"
# jusqu'à épuisement du vivier). Le dernier département utilisé est mémorisé dans
# data/memoire/rotation_departement.json ; à chaque run, l'agent passe au suivant.
# Ajouter des départements ici quand un run ramène moins que OBJECTIF_PAR_RUN.
DEPARTEMENTS_CIBLE = ["75", "92", "93", "94", "77", "78", "91", "95"]  # Île-de-France

# Nombre de NOUVEAUX prospects visés par exécution (objectif commercial : 50/sem.).
OBJECTIF_PAR_RUN = 3

# Seuil de rétention sur le score de priorité (somme de points, max 20 pour les
# critères automatisables) :
#   None -> on garde tous les prospects (triés par score décroissant).
#   12   -> on ne garde que les prospects cumulant plusieurs signaux forts.
# Laissé à None pour ne rien perdre avant l'arbitrage de Pauline.
SEUIL_RETENTION = None

# Injection Pipedrive (brique 5). Passer à True une fois le token (.env) en place
# et les champs créés côté CRM. False = on s'arrête à l'Excel.
INJECTER_PIPEDRIVE = True

# Exclure les entreprises en procédure collective (sauvegarde, redressement,
# liquidation) via le BODACC. Demandé par Pauline : ces prospects ne servent à rien.
EXCLURE_PROCEDURE_COLLECTIVE = True

# Notification de fin d'exécution (récapitulatif). Toujours affiché + enregistré en
# fichier ; envoi vers Slack/Teams en plus si NOTIF_WEBHOOK_URL est défini dans .env.
NOTIFIER = True
