# init_db.py
from app import app, db
from models import User, Offer, Application, Subscription
from datetime import date

def init_database():
    with app.app_context():
        print("🔧 Création des tables...")
        db.create_all()
        print("✅ Tables créées")
        
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables: {tables}")
        
        if "offers" in tables and Offer.query.count() == 0:
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
            print(f"✅ {len(demo_offers)} offres ajoutées")

if __name__ == "__main__":
    init_database()