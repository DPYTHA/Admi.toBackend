# services/notifications.py
import requests
from app import db
from models import PushToken

EXPO_PUSH_API_URL = "https://exp.host/--/api/v2/push/send"

def notify_users_about_new_offer(offer):
    """
    Notifie tous les utilisateurs d'une nouvelle offre.
    Appelée avec le contexte d'application.
    """
    # Récupérer tous les tokens
    tokens = PushToken.query.all()
    
    if not tokens:
        print("⚠️ Aucun token push enregistré")
        return
    
    print(f"📨 Envoi de notifications à {len(tokens)} utilisateurs")
    
    title = f"🎓 Nouvelle offre : {offer.title}"
    body = f"{offer.organization} - {offer.category}"
    data = {
        "offer_id": offer.id,
        "screen": "OfferDetail",
        "title": offer.title,
    }
    
    success_count = 0
    for push_token in tokens:
        try:
            message = {
                "to": push_token.token,
                "sound": "default",
                "title": title,
                "body": body,
                "data": data,
                "priority": "high",
            }
            
            response = requests.post(
                EXPO_PUSH_API_URL,
                json=message,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=10
            )
            
            result = response.json()
            if result.get("data", {}).get("status") == "ok":
                success_count += 1
                print(f"✅ Notification envoyée à l'utilisateur {push_token.user_id}")
            else:
                print(f"⚠️ Échec envoi à {push_token.user_id}: {result}")
                
        except Exception as e:
            print(f"❌ Erreur pour {push_token.user_id}: {e}")
    
    print(f"📊 Résumé: {success_count}/{len(tokens)} notifications envoyées avec succès")