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
    "departement": "75",                                         # secteur test : Paris — à faire tourner
    # "convention_collective_renseignee": True,                  # ne garder que les CC connues
    # "ca_min": 5_000_000,                                        # proxy de masse salariale
}

# Nombre de NOUVEAUX prospects visés par exécution (objectif commercial : 50/sem.).
OBJECTIF_PAR_RUN = 20

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
