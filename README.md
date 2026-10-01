# Seitenweise – Digitale Bibliothek

Eine Flask-Webanwendung zur Verwaltung einer persönlichen digitalen Bibliothek. Bücher können Autorinnen und Autoren zugeordnet, gesucht, sortiert, bewertet und über eine KI-Funktion empfohlen werden.

## Funktionen

- Autorinnen und Autoren sowie Bücher hinzufügen
- Bücher nach Titel, Autor, ISBN oder Erscheinungsjahr durchsuchen
- Bücher nach Titel oder Autor sortieren
- Detailseiten für Bücher und Autorinnen und Autoren anzeigen
- Bücher bewerten und löschen
- Nicht mehr verwendete Autoren löschen
- Buchempfehlungen über RapidAPI anfordern
- Responsive Benutzeroberfläche mit hellem und dunklem Design

## Voraussetzungen

- Python 3
- Ein RapidAPI-Konto und ein API-Schlüssel für die Empfehlungsfunktion

## Installation unter Windows

Repository klonen und in den Projektordner wechseln:

```powershell
git clone https://github.com/Strixik/bibliothek.git
cd bibliothek
```

Virtuelle Umgebung erstellen und aktivieren:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Benötigte Pakete installieren:

```powershell
pip install Flask Flask-SQLAlchemy
```

Falls der Ordner `data` noch nicht existiert, erstelle ihn:

```powershell
New-Item -ItemType Directory -Force data
```

Datenbanktabellen erstellen und die Bewertungsspalte ergänzen:

```powershell
python create_tables.py
python migrate_rating.py
```

Optional Beispieldaten laden:

```powershell
python seed_data.py
```

Der Beispieldatensatz kann erneut geladen werden, ohne vorhandene Autoren und Bücher zu duplizieren.

## RapidAPI-Schlüssel einrichten

Der API-Schlüssel wird nicht im Quellcode gespeichert. Setze ihn in derselben PowerShell-Sitzung, in der du die Anwendung startest:

```powershell
$env:RAPIDAPI_KEY = "DEIN_API_SCHLÜSSEL"
```

Ohne API-Schlüssel funktionieren die Bibliotheksfunktionen weiterhin. Für KI-Buchempfehlungen wird der Schlüssel benötigt.

## Anwendung starten

```powershell
python app.py
```

Öffne danach die lokale Adresse, die im Terminal angezeigt wird. Bei Port 5002 lautet sie:

```text
http://127.0.0.1:5002
```

## Projektstruktur

```text
bibliothek/
├── app.py
├── data_models.py
├── create_tables.py
├── migrate_rating.py
├── seed_data.py
├── data/
├── static/
│   ├── script.js
│   └── style.css
└── templates/
```

Die SQLite-Datenbank und API-Schlüssel werden nicht in GitHub gespeichert. Die Datenbank wird lokal erstellt und kann anschließend mit Beispieldaten gefüllt werden.