"""
Enregistre l'URL de callback aupres de Genius Pay pour qu'ils sachent ou
envoyer leurs notifications de paiement (payment.success, payment.failed...).

A LANCER UNE SEULE FOIS, une fois que ton backend est deploye et accessible
publiquement (ex: sur Railway) - Genius Pay doit pouvoir atteindre l'URL.

Usage : python register_webhook.py
"""
from app import app
from config import Config
import payments

with app.app_context():
    if not Config.GENIUS_PAY_API_KEY or not Config.GENIUS_PAY_API_SECRET:
        print("GENIUS_PAY_API_KEY / GENIUS_PAY_API_SECRET manquants dans ton .env")
        raise SystemExit(1)

    print(f"Enregistrement du webhook vers : {Config.GENIUS_PAY_CALLBACK_URL}")
    try:
        result = payments.register_genius_pay_webhook(Config)
        print("\n✓ Webhook enregistre avec succes !")
        print(result)
        print(
            "\nSi la reponse contient un champ 'secret' (whsec_...), copie-le "
            "dans GENIUS_PAY_WEBHOOK_SECRET si ce n'est pas deja fait - il "
            "n'est affiche qu'une seule fois par Genius Pay."
        )
    except Exception as e:
        print(f"\n✗ Erreur lors de l'enregistrement du webhook : {e}")
