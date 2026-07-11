# Dockerfile
FROM python:3.13-slim

# Installer les dépendances système nécessaires pour psycopg2
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

# Exposer le port
EXPOSE 5000

# Lancer l'application avec gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]