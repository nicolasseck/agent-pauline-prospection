# Paramétrer l'agent depuis le fichier Excel / Google Sheet

Ce document explique **chaque ligne** du fichier de configuration externe
modèle : `docs/modele_config_prospection.xlsx`, à utiliser depuis un Google
Sheet. Il sert à changer le comportement de l'agent prospection **sans toucher au code**.

## Comment ça marche, en deux règles

1. **Une cellule "Valeur" vide (ou une ligne absente) = rien ne change** :
   l'agent garde le réglage écrit dans le code.
2. **Une cellule remplie remplace le réglage du code**, à condition d'être du
   bon format (voir le détail de chaque ligne ci-dessous). Une valeur du
   mauvais format est ignorée (avec un message dans les logs) plutôt que de
   faire planter l'agent — au pire, ça n'a aucun effet.

Le tableau a 3 colonnes : **Variable** (ne pas renommer, c'est le nom que le
code recherche), **Valeur** (ce qui est à modifier), **Description** (aide-
mémoire).

---

## Table de référence rapide

| Ligne (colonne "Variable") | Constante dans le code python | Format attendu | Lié à l'API gouvernementale ? |
|---|---|---|---|
| `section_activite_principale` | `FILTRES_CIBLE["section_activite_principale"]` | lettres séparées par des virgules | ✅ paramètre `section_activite_principale` |
| `tranche_effectif_salarie` | `FILTRES_CIBLE["tranche_effectif_salarie"]` | codes séparés par des virgules | ✅ paramètre `tranche_effectif_salarie` |
| `categorie_entreprise` | `FILTRES_CIBLE["categorie_entreprise"]` | codes séparés par des virgules | ✅ paramètre `categorie_entreprise` |
| `etat_administratif` | `FILTRES_CIBLE["etat_administratif"]` | une lettre | ✅ paramètre `etat_administratif` |
| `departements_cible` | `DEPARTEMENTS_CIBLE` | numéros de département séparés par des virgules | ✅ paramètre `departement` (un par exécution) |
| `objectif_par_run` | `OBJECTIF_PAR_RUN` | un nombre entier | ❌ usage interne uniquement |
| `seuil_retention` | `SEUIL_RETENTION` | un nombre entier, ou vide | ❌ usage interne uniquement |
| `injecter_pipedrive` | `INJECTER_PIPEDRIVE` | `Oui` ou `Non` | ❌ concerne Pipedrive, pas l'API gouvernementale |
| `exclure_procedure_collective` | `EXCLURE_PROCEDURE_COLLECTIVE` | `Oui` ou `Non` | ✅ mais l'API du **BODACC**, pas Recherche d'Entreprises |
| `notifier` | `NOTIFIER` | `Oui` ou `Non` | ❌ usage interne uniquement |

L'« API gouvernementale » principale est **Recherche d'Entreprises** (DINUM) :
`https://recherche-entreprises.api.gouv.fr/search` — gratuite, sans clé. C'est
elle qui fournit la liste des entreprises correspondant aux filtres. Le BODACC
(procédures collectives) est une API différente, gratuite elle aussi.

---

## Détail de chaque ligne

### `section_activite_principale` — quels secteurs d'activité cibler

Envoyé tel quel à l'API dans le paramètre `section_activite_principale`. Ce
sont des lettres de la nomenclature NAF (section), séparées par des virgules.
Valeur actuelle par défaut : `E,F,H,I,N,Q`.

| Lettre | Secteur |
|---|---|
| A | Agriculture, sylviculture, pêche |
| B | Industries extractives |
| C | Industrie manufacturière | 
| D | Énergie |
| E | Eau, déchets |
| F | Construction (BTP) |
| G | Commerce, réparation auto |
| H | Transports et entreposage |
| I | Hébergement et restauration |
| J | Information et communication |
| K | Activités financières et d'assurance |
| L | Activités immobilières |
| M | Activités scientifiques et techniques |
| N | Services administratifs et de soutien |
| O | Administration publique |
| P | Enseignement |
| Q | Santé humaine et action sociale |
| R | Arts, spectacles, loisirs |
| S | Autres activités de services |
| T | Activités des ménages employeurs |
| U | Activités extra-territoriales |

Pour cibler un autre secteur, ajouter sa lettre (ex. `G` = commerce).

### `tranche_effectif_salarie` — quelle taille d'entreprise (en nombre de salariés)

Envoyé à l'API dans le paramètre `tranche_effectif_salarie`. Ce sont des codes
INSEE de "tranche d'effectif", séparés par des virgules — pas le nombre exact
de salariés, l'INSEE ne le fournit que par tranche.

| Code | Tranche |
|---|---|
| NN | Non renseigné / non employeur |
| 00 | 0 salarié |
| 01 | 1 à 2 salariés |
| 02 | 3 à 5 salariés | 
| 03 | 6 à 9 salariés |
| 11 | 10 à 19 salariés |
| 12 | 20 à 49 salariés |
| 21 | 50 à 99 salariés |
| 22 | 100 à 199 salariés |
| 31 | 200 à 249 salariés |
| 32 | 250 à 499 salariés |
| 41 | 500 à 999 salariés |
| 42 | 1 000 à 1 999 salariés |
| 51 | 2 000 à 4 999 salariés |
| 52 | 5 000 à 9 999 salariés |
| 53 | 10 000 salariés et plus |

Valeur par défaut : `21,22,31,32,41,42,51,52,53` (50 salariés et plus). Pour
élargir à des entreprises plus petites, ajouter par exemple `12` (20 à 49
salariés).

### `categorie_entreprise` — quelle catégorie officielle d'entreprise

Envoyé à l'API dans le paramètre `categorie_entreprise`. Catégories officielles
INSEE, basées sur l'effectif ET le chiffre d'affaires :

- **PME** : Petite et Moyenne Entreprise
- **ETI** : Entreprise de Taille Intermédiaire
- **GE** : Grande Entreprise

Valeur par défaut : `PME,ETI,GE`. Retirer `GE` ici pour exclure les très grandes entreprises.

### `etat_administratif` — entreprise active ou non

Envoyé à l'API dans le paramètre `etat_administratif`. `A` = active, `C` =
cessée. **/!\ Ne pas mettre `C` /!\\** : l'agent perdrait tout son intérêt (il servirait
à démarcher des entreprises qui n'existent plus). Valeur par défaut et
recommandée : `A`.

### `departements_cible` — dans quels départements chercher

Envoyé à l'API dans le paramètre `departement` — mais **un seul département à
la fois**. Cette ligne définit la LISTE des départements à parcourir ; l'agent
passe automatiquement au département suivant à chaque exécution (mémorisé dans
par l'agent), pour ne pas épuiser le même bassin
d'entreprises à chaque recherche.

Format : numéros de département séparés par des virgules, ex. `971` (un seul
département, toujours le même à chaque exécution) ou `75,92,93,94,77,78,91,95`
(rotation sur plusieurs départements, un par exécution).

⚠️ Le filtre `departement` de l'API matche au niveau **établissement**, pas
uniquement siège social : une entreprise dont le siège est à Paris peut
apparaître dans une recherche "971" si elle a une agence en Guadeloupe.
L'agent affiche alors l'adresse de cet établissement local, pas celle du
siège.

### `objectif_par_run` — combien de nouveaux prospects par exécution

**Pas envoyé à l'API** — c'est une limite appliquée par l'agent lui-même
(nombre de résultats à collecter avant de s'arrêter). Un nombre entier, ex.
`50`. Plus ce nombre est élevé, plus l'exécution prend de temps (l'agent
interroge l'API par pages de 25 résultats).

### `seuil_retention` — score minimum pour garder un prospect

**Pas envoyé à l'API** — filtre appliqué après le calcul du score de
pertinence (Grille de Pauline, 0 à 20 points). Un nombre
entier, ex. `12` pour ne garder que les prospects cumulant plusieurs signaux
forts. **Laisser la cellule vide** pour ne rien perdre (comportement par
défaut : tous les prospects sont gardés, triés par score décroissant au moment de la suggestion).

### `injecter_pipedrive` — envoyer les prospects dans le CRM Pipedrive

**Sans lien avec l'API gouvernementale** — concerne uniquement l'injection
dans Pipedrive. `Oui` ou `Non`. Si `Non`, l'agent s'arrête à
l'export Excel, rien n'est envoyé dans Pipedrive.

### `exclure_procedure_collective` — écarter les entreprises en difficulté

Concerne une **autre API gouvernementale : le BODACC** (annonces légales des
procédures collectives — sauvegarde, redressement, liquidation judiciaires),
pas l'API Recherche d'Entreprises. `Oui` ou `Non`. Si `Oui` (recommandé), pour
chaque entreprise trouvée, l'agent vérifie sur le BODACC qu'elle n'est pas en
procédure collective avant de la proposer comme prospect.

### `notifier` — envoyer le récapitulatif de fin d'exécution

**Sans lien avec l'API gouvernementale**. `Oui` ou `Non`. Si `Oui`, un résumé
de l'exécution (nombre de prospects trouvés, top prospects, etc.) est affiché
en console, écrit dans `data/sorties/recap_AAAAMMJJ.txt`. Pour le consulter, contacter l'équipe Cortex, 
- Intégration V2 un message est envoyé sur Slack/Teams si un webhook est configuré (`NOTIF_WEBHOOK_URL` dans `.env`).

---

## Ce que cette configuration NE permet PAS de changer

Certains réglages restent uniquement dans le code (pas de ligne dédiée dans le
fichier externe) : les pondérations du score (`src/scoring.py`), les secteurs
prioritaires et leurs poids (`src/referentiels.py`), les champs Pipedrive
utilisés (`src/pipedrive.py`). Modifier ces points nécessite de changer le
code directement. Certaines fonctionnalités peuvent faire l'objet d'une intégration pour la V2 du Bot.
