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
│   │   ├── siren_vus.json             mémoire de l'agent (SIREN déjà collectés)
│   │   └── rotation_departement.json  dernier département utilisé (rotation)
│   ├── convetions_c/
│   │   └── convention.json    export Légifrance (noms + liens des CCN par IDCC)
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

**Alternative sans toucher au code** : si `CONFIG_SHEET_URL` est défini dans
`.env`, ses valeurs remplacent celles de `config/cibles.py` — ligne par ligne,
une ligne vide ou absente laissant la valeur du code inchangée. **En production
(conteneur Docker chez un hébergeur), ce doit être un lien Google Sheet** — pas
un fichier OneDrive : le tenant Microsoft 365 de G2S interdit les liens de
partage anonymes, un Google Sheet n'est pas concerné (compte Google, pas le
tenant G2S). N'importe quel lien Google Sheets standard convient (le lien
"Copier le lien" du bouton Partager) — il est converti automatiquement en URL
d'export CSV. Seule condition : partagé en lecture pour **"Toute personne
disposant du lien"** (pas "Accès restreint", sinon Google redirige vers une
page de connexion que le conteneur ne peut pas franchir). Un fichier `.xlsx`
local reste accepté, uniquement pour des tests hors conteneur. Voir
`config/surcharge_config.py` pour le format exact des lignes reconnues.

**Fichier modèle** : `docs/modele_config_prospection.xlsx` (pré-rempli avec les
valeurs actuelles de `config/cibles.py`, une colonne "Description" par ligne).
Pauline l'importe dans un nouveau Google Sheet (Fichier > Importer), l'ajuste,
le partage ("Toute personne disposant du lien", rôle Lecteur), puis colle le
lien copié dans `CONFIG_SHEET_URL`. Régénérable avec
`python config/generer_modele_excel.py` si les valeurs par défaut de
`config/cibles.py` changent.

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
- **Libellés IDCC** : ✅ fait, sourcé depuis un export Légifrance couvrant 408
  IDCC (voir journal 2026-07) ; un code absent reste affiché tel quel.
- **Conformité RGPD** : base légale (intérêt légitime B2B) + process de suppression.
- **Statut judiciaire** : décidé avec Pauline — on **exclut** toutes les entreprises en
  procédure collective (via BODACC), en plus des entreprises cessées (déjà filtrées).

---

## Journal d'avancement

- **2026-07 — Adresse affichée = établissement correspondant, pas toujours le
  siège.** Bug détecté en filtrant sur un département d'outre-mer (971) : des
  entreprises dont le SIÈGE est à Paris (ex. MASFIP) apparaissaient dans les
  résultats, avec l'adresse du siège affichée — trompeur, car le filtre
  `departement` de l'API Recherche d'Entreprises matche au niveau
  ÉTABLISSEMENT, pas siège (MASFIP a une antenne DRFIP en Guadeloupe qui a fait
  matcher la recherche). `src/collecte.py` : nouvelle fonction
  `_etablissement_pertinent()` — cherche dans `matching_etablissements` le
  premier établissement ACTIF qui n'est PAS le siège et affiche SON adresse
  (`adresse`, `code_postal`, `ville`, `departement`) ; à défaut, retombe sur le
  siège comme avant (aucune régression pour les entreprises mono-site). Le
  SIRET reste volontairement celui du siège (identité légale, dédup Pipedrive).
- **2026-07 — Configuration externe via Google Sheet.** Nouveau module
  `config/surcharge_config.py` : si `CONFIG_SHEET_URL` (`.env`) est défini, ses
  valeurs remplacent celles de `config/cibles.py` au chargement — variable par
  variable, une ligne vide ou absente laissant la valeur du code inchangée. Une
  valeur invalide (mauvais type, booléen non reconnu) est ignorée avec un
  message, jamais bloquante. Objectif : Pauline ajuste le ciblage sans toucher
  au code. Sans `CONFIG_SHEET_URL`, aucun changement de comportement.
  **Détour OneDrive/SharePoint abandonné** : premier essai avec un lien de
  partage OneDrive téléchargé par HTTP, mais le tenant Microsoft 365 de G2S
  interdit les liens "Toute personne disposant du lien" (constaté à l'écran de
  partage — seules les options "personnes de l'organisation" ou "personnes
  choisies" existent, toutes deux nécessitant une authentification qu'un
  conteneur non interactif ne peut pas fournir sans API Graph + app
  registration). Solution retenue à la place : un **Google Sheet partagé**
  ("Toute personne disposant du lien", rôle Lecteur), hors de la politique de
  partage du tenant G2S puisque c'est un compte Google — le conteneur le
  télécharge par un simple GET HTTP (`requests`), sans authentification. Un
  fichier `.xlsx` local reste accepté en plus, pour tester hors conteneur.
  `docker-compose.yaml` transmet la variable au conteneur. Fichier modèle :
  `docs/modele_config_prospection.xlsx`, généré par
  `config/generer_modele_excel.py`, à importer dans Google Sheets.
  **Correctif** : `CONFIG_SHEET_URL` acceptait initialement seulement une URL
  de publication CSV (Fichier > Partager > Publier sur le web), une étape
  cachée que Pauline n'avait pas suivie — collé le lien "Copier le lien"
  standard, le code parsait alors du HTML comme du CSV sans erreur mais sans
  rien appliquer non plus (silencieux, trompeur). `config/surcharge_config.py`
  convertit désormais automatiquement n'importe quel lien Google Sheets
  standard vers l'URL d'export CSV, et signale explicitement le cas "0
  variable reconnue" plutôt que d'afficher un faux message de succès.
- **2026-07 — Lien Légifrance de la convention collective.** Répond à l'ancienne
  décision ouverte « afficher le nom de la convention à côté du code IDCC ? ».
  `src/referentiels.py` charge désormais `data/convetions_c/convention.json` (export
  Légifrance, 408 IDCC couverts) au lieu d'une table figée dans le code : pour
  chaque IDCC, on retient le texte de convention encore EN VIGUEUR (pas un
  avenant isolé, pas un texte abrogé/dénoncé/périmé) et son URL Légifrance
  d'origine. Chargé une fois puis mis en cache (`libelle_idcc()` /
  `lien_legifrance_idcc()`). Un code absent du fichier reste affiché tel quel. La
  colonne « Convention(s) collective(s) » reste du texte brut (nom si connu, sinon
  code) ; quand
  l'entreprise n'a qu'une seule CCN reconnue, une colonne dédiée « Lien Légifrance
  (CCN) » apparaît en plus (même mécanique que les colonnes lien_linkedin /
  lien_google / lien_site_web : libellé fixe « Ouvrir Légifrance », cliquable).
  Si plusieurs CCN ou code inconnu, pas de lien (pas de choix arbitraire entre
  plusieurs conventions). Côté Pipedrive, l'URL part dans un champ dédié (« Lien
  CCN (Légifrance) »), comme le champ adresse : directement cliquable sur la
  fiche organisation, pas besoin d'ouvrir une note — absent chez Pauline -> note,
  comme les autres champs optionnels. Le champ « CCN » garde le nom en texte brut
  pour la recherche/le filtrage.
- **2026-07 — Lien site internet de l'entreprise.** Ajout d'une colonne
  `lien_site_web` (Excel + note Pipedrive) : comme pour le contact DRH/DAF, l'API
  gratuite ne fournit pas l'URL du site et un domaine deviné serait trop souvent
  faux, donc l'agent génère un lien de recherche Google (raison sociale + ville)
  cliquable depuis `src/enrichissement.py`. Aucune extraction.
- **2026-07 — Diversité des recherches de prospects.** Deux changements dans
  `src/collecte.py` pour ne plus retomber sur les mêmes prospects (ou des prospects
  trop similaires) d'une exécution à l'autre : (1) le département ciblé tourne
  automatiquement à chaque run parmi `DEPARTEMENTS_CIBLE` (config/cibles.py), état
  mémorisé dans `data/memoire/rotation_departement.json`, au lieu du `departement`
  unique et figé ; (2) les pages de résultats de l'API sont explorées dans un ordre
  mélangé plutôt que 1, 2, 3... systématiquement, pour échantillonner plus largement
  le vivier disponible. La mémoire SIREN (`data/memoire/siren_vus.json`) reste la
  garantie stricte de non-répétition. Voir `carte.md` §7.
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
