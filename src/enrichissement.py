"""
Brique 2 — Enrichissement / identification du contact (DRH / DAF).
==================================================================

PARTIE FAITE (gratuite + conforme) : pour chaque entreprise, l'agent génère des
LIENS DE RECHERCHE (LinkedIn + Google) vers le DRH/DAF. Il n'extrait RIEN : il
prépare la recherche, et Pauline l'ouvre dans sa session pour identifier puis
contacter la personne. La consultation manuelle de profils publics est légale ;
le scraping automatisé, lui, est interdit (CGU LinkedIn) et risqué (CNIL).

PARTIE NON RÉSOLUE : récupération automatique de l'email pro vérifié — pas de
solution à la fois gratuite et conforme à ~200/mois. Décision en attente (README).
"""

from urllib.parse import quote

# Fonctions ciblées par la recherche (modifiable, à valider avec Pauline).
FONCTIONS_CIBLES = [
    "DRH", "DAF",
    '"directeur des ressources humaines"',
    '"directeur administratif et financier"',
]


def liens_recherche(fiche):
    """Construit les URL de recherche du contact pour une entreprise.
    Aucune donnée n'est récupérée : on fabrique seulement des liens à cliquer."""
    raison = (fiche.get("raison_sociale") or "").strip()
    fonctions = " OR ".join(FONCTIONS_CIBLES)

    # Recherche de personnes sur LinkedIn (par mots-clés, session de l'utilisateur).
    kw_linkedin = f'({fonctions}) "{raison}"'
    lien_linkedin = ("https://www.linkedin.com/search/results/people/?keywords="
                     + quote(kw_linkedin))

    # Recherche Google ciblant les profils LinkedIn (dork).
    requete_google = f'({fonctions}) "{raison}" site:linkedin.com/in'
    lien_google = "https://www.google.com/search?q=" + quote(requete_google)

    return {"lien_linkedin": lien_linkedin, "lien_google": lien_google}
