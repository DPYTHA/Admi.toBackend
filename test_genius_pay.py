# test_genius.py
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_genius_pay_connection():
    """Test la connexion à l'API Genius Pay"""
    print("=" * 50)
    print("🧪 TEST DE CONNEXION GENIUS PAY")
    print("=" * 50)
    
    # Récupérer les clés depuis les variables d'environnement
    api_url = os.environ.get("GENIUS_PAY_API_URL", "https://api.geniuspay.com/v1/merchant")
    api_key = os.environ.get("GENIUS_PAY_API_KEY", "")
    api_secret = os.environ.get("GENIUS_PAY_API_SECRET", "")
    
    print(f"\n📋 Configuration:")
    print(f"  URL: {api_url}")
    print(f"  API Key: {api_key[:15]}..." if api_key else "  API Key: NON DÉFINIE ❌")
    print(f"  API Secret: {api_secret[:15]}..." if api_secret else "  API Secret: NON DÉFINIE ❌")
    
    if not api_key or not api_secret:
        print("\n❌ ERREUR: Clés API manquantes!")
        print("   Définissez GENIUS_PAY_API_KEY et GENIUS_PAY_API_SECRET")
        return False
    
    # Test 1: Vérifier l'API Health
    print("\n📡 Test 1: Vérification de l'API Genius Pay...")
    try:
        health_url = "https://api.geniuspay.com/v1/merchant/health"
        response = requests.get(health_url, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print("  ✅ API Genius Pay accessible")
        else:
            print(f"  ⚠️ Réponse inattendue: {response.text}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
    
    # Test 2: Tester avec les clés (créer un paiement de test)
    print("\n💰 Test 2: Création d'un paiement test...")
    try:
        url = f"{api_url}/payments"
        headers = {
            "X-API-Key": api_key,
            "X-API-Secret": api_secret,
            "Content-Type": "application/json",
        }
        payload = {
            "amount": "1.00",
            "currency": "EUR",
            "description": "Test Admi.To",
            "customer": {
                "name": "Test User",
                "email": "test@example.com",
            },
            "success_url": "https://example.com/success",
            "error_url": "https://example.com/error",
        }
        
        print(f"  📤 Envoi à: {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"  📥 Status: {response.status_code}")
        print(f"  📄 Réponse: {response.text[:200]}...")
        
        if response.status_code == 200 or response.status_code == 201:
            print("  ✅ Paiement test créé avec succès!")
            data = response.json()
            if "data" in data:
                data = data["data"]
            print(f"  📋 Référence: {data.get('reference')}")
            print(f"  🔗 URL: {data.get('checkout_url')}")
            return True
        else:
            print(f"  ❌ Erreur: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("  ❌ Timeout - L'API Genius Pay ne répond pas")
        return False
    except requests.exceptions.ConnectionError:
        print("  ❌ Erreur de connexion - Vérifiez votre réseau")
        return False
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_backend_api():
    """Test l'API de votre backend"""
    print("\n" + "=" * 50)
    print("🧪 TEST DE L'API BACKEND")
    print("=" * 50)
    
    backend_url = "https://admitobackend-production.up.railway.app"
    
    # Test 1: Health
    print("\n📡 Test 1: Health check...")
    try:
        response = requests.get(f"{backend_url}/api/health", timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ Backend accessible: {response.json()}")
        else:
            print(f"  ❌ Erreur: {response.text}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return
    
    # Test 2: Configuration Genius Pay
    print("\n📡 Test 2: Configuration Genius Pay...")
    try:
        response = requests.get(f"{backend_url}/api/genius-pay-test", timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            config = response.json()
            print(f"  ✅ Configuration: {config}")
        else:
            print(f"  ❌ Erreur: {response.text}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
    
    # Test 3: Login
    print("\n🔐 Test 3: Login...")
    try:
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        response = requests.post(
            f"{backend_url}/api/auth/login",
            json=login_data,
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"  ✅ Login réussi")
            print(f"  🔑 Token: {token[:50]}...")
            
            # Test 4: Paiement
            print("\n💰 Test 4: Création paiement...")
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            pay_response = requests.post(
                f"{backend_url}/api/subscription/pay/genius-pay",
                json={"currency": "EUR"},
                headers=headers,
                timeout=30
            )
            print(f"  Status: {pay_response.status_code}")
            if pay_response.status_code == 200:
                data = pay_response.json()
                print(f"  ✅ Paiement créé!")
                print(f"  📋 Référence: {data.get('reference')}")
                print(f"  🔗 URL: {data.get('checkout_url')}")
            else:
                print(f"  ❌ Erreur: {pay_response.text}")
        else:
            print(f"  ❌ Login échoué: {response.text}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")

if __name__ == "__main__":
    print("\n🚀 Début des tests...\n")
    
    # Tester la connexion à Genius Pay
    genius_ok = test_genius_pay_connection()
    
    if genius_ok:
        print("\n✅ Genius Pay fonctionne correctement!")
    else:
        print("\n❌ Problème avec Genius Pay - Vérifiez:")
        print("  1. Les clés API sont-elles correctes?")
        print("  2. L'URL de l'API est-elle correcte?")
        print("  3. Votre réseau permet-il d'accéder à Genius Pay?")
    
    # Tester le backend
    test_backend_api()
    
    print("\n" + "=" * 50)
    print("🏁 Tests terminés")
    print("=" * 50)