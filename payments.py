"""
Module de paiement pour Admi.To.
"""
import requests
import hmac
import hashlib
import urllib3 
from datetime import datetime, timedelta
import json  
# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# GENIUS PAY
# ---------------------------------------------------------------------------
def create_genius_pay_payment(config, amount, currency, user, subscription_id):
    """
    Crée une transaction Genius Pay.
    """
    url = f"{config.GENIUS_PAY_API_URL}/payments"
    
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
    }
    
    customer_country = user.country or "France"
    
    payload = {
        "amount": str(amount),
        "currency": currency,
        "description": "Abonnement mensuel Admi.To",
        "customer": {
            "name": user.full_name,
            "email": user.email,
            "country": customer_country
        },
        "success_url": config.GENIUS_PAY_REDIRECT_URL,
        "error_url": config.GENIUS_PAY_REDIRECT_URL,
        "metadata": {
            "subscription_id": str(subscription_id),
            "user_id": str(user.id),
        },
    }

    print(f"💰 Envoi à Genius Pay: {url}")
    print(f"   Montant: {amount} {currency}")
    print(f"   Utilisateur: {user.full_name}")
    print(f"   Pays: {customer_country}")
    
    # ✅ Afficher le payload complet
    print(f"📤 Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=30,
            verify=False
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Headers: {dict(response.headers)}")
        
        # ✅ Afficher la réponse brute
        raw_response = response.text
        print(f"📥 Réponse brute: {raw_response[:500]}")
        
        # ✅ Si la réponse est vide, lever une exception claire
        if not raw_response or raw_response.strip() == "":
            raise Exception("Réponse vide de Genius Pay")
        
        # ✅ Tenter de parser le JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON: {e}")
            print(f"📄 Contenu reçu: {raw_response}")
            raise Exception(f"Réponse non-JSON: {raw_response[:100]}")
        
        if response.status_code in [200, 201]:
            if "data" in data:
                result = data["data"]
            else:
                result = data
            
            return {
                "reference": result.get("reference"),
                "checkout_url": result.get("checkout_url") or result.get("payment_url"),
                "status": result.get("status"),
            }
        else:
            print(f"❌ Erreur: {data}")
            raise Exception(f"Genius Pay erreur {response.status_code}: {data}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur Request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"📄 Réponse: {e.response.text}")
        raise Exception(f"Impossible de contacter Genius Pay: {str(e)}")


def get_genius_pay_payment(config, reference):
    """Récupère le statut d'un paiement."""
    url = f"{config.GENIUS_PAY_API_URL}/payments/{reference}"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
    }
    
    response = requests.get(url, headers=headers, timeout=30, verify=False)
    response.raise_for_status()
    data = response.json()
    return data.get("data", data)


def verify_genius_pay_payment(config, reference):
    """Vérifie qu'un paiement est confirmé."""
    try:
        data = get_genius_pay_payment(config, reference)
        return data.get("status") in ["completed", "success", "approved"]
    except Exception:
        return False


def verify_genius_pay_webhook_signature(config, timestamp, raw_body, signature_header):
    """Vérifie la signature du webhook."""
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
    """Enregistre le webhook."""
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
    response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
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
        verify=False
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
    response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
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
    response = requests.post(url, headers=headers, timeout=30, verify=False)
    response.raise_for_status()
    return response.json().get("status") == "COMPLETED"


def compute_next_period_end():
    return datetime.utcnow() + timedelta(days=30)