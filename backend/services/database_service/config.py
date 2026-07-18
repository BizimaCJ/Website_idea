import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# This is the ONLY service that should ever open this file directly.
DATABASE = os.path.join(BASE_DIR, '..', '..', 'database', 'ubuntuskills.db')

PORT = 5002
