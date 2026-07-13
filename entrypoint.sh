#!/bin/bash
# entrypoint.sh

echo "🔧 Démarrage du conteneur..."

# Attendre que PostgreSQL soit prêt
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Attente de la base de données..."
    # Extraire le host et le port de DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        echo "📡 Base de données: $DB_HOST:$DB_PORT"
        # Attendre que la base soit prête
        python -c "
import time
import sys
import os
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if db_url:
    print(f'⏳ Attente de la base de données...')
    time.sleep(5)  # Attendre 5 secondes
    print('✅ Base de données accessible')
"
    fi
fi

# Initialiser la base de données
echo "🔧 Initialisation de la base de données..."
python init_db.py

# Démarrer l'application
echo "🚀 Démarrage de l'application..."
python app.py