FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer le script d'entrée
RUN echo '#!/bin/bash\n\
    echo "Starting Gunicorn..."\n\
    gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 2 app:app' > entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["./entrypoint.sh"]