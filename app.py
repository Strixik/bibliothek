import http.client
import json
import os
import re
import time
from datetime import date

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import String, cast, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from data_models import Author, Book, db


app = Flask(__name__)

# Datenbankdatei im Ordner „data“ festlegen
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'data', 'library.sqlite')}"
)

# Geheimen Schlüssel für Flask-Nachrichten festlegen
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(32)

# Flask-Anwendung mit Flask-SQLAlchemy verbinden
db.init_app(app)


def parse_optional_date(value):
    """Wandelt ein optionales Datum im Format YYYY-MM-DD um."""
    value = value.strip()

    if not value:
        return None

    try:
        parsed_date = date.fromisoformat(value)
    except ValueError:
        return None

    if parsed_date.isoformat() != value:
        return None

    return parsed_date


def is_valid_isbn(value):
    """Prüft die Prüfziffer einer ISBN-10 oder ISBN-13."""
    isbn = re.sub(r"[-\s]", "", value).upper()

    if len(isbn) == 10:
        if not isbn[:9].isascii() or not isbn[:9].isdigit():
            return False

        if not (
            isbn[9].isascii() and isbn[9].isdigit()
            or isbn[9] == "X"
        ):
            return False

        digits = [int(char) for char in isbn[:9]]
        check_digit = 10 if isbn[9] == "X" else int(isbn[9])

        return (
            sum(
                (10 - index) * digit
                for index, digit in enumerate(digits)
            )
            + check_digit
        ) % 11 == 0

    if (
        len(isbn) == 13
        and isbn.isascii()
        and isbn.isdigit()
    ):
        digits = [int(char) for char in isbn]
        checksum = sum(
            digit * (1 if index % 2 == 0 else 3)
            for index, digit in enumerate(digits[:12])
        )
        expected_digit = (10 - checksum % 10) % 10

        return digits[12] == expected_digit

    return False


def get_book_recommendation(books):
    """Fragt über RapidAPI eine Buchempfehlung an."""
    api_key = os.environ.get("RAPIDAPI_KEY", "").strip()

    if not api_key:
        raise RuntimeError("Der RapidAPI-Schlüssel ist nicht eingerichtet.")

    book_list = "\n".join(
        f"- {book.title} von {book.author.name}"
        + (
            f", Bewertung: {book.rating}/10"
            if book.rating is not None
            else ", noch nicht bewertet"
        )
        for book in books
    )

    payload = json.dumps({
        "max_tokens": 256,
        "messages": [{
            "content": (
                "Empfiehl ein neues Buch, das zu meiner Sammlung passt. "
                "Empfiehl kein Buch, das bereits in der Liste steht. "
                "Berücksichtige besonders die Bewertungen, sofern vorhanden, "
                "und begründe die Empfehlung kurz.\n\n"
                f"Meine Bücher:\n{book_list}"
            ),
            "role": "user",
        }],
        "system_prompt": (
            "Du bist ein freundlicher deutschsprachiger Buchberater."
        ),
        "temperature": 0.7,
        "top_k": 5,
        "top_p": 0.9,
        "web_access": False,
    })

    connection = http.client.HTTPSConnection(
        "chatgpt-42.p.rapidapi.com",
        timeout=20,
    )

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "chatgpt-42.p.rapidapi.com",
        "Content-Type": "application/json",
    }

    try:
        connection.request(
            "POST",
            "/conversationgpt4-2",
            payload,
            headers,
        )
        response = connection.getresponse()
        response_text = response.read().decode("utf-8")

        if response.status != 200:
            raise RuntimeError(
                f"RapidAPI meldet HTTP-Status {response.status}."
            )

        result_data = json.loads(response_text)

        if not isinstance(result_data, dict):
            raise RuntimeError("Die API-Antwort hat ein ungültiges Format.")

        if result_data.get("status") is not True:
            raise RuntimeError("RapidAPI konnte keine Empfehlung erstellen.")

        recommendation = result_data.get("result")

        if (
            not isinstance(recommendation, str)
            or not recommendation.strip()
        ):
            raise RuntimeError("Die API-Antwort enthält keine Empfehlung.")

        return recommendation.strip()

    finally:
        connection.close()


@app.route("/")
def index():
    """Zeigt Bücher an und durchsucht wichtige Buchfelder."""
    search_term = request.args.get("search", "").strip()
    sort_by = request.args.get("sort", "title").strip()
    search_error = None

    if sort_by not in ("title", "author"):
        sort_by = "title"

    authors = db.session.scalars(
        select(Author).order_by(Author.name.asc())
    ).all()

    if len(search_term) > 100:
        search_error = "Der Suchbegriff darf höchstens 100 Zeichen lang sein."
        books = []
    else:
        statement = select(Book)

        if search_term:
            isbn_search_term = re.sub(r"[-\s]", "", search_term)

            search_conditions = [
                Book.title.contains(search_term, autoescape=True),
                Author.name.contains(search_term, autoescape=True),
                cast(Book.publication_year, String).contains(
                    search_term,
                    autoescape=True,
                ),
            ]

            if isbn_search_term:
                search_conditions.append(
                    Book.isbn.contains(
                        isbn_search_term,
                        autoescape=True,
                    )
                )

            statement = (
                statement
                .join(Author, Book.author_id == Author.id)
                .where(or_(*search_conditions))
            )

        if sort_by == "author":
            if not search_term:
                statement = statement.join(
                    Author,
                    Book.author_id == Author.id,
                )

            statement = statement.order_by(
                Author.name.asc(),
                Book.title.asc(),
            )
        else:
            statement = statement.order_by(Book.title.asc())

        books = db.session.scalars(statement).all()

    return render_template(
        "home.html",
        books=books,
        authors=authors,
        sort_by=sort_by,
        search_term=search_term,
        search_error=search_error,
    )


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    """Zeigt die Details eines Buches an."""
    book = db.session.get(Book, book_id)

    if book is None:
        abort(404)

    return render_template("book_detail.html", book=book)


@app.route("/book/<int:book_id>/rate", methods=["POST"])
def rate_book(book_id):
    """Speichert eine Bewertung zwischen 1 und 10."""
    book = db.session.get(Book, book_id)

    if book is None:
        abort(404)

    rating_text = request.form.get("rating", "").strip()

    if not rating_text.isascii() or not rating_text.isdigit():
        flash("Bitte wähle eine gültige Bewertung aus.", "error")
        return redirect(url_for("book_detail", book_id=book.id))

    rating = int(rating_text)

    if not 1 <= rating <= 10:
        flash("Die Bewertung muss zwischen 1 und 10 liegen.", "error")
        return redirect(url_for("book_detail", book_id=book.id))

    try:
        book.rating = rating
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Die Bewertung konnte nicht gespeichert werden.")
        flash("Die Bewertung konnte nicht gespeichert werden.", "error")
        return redirect(url_for("book_detail", book_id=book.id))

    flash("Deine Bewertung wurde gespeichert.", "success")
    return redirect(url_for("book_detail", book_id=book.id))


@app.route("/author/<int:author_id>")
def author_detail(author_id):
    """Zeigt die Details eines Autors und seine Bücher an."""
    author = db.session.get(Author, author_id)

    if author is None:
        abort(404)

    books = db.session.scalars(
        select(Book)
        .where(Book.author_id == author.id)
        .order_by(Book.title.asc())
    ).all()

    return render_template(
        "author_detail.html",
        author=author,
        books=books,
    )


@app.route("/add_author", methods=["GET", "POST"])
def add_author():
    """Zeigt das Autorenformular an und speichert neue Autoren."""
    if request.method == "GET":
        return render_template("add_author.html", form_data={})

    form_data = {
        "name": request.form.get("name", ""),
        "birth_date": request.form.get("birth_date", ""),
        "date_of_death": request.form.get("date_of_death", ""),
    }

    name = form_data["name"].strip()
    birth_date_text = form_data["birth_date"].strip()
    date_of_death_text = form_data["date_of_death"].strip()

    if not name:
        flash("Bitte gib den Namen des Autors ein.", "error")
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 400

    if len(name) > 100:
        flash("Der Name darf höchstens 100 Zeichen lang sein.", "error")
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 400

    birth_date = parse_optional_date(birth_date_text)
    date_of_death = parse_optional_date(date_of_death_text)

    if birth_date_text and birth_date is None:
        flash("Das Geburtsdatum ist ungültig.", "error")
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 400

    if date_of_death_text and date_of_death is None:
        flash("Das Todesdatum ist ungültig.", "error")
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 400

    if birth_date and date_of_death and date_of_death < birth_date:
        flash(
            "Das Todesdatum darf nicht vor dem Geburtsdatum liegen.",
            "error",
        )
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 400

    author = Author(
        name=name,
        birth_date=birth_date,
        date_of_death=date_of_death,
    )

    try:
        db.session.add(author)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Der Autor konnte nicht gespeichert werden.", "error")
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 400
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Der Autor konnte nicht gespeichert werden.")
        flash("Beim Speichern des Autors ist ein Fehler aufgetreten.", "error")
        return render_template(
            "add_author.html",
            form_data=form_data,
        ), 500

    flash("Der Autor wurde erfolgreich hinzugefügt.", "success")
    return redirect(url_for("add_author"))


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    """Zeigt das Buchformular an und speichert neue Bücher."""
    authors = db.session.scalars(
        select(Author).order_by(Author.name.asc())
    ).all()

    if request.method == "GET":
        return render_template(
            "add_book.html",
            authors=authors,
            form_data={},
        )

    form_data = {
        "isbn": request.form.get("isbn", ""),
        "title": request.form.get("title", ""),
        "publication_year": request.form.get("publication_year", ""),
        "author_id": request.form.get("author_id", ""),
    }

    isbn = re.sub(r"[-\s]", "", form_data["isbn"].strip()).upper()
    title = form_data["title"].strip()
    publication_year_text = form_data["publication_year"].strip()
    author_id_text = form_data["author_id"].strip()

    if not isbn or not title or not author_id_text:
        flash("Bitte fülle alle Pflichtfelder aus.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400

    if len(title) > 200:
        flash("Der Titel darf höchstens 200 Zeichen lang sein.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400

    if not is_valid_isbn(isbn):
        flash("Bitte gib eine gültige ISBN-10 oder ISBN-13 ein.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400

    existing_book_id = db.session.scalar(
        select(Book.id).where(Book.isbn == isbn)
    )

    if existing_book_id is not None:
        flash("Diese ISBN ist bereits in der Bibliothek vorhanden.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400

    publication_year = None

    if publication_year_text:
        if (
            not publication_year_text.isascii()
            or not publication_year_text.isdigit()
        ):
            flash("Das Erscheinungsjahr muss eine Zahl sein.", "error")
            return render_template(
                "add_book.html",
                authors=authors,
                form_data=form_data,
            ), 400

        publication_year = int(publication_year_text)

        if not 1 <= publication_year <= 9999:
            flash("Das Erscheinungsjahr ist ungültig.", "error")
            return render_template(
                "add_book.html",
                authors=authors,
                form_data=form_data,
            ), 400

    if (
        not author_id_text.isascii()
        or not author_id_text.isdigit()
    ):
        flash("Bitte wähle einen gültigen Autor aus.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400

    author_id = int(author_id_text)
    author = db.session.get(Author, author_id)

    if author is None:
        flash("Der ausgewählte Autor wurde nicht gefunden.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400

    book = Book(
        isbn=isbn,
        title=title,
        publication_year=publication_year,
        author_id=author.id,
    )

    try:
        db.session.add(book)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "Das Buch konnte nicht gespeichert werden. "
            "Möglicherweise ist die ISBN bereits vorhanden.",
            "error",
        )
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 400
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Das Buch konnte nicht gespeichert werden.")
        flash("Beim Speichern des Buches ist ein Fehler aufgetreten.", "error")
        return render_template(
            "add_book.html",
            authors=authors,
            form_data=form_data,
        ), 500

    flash("Das Buch wurde erfolgreich hinzugefügt.", "success")
    return redirect(url_for("add_book"))


@app.route("/book/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    """Löscht ein Buch und bei Bedarf den verwaisten Autor."""
    book = db.session.get(Book, book_id)

    if book is None:
        flash("Das Buch wurde nicht gefunden.", "error")
        return redirect(url_for("index"))

    author = book.author
    author_name = author.name if author is not None else None

    try:
        db.session.delete(book)
        db.session.flush()

        if author is not None:
            remaining_book_id = db.session.scalar(
                select(Book.id)
                .where(Book.author_id == author.id)
                .limit(1)
            )

            if remaining_book_id is None:
                db.session.delete(author)

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Das Buch konnte nicht gelöscht werden.")
        flash("Das Buch konnte nicht gelöscht werden.", "error")
        return redirect(url_for("index"))

    if author_name is not None:
        flash(
            f"Das Buch wurde gelöscht. "
            f"Falls es das letzte Buch von {author_name} war, "
            "wurde auch der Autor entfernt.",
            "success",
        )
    else:
        flash("Das Buch wurde erfolgreich gelöscht.", "success")

    return redirect(url_for("index"))


@app.route("/author/<int:author_id>/delete", methods=["POST"])
def delete_author(author_id):
    """Löscht einen Autor und alle zugehörigen Bücher."""
    author = db.session.get(Author, author_id)

    if author is None:
        flash("Der Autor wurde nicht gefunden.", "error")
        return redirect(url_for("index"))

    author_name = author.name

    try:
        for book in list(author.books):
            db.session.delete(book)

        db.session.delete(author)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Der Autor konnte nicht gelöscht werden.")
        flash("Der Autor konnte nicht gelöscht werden.", "error")
        return redirect(url_for("index"))

    flash(
        f"Der Autor „{author_name}“ und seine Bücher wurden gelöscht.",
        "success",
    )
    return redirect(url_for("index"))


@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    """Zeigt eine Buchempfehlung für die eigene Bibliothek an."""
    recommendation = None
    error = None

    if request.method == "POST":
        books = db.session.scalars(
            select(Book).order_by(Book.title.asc())
        ).all()

        if not books:
            error = "Füge zuerst Bücher zu deiner Bibliothek hinzu."
        else:
            now = time.time()
            last_request = session.get("last_recommendation_at", 0)
            remaining = 60 - int(now - last_request)

            if remaining > 0:
                error = (
                    f"Bitte warte noch {remaining} Sekunden, "
                    "bevor du eine neue Empfehlung anforderst."
                )
            else:
                # Anfragezeit vor dem API-Aufruf speichern
                session["last_recommendation_at"] = now

                try:
                    recommendation = get_book_recommendation(books)
                except (
                    http.client.HTTPException,
                    OSError,
                    ValueError,
                    RuntimeError,
                ):
                    app.logger.exception("RapidAPI-Anfrage fehlgeschlagen.")
                    error = (
                        "Die Buchempfehlung konnte gerade "
                        "nicht erstellt werden."
                    )

    return render_template(
        "recommendations.html",
        recommendation=recommendation,
        error=error,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)