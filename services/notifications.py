# services/notifications.py
import requests
import json
from app import db
from models import PushToken

EXPO_PUSH_API_URL = "https://exp.host/--/api/v2/push/send"

def send_push_notification(token, title, body, data=None):
    """
    Envoie une notification push via Expo.
    """
    if not token:
        return {"error": "Token manquant"}
    
    message = {
        "to": token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
        "priority": "high",
    }
    
    try:
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
        
        # Vérifier si la notification a été envoyée avec succès
        if result.get("data", {}).get("status") == "error":
            error_details = result.get("data", {}).get("details", {})
            error = error_details.get("error", "Erreur inconnue")
            print(f"❌ Erreur Expo: {error}")
            
            # Si l'erreur est permanente, supprimer le token
            if error in ["DeviceNotRegistered", "InvalidCredentials", "InvalidToken"]:
                PushToken.query.filter_by(token=token).delete()
                db.session.commit()
        
        return result
    except Exception as e:
        print(f"❌ Erreur envoi notification: {e}")
        return {"error": str(e)}

def notify_users_about_new_offer(offer):
    """
    Notifie tous les utilisateurs d'une nouvelle offre.
    """
    # Récupérer tous les tokens
    tokens = PushToken.query.all()
    
    if not tokens:
        print("⚠️ Aucun token push enregistré")
        return
    
    print(f"📨 Envoi de notifications à {len(tokens)} utilisateurs")
    
    # Titre et corps de la notification
    title = f"🎓 Nouvelle offre : {offer.title}"
    body = f"{offer.organization} - {offer.category}"
    
    # Données pour la navigation
    data = {
        "offer_id": offer.id,
        "screen": "OfferDetail",
        "title": offer.title,
    }
    
    # Envoyer à chaque utilisateur
    success_count = 0
    for push_token in tokens:
        try:
            result = send_push_notification(
                push_token.token,
                title,
                body,
                data
            )
            
            # Vérifier si la notification a été envoyée
            if result.get("data", {}).get("status") == "ok":
                success_count += 1
                print(f"✅ Notification envoyée à l'utilisateur {push_token.user_id}")
            else:
                print(f"⚠️ Échec envoi à {push_token.user_id}: {result}")
                
        except Exception as e:
            print(f"❌ Erreur pour {push_token.user_id}: {e}")
    
    print(f"📊 Résumé: {success_count}/{len(tokens)} notifications envoyées avec succès")