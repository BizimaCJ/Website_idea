import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = 'ubuntu_skills_secret_key'

# auth/ no longer opens the database file directly - it talks to
# database_service over HTTP instead. See db_client.py.
DB_SERVICE_URL = os.environ.get("DB_SERVICE_URL", "http://localhost:5002")

# Anyone signing up with an email ending in this domain is verified
# automatically. Everyone else must go through the manual document
# review path instead. This is a single domain for now since the pilot
# only covers one school, and becomes a list once more schools join.
SCHOOL_EMAIL_DOMAIN = os.environ.get("SCHOOL_EMAIL_DOMAIN", "@anu.ac.rw")
