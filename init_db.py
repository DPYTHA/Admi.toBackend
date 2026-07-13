# init_db.py
import os
import sys
from app import app, db
from models import Offer
from datetime import date

def init_database():
    with app.app_context():
        print("🔧 Initialisation de la base de données...")
        
        try:
            # Tester la connexion
            db.engine.connect()
            print("✅ Connexion réussie")
            
            # Créer les tables
            db.create_all()
            print("✅ Tables créées/vérifiées")
            
            # Vérifier les tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tables: {tables}")
            
            # Ajouter des offres de test
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
            else:
                print(f"📊 {Offer.query.count()} offres déjà présentes")
                
            print("✅ Initialisation terminée avec succès")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    init_database()