from flask import Blueprint, request, jsonify
import db_client
from db_client import DBServiceError

skills_bp = Blueprint("skills", __name__)


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def handle_db_error(e: DBServiceError):
    return error_response(e.message, e.status_code)


# add a teach or learn skill listing to a user's profile
@skills_bp.route("/api/users/<int:user_id>/skills", methods=["POST"])
def add_user_skill(user_id):
    """
    Expected JSON body:
    { "category_id": 3, "description": "React and Tailwind", "skill_type": "teach" }
    category_id must come from the admin curated SkillCategories list, the
    student only writes the free text description within that category.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    category_id = data.get("category_id")
    description = data.get("description")
    skill_type = data.get("skill_type")

    if category_id is None or not description:
        return error_response("'category_id' and 'description' are required", 400)

    if skill_type not in ("teach", "learn"):
        return error_response("'skill_type' must be 'teach' or 'learn'", 400)

    try:
        new_user_skill = db_client.insert_user_skill(user_id, category_id, description, skill_type)
        return jsonify({"message": "Skill added to profile", "user_skill": new_user_skill}), 201
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# list a user's teach and learn skills
@skills_bp.route("/api/users/<int:user_id>/skills", methods=["GET"])
def get_user_skills(user_id):
    """Optional query string: ?type=teach|learn"""
    type_filter = request.args.get("type")
    if type_filter and type_filter not in ("teach", "learn"):
        return error_response("'type' query param must be 'teach' or 'learn'", 400)

    try:
        skills = db_client.get_user_skills(user_id, type_filter)
        return jsonify({"user_id": user_id, "count": len(skills), "skills": skills}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# remove a skill listing from a user's profile
@skills_bp.route("/api/users/<int:user_id>/skills/<int:user_skill_id>", methods=["DELETE"])
def remove_user_skill(user_id, user_skill_id):
    try:
        removed_count = db_client.delete_user_skill(user_id, user_skill_id)
        if removed_count == 0:
            return error_response("No matching skill listing found for that user", 404)

        return jsonify({
            "message": "Skill removed from profile",
            "user_id": user_id,
            "user_skill_id": user_skill_id,
        }), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# main search page, filters combine with AND
@skills_bp.route("/api/search/skills", methods=["GET"])
def search_skills():
    """
    Query string, every filter optional:
    ?type=teach|learn&category_id=&degree_id=&class_year=
    type here means whether the results are people who CAN TEACH that
    skill or people who WANT TO LEARN it, matching the mockup's
    Can teach me / Wants to learn filter tabs.
    """
    type_filter = request.args.get("type")
    category_id = request.args.get("category_id")
    degree_id = request.args.get("degree_id")
    class_year = request.args.get("class_year")

    if type_filter and type_filter not in ("teach", "learn"):
        return error_response("'type' query param must be 'teach' or 'learn'", 400)

    try:
        results = db_client.search_user_skills(type_filter, category_id, degree_id, class_year)
        for result in results:
            result.pop("password_hash", None)
        return jsonify({"count": len(results), "results": results}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)
