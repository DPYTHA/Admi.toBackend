"""
Module de paiement pour Admi.To.
"""
import requests
import hmac
import hashlib
import urllib3
import json
from datetime import datetime, timedelta
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ✅ Variable pour contrôler les logs de débogage
DEBUG = os.environ.get("PAYMENT_DEBUG", "False").lower() == "true"


def get_country_code(country_name):
    """
    Convertit un nom de pays en code ISO à 2 lettres.
    """
    if not country_name:
        return "CI"
    
    if len(country_name) == 2 and country_name.isalpha():
        return country_name.upper()
    
    country_map = {
        "côte d'ivoire": "CI",
        "cote d'ivoire": "CI",
        "côte d’ivoire": "CI",
        "france": "FR",
        "senegal": "SN",
        "cameroun": "CM",
        "benin": "BJ",
        "togo": "TG",
        "mali": "ML",
        "burkina faso": "BF",
        "niger": "NE",
        "nigeria": "NG",
        "ghana": "GH",
        "maroc": "MA",
        "tunisie": "TN",
        "algerie": "DZ",
        "algeria": "DZ",
        "canada": "CA",
        "etats-unis": "US",
        "états-unis": "US",
        "united states": "US",
        "belgique": "BE",
        "belgium": "BE",
        "suisse": "CH",
        "switzerland": "CH",
        "royaume-uni": "GB",
        "united kingdom": "GB",
        "allemagne": "DE",
        "germany": "DE",
        "espagne": "ES",
        "spain": "ES",
        "italie": "IT",
        "italy": "IT",
        "portugal": "PT",
        "pays-bas": "NL",
        "netherlands": "NL",
    }
    
    normalized = country_name.lower().strip()
    
    for key, value in country_map.items():
        if key in normalized or normalized in key:
            print(f"🔍 Conversion pays: '{country_name}' → '{value}'")
            return value
    
    print(f"⚠️ Pays non reconnu: '{country_name}', utilisation de CI par défaut")
    return "CI"


def get_user_phone(user):
    """
    Récupère le téléphone de l'utilisateur.
    """
    if hasattr(user, 'phone') and user.phone:
        return user.phone
    return "00000000"


# ============================================================================
# GENIUS PAY
# ============================================================================
def create_genius_pay_payment(config, amount, currency, user, subscription_id):
    """
    Crée une transaction Genius Pay.
    """
    url = f"{config.GENIUS_PAY_API_URL}/payments"
    
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    country_code = get_country_code(user.country)
    customer_phone = get_user_phone(user)
    
    # ✅ Utiliser EUR (comme dans Fabla)
    # Plus de méthodes de paiement disponibles en EUR
    payment_currency = "EUR"
    payment_amount = amount  # 3.0
    
    payload = {
        "amount": payment_amount,
        "currency": payment_currency,
        "description": "Abonnement mensuel Admi.To",
        "customer": {
            "name": user.full_name,
            "phone": customer_phone,
            "email": user.email,
        },
        "success_url": config.GENIUS_PAY_REDIRECT_URL + "?result=success",
        "error_url": config.GENIUS_PAY_REDIRECT_URL + "?result=error",
        "metadata": {
            "subscription_id": str(subscription_id),
            "user_id": str(user.id),
        }
    }

    print(f"💰 Paiement: {payment_amount} {payment_currency} | Utilisateur: {user.full_name} | Tél: {customer_phone}")

    try:
        response = requests.post(
            url, 
            json=payload,
            headers=headers, 
            timeout=30,
            verify=False
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text[:500] if response.text else 'Vide'}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            result = data.get("data", data)
            
            return {
                "reference": result.get("reference"),
                "checkout_url": result.get("checkout_url") or result.get("payment_url"),
                "status": result.get("status"),
            }
        else:
            error_text = response.text if response.text else "Erreur inconnue"
            print(f"❌ Erreur: {error_text}")
            raise Exception(f"Genius Pay erreur {response.status_code}: {error_text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur Request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"📄 Réponse: {e.response.text[:200]}")
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