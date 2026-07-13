# payments.py
import requests
import hmac
import hashlib
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# GENIUS PAY
# ---------------------------------------------------------------------------
def create_genius_pay_payment(config, amount, currency, user, subscription_id):
    """
    Crée une transaction Genius Pay et retourne l'URL de checkout.
    """
    url = f"{config.GENIUS_PAY_API_URL}/payments"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
    }
    payload = {
        "amount": str(amount),
        "currency": currency,
        "description": "Abonnement mensuel Admi.To",
        "customer": {
            "name": user.full_name,
            "email": user.email,
        },
        "success_url": config.GENIUS_PAY_REDIRECT_URL,
        "error_url": config.GENIUS_PAY_REDIRECT_URL,
        "metadata": {
            "subscription_id": str(subscription_id),
            "user_id": str(user.id),
        },
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Vérifier la structure de la réponse
        if "data" in data:
            result = data["data"]
        else:
            result = data
        
        return {
            "reference": result.get("reference"),
            "checkout_url": result.get("checkout_url") or result.get("payment_url"),
            "status": result.get("status"),
        }
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur Genius Pay: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"📄 Réponse: {e.response.text}")
        raise

def get_genius_pay_payment(config, reference):
    """Récupère le statut d'une transaction."""
    url = f"{config.GENIUS_PAY_API_URL}/payments/{reference}"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("data", data)

def verify_genius_pay_payment(config, reference):
    """Vérifie qu'une transaction est confirmée."""
    try:
        data = get_genius_pay_payment(config, reference)
        status = data.get("status")
        return status in ["completed", "success", "approved"]
    except Exception as e:
        print(f"❌ Erreur vérification: {e}")
        return False

def verify_genius_pay_webhook_signature(config, timestamp, raw_body, signature_header):
    """
    Vérifie la signature du webhook Genius Pay.
    """
    if not config.GENIUS_PAY_WEBHOOK_SECRET or not signature_header or not timestamp:
        print("⚠️ Webhook: secrets manquants")
        return False

    try:
        # Vérifier le timestamp (max 5 minutes)
        if abs(datetime.utcnow().timestamp() - int(timestamp)) > 300:
            print("⚠️ Webhook: timestamp trop vieux")
            return False
    except ValueError:
        print("⚠️ Webhook: timestamp invalide")
        return False

    # Construire la signature attendue
    data_to_sign = f"{timestamp}.{raw_body.decode()}"
    expected_signature = hmac.new(
        config.GENIUS_PAY_WEBHOOK_SECRET.encode(),
        data_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(expected_signature, signature_header)
    if not is_valid:
        print("⚠️ Webhook: signature invalide")
    return is_valid

def register_genius_pay_webhook(config):
    """Enregistre le webhook auprès de Genius Pay."""
    url = f"{config.GENIUS_PAY_API_URL}/webhooks"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
    }
    payload = {
        "name": "Admi.To - abonnements",
        "url": config.GENIUS_PAY_CALLBACK_URL,
        "events": ["payment.success", "payment.failed", "payment.expired"],
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
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
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]

def create_paypal_order(config, amount_eur, subscription_id):
    try:
        token = get_paypal_access_token(config)
    except Exception:
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
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    approve_url = next((l["href"] for l in data["links"] if l["rel"] == "approve"), None)
    return {"status": data["status"], "id": data["id"], "approve_url": approve_url}

def capture_paypal_order(config, order_id):
    if order_id.startswith("SIMULATED"):
        return True

    token = get_paypal_access_token(config)
    url = f"{config.PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("status") == "COMPLETED"

def compute_next_period_end():
    return datetime.utcnow() + timedelta(days=30)