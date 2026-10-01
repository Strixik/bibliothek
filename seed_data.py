from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import app
from data_models import Author, Book, db

import random


# Beispieldaten: zehn Autorinnen und Autoren mit jeweils zwei Büchern
SAMPLE_DATA = [
    {
        "author": "Franz Kafka",
        "books": [
            ("Die Verwandlung", "9783518013519", 1915),
            ("Der Prozess", "9783596709625", 1925),
        ],
    },
    {
        "author": "Thomas Mann",
        "books": [
            ("Buddenbrooks", "9783596521487", 1901),
            ("Der Zauberberg", "9783103481280", 1924),
        ],
    },
    {
        "author": "Hermann Hesse",
        "books": [
            ("Der Steppenwolf", "9783518460634", 1927),
            ("Siddhartha", "9783518366820", 1922),
        ],
    },
    {
        "author": "Friedrich Schiller",
        "books": [
            ("Die Räuber", "9783159600154", 1781),
            ("Maria Stuart", "9783123524509", 1800),
        ],
    },
    {
        "author": "Michael Ende",
        "books": [
            ("Momo", "9783522202107", 1973),
            ("Die unendliche Geschichte", "9783522202503", 1979),
        ],
    },
    {
        "author": "Erich Maria Remarque",
        "books": [
            ("Im Westen nichts Neues", "9783462046328", 1929),
            ("Drei Kameraden", "9783462046311", 1936),
        ],
    },
    {
        "author": "Theodor Fontane",
        "books": [
            ("Effi Briest", "9783150195970", 1895),
            ("Irrungen, Wirrungen", "9783150196014", 1888),
        ],
    },
    {
        "author": "Friedrich Dürrenmatt",
        "books": [
            ("Der Besuch der alten Dame", "9783257230451", 1956),
            ("Die Physiker", "9783257230475", 1962),
        ],
    },
    {
        "author": "Erich Kästner",
        "books": [
            ("Emil und die Detektive", "9783855356034", 1929),
            ("Das fliegende Klassenzimmer", "9783855356072", 1933),
        ],
    },
    {
        "author": "Cornelia Funke",
        "books": [
            ("Tintenherz", "9783791504650", 2003),
            ("Tintenblut", "9783791504674", 2005),
        ],
    },
]


def seed_library():
    """Fügt Beispieldaten hinzu, ohne vorhandene Einträge zu duplizieren."""
    added_authors = 0
    added_books = 0

    with app.app_context():
        db.create_all()

        try:
            for entry in SAMPLE_DATA:
                author_name = entry["author"]

                author = db.session.scalar(
                    select(Author).where(Author.name == author_name)
                )

                if author is None:
                    author = Author(name=author_name)
                    db.session.add(author)
                    db.session.flush()
                    added_authors += 1

                for title, isbn, publication_year in entry["books"]:
                    existing_book_id = db.session.scalar(
                        select(Book.id).where(Book.isbn == isbn)
                    )

                    if existing_book_id is not None:
                        continue

                    book = Book(
                        isbn=isbn,
                        title=title,
                        publication_year=publication_year,
                        author_id=author.id,
                        rating=random.randint(1, 10),
                    )
                    db.session.add(book)
                    added_books += 1

            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            raise

    print(f"Neue Autorinnen und Autoren: {added_authors}")
    print(f"Neue Bücher: {added_books}")


if __name__ == "__main__":
    seed_library()