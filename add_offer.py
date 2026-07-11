"""
Script interactif pour ajouter une offre (bourse, admission ou travail) directement
dans la base de donnees, sans passer par l'API.
Usage : python add_offer.py
"""
from datetime import datetime
from app import app
from models import db, Offer


def ask(label, required=True):
    while True:
        value = input(f"{label} : ").strip()
        if value or not required:
            return value
        print("  -> ce champ est obligatoire, merci de le remplir.")


def main():
    print("=== Ajouter une nouvelle offre sur Admi.To ===\n")

    title = ask("Titre de l'offre")
    organization = ask("Organisme")

    category = ""
    while category not in ("bourse", "admission", "travail"):
        category = ask("Categorie (bourse / admission / travail)").lower()

    country = ask("Pays / zone", required=False)
    image_url = ask("URL de l'image (laisser vide si aucune)", required=False)
    description = ask("Description", required=False)
    how_to_apply = ask("Comment postuler (etapes)", required=False)
    official_link = ask("Lien officiel", required=False)

    deadline = None
    deadline_str = ask("Date limite (AAAA-MM-JJ, laisser vide si aucune)", required=False)
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            print("Format de date invalide, l'offre sera enregistree sans date limite.")

    with app.app_context():
        offer = Offer(
            title=title,
            organization=organization,
            category=category,
            country=country or None,
            image_url=image_url or None,
            description=description or None,
            how_to_apply=how_to_apply or None,
            official_link=official_link or None,
            deadline=deadline,
        )
        db.session.add(offer)
        db.session.commit()
        print(f"\n✓ Offre ajoutee avec succes (id={offer.id}) !")


if __name__ == "__main__":
    main()
