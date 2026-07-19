from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import bcrypt

db = SQLAlchemy()

# models.py - Ajouter à la fin du fichier

c# models.py - Ajouter à la fin du fichier

class PushToken(db.Model):
    """Token de notification push pour Expo."""
    __tablename__ = "push_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    platform = db.Column(db.String(20), default="unknown")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="push_tokens")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token": self.token[:10] + "...",  # Masquer le token
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    profile_type = db.Column(db.String(30), default="etudiant")  # etudiant / travailleur
    country = db.Column(db.String(100), default="France")
    currency = db.Column(db.String(10), default="EUR")  # devise locale du client (XOF, XAF, CAD, ...)
    account_status = db.Column(db.String(20), default="inactive")  # inactive / active
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    push_tokens = db.relationship("PushToken", back_populates="user")
    subscription = db.relationship("Subscription", uselist=False, back_populates="user")
    applications = db.relationship("Application", back_populates="user")

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "profile_type": self.profile_type,
            "country": self.country,
            "currency": self.currency,
            "account_status": self.account_status,
            "is_premium": self.subscription.is_active if self.subscription else False,
        }


class Offer(db.Model):
    """Une offre d'admission, de bourse ou d'emploi."""
    __tablename__ = "offers"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(30), nullable=False)  # bourse / admission / travail
    country = db.Column(db.String(100))
    description = db.Column(db.Text)
    how_to_apply = db.Column(db.Text)  # etapes pour postuler
    official_link = db.Column(db.String(500))
    image_url = db.Column(db.String(500))  # image illustrant l'offre (affichee dans la grille)
    deadline = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "organization": self.organization,
            "category": self.category,
            "country": self.country,
            "description": self.description,
            "how_to_apply": self.how_to_apply,
            "official_link": self.official_link,
            "image_url": self.image_url,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            # "Nouveau" (en vert) tant que l'offre a moins d'un mois sur la plateforme
            "is_new": (datetime.utcnow() - self.created_at) < timedelta(days=30),
        }


class Application(db.Model):
    """Le 'portefeuille' : suivi des offres sauvegardees/appliquees par un utilisateur."""
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    offer_id = db.Column(db.Integer, db.ForeignKey("offers.id"), nullable=False)
    status = db.Column(db.String(30), default="a_faire")  # a_faire / en_cours / envoye / accepte / refuse
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    user = db.relationship("User", back_populates="applications")
    offer = db.relationship("Offer")

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "notes": self.notes,
            "saved_at": self.saved_at.isoformat(),
            "offer": self.offer.to_dict(),
        }


class Subscription(db.Model):
    """Abonnement premium 3 euros/mois (Genius Pay ou PayPal)."""
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    provider = db.Column(db.String(20))  # genius_pay / paypal
    provider_reference = db.Column(db.String(255))  # id transaction cote provider
    is_active = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="subscription")

    def to_dict(self):
        return {
            "provider": self.provider,
            "is_active": self.is_active,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
        }
# models.py - Ajouter à la fin du fichier

class PaymentEvent(db.Model):
    """Journal des événements de paiement pour audit."""
    __tablename__ = "payment_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    provider = db.Column(db.String(20))  # genius_pay / paypal
    reference = db.Column(db.String(255))
    event_type = db.Column(db.String(50))  # payment.success, payment.failed, etc.
    status = db.Column(db.String(50))
    amount = db.Column(db.Float)
    currency = db.Column(db.String(10))
    raw_payload = db.Column(db.Text)  # Pour audit complet
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "reference": self.reference,
            "event_type": self.event_type,
            "status": self.status,
            "amount": self.amount,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }