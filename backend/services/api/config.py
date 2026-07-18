import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# api/ no longer opens the database file directly - it talks to
# database_service over HTTP instead. See db_client.py.
DB_SERVICE_URL = os.environ.get("DB_SERVICE_URL", "http://localhost:5002")