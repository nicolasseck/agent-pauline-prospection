"""
Brique 6 — Notification (récapitulatif de fin d'exécution).
===========================================================
À chaque exécution, l'agent produit un récapitulatif :
    - affiché dans la console,
    - enregistré dans data/sorties/recap_AAAAMMJJ.txt (toujours, gratuit, sans config),
    - envoyé en option vers un canal d'équipe (Slack / Teams) si une URL de webhook
      est définie dans .env (NOTIF_WEBHOOK_URL). Compatible avec les webhooks entrants
      Slack et Teams (envoi d'un simple message texte).

Aucune dépendance ni coût. L'email (SMTP) pourra être ajouté si Pauline le préfère.
"""

import os
import datetime
import requests


def _lire_env(cle, racine):
    val = os.environ.get(cle)
    if val:
        return val.strip()
    chemin = os.path.join(racine, ".env")
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne.startswith(cle) and "=" in ligne:
                    return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def construire_resume(stats, fiches):
    """Compose le texte du récapitulatif à partir des statistiques du run."""
    jour = datetime.date.today().strftime("%d/%m/%Y")
    lignes = [f"Agent de prospection G2S — exécution du {jour}", ""]
    lignes.append(f"Nouveaux prospects collectés : {stats.get('collectes', 0)}")
    if stats.get("exclus_pc"):
        lignes.append(f"Exclus (procédure collective) : {stats['exclus_pc']}")
    lignes.append(f"Prospects retenus : {len(fiches)}")
    inj = stats.get("injection")
    if inj is not None:
        lignes.append(f"Pipedrive : {inj['crees']} créé(s), "
                      f"{inj['ignores']} doublon(s) ignoré(s), {inj['erreurs']} erreur(s)")
    if fiches:
        lignes.append("")
        lignes.append("Top prospects :")
        for f in sorted(fiches, key=lambda x: x.get("score", 0), reverse=True)[:5]:
            ville = f.get("ville") or ""
            lignes.append(f"  • {f.get('score', '?')} — {f.get('raison_sociale', '?')} ({ville})")
    return "\n".join(lignes)


def enregistrer(resume, dossier_sorties):
    os.makedirs(dossier_sorties, exist_ok=True)
    chemin = os.path.join(dossier_sorties, f"recap_{datetime.date.today():%Y%m%d}.txt")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(resume)
    return chemin


def envoyer_webhook(resume, url):
    try:
        r = requests.post(url, json={"text": resume}, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"  [i] Webhook de notification non envoyé : {e}")
        return False


def notifier(stats, fiches, dossier_sorties, racine):
    """Affiche, enregistre et (en option) envoie le récapitulatif."""
    resume = construire_resume(stats, fiches)
    print("\n----- Récapitulatif -----\n" + resume + "\n-------------------------")
    enregistrer(resume, dossier_sorties)
    url = _lire_env("NOTIF_WEBHOOK_URL", racine)
    if url:
        envoyer_webhook(resume, url)
    return resume
