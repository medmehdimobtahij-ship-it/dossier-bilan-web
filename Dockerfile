# Dossier Bilan, image pour un hébergeur :
#   docker build -t dossier-bilan .
#   docker run -p 8095:8095 -v dossier-bilan-data:/data dossier-bilan
# Démo hors ligne (dossiers fictifs, sans mot de passe) : ajouter -e BILAN_DEMO=1
# Les données (dossiers, comptes, jeton Pennylane, clé de session) vivent dans le volume /data, jamais dans l'image.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home bilan
COPY serveur ./serveur
COPY web ./web
ENV BILAN_DATA=/data BILAN_PORT=8095 PYTHONUNBUFFERED=1
# Derrière un proxy HTTPS, ajouter -e BILAN_HTTPS=1 (cookies de session « Secure »).
RUN mkdir -p /data && chown bilan /data
USER bilan
EXPOSE 8095
CMD ["python", "serveur/lancer.py"]
