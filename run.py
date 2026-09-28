"""
run.py
-------
Entry point to start the Flask development server.

Usage:
    python run.py

Make sure you've:
1. Created a MySQL database (see README.md)
2. Copied .env.example -> .env and filled in your values
3. Run `python seed_data.py` at least once to create tables + demo data
"""

import os
from app import create_app
from app import db
from app.db_utils import assert_database_ready, synchronize_existing_schema

# Load .env file if python-dotenv is installed (optional convenience)
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:
    pass

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    try:
        db_info = assert_database_ready(app)
        print(f"Database connection OK: {db_info['masked_uri']}")
        if db_info.get("created_database"):
            print(f"Created missing MySQL database: {db_info['database']}")
        with app.app_context():
            db.create_all()
        schema_changes = synchronize_existing_schema(app)
        if schema_changes:
            print("Updated existing schema columns: " + ", ".join(schema_changes))
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from exc

    app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    debug=True,
    use_reloader=False
    )
