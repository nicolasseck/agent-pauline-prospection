"""
Brique 4 — Déduplication.
=========================
STATUT : partiel.

Fait : la collecte tient déjà une mémoire locale des SIREN vus
       (data/memoire/siren_vus.json) -> pas de re-collecte des mêmes entreprises.

Reste à faire : synchroniser cette mémoire avec Pipedrive.
    - Au démarrage, initialiser siren_vus avec les SIREN déjà présents dans le CRM
      (recherche par SIREN ou email) pour ne jamais re-proposer un prospect existant.
    - Sera câblé en même temps que la brique 5 (injection Pipedrive).
"""

# TODO : def siren_existants_pipedrive() -> set[str]
