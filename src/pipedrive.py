"""
Brique 5 — Injection dans Pipedrive (sortie CRM).
==================================================
S'ADAPTE AUX CHAMPS EXISTANTS de Pipedrive : le module mappe nos données sur les
noms de champs présents chez Pauline, utilise ceux qui existent, et bascule le
reste dans une NOTE attachée à l'affaire. Il est aussi TOLÉRANT AU TYPE : si un
champ attend un nombre (ou une liste d'options) et que notre valeur ne convient
pas, l'info part dans la note plutôt que de provoquer une erreur.

Sécurité :
    - Token lu via PIPEDRIVE_TOKEN ou un fichier .env. Jamais en dur.
    - Déduplication sur le SIRET si le champ existe, sinon le SIREN, sinon la raison sociale.
    - Les clés techniques des champs sont retrouvées seules, par leur nom.

Le contact (Personne) n'est PAS créé ici (identification manuelle, brique 2).
"""

import os
import time
import requests

BASE = "https://api.pipedrive.com/v1"

# Correspondance : clé de fiche -> nom du champ tel qu'il existe (ou existera) dans
# Pipedrive. On privilégie les champs déjà présents chez Pauline ; les champs absents
# partent dans la note en attendant une éventuelle création manuelle.
CHAMPS_ORG = {
    "siret": "SIRET",
    "siren": "SIREN",                               # absent chez Pauline -> note
    "naf": "Code NAF",                              # absent chez Pauline -> note (code NAF)
    "secteur_activite": "Secteur d'activités",
    "chiffre_affaires": "Chiffre d'affaires",
    "tranche_effectif": "Nombre d'employés",
    "forme_juridique": "Forme juridique",           # absent -> note
    "conventions_idcc": "CCN",
    "conventions_idcc_url": "Lien CCN (Légifrance)",  # absent -> note ; sinon cliquable comme le champ adresse
    "dirigeants": "Nom dirigeant",
    "source": "Source",                             # absent -> note
    "lien_linkedin": "Profil LinkedIn",
    "lien_google": "Recherche Google (DRH/DAF)",    # absent -> note
    "lien_site_web": "Site web",               # absent -> note
}
CHAMP_DEAL_SCORE = "Score de pertinence"
VALEUR_SOURCE = "Agent IA"
ETAPE_NOUVEAU_LEAD = "Nouvelle affaire"  # 1re étape du pipeline de Pauline


