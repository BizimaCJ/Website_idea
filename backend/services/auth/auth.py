from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from config import SECRET_KEY, SCHOOL_EMAIL_DOMAIN
import db_client
from db_client import DBServiceError

app = Flask(__name__)
CORS(app)
app.secret_key = SECRET_KEY
bcrypt = Bcrypt(app)


# ─ REGISTER ROUTE ─
@app.route('/register', methods=['POST'])
def register():
    """
    Expected JSON body:
    {
        "name": "...", "email": "...", "password": "...",
        "degree_id": 2, "class_year": 2027,
        "verification_document_path": null
    }
    If the email ends in the trusted school domain, the account is
    verified immediately. Otherwise verification_document_path must be
    provided, and the account sits at 'pending' until someone on the team
    reviews the document and approves or rejects it manually.
    """
    data = request.get_json()

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    degree_id = data.get('degree_id')
    class_year = data.get('class_year')
    verification_document_path = data.get('verification_document_path')

    # Check all fields are provided
    if not name or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    is_school_email = email.lower().endswith(SCHOOL_EMAIL_DOMAIN.lower())

    if is_school_email:
        verification_method = 'school_email'
        verification_status = 'verified'
    else:
        if not verification_document_path:
            return jsonify({
                'error': (
                    "This email is not a recognized school address, so a "
                    "verification document is required to sign up"
                )
            }), 400
        verification_method = 'document'
        verification_status = 'pending'

    try:
        # Check if email already exists
        existing_user = db_client.get_user_by_email(email)
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409

        # Hash the password before saving
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        # Save new user to database
        user_id = db_client.insert_user(
            name, email, password_hash, verification_method, verification_status,
            degree_id=degree_id, class_year=class_year,
            verification_document_path=verification_document_path,
        )

        return jsonify({
            'message': 'User registered successfully',
            'verification_method': verification_method,
            'verification_status': verification_status,
        }), 201

    except DBServiceError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─ LOGIN ROUTE ─
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    # Check all fields are provided
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    try:
        # Look up user by email
        user = db_client.get_user_by_email(email)

        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Compare entered password with stored hash
        if not bcrypt.check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid email or password'}), 401

        # A pending manual verification cannot log in yet, a rejected one never can
        if user['verification_status'] == 'pending':
            return jsonify({'error': 'Your account is still awaiting verification'}), 403
        if user['verification_status'] == 'rejected':
            return jsonify({'error': 'Your verification was not approved'}), 403

        session['user_id'] = user['user_id']
        session['name'] = user['name']
        return jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
            }
        }), 200

    except DBServiceError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─ HEALTH CHECK ROUTE ─
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'auth'}), 200


# ─ LOGOUT ROUTE ─
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
