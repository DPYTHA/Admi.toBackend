# Dockerfile
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code
COPY . .

# Rendre entrypoint.sh exécutable
RUN chmod +x entrypoint.sh

# Exposer le port
EXPOSE 5000

# Utiliser entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]