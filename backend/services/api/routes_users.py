from flask import Blueprint, request, jsonify
import db_client
from db_client import DBServiceError

users_bp = Blueprint("users", __name__)


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def handle_db_error(e: DBServiceError):
    return error_response(e.message, e.status_code)


# degrees dropdown endpoint, admin curated list
@users_bp.route("/api/degrees", methods=["GET"])
def get_degrees():
    try:
        degrees = db_client.list_degrees()
        return jsonify({"count": len(degrees), "degrees": degrees}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# skill categories dropdown endpoint, admin curated list
@users_bp.route("/api/skill-categories", methods=["GET"])
def get_skill_categories():
    try:
        categories = db_client.list_categories()
        return jsonify({"count": len(categories), "categories": categories}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# profile view endpoint
@users_bp.route("/api/users/<int:user_id>", methods=["GET"])
def get_user_profile(user_id):
    try:
        user = db_client.get_user(user_id)
        if not user:
            return error_response(f"No user found with user_id {user_id}", 404)

        # Never send the password hash back to a client, even on their own profile
        user.pop("password_hash", None)

        return jsonify({"user": user}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# profile edit endpoint
@users_bp.route("/api/users/<int:user_id>", methods=["PATCH"])
def update_user_profile(user_id):
    """
    Expected JSON body, every field optional:
    { "name": "...", "bio": "...", "avatar_url": "...", "degree_id": 2, "class_year": 2027 }
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    editable_fields = ("name", "bio", "avatar_url", "degree_id", "class_year")
    fields = {key: data[key] for key in editable_fields if key in data}

    if not fields:
        return error_response("Provide at least one editable field to update", 400)

    try:
        user = db_client.get_user(user_id)
        if not user:
            return error_response(f"No user found with user_id {user_id}", 404)

        updated = db_client.update_user(user_id, fields)
        updated.pop("password_hash", None)

        return jsonify({"message": "Profile updated successfully", "user": updated}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# search users endpoint, name search only, no other filters per the spec
@users_bp.route("/api/search/users", methods=["GET"])
def search_users():
    """Optional query string: ?q=partial_name"""
    q = request.args.get("q")
    try:
        users = db_client.search_users(q)
        for user in users:
            user.pop("password_hash", None)
        return jsonify({"count": len(users), "users": users}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# a user's received reviews, shown on their profile
@users_bp.route("/api/users/<int:user_id>/reviews", methods=["GET"])
def get_user_reviews(user_id):
    try:
        reviews = db_client.get_user_reviews(user_id)
        return jsonify({"user_id": user_id, "count": len(reviews), "reviews": reviews}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)
