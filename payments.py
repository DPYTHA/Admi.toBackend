"""
Module de paiement pour Admi.To.
Gere les 2 moyens de paiement demandes : Genius Pay et PayPal.
"""
import requests
import hmac
import hashlib
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# GENIUS PAY (https://pay.genius.ci) - integration reelle basee sur leur doc officielle
# ---------------------------------------------------------------------------
def create_genius_pay_payment(config, amount, currency, user, subscription_id):
    """
    Cree une transaction Genius Pay et retourne l'URL de checkout hebergee.
    On n'envoie pas 'payment_method' : le client choisit lui-meme (Wave, Orange
    Money, MTN, carte...) sur la page de paiement Genius Pay - c'est l'approche
    recommandee par leur documentation pour maximiser les conversions.
    """
    url = f"{config.GENIUS_PAY_API_URL}/payments"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
    }
    payload = {
        "amount": amount,
        "currency": currency,  # XOF, EUR ou USD - Genius Pay convertit automatiquement
        "description": "Abonnement mensuel Admi.To",
        "customer": {
            "name": user.full_name,
            "email": user.email,
        },
        "success_url": f"{config.GENIUS_PAY_REDIRECT_URL}?result=success",
        "error_url": f"{config.GENIUS_PAY_REDIRECT_URL}?result=error",
        "metadata": {
            "subscription_id": subscription_id,
            "user_id": user.id,
        },
    }

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()["data"]

    return {
        "reference": data["reference"],
        "checkout_url": data.get("checkout_url") or data.get("payment_url"),
        "status": data["status"],
    }


def get_genius_pay_payment(config, reference):
    """Recupere le statut a jour d'une transaction via sa reference (ex: MTX-XXXXXXXXXX)."""
    url = f"{config.GENIUS_PAY_API_URL}/payments/{reference}"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()["data"]


def verify_genius_pay_payment(config, reference):
    """Verifie qu'une transaction est bien confirmee cote Genius Pay."""
    try:
        data = get_genius_pay_payment(config, reference)
        return data.get("status") == "completed"
    except Exception:
        return False


def verify_genius_pay_webhook_signature(config, timestamp, raw_body, signature_header):
    """
    Verifie la signature d'un webhook Genius Pay.
    Format documente : HMAC-SHA256(timestamp + "." + json_payload, webhook_secret)
    Protege aussi contre les attaques par rejeu (timestamp de plus de 5 minutes refuse).
    """
    if not config.GENIUS_PAY_WEBHOOK_SECRET or not signature_header or not timestamp:
        return False

    try:
        if abs(datetime.utcnow().timestamp() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    data_to_sign = f"{timestamp}.{raw_body.decode()}"
    expected_signature = hmac.new(
        config.GENIUS_PAY_WEBHOOK_SECRET.encode(),
        data_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


def register_genius_pay_webhook(config):
    """
    Enregistre (une seule fois) l'URL de callback aupres de Genius Pay, pour
    qu'ils sachent ou envoyer leurs notifications de paiement. A lancer une
    fois manuellement (voir register_webhook.py), pas a chaque paiement.
    """
    url = f"{config.GENIUS_PAY_API_URL}/webhooks"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
    }
    payload = {
        "name": "Admi.To - abonnements",
        "url": config.GENIUS_PAY_CALLBACK_URL,
        "events": ["payment.success", "payment.failed", "payment.expired", "payment.cancelled"],
    }
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# PAYPAL
# ---------------------------------------------------------------------------
def get_paypal_access_token(config):
    url = f"{config.PAYPAL_BASE_URL}/v1/oauth2/token"
    response = requests.post(
        url,
        data={"grant_type": "client_credentials"},
        auth=(config.PAYPAL_CLIENT_ID, config.PAYPAL_CLIENT_SECRET),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_paypal_order(config, amount_eur, subscription_id):
    """Cree une commande PayPal pour l'abonnement mensuel."""
    # TODO: necessite des vrais identifiants PAYPAL_CLIENT_ID / SECRET
    try:
        token = get_paypal_access_token(config)
    except Exception:
        # Simulation MVP si les cles ne sont pas encore configurees
        return {
            "status": "CREATED",
            "id": f"SIMULATED-{subscription_id}",
            "approve_url": "https://www.sandbox.paypal.com/checkoutnow?token=SIMULATED",
        }

    url = f"{config.PAYPAL_BASE_URL}/v2/checkout/orders"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "EUR", "value": f"{amount_eur:.2f}"},
            "description": "Abonnement mensuel Admi.To",
            "custom_id": f"admito-sub-{subscription_id}",
        }],
    }
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    approve_url = next((l["href"] for l in data["links"] if l["rel"] == "approve"), None)
    return {"status": data["status"], "id": data["id"], "approve_url": approve_url}


def capture_paypal_order(config, order_id):
    """Confirme le paiement PayPal une fois approuve par l'utilisateur."""
    if order_id.startswith("SIMULATED"):
        return True  # simulation MVP

    token = get_paypal_access_token(config)
    url = f"{config.PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json().get("status") == "COMPLETED"


def compute_next_period_end():
    return datetime.utcnow() + timedelta(days=30)
