# Agent IA de prospection commerciale — G2S

Agent qui récupère automatiquement des prospects qualifiés (secteur, effectif, forme
juridique, convention collective), les score, les dédoublonne et les injecte dans
Pipedrive, prêts à être travaillés — **avec un budget de zéro euro**.

> Document vivant : ce README est complété à chaque étape (voir *Journal d'avancement*).

---

## État d'avancement par brique

| # | Brique | Statut | Détail |
|---|--------|--------|--------|
| 1 | Collecte | ✅ Fait | API Recherche d'Entreprises (gratuite) + mémoire anti-doublons + export Excel |
| 2 | Enrichissement contact DRH/DAF | 🟡 Partiel | Liens de recherche LinkedIn + Google par entreprise (gratuit, conforme) ; email auto non résolu |
| 3 | Scoring (1-10) | ✅ Fait | Par règles déterministes (gratuit) ; tri par score + seuil de rétention configurable |
| 4 | Déduplication | ✅ Fait | Mémoire SIREN locale + vérification dans Pipedrive avant création |
| 5 | Injection Pipedrive | 🟡 Prêt | Codé et testé sur API simulée ; à activer avec le token + champs, puis valider en réel |
| 6 | Notification | ✅ Fait | Récap console + fichier ; webhook Slack/Teams en option |

---

## Structure du projet

```
agent_prospection_g2s/
├── README.md                  ← ce fichier
├── requirements.txt           dépendances (requests, openpyxl)
├── .gitignore
├── main.py                    orchestrateur — point d'entrée
├── config/
│   └── cibles.py              ⭐ paramètres de ciblage (§7) — LE fichier à éditer
├── src/
│   ├── collecte.py            brique 1 — collecte + mémoire anti-doublons
│   ├── enrichissement.py      brique 2 — (squelette)
│   ├── scoring.py             brique 3 — (squelette)
│   ├── deduplication.py       brique 4 — (squelette)
│   ├── pipedrive.py           brique 5 — (squelette)
│   ├── notification.py        brique 6 — (squelette)
│   ├── export_excel.py        export Excel formaté (sortie commune)
│   └── referentiels.py        tables de correspondance (codes INSEE → libellés)
├── data/
│   ├── memoire/
│   │   └── siren_vus.json     mémoire de l'agent (SIREN déjà collectés)
│   └── sorties/
│       └── prospects_AAAAMMJJ.xlsx   fichiers générés
└── docs/
    └── cahier_des_charges.pdf
```

---

## Installation

```bash
cd agent_prospection_g2s
python -m venv .venv && source .venv/bin/activate   # optionnel mais recommandé
pip install -r requirements.txt
```

## Utilisation

Depuis la racine du projet :

```bash
python main.py
```

Chaque exécution collecte de **nouveaux** prospects (jamais les mêmes deux fois
grâce à `data/memoire/siren_vus.json`) et écrit un Excel dans `data/sorties/`.

## Configurer le ciblage

Tout se règle dans **`config/cibles.py`** : secteurs, tranches d'effectif, forme,
département, objectif par run. Si un run ramène moins de prospects que l'objectif,
c'est que la cible s'épuise → changer de département ou de codes NAF.

---

## Source de données

**API Recherche d'Entreprises** (DINUM) — `https://recherche-entreprises.api.gouv.fr`
Gratuite, ouverte, sans clé. Remplace Pappers (payant). Fournit SIREN, NAF, forme
juridique, tranche d'effectif, CA, conventions collectives (IDCC), localisation,
mandataires sociaux. Limite : 7 req/s. Effectif en **tranche** (pas le chiffre exact).

---

## Décisions ouvertes (à arbitrer avec Pauline)

- **Contact DRH/DAF (brique 2).** Pas de solution gratuite + conforme RGPD à ~200
  contacts/mois. Choisir : (a) enrichir seulement les meilleurs scores dans un quota
  gratuit, (b) email générique deviné, ou (c) contact laissé au commercial.
- **Liste exacte des secteurs / codes NAF** à cibler (§7).
- **Règles de scoring** : qu'est-ce qu'un « bon » prospect (seuils effectif/CA, poids
  des secteurs et conventions).
- **Libellés IDCC** : afficher le nom de la convention à côté du code ? (table Kali).
- **Conformité RGPD** : base légale (intérêt légitime B2B) + process de suppression.
- **Statut judiciaire** : décidé avec Pauline — on **exclut** toutes les entreprises en
  procédure collective (via BODACC), en plus des entreprises cessées (déjà filtrées).

---

## Journal d'avancement

- **2026-06 — Injection adaptée aux champs de Pauline.** Le module Pipedrive mappe
  désormais nos données sur les champs DÉJÀ présents dans son compte (SIRET, Secteur
  d'activité, Chiffre d'affaires annuel, Nombre d'employés, Nom dirigeant, CCN, Profil
  LinkedIn, Adresse). Ajout d'une tolérance au TYPE : si un champ attend un nombre ou une
  liste d'options et que la valeur ne convient pas, l'info va dans la note (pas d'erreur).
  Dédup par SIRET → SIREN → raison sociale. Étape par défaut = « Nouvelle affaire ».
- **2026-06 — Brique 6 (notification).** Module `src/notification.py` : récapitulatif de
  fin d'exécution (collectés, exclus procédure collective, retenus, résultat Pipedrive,
  top prospects). Toujours affiché en console et enregistré dans `data/sorties/recap_*.txt` ;
  envoi en option vers Slack/Teams si `NOTIF_WEBHOOK_URL` est défini dans `.env`. Sans coût.
- **2026-06 — Exclusion des procédures collectives (BODACC).** Nouveau module
  `src/bodacc.py` : pour chaque SIREN, interroge l'API ouverte du BODACC et exclut
  l'entreprise si une annonce de la famille « Procédures collectives » (sauvegarde,
  redressement, liquidation) existe. Activé par `EXCLURE_PROCEDURE_COLLECTIVE`. Complète
  le filtre des entreprises cessées (`etat_administratif = A`). Gratuit ; fail-open si le
  BODACC est indisponible. Testé sur API simulée.
- **2026-06 — Brique 5 (injection Pipedrive).** Module `src/pipedrive.py` : lit le token
  via `.env`, retrouve seul les clés des champs personnalisés par leur nom, dédoublonne
  sur le SIREN, crée l'Organisation (champs perso + tag Source) et l'Affaire en étape
  « Nouveau lead » avec le score. **Tolérant aux champs** : utilise ceux qui existent et
  bascule le reste dans une note attachée à l'affaire — fonctionne avec 0, 2 ou 7 champs.
  Rejouable sans risque, gère le rate limit. Activable via `INJECTER_PIPEDRIVE`. Testé sur
  API simulée ; reste à valider en réel. Le contact (Personne) reste manuel (brique 2).
- **2026-06 — Scoring v2 (grille Pauline).** Intégration de la grille de qualification
  de Pauline (poids 4/3/2/1). Le score devient la somme des points des critères validés.
  Critères réellement automatisables retenus : effectif, secteur précis (NAF → déchets,
  propreté, intérim, transport, BTP, santé, sécurité, HCR), multi-établissements,
  convention complexe (renseignée + secteur complexe), masse salariale (proxy effectif/CA).
  Corrige le double comptage de l'ancienne version et exploite enfin le secteur précis.
  Collecte élargie en conséquence (sections E,F,H,I,N,Q ; effectif ≥ 50 dont 500+ ; GE inclus).
  NON automatisables (hors source gratuite) : contact DRH/DAF, recrutement/croissance,
  fusion-acquisition, levée de fonds, AT-MP, absentéisme, contrôle URSSAF — à traiter
  manuellement ou en phase 2.
- **2026-06 — Brique 2 (partielle).** Approche « humain dans la boucle » pour le
  contact DRH/DAF, gratuite et conforme : l'agent n'extrait rien de LinkedIn (scraping
  interdit par les CGU + risque CNIL), mais génère pour chaque entreprise un lien de
  recherche **LinkedIn** et **Google** (colonnes cliquables dans l'Excel, et après
  import dans Google Sheets). Pauline ouvre la recherche dans sa propre session,
  identifie et contacte le DRH/DAF (consultation manuelle = légale). Reste non résolu :
  l'email pro vérifié en automatique (pas de voie gratuite + conforme à ~200/mois).
- **2026-06 — Brique 3.** Scoring par règles (gratuit, sans IA payante) : note 1-10
  pondérée sur effectif, chiffre d'affaires, secteur, convention collective renseignée
  et complétude. Pondérations isolées en haut de `src/scoring.py`, à affiner avec Pauline.
  Résultats triés par score décroissant ; seuil de rétention configurable dans
  `config/cibles.py` (désactivé par défaut). Colonnes `Score` + `Justification` en tête
  de l'Excel ; l'export n'affiche que les colonnes déclarées (champs techniques masqués).
- **2026-06 — Brique 1.** Collecteur opérationnel sur l'API gratuite. Corrections vs
  cahier des charges : paramètre `activite_principale` (pas `code_naf`), effectif par
  code de tranche, `per_page` plafonné à 25, aucune clé requise. Ajout des conventions
  collectives (IDCC) + CA, nettoyage des dirigeants, export Excel formaté, et mémoire
  anti-doublons (SIREN persistés) pour ne ramener que des prospects nouveaux.
# agent-pauline-prospection