def charger_token(racine=None):
    """Récupère le token : variable d'environnement, sinon fichier .env."""
    token = os.environ.get("PIPEDRIVE_TOKEN")
    if token:
        return token.strip()
    racine = racine or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chemin_env = os.path.join(racine, ".env")
    if os.path.exists(chemin_env):
        with open(chemin_env, encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne.startswith("PIPEDRIVE_TOKEN") and "=" in ligne:
                    return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Token Pipedrive introuvable (ni PIPEDRIVE_TOKEN, ni .env).")


def _est_nombre(valeur):
    if isinstance(valeur, (int, float)):
        return True
    return str(valeur).replace(" ", "").replace(".", "", 1).replace(",", "", 1).isdigit()


class Pipedrive:
    def __init__(self, token):
        self.token = token
        self._org = None
        self._deal = None
        self._stage_id = None
        self._avert_id = False

    def _req(self, methode, chemin, params=None, json=None):
        params = dict(params or {})
        params["api_token"] = self.token
        for _ in range(5):
            r = requests.request(methode, f"{BASE}{chemin}", params=params, json=json, timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 2)))
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("Trop de tentatives (rate limit) sur Pipedrive.")

    @staticmethod
    def _indexer(champs):
        index = {}
        for c in champs:
            options = {o["label"].lower(): o["id"] for o in (c.get("options") or [])}
            index[c["name"]] = {"key": c["key"], "type": c.get("field_type"), "options": options}
        return index

    def _charger_champs(self):
        if self._org is None:
            self._org = self._indexer(self._req("GET", "/organizationFields")["data"])
            self._deal = self._indexer(self._req("GET", "/dealFields")["data"])

    def _valeur(self, champ_def, valeur):
        """Formate la valeur selon le TYPE réel du champ.
        Renvoie None si la valeur ne convient pas au type (=> à mettre en note)."""
        if valeur in (None, ""):
            return None
        t = champ_def.get("type")
        if t in ("enum", "set"):
            opt = champ_def["options"].get(str(valeur).lower())
            if opt is None:
                return None
            return opt if t == "enum" else [opt]
        if t in ("double", "monetary", "int"):
            if not _est_nombre(valeur):
                return None
            return valeur if isinstance(valeur, (int, float)) else float(str(valeur).replace(",", "."))
        return str(valeur)  # varchar, text, address, phone, etc.

    def id_etape_nouveau_lead(self):
        if self._stage_id is None:
            stages = self._req("GET", "/stages")["data"] or []
            cible = next((s for s in stages if s["name"].strip().lower() == ETAPE_NOUVEAU_LEAD.lower()), None)
            self._stage_id = (cible or stages[0])["id"] if stages else None
        return self._stage_id

    def existe_deja(self, fiche):
        """Dédup par SIRET, sinon SIREN, sinon raison sociale."""
        for cle_id, nom in (("siret", "SIRET"), ("siren", "SIREN")):
            if nom in self._org and fiche.get(cle_id):
                res = self._req("GET", "/organizations/search",
                                params={"term": fiche[cle_id], "fields": "custom_fields", "exact_match": "true"})
                return bool((res.get("data") or {}).get("items"))
        if not self._avert_id:
            print("  [i] Ni champ SIRET ni SIREN : dédup par raison sociale (moins fiable).")
            self._avert_id = True
        nom = fiche.get("raison_sociale")
        if not nom:
            return False
        res = self._req("GET", "/organizations/search",
                        params={"term": nom, "fields": "name", "exact_match": "true"})
        return bool((res.get("data") or {}).get("items"))

    def creer_organisation(self, fiche, note_lignes):
        corps = {"name": fiche.get("raison_sociale") or fiche.get("siren")}
        adresse = " ".join(str(fiche.get(k) or "") for k in ("adresse", "code_postal", "ville")).strip()
        if adresse:
            corps["address"] = adresse
        for cle_fiche, nom_champ in CHAMPS_ORG.items():
            brut = VALEUR_SOURCE if cle_fiche == "source" else fiche.get(cle_fiche)
            if brut in (None, ""):
                continue
            champ = self._org.get(nom_champ)
            val = self._valeur(champ, brut) if champ else None
            if val is not None:
                corps[champ["key"]] = val          # champ présent + type compatible
            else:
                note_lignes.append(f"{nom_champ} : {brut}")  # absent ou type incompatible
        return self._req("POST", "/organizations", json=corps)["data"]["id"]

    def creer_affaire(self, org_id, fiche, note_lignes):
        corps = {"title": f"{fiche.get('raison_sociale')} — prospection", "org_id": org_id}
        stage = self.id_etape_nouveau_lead()
        if stage:
            corps["stage_id"] = stage
        if fiche.get("score") is not None:
            champ = self._deal.get(CHAMP_DEAL_SCORE)
            val = self._valeur(champ, fiche["score"]) if champ else None
            if val is not None:
                corps[champ["key"]] = val
            else:
                note_lignes.append(f"{CHAMP_DEAL_SCORE} : {fiche['score']}")
        return self._req("POST", "/deals", json=corps)["data"]["id"]

    def creer_note(self, deal_id, lignes):
        if not lignes:
            return
        contenu = "Fiche Agent IA\n" + "\n".join(lignes)
        self._req("POST", "/notes", json={"content": contenu, "deal_id": deal_id})

    def injecter(self, fiches):
        self._charger_champs()
        resume = {"crees": 0, "ignores": 0, "erreurs": 0}
        for fiche in fiches:
            try:
                if self.existe_deja(fiche):
                    resume["ignores"] += 1
                    continue
                note_lignes = []
                org_id = self.creer_organisation(fiche, note_lignes)
                deal_id = self.creer_affaire(org_id, fiche, note_lignes)
                self.creer_note(deal_id, note_lignes)
                resume["crees"] += 1
                time.sleep(0.2)
            except Exception as e:
                resume["erreurs"] += 1
                print(f"  [!] {fiche.get('raison_sociale')} : {e}")
        return resume