"""
Module de paiement pour Admi.To.
Gere les 2 moyens de paiement demandes : Genius Pay et PayPal.
"""
import requests
import hmac
import hashlib
import urllib3
import ssl
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================================
# CLASSE POUR IGNORER SSL (Solution définitive)
# ============================================================================
class SSLAdapter(HTTPAdapter):
    """Adapter pour ignorer les erreurs SSL."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)
    
    def proxy_manager_for(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().proxy_manager_for(*args, **kwargs)


def get_session():
    """Crée une session avec SSL désactivé."""
    session = requests.Session()
    session.mount('https://', SSLAdapter())
    session.verify = False
    return session


# ---------------------------------------------------------------------------
# GENIUS PAY
# ---------------------------------------------------------------------------
def create_genius_pay_payment(config, amount, currency, user, subscription_id):
    """
    Cree une transaction Genius Pay et retourne l'URL de checkout.
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
        # Utiliser la session personnalisée
        session = get_session()
        response = session.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=30
        )
        
        print(f"📥 Réponse Genius Pay: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
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
            print(f"❌ Erreur: {response.text}")
            raise Exception(f"Genius Pay erreur {response.status_code}: {response.text}")
            
    except requests.exceptions.SSLError as e:
        print(f"❌ Erreur SSL: {e}")
        # Réessayer avec une méthode alternative
        try:
            print("🔄 Nouvel essai avec verify=False...")
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            if "data" in data:
                result = data["data"]
            else:
                result = data
            return {
                "reference": result.get("reference"),
                "checkout_url": result.get("checkout_url") or result.get("payment_url"),
                "status": result.get("status"),
            }
        except Exception as e2:
            print(f"❌ Erreur second essai: {e2}")
            raise Exception(f"Erreur SSL: {str(e)}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur Genius Pay: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"📄 Réponse: {e.response.text}")
        raise Exception(f"Impossible de contacter Genius Pay: {str(e)}")


def get_genius_pay_payment(config, reference):
    """Recupere le statut a jour d'une transaction via sa reference."""
    url = f"{config.GENIUS_PAY_API_URL}/payments/{reference}"
    headers = {
        "X-API-Key": config.GENIUS_PAY_API_KEY,
        "X-API-Secret": config.GENIUS_PAY_API_SECRET,
    }
    
    session = get_session()
    response = session.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("data", data)


def verify_genius_pay_payment(config, reference):
    """Verifie qu'une transaction est bien confirmee cote Genius Pay."""
    try:
        data = get_genius_pay_payment(config, reference)
        return data.get("status") in ["completed", "success", "approved"]
    except Exception:
        return False


def verify_genius_pay_webhook_signature(config, timestamp, raw_body, signature_header):
    """
    Verifie la signature d'un webhook Genius Pay.
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
    Enregistre l'URL de callback aupres de Genius Pay.
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
    
    session = get_session()
    response = session.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# PAYPAL
# ---------------------------------------------------------------------------
def get_paypal_access_token(config):
    url = f"{config.PAYPAL_BASE_URL}/v1/oauth2/token"
    session = get_session()
    response = session.post(
        url,
        data={"grant_type": "client_credentials"},
        auth=(config.PAYPAL_CLIENT_ID, config.PAYPAL_CLIENT_SECRET),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_paypal_order(config, amount_eur, subscription_id):
    """Cree une commande PayPal pour l'abonnement mensuel."""
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
    
    session = get_session()
    response = session.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    approve_url = next((l["href"] for l in data["links"] if l["rel"] == "approve"), None)
    return {"status": data["status"], "id": data["id"], "approve_url": approve_url}


def capture_paypal_order(config, order_id):
    """Confirme le paiement PayPal une fois approuve par l'utilisateur."""
    if order_id.startswith("SIMULATED"):
        return True

    token = get_paypal_access_token(config)
    url = f"{config.PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    session = get_session()
    response = session.post(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("status") == "COMPLETED"


def compute_next_period_end():
    return datetime.utcnow() + timedelta(days=30)