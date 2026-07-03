# Image de base légère et stable
FROM python:3.12-slim

# Sorties non bufferisées (logs lisibles) + fuseau horaire pour la planification
ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Paris

WORKDIR /app

# Dépendances d'abord (profite du cache Docker : réinstallées seulement si elles changent)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Puis le code du projet
COPY . .

# L'agent fait UNE exécution complète puis s'arrête (tâche planifiée, pas un serveur).
CMD ["python", "main.py"]
