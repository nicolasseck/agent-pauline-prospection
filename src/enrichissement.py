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

SITE INTERNET DE L'ENTREPRISE : même logique — l'API de collecte (gratuite) ne
fournit pas l'URL du site, et un domaine deviné à partir de la raison sociale
serait trop souvent faux ou renverrait vers un autre site. On génère donc un
lien de recherche Google (raison sociale + ville) que Pauline ouvre pour
retrouver le site officiel en un clic.
"""

import re
from urllib.parse import quote

# Fonctions ciblées par la recherche (modifiable, à valider avec Pauline).
FONCTIONS_CIBLES = [
    "DRH", "DAF",
    '"directeur des ressources humaines"',
    '"directeur administratif et financier"',
]


def _nettoyer(texte):
    """Retire les guillemets doubles (non échappables dans une recherche
    LinkedIn/Google) pour ne pas casser la syntaxe de la requête."""
    return (texte or "").replace('"', "").strip()


def _bloc_entreprise(raison):
    """Construit le bloc de requête pour le nom d'entreprise.

    - Si la raison sociale contient un sigle entre parenthèses (ex:
      "... (SOCATRA)"), on l'extrait pour le chercher en OR séparément :
      personne n'écrit son entreprise avec la parenthèse sur son profil.
    - Si la raison sociale est vide après nettoyage, on renvoie une chaîne
      vide : le bloc est alors simplement omis de la requête plutôt que de
      produire des guillemets vides ('""').
    """
    match = re.search(r"\(([^)]+)\)", raison or "")
    nom_sans_sigle = _nettoyer(re.sub(r"\s*\([^)]+\)", "", raison or ""))

    if not nom_sans_sigle:
        return ""

    if match:
        sigle = _nettoyer(match.group(1))
        if sigle:
            return f'("{nom_sans_sigle}" OR "{sigle}")'

    return f'"{nom_sans_sigle}"'


def lien_site_officiel(fiche):
    """Lien de recherche Google vers le site officiel de l'entreprise (aucune
    extraction, aucun domaine deviné : voir note en tête de fichier)."""
    raison = (fiche.get("raison_sociale") or "").strip()
    ville = _nettoyer(fiche.get("ville") or "")
    entreprise = _bloc_entreprise(raison)

    parties = [p for p in [entreprise, ville, "site officiel"] if p]
    requete = " ".join(parties)
    return "https://www.google.com/search?q=" + quote(requete)


def liens_recherche(fiche):
    """Construit les URL de recherche (contact DRH/DAF + site internet) pour une
    entreprise. Aucune donnée n'est récupérée : on fabrique seulement des liens
    à cliquer.

    Si la raison sociale est vide ou illisible après nettoyage, les liens
    LinkedIn/Google ciblant le contact renvoient None : sans nom d'entreprise,
    la recherche ne serait plus "ciblée" mais un simple listing de DRH/DAF,
    ce qui n'a pas de valeur pour Pauline.
    """
    raison = (fiche.get("raison_sociale") or "").strip()
    fonctions = " OR ".join(FONCTIONS_CIBLES)
    entreprise = _bloc_entreprise(raison)

    if not entreprise:
        lien_linkedin = None
        lien_google = None
    else:
        # Recherche de personnes sur LinkedIn (par mots-clés, session utilisateur).
        kw_linkedin = f'({fonctions}) AND {entreprise}'
        lien_linkedin = ("https://www.linkedin.com/search/results/people/?keywords="
                         + quote(kw_linkedin))

        # Recherche Google ciblant les profils LinkedIn (dork).
        requete_google = f'({fonctions}) AND {entreprise} site:linkedin.com/in'
        lien_google = "https://www.google.com/search?q=" + quote(requete_google)

    return {
        "lien_linkedin": lien_linkedin,
        "lien_google": lien_google,
        "lien_site_web": lien_site_officiel(fiche),
    }