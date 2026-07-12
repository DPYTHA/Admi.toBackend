# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Base de données PostgreSQL
    database_url = os.environ.get("DATABASE_URL")
    
    # Railway utilise parfois 'postgres://' au lieu de 'postgresql://'
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Si DATABASE_URL n'existe pas, utiliser local
    if not database_url:
        database_url = "postgresql://admito_user:Pytha1991@localhost:5432/admito_db"
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7  # 7 jours

    # Genius Pay (https://pay.genius.ci) - authentification par cle publique + cle secrete
    GENIUS_PAY_API_URL = os.environ.get("GENIUS_PAY_API_URL", "https://pay.genius.ci/api/v1/merchant")
    GENIUS_PAY_API_KEY = os.environ.get("GENIUS_PAY_API_KEY", "")       # X-API-Key (pk_live_... / pk_sandbox_...)
    GENIUS_PAY_API_SECRET = os.environ.get("GENIUS_PAY_API_SECRET", "")  # X-API-Secret (sk_live_... / sk_sandbox_...)
    GENIUS_PAY_WEBHOOK_SECRET = os.environ.get("GENIUS_PAY_WEBHOOK_SECRET", "")  # whsec_...
   
    # PayPal
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_BASE_URL = os.environ.get("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")

    # Abonnement
    SUBSCRIPTION_PRICE_EUR = float(os.environ.get("SUBSCRIPTION_PRICE_EUR", "3.00"))

    # Identifiants admin (email + mot de passe) pour acceder a l'ecran d'administration
    # dans l'app et gerer les offres. Le mot de passe est stocke sous forme de hash bcrypt,
    # jamais en clair.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@admi.to")
    ADMIN_PASSWORD_HASH = os.environ.get(
        "ADMIN_PASSWORD_HASH",
        "$2b$12$PlXCKViz9djaEz/VsFHNhOAJ4qTxAHO0W4WZwOumEY3mdyS5i6ShG"
    )