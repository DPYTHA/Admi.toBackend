import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity,
    verify_jwt_in_request, get_jwt
)
from datetime import datetime
from functools import wraps
import bcrypt

from config import Config
from models import db, User, Offer, Application, Subscription
import payments

VALID_CATEGORIES = ("bourse", "admission", "travail")

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
db.init_app(app)
jwt = JWTManager(app)

# === AJOUTER ICI L'INITIALISATION ===
with app.app_context():
    try:
        db.create_all()
        print("✅ Tables vérifiées/créées au chargement")
        
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables: {tables}")
        
        # Ajouter des offres de test si nécessaire
        if "offers" in tables and Offer.query.count() == 0:
            from datetime import date
            print("📝 Ajout d'offres de test...")
            demo_offers = [
                Offer(
                    title="Bourse d'excellence Erasmus+",
                    organization="Union Européenne",
                    category="bourse",
                    country="Europe",
                    description="Bourse de mobilité pour études en Europe",
                    deadline=date(2026, 12, 31)
                ),
                Offer(
                    title="Master en Intelligence Artificielle",
                    organization="Université de Paris",
                    category="admission",
                    country="France",
                    description="Master en IA avec spécialisation Deep Learning",
                    deadline=date(2026, 10, 15)
                ),
                Offer(
                    title="Développeur Full-Stack",
                    organization="TechCorp",
                    category="travail",
                    country="France",
                    description="Poste en CDI pour développeur Full-Stack",
                    deadline=date(2026, 9, 30)
                ),
            ]
            for offer in demo_offers:
                db.session.add(offer)
            db.session.commit()
            print(f"✅ {len(demo_offers)} offres de test ajoutées")
            
    except Exception as e:
        print(f"⚠️ Erreur d'initialisation: {e}")


def require_admin(f):
    """Protege une route : necessite un token JWT admin (obtenu via /api/admin/login)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"error": "Authentification admin requise"}), 401

        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Acces reserve a l'administrateur"}), 403

        return f(*args, **kwargs)
    return wrapper


def require_active_subscription(f):
    """
    Protege une route : le compte doit avoir un abonnement premium actif.
    A utiliser APRES @jwt_required() dans la pile de decorateurs, pour que
    get_jwt_identity() soit deja disponible.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.subscription or not user.subscription.is_active:
            return jsonify({
                "error": "Un abonnement premium actif est necessaire pour voir les offres.",
                "requires_subscription": True,
            }), 402
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data.get("email") or not data.get("password") or not data.get("full_name"):
        return jsonify({"error": "Nom, email et mot de passe requis"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Cet email est deja utilise"}), 409

    user = User(
        full_name=data["full_name"],
        email=data["email"],
        profile_type=data.get("profile_type", "etudiant"),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    # Cree un abonnement inactif par defaut
    sub = Subscription(user_id=user.id, is_active=False)
    db.session.add(sub)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not user.check_password(data.get("password", "")):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 200


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    user = User.query.get_or_404(get_jwt_identity())
    return jsonify(user.to_dict())


# ---------------------------------------------------------------------------
# OFFRES (bourses / admissions / travail)
# ---------------------------------------------------------------------------
@app.route("/api/offers", methods=["GET"])
@jwt_required()
@require_active_subscription
def list_offers():
    category = request.args.get("category")  # bourse / admission / travail
    query = Offer.query
    if category:
        query = query.filter_by(category=category)
    offers = query.order_by(Offer.deadline.asc()).all()
    return jsonify([o.to_dict() for o in offers])


@app.route("/api/offers/<int:offer_id>", methods=["GET"])
@jwt_required()
@require_active_subscription
def get_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    return jsonify(offer.to_dict())


# ---------------------------------------------------------------------------
# ADMINISTRATION DES OFFRES
# ---------------------------------------------------------------------------
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    email = data.get("email", "")
    password = data.get("password", "")

    if email != Config.ADMIN_EMAIL or not bcrypt.checkpw(
        password.encode(), Config.ADMIN_PASSWORD_HASH.encode()
    ):
        return jsonify({"error": "Email ou mot de passe administrateur incorrect"}), 401

    token = create_access_token(identity="admin", additional_claims={"role": "admin"})
    return jsonify({"token": token})


@app.route("/api/admin/offers", methods=["POST"])
@require_admin
def create_offer():
    data = request.get_json()
    required = ["title", "organization", "category"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    if data["category"] not in VALID_CATEGORIES:
        return jsonify({"error": f"Categorie invalide, doit etre : {', '.join(VALID_CATEGORIES)}"}), 400

    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Le format de deadline doit etre AAAA-MM-JJ"}), 400

    offer = Offer(
        title=data["title"],
        organization=data["organization"],
        category=data["category"],
        country=data.get("country"),
        description=data.get("description"),
        how_to_apply=data.get("how_to_apply"),
        official_link=data.get("official_link"),
        image_url=data.get("image_url"),
        deadline=deadline,
    )
    db.session.add(offer)
    db.session.commit()
    return jsonify(offer.to_dict()), 201


@app.route("/api/admin/offers", methods=["GET"])
@require_admin
def admin_list_offers():
    offers = Offer.query.order_by(Offer.created_at.desc()).all()
    return jsonify([o.to_dict() for o in offers])


@app.route("/api/admin/offers/<int:offer_id>", methods=["PATCH"])
@require_admin
def update_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    data = request.get_json()

    if "category" in data and data["category"] not in VALID_CATEGORIES:
        return jsonify({"error": f"Categorie invalide, doit etre : {', '.join(VALID_CATEGORIES)}"}), 400

    for field in ["title", "organization", "category", "country", "description",
                  "how_to_apply", "official_link", "image_url"]:
        if field in data:
            setattr(offer, field, data[field])

    if "deadline" in data:
        try:
            offer.deadline = datetime.strptime(data["deadline"], "%Y-%m-%d").date() if data["deadline"] else None
        except ValueError:
            return jsonify({"error": "Le format de deadline doit etre AAAA-MM-JJ"}), 400

    db.session.commit()
    return jsonify(offer.to_dict())


@app.route("/api/admin/offers/<int:offer_id>", methods=["DELETE"])
@require_admin
def delete_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    db.session.delete(offer)
    db.session.commit()
    return jsonify({"message": "Offre supprimee"})


# ---------------------------------------------------------------------------
# PORTEFEUILLE
# ---------------------------------------------------------------------------
@app.route("/api/wallet", methods=["GET"])
@jwt_required()
@require_active_subscription
def get_wallet():
    user_id = get_jwt_identity()
    apps = Application.query.filter_by(user_id=user_id).order_by(Application.saved_at.desc()).all()
    return jsonify([a.to_dict() for a in apps])


@app.route("/api/wallet", methods=["POST"])
@jwt_required()
@require_active_subscription
def add_to_wallet():
    user_id = get_jwt_identity()
    data = request.get_json()
    offer_id = data.get("offer_id")

    existing = Application.query.filter_by(user_id=user_id, offer_id=offer_id).first()
    if existing:
        return jsonify({"error": "Cette offre est deja dans ton portefeuille"}), 409

    application = Application(user_id=user_id, offer_id=offer_id, status="a_faire")
    db.session.add(application)
    db.session.commit()
    return jsonify(application.to_dict()), 201


@app.route("/api/wallet/<int:application_id>", methods=["PATCH"])
@jwt_required()
@require_active_subscription
def update_wallet_item(application_id):
    user_id = get_jwt_identity()
    application = Application.query.filter_by(id=application_id, user_id=user_id).first_or_404()
    data = request.get_json()
    if "status" in data:
        application.status = data["status"]
    if "notes" in data:
        application.notes = data["notes"]
    db.session.commit()
    return jsonify(application.to_dict())


@app.route("/api/wallet/<int:application_id>", methods=["DELETE"])
@jwt_required()
@require_active_subscription
def remove_from_wallet(application_id):
    user_id = get_jwt_identity()
    application = Application.query.filter_by(id=application_id, user_id=user_id).first_or_404()
    db.session.delete(application)
    db.session.commit()
    return jsonify({"message": "Retire du portefeuille"})


# ---------------------------------------------------------------------------
# ABONNEMENT / PAIEMENT (Genius Pay + PayPal)
# ---------------------------------------------------------------------------
@app.route("/api/subscription", methods=["GET"])
@jwt_required()
def get_subscription():
    user_id = get_jwt_identity()
    sub = Subscription.query.filter_by(user_id=user_id).first()
    return jsonify(sub.to_dict() if sub else {"is_active": False})


# app.py - Dans la route /api/subscription/pay/genius-pay

# app.py - Dans pay_with_genius_pay

@app.route("/api/subscription/pay/genius-pay", methods=["POST"])
@jwt_required()
def pay_with_genius_pay():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    sub = Subscription.query.filter_by(user_id=user_id).first()

    data = request.get_json(silent=True) or {}
    currency = data.get("currency", "EUR").upper()
    if currency not in ("EUR", "USD", "XOF"):
        currency = "EUR"

    try:
        print(f"💰 Création paiement Genius Pay pour user {user_id}")
        print(f"   Montant: {Config.SUBSCRIPTION_PRICE_EUR} {currency}")
        print(f"   Pays: {user.country}")  # ✅ Afficher le pays
        
        result = payments.create_genius_pay_payment(
            Config, 
            Config.SUBSCRIPTION_PRICE_EUR, 
            currency, 
            user, 
            sub.id
            # ✅ PAS de 6ème argument - le pays est pris depuis user.country
        )
        
        print(f"✅ Paiement créé: {result}")
        
    except Exception as e:
        print(f"❌ Erreur Genius Pay: {e}")
        return jsonify({"error": f"Impossible de contacter Genius Pay: {str(e)}"}), 502

    sub.provider = "genius_pay"
    sub.provider_reference = result["reference"]
    db.session.commit()

    return jsonify(result), 200

@app.route("/api/subscription/confirm/genius-pay", methods=["POST"])
@jwt_required()
def confirm_genius_pay():
    user_id = get_jwt_identity()
    sub = Subscription.query.filter_by(user_id=user_id).first()

    if sub and sub.is_active:
        return jsonify({"message": "Abonnement actif", "subscription": sub.to_dict()}), 200

    # ✅ VÉRIFIER LE STATUT AUPRÈS DE GENIUS PAY
    if sub and sub.provider_reference:
        try:
            is_paid = payments.verify_genius_pay_payment(Config, sub.provider_reference)
            if is_paid:
                user = User.query.get(user_id)
                _activate_subscription(user, sub)
                return jsonify({
                    "message": "Paiement confirmé !",
                    "subscription": sub.to_dict()
                }), 200
        except Exception as e:
            print(f"❌ Erreur vérification paiement: {e}")

    return jsonify({
        "error": "Paiement pas encore confirmé.",
        "subscription": sub.to_dict() if sub else None,
    }), 402

    
@app.route("/api/payment/webhook", methods=["POST"])
def genius_pay_webhook():
    """
    Endpoint appele directement par les serveurs de Genius Pay des qu'un
    evenement de paiement se produit (payment.success, payment.failed, ...).
    C'est la source de verite : c'est ici, et seulement ici, qu'on doit se
    fier pour activer un compte, car cet appel vient serveur a serveur et
    est signe avec le secret webhook.

    A enregistrer une seule fois aupres de Genius Pay via register_webhook.py
    (voir README) avec l'URL : GENIUS_PAY_CALLBACK_URL
    """
    raw_body = request.get_data()
    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    event = request.headers.get("X-Webhook-Event", "")

    if not payments.verify_genius_pay_webhook_signature(Config, timestamp, raw_body, signature):
        return jsonify({"error": "Signature invalide"}), 401

    payload = request.get_json(silent=True) or {}
    transaction = payload.get("data", {})
    reference = transaction.get("reference")

    if not reference:
        return jsonify({"error": "Reference manquante"}), 400

    sub = Subscription.query.filter_by(provider_reference=reference).first()
    if not sub:
        return jsonify({"error": "Abonnement introuvable pour cette reference"}), 404

    # Journalisation pour l'audit trail visible dans le dashboard admin
    db.session.add(PaymentEvent(
        user_id=sub.user_id,
        provider="genius_pay",
        reference=reference,
        event_type=event,
        status=transaction.get("status"),
        amount=transaction.get("amount"),
        currency=transaction.get("currency"),
        raw_payload=request.get_data(as_text=True),
    ))
    db.session.commit()

    if event == "payment.success" or transaction.get("status") == "completed":
        user = User.query.get(sub.user_id)
        _activate_subscription(user, sub)

    # On repond toujours 200 pour accuser reception (evite les re-envois
    # en boucle par Genius Pay), meme si le statut est un echec.
    return jsonify({"received": True}), 200


@app.route("/api/payment/redirect", methods=["GET"])
def payment_redirect():
    """
    Page affichee au client dans son navigateur juste apres avoir paye (ou
    annule) sur Genius Pay. L'activation reelle du compte se fait via le
    webhook, pas ici : cette page ne sert qu'a informer le client qu'il peut
    revenir sur l'application.
    """
    result = request.args.get("result", "success")
    if result == "success":
        message = "Paiement recu ! Ton abonnement Admi.To sera actif dans quelques instants. Tu peux revenir sur l'application."
    else:
        message = "Le paiement n'a pas abouti. Tu peux revenir sur l'application et reessayer."

    return f"""
    <html>
      <head><meta charset="utf-8"><title>Admi.To</title></head>
      <body style="font-family: sans-serif; background:#5C3A21; color:#fff; text-align:center; padding:60px 20px;">
        <h2>Admi.To</h2>
        <p>{message}</p>
      </body>
    </html>
    """


def _activate_subscription(user, sub):
    """Active l'abonnement premium ET fait passer le compte utilisateur a 'active'."""
    sub.is_active = True
    sub.started_at = datetime.utcnow()
    sub.current_period_end = payments.compute_next_period_end()
    user.account_status = "active"
    db.session.commit()


@app.route("/api/subscription/pay/paypal", methods=["POST"])
@jwt_required()
def pay_with_paypal():
    user_id = get_jwt_identity()
    sub = Subscription.query.filter_by(user_id=user_id).first()

    result = payments.create_paypal_order(Config, Config.SUBSCRIPTION_PRICE_EUR, sub.id)
    sub.provider = "paypal"
    sub.provider_reference = result["id"]
    db.session.commit()

    return jsonify(result)


@app.route("/api/subscription/confirm/paypal", methods=["POST"])
@jwt_required()
def confirm_paypal():
    """Appele apres que l'utilisateur ait approuve le paiement dans l'app PayPal."""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    sub = Subscription.query.filter_by(user_id=user_id).first()

    if payments.capture_paypal_order(Config, sub.provider_reference):
        _activate_subscription(user, sub)
        return jsonify({"message": "Abonnement active", "subscription": sub.to_dict()})

    return jsonify({"error": "Paiement non confirme"}), 402


# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app": "Admi.To API"})


# ---------------------------------------------------------------------------
# PRODUCTION ENTRY ADMIN WEB
# ---------------------------------------------------------------------------

# ===== ADMIN - GESTION DES UTILISATEURS =====
@app.route("/api/admin/users", methods=["GET"])
@require_admin
def admin_list_users():
    """Liste tous les utilisateurs pour l'administration"""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])

@app.route("/api/admin/users/<int:user_id>", methods=["GET"])
@require_admin
def admin_get_user(user_id):
    """Récupère un utilisateur spécifique"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

# ===== ADMIN - GESTION DES ABONNEMENTS =====
@app.route("/api/admin/subscriptions", methods=["GET"])
@require_admin
def admin_list_subscriptions():
    """Liste tous les abonnements"""
    subs = Subscription.query.order_by(Subscription.started_at.desc().nullslast()).all()
    return jsonify([s.to_dict() for s in subs])

# ===== ADMIN - STATISTIQUES =====
@app.route("/api/admin/stats", methods=["GET"])
@require_admin
def admin_stats():
    """Statistiques générales pour le dashboard"""
    total_users = User.query.count()
    active_users = User.query.filter_by(account_status="active").count()
    total_offers = Offer.query.count()
    active_subs = Subscription.query.filter_by(is_active=True).count()
    
    # Compter les offres par catégorie
    offers_by_category = {}
    for cat in ["bourse", "admission", "travail"]:
        offers_by_category[cat] = Offer.query.filter_by(category=cat).count()
    
    # Revenus (3€ par abonnement actif)
    revenue = active_subs * 3.00
    
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "total_offers": total_offers,
        "active_subscriptions": active_subs,
        "offers_by_category": offers_by_category,
        "revenue": revenue
    })


# app.py - AJOUTER CETTE ROUTE (seulement ça)

@app.route("/api/admin/users/<int:user_id>", methods=["PATCH"])
@require_admin
def admin_update_user(user_id):
    """Active ou désactive un utilisateur"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if "account_status" in data:
        if data["account_status"] not in ["active", "inactive"]:
            return jsonify({"error": "Statut invalide"}), 400
        user.account_status = data["account_status"]
        db.session.commit()
        return jsonify(user.to_dict()), 200
    
    return jsonify({"error": "Champ account_status requis"}), 400
# ---------------------------------------------------------------------------
# PRODUCTION ENTRY POINT
# ---------------------------------------------------------------------------

@app.route("/api/admin/init-db", methods=["POST"])
@require_admin
def init_database():
    """Force la création des tables et ajoute des données de test"""
    try:
        print("🔧 Initialisation forcée de la base de données...")
        
        # 1. Créer les tables
        db.create_all()
        print("✅ Tables créées")
        
        # 2. Vérifier les tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables: {tables}")
        
        # 3. Ajouter des offres de test si la table est vide
        if "offers" in tables and Offer.query.count() == 0:
            print("📝 Ajout d'offres de test...")
            from datetime import date, timedelta
            
            demo_offers = [
                Offer(
                    title="Bourse d'excellence Erasmus+",
                    organization="Union Européenne",
                    category="bourse",
                    country="Europe",
                    description="Bourse de mobilité pour études en Europe",
                    deadline=date(2026, 12, 31)
                ),
                Offer(
                    title="Master en Intelligence Artificielle",
                    organization="Université de Paris",
                    category="admission",
                    country="France",
                    description="Master en IA avec spécialisation en Deep Learning",
                    deadline=date(2026, 10, 15)
                ),
                Offer(
                    title="Développeur Full-Stack",
                    organization="TechCorp",
                    category="travail",
                    country="France",
                    description="Poste en CDI pour développeur Full-Stack",
                    deadline=date(2026, 9, 30)
                ),
            ]
            
            for offer in demo_offers:
                db.session.add(offer)
            db.session.commit()
            print(f"✅ {len(demo_offers)} offres ajoutées")
        
        return jsonify({
            "status": "success",
            "message": "Base de données initialisée avec succès",
            "tables": tables,
            "offer_count": Offer.query.count(),
            "user_count": User.query.count()
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ Erreur: {error_detail}")
        return jsonify({
            "error": str(e),
            "detail": error_detail
        }), 500



#reinitialiser mots de passe



@app.route("/api/auth/check-email", methods=["POST"])
def check_email():
    """Vérifie si un email existe"""
    data = request.get_json()
    email = data.get("email")
    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"exists": True, "email": email}), 200
    return jsonify({"exists": False}), 404

@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Réinitialise le mot de passe"""
    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email non trouvé"}), 404
    
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({"message": "Mot de passe réinitialisé"}), 200
# ---------------------------------------------------------------------------
# PRODUCTION ENTRY POINT
# ---------------------------------------------------------------------------
# app.py - Section d'initialisation
if __name__ == "__main__":
    with app.app_context():
        try:
            # Tester la connexion
            db.engine.connect()
            print("✅ Connexion à la base de données établie")
            
            # Créer les tables
            db.create_all()
            print("✅ Tables créées/vérifiées")
            
            # Vérifier les tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tables existantes: {tables}")
            
            # Ajouter des offres de test si nécessaire
            if "offers" in tables and Offer.query.count() == 0:
                from datetime import date
                print("📝 Ajout d'offres de test...")
                demo_offers = [
                    Offer(
                        title="Bourse d'excellence Erasmus+",
                        organization="Union Européenne",
                        category="bourse",
                        country="Europe",
                        description="Bourse de mobilité pour études en Europe",
                        deadline=date(2026, 12, 31)
                    ),
                    Offer(
                        title="Master en Intelligence Artificielle",
                        organization="Université de Paris",
                        category="admission",
                        country="France",
                        description="Master en IA avec spécialisation Deep Learning",
                        deadline=date(2026, 10, 15)
                    ),
                    Offer(
                        title="Développeur Full-Stack",
                        organization="TechCorp",
                        category="travail",
                        country="France",
                        description="Poste en CDI pour développeur Full-Stack",
                        deadline=date(2026, 9, 30)
                    ),
                ]
                for offer in demo_offers:
                    db.session.add(offer)
                db.session.commit()
                print(f"✅ {len(demo_offers)} offres de test ajoutées")
            else:
                if "offers" in tables:
                    print(f"📊 {Offer.query.count()} offres déjà présentes")
                
        except Exception as e:
            print(f"❌ Erreur de base de données: {e}")
            import traceback
            traceback.print_exc()
    
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    
    print(f"🚀 Démarrage du serveur sur le port {port}")
    app.run(debug=debug, host="0.0.0.0", port=port)