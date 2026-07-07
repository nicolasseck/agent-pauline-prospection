# Cartographie du projet — Agent de prospection G2S

> Vue d'ensemble technique du dépôt, générée pour s'orienter rapidement dans le code.
> Pour le suivi fonctionnel détaillé (statut par brique, décisions ouvertes), voir `README.md`.

## 1. Vue d'ensemble

Script Python **exécuté à la demande** (`python main.py`, pas de serveur ni de tâche
planifiée dans le repo — un `docker-compose.yaml`/`Dockerfile` existent pour packager
l'exécution). À chaque exécution, l'agent :

1. collecte de nouvelles entreprises correspondant à un ciblage (secteur, effectif,
   forme juridique, département) via l'API publique **Recherche d'Entreprises** ;
2. exclut celles en procédure collective (BODACC) ;
3. génère des liens de recherche pour trouver le contact DRH/DAF (pas d'extraction) ;
4. calcule un score de pertinence (règles déterministes, grille Pauline) ;
5. injecte les fiches dans **Pipedrive** (CRM), si activé ;
6. exporte un Excel et envoie une notification récapitulative (console + fichier +
   webhook Slack/Teams optionnel).

Aucune IA générative, aucune dépendance payante : uniquement des API publiques
gratuites (`requests`) et la mise en forme Excel (`openpyxl`).

## 2. Point d'entrée et flux de données

```
main.py
  │
  ├─ config/cibles.py ................ paramètres de ciblage (à éditer)
  │
  ├─ src/collecte.py ................. Brique 1 : appelle l'API, aplatit les résultats,
  │                                     gère la mémoire anti-doublons (SIREN déjà vus)
  │        │
  │        ▼ fiches (liste de dicts)
  │
  ├─ src/bodacc.py .................... exclut les entreprises en procédure collective
  │                                     (si EXCLURE_PROCEDURE_COLLECTIVE)
  │
  ├─ src/enrichissement.py ............ Brique 2 : ajoute lien_linkedin / lien_google
  │                                     par fiche (aucune donnée extraite)
  │
  ├─ src/scoring.py ................... Brique 3 : ajoute score + score_raison,
  │                                     tri par score décroissant, filtre SEUIL_RETENTION
  │
  ├─ src/pipedrive.py ................. Brique 5 : injecte dans le CRM (si INJECTER_PIPEDRIVE)
  │                                     — dédup interne SIRET/SIREN/raison sociale
  │
  ├─ src/export_excel.py .............. écrit data/sorties/prospects_AAAAMMJJ.xlsx
  │
  └─ src/notification.py .............. Brique 6 : récap console + data/sorties/recap_*.txt
                                        + webhook optionnel (NOTIF_WEBHOOK_URL)
```

`src/referentiels.py` est transverse : tables de correspondance (codes INSEE →
libellés, secteurs prioritaires, en-têtes Excel) utilisées par `collecte.py`,
`scoring.py` et `export_excel.py`.

`src/deduplication.py` est un squelette (TODO) : la dédup SIREN locale est déjà
faite dans `collecte.py`, il reste à synchroniser avec les SIREN déjà présents
dans Pipedrive au démarrage.

## 3. Fichier par fichier

| Fichier | Rôle | Points clés |
|---|---|---|
| `main.py` | Orchestrateur, point d'entrée unique | Enchaîne les briques 1→6, gère les stats du run |
| `config/cibles.py` | **Le fichier à éditer** pour changer le ciblage | `FILTRES_CIBLE`, `OBJECTIF_PAR_RUN`, `SEUIL_RETENTION`, flags `INJECTER_PIPEDRIVE` / `EXCLURE_PROCEDURE_COLLECTIVE` / `NOTIFIER` |
| `src/collecte.py` | Brique 1 — appel API + mémoire anti-doublons | `collecter()` pagine l'API ; `charger_siren_vus` / `sauver_siren_vus` persistent `data/memoire/siren_vus.json` |
| `src/bodacc.py` | Exclusion procédures collectives | Une requête BODACC par SIREN ; fail-open si API indisponible ; journalise dans `data/exclusions/procedures_collectives.csv` |
| `src/enrichissement.py` | Brique 2 (partielle) — liens de recherche contact | Génère des URL LinkedIn/Google cliquables, aucune extraction (conformité CGU/RGPD) |
| `src/scoring.py` | Brique 3 — scoring par règles | Somme de points pondérés (effectif, secteur, multi-sites, convention complexe, masse salariale) |
| `src/deduplication.py` | Brique 4 (squelette) | TODO : lire les SIREN déjà présents dans Pipedrive |
| `src/pipedrive.py` | Brique 5 — injection CRM | Mappe sur les champs existants chez Pauline, reste en note sinon ; dédup avant création |
| `src/export_excel.py` | Export Excel formaté | Colonnes pilotées par `referentiels.ENTETES` ; liens cliquables |
| `src/notification.py` | Brique 6 — récapitulatif | Toujours écrit en fichier ; webhook optionnel |
| `src/referentiels.py` | Tables de référence | Tranches d'effectif, sections NAF, secteurs prioritaires, formes juridiques, en-têtes Excel |
| `data/memoire/siren_vus.json` | Mémoire persistante | Ensemble des SIREN déjà collectés (jamais deux fois) |
| `data/exclusions/procedures_collectives.csv` | Registre cumulatif | Entreprises exclues pour procédure collective |
| `data/sorties/` | Sorties d'exécution | `prospects_AAAAMMJJ.xlsx`, `recap_AAAAMMJJ.txt` |
| `docs/cahier_des_charges.pdf` | Spécification d'origine | Réf. métier |
| `.env` / `.env.example` | Secrets locaux (non versionnés) | `PIPEDRIVE_TOKEN`, `NOTIF_WEBHOOK_URL` |
| `Dockerfile` / `docker-compose.yaml` | Packaging d'exécution | Conteneurise `python main.py` |

## 4. Sources externes (toutes gratuites, sans clé sauf Pipedrive)

- **API Recherche d'Entreprises** (DINUM) — `recherche-entreprises.api.gouv.fr` : collecte des entreprises (brique 1). Limite 7 req/s, pagination 25/page.
- **BODACC** (DILA, via Opendatasoft) — exclusion procédures collectives.
- **Pipedrive API v1** — injection CRM (nécessite `PIPEDRIVE_TOKEN`).
- **LinkedIn / Google** — uniquement des URL de recherche générées, jamais appelées côté serveur.

## 5. État des briques (résumé, voir README pour le détail)

✅ Collecte · 🟡 Enrichissement contact (partiel, humain dans la boucle) · ✅ Scoring
· ✅ Déduplication locale (Pipedrive à synchroniser) · 🟡 Injection Pipedrive (prête,
à valider en réel) · ✅ Notification.

## 6. Limites connues / dette

- Le ciblage géographique était figé sur un seul département (`departement` dans
  `FILTRES_CIBLE`) — épuisement rapide du vivier et prospects peu variés en cas
  d'exécutions répétées. **Voir section 7 pour la correction apportée.**
- Pas de contact DRH/DAF automatique (arbitrage RGPD/coût en attente).
- `src/deduplication.py` non câblé sur Pipedrive (TODO explicite dans le fichier).

## 7. Nouvelle fonctionnalité — diversité des recherches de prospects

Deux mécanismes ajoutés dans `src/collecte.py` / `config/cibles.py` / `main.py` pour
que deux exécutions successives ne renvoient jamais le même lot de prospects et
échantillonnent plus largement le vivier disponible :

1. **Rotation géographique automatique** — `DEPARTEMENTS_CIBLE` (liste, dans
   `config/cibles.py`) remplace l'ancien `departement` figé. Chaque exécution passe
   au département suivant dans la liste (round-robin), état persisté dans
   `data/memoire/rotation_departement.json`. Plus besoin d'éditer la config à la main
   quand un département s'épuise.
2. **Échantillonnage aléatoire des pages** — `collecter()` ne parcourt plus les pages
   de résultats de l'API dans l'ordre fixe 1, 2, 3… (ordre stable côté API, donc
   toujours les mêmes fiches en tête) mais dans un ordre mélangé à chaque appel, tout
   en explorant le même nombre de pages qu'avant si besoin pour atteindre l'objectif.

La garantie de non-répétition stricte reste la mémoire SIREN existante
(`data/memoire/siren_vus.json`) : un SIREN déjà proposé n'est plus jamais recollecté,
quel que soit le département ou l'ordre de pagination.
