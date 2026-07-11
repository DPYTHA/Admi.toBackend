"""Peuple la base de donnees avec quelques offres de demonstration."""
from datetime import date
from app import app
from models import db, Offer

DEMO_OFFERS = [
    {
        "title": "Bourse d'excellence Erasmus+",
        "organization": "Union Europeenne",
        "category": "bourse",
        "country": "Europe",
        "image_url": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=400",
        "description": "Bourse de mobilite pour etudes en Europe, couvrant frais de scolarite et vie.",
        "how_to_apply": "1. Contacter le bureau des relations internationales de ton universite\n2. Preparer releve de notes et lettre de motivation\n3. Deposer le dossier avant la date limite",
        "official_link": "https://erasmus-plus.ec.europa.eu",
        "deadline": date(2026, 10, 15),
    },
    {
        "title": "Admission Master Informatique",
        "organization": "Universite de Montreal",
        "category": "admission",
        "country": "Canada",
        "image_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=400",
        "description": "Programme de Master en informatique, campus Montreal.",
        "how_to_apply": "1. Creer un compte sur le portail admission\n2. Uploader diplomes et CV\n3. Passer un entretien en ligne",
        "official_link": "https://umontreal.ca/admission",
        "deadline": date(2026, 12, 1),
    },
    {
        "title": "Programme Jeunes Talents Afrique",
        "organization": "Fondation Mastercard",
        "category": "bourse",
        "country": "International",
        "image_url": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=400",
        "description": "Bourse complete pour etudiants africains a fort potentiel.",
        "how_to_apply": "1. Verifier l'eligibilite sur le site officiel\n2. Remplir le formulaire en ligne\n3. Joindre lettres de recommandation",
        "official_link": "https://mastercardfdn.org/scholars",
        "deadline": date(2026, 9, 30),
    },
    {
        "title": "Developpeur Junior Full-Stack",
        "organization": "TechCorp",
        "category": "travail",
        "country": "France",
        "image_url": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=400",
        "description": "Poste junior en CDI pour rejoindre une equipe produit dynamique, teletravail partiel possible.",
        "how_to_apply": "1. Envoyer CV et lettre de motivation via le site\n2. Test technique en ligne\n3. Entretien avec l'equipe",
        "official_link": "https://techcorp-exemple.com/carrieres",
        "deadline": date(2026, 8, 31),
    },
]

with app.app_context():
    db.create_all()
    if Offer.query.count() == 0:
        for data in DEMO_OFFERS:
            db.session.add(Offer(**data))
        db.session.commit()
        print(f"{len(DEMO_OFFERS)} offres de demo ajoutees.")
    else:
        print("La base contient deja des offres, rien ajoute.")
