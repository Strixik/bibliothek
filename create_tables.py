from app import app
from data_models import db


# Tabellen innerhalb des Anwendungskontexts erstellen
with app.app_context():
    db.create_all()

print("Tabellen wurden erstellt.")