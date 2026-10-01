from sqlalchemy import inspect, text

from app import app, db


with app.app_context():
    columns = {
        column["name"]
        for column in inspect(db.engine).get_columns("books")
    }

    if "rating" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE books ADD COLUMN rating INTEGER")
            )

        print("Die Bewertungsspalte wurde hinzugefügt.")
    else:
        print("Die Bewertungsspalte ist bereits vorhanden.")