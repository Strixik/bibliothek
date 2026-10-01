from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

db = SQLAlchemy()


class Author(db.Model):
    """Repräsentiert einen Autor in der Datenbank."""

    __tablename__ = "authors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    date_of_death = db.Column(db.Date, nullable=True)

    # Verbindet einen Autor mit seinen Büchern
    books = db.relationship("Book", backref="author", lazy=True)

    def __str__(self):
        """Gibt den Namen des Autors zurück."""
        return self.name

    def __repr__(self):
        """Gibt eine hilfreiche Darstellung des Autors zurück."""
        return f"Author(id={self.id}, name={self.name!r})"


class Book(db.Model):
    """Repräsentiert ein Buch in der Datenbank."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    publication_year = db.Column(db.Integer, nullable=True)
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("authors.id"),
        nullable=False,
    )
    rating = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 10",
            name="ck_books_rating_range",
        ),
    )

    def __str__(self):
        """Gibt den Buchtitel zurück."""
        return self.title

    def __repr__(self):
        """Gibt eine hilfreiche Darstellung des Buches zurück."""
        return f"Book(id={self.id}, title={self.title!r})"