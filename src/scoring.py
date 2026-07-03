"""
Brique 3 — Scoring de pertinence (grille Pauline, v1.0 du 22/06/2026).
======================================================================
Scoring PAR RÈGLES, déterministe et gratuit. Le score est la SOMME des points
des critères validés (échelle Pauline : Très élevée=4, Élevée=3, Moyenne=2, Faible=1).

⚠️ La grille de Pauline contient des critères que l'agent NE PEUT PAS mesurer
automatiquement avec la source gratuite (contact DRH/DAF, recrutement massif,
fusion/acquisition, levée de fonds, AT-MP, absentéisme, contrôle URSSAF, etc.).
Ne sont notés ici que les critères RÉELLEMENT disponibles dans la donnée publique :
    - Effectif        (tranche INSEE)
    - Secteur         (code NAF -> secteurs prioritaires de la grille)
    - Multi-sites     (nombre d'établissements > 1)
    - Convention complexe (convention renseignée ET secteur complexe)
    - Masse salariale (proxy : effectif élevé ou CA élevé)

Pondérations regroupées ci-dessous, faciles à ajuster avec Pauline.
"""

from src.referentiels import secteur_prioritaire, SECTEURS_COMPLEXES

# --- Pondérations (grille Pauline, ajustables) ----------------------------------
EFFECTIF_GE_100 = 4   # >= 100 salariés (Très élevée)
EFFECTIF_50_99 = 3    # 50-99 (Élevée)
EFFECTIF_LT_50 = 1    # < 50 (Faible)
MULTI_SITES = 4       # multi-établissements (Très élevée)
CONVENTION_COMPLEXE = 4
MASSE_SALARIALE = 4
SEUIL_CA_MASSE = 10_000_000  # CA à partir duquel on considère la masse salariale élevée

CODES_GE_100 = {"22", "31", "32", "41", "42", "51", "52", "53"}  # >= 100 salariés


def scorer(fiche):
    """Renvoie (score = somme des points, raison listant les critères validés)."""
    points = 0
    raisons = []

    # Effectif
    code = fiche.get("tranche_effectif_code")
    if code in CODES_GE_100:
        points += EFFECTIF_GE_100
        raisons.append(f"effectif ≥100 ({EFFECTIF_GE_100})")
    elif code == "21":
        points += EFFECTIF_50_99
        raisons.append(f"effectif 50-99 ({EFFECTIF_50_99})")
    else:
        points += EFFECTIF_LT_50
        raisons.append(f"effectif <50 ({EFFECTIF_LT_50})")

    # Secteur prioritaire
    secteur = secteur_prioritaire(fiche.get("naf"))
    if secteur:
        label, poids = secteur
        points += poids
        raisons.append(f"{label} ({poids})")

    # Multi-établissements
    if (fiche.get("nb_etablissements") or 0) > 1:
        points += MULTI_SITES
        raisons.append(f"multi-sites ({MULTI_SITES})")

    # Convention collective complexe (renseignée + secteur complexe)
    label_secteur = secteur[0] if secteur else None
    if fiche.get("conv_renseignee") == "Oui" and label_secteur in SECTEURS_COMPLEXES:
        points += CONVENTION_COMPLEXE
        raisons.append(f"convention complexe ({CONVENTION_COMPLEXE})")

    # Masse salariale importante (proxy : effectif élevé ou CA élevé)
    ca = fiche.get("chiffre_affaires")
    if code in CODES_GE_100 or (ca and ca >= SEUIL_CA_MASSE):
        points += MASSE_SALARIALE
        raisons.append(f"masse salariale élevée ({MASSE_SALARIALE})")

    return points, " · ".join(raisons)
