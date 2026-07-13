# config.py
import os
import urllib.parse

class Config:
    # === BASE DE DONNÉES ===
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    
    if not database_url:
        pg_host = os.environ.get("PGHOST", "postgres.railway.internal")
        pg_port = os.environ.get("PGPORT", "5432")
        pg_db = os.environ.get("PGDATABASE", "railway")
        pg_user = os.environ.get("PGUSER", "postgres")
        pg_pass = os.environ.get("PGPASSWORD", "")
        
        if pg_pass:
            database_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    
    if not database_url:
        database_url = "postgresql://admito_user:Pytha1991@localhost:5432/admito_db"
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if database_url:
        parsed = urllib.parse.urlparse(database_url)
        if parsed.password:
            password_encoded = urllib.parse.quote(parsed.password, safe='')
            database_url = database_url.replace(parsed.password, password_encoded)
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 30,
    }

    # === JWT ===
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7

    # === GENIUS PAY (CORRIGÉ) ===
    # L'URL correcte pour Genius Pay
    GENIUS_PAY_API_URL = os.environ.get("GENIUS_PAY_API_URL", "https://api.geniuspay.com/v1/merchant")
    GENIUS_PAY_API_KEY = os.environ.get("GENIUS_PAY_API_KEY", "")
    GENIUS_PAY_API_SECRET = os.environ.get("GENIUS_PAY_API_SECRET", "")
    GENIUS_PAY_WEBHOOK_SECRET = os.environ.get("GENIUS_PAY_WEBHOOK_SECRET", "")
    
    # URLs de redirection (doivent être accessibles publiquement)
    GENIUS_PAY_REDIRECT_URL = os.environ.get(
        "GENIUS_PAY_REDIRECT_URL", 
        "https://admitobackend-production.up.railway.app/api/payment/redirect"
    )
    GENIUS_PAY_CALLBACK_URL = os.environ.get(
        "GENIUS_PAY_CALLBACK_URL",
        "https://admitobackend-production.up.railway.app/api/payment/webhook"
    )

    # === PAYPAL ===
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_BASE_URL = os.environ.get("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")

    # === ABONNEMENT ===
    SUBSCRIPTION_PRICE_EUR = float(os.environ.get("SUBSCRIPTION_PRICE_EUR", "3.00"))

    # === ADMIN ===
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@admi.to")
    ADMIN_PASSWORD_HASH = os.environ.get(
        "ADMIN_PASSWORD_HASH",
        "$2b$12$PlXCKViz9djaEz/VsFHNhOAJ4qTxAHO0W4WZwOumEY3mdyS5i6ShG"
    )