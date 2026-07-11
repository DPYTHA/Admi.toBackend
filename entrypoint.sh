# Créer entrypoint.sh
@"
#!/bin/bash
echo "🚀 Démarrage de l'application Admi.To..."
echo "🔧 Lancement de Gunicorn..."
exec gunicorn --bind 0.0.0.0:\$PORT --timeout 120 --workers 2 --access-logfile - --error-logfile - app:app
"@ | Out-File -FilePath entrypoint.sh -Encoding utf8