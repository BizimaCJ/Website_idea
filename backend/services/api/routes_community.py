from flask import Blueprint, request, jsonify
import db_client
from db_client import DBServiceError

community_bp = Blueprint("community", __name__)


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def handle_db_error(e: DBServiceError):
    return error_response(e.message, e.status_code)


# host a group session, teacher is auto-added as the first member
@community_bp.route("/api/group-sessions", methods=["POST"])
def create_group_session():
    """
    Expected JSON body:
    { "teacher_id": 4, "category_id": 3, "topic": "Intro to React",
      "scheduled_time": "2026-07-22T18:00", "max_participants": 5 }
    Announces the session to every user who listed this category as
    something they want to learn, by sending each of them a notification.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    teacher_id = data.get("teacher_id")
    category_id = data.get("category_id")
    topic = data.get("topic")
    scheduled_time = data.get("scheduled_time")
    max_participants = data.get("max_participants", 5)

    if not all([teacher_id, category_id, topic, scheduled_time]):
        return error_response("'teacher_id', 'category_id', 'topic', and 'scheduled_time' are required", 400)

    try:
        group_session_id = db_client.insert_group_session(
            teacher_id, category_id, topic, scheduled_time, max_participants
        )

        # The teacher is a member of their own group session from the start,
        # this is what makes the seat count start at 1 out of max_participants.
        db_client.insert_group_member(group_session_id, teacher_id)

        # A group chat is created up front, with just the teacher in it for now.
        conversation_id = db_client.insert_conversation(
            participant_ids=[teacher_id], is_group=True, group_session_id=group_session_id
        )

        learner_ids = db_client.category_learners(category_id)
        for learner_id in learner_ids:
            if learner_id == teacher_id:
                continue
            db_client.insert_notification(
                user_id=learner_id,
                notification_type="group_session_announced",
                message=f"A new group session on {topic} was just announced",
                related_group_session_id=group_session_id,
            )

        new_group_session = db_client.get_group_session(group_session_id)
        return jsonify({
            "message": "Group session created",
            "group_session": new_group_session,
            "conversation_id": conversation_id,
        }), 201

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# list group sessions for the Community page
@community_bp.route("/api/group-sessions", methods=["GET"])
def list_group_sessions():
    """Optional query string: ?status=scheduled|completed|cancelled, defaults to scheduled"""
    status_filter = request.args.get("status", "scheduled")

    try:
        group_sessions = db_client.list_group_sessions(status_filter)
        return jsonify({"count": len(group_sessions), "group_sessions": group_sessions}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# join a group session, and automatically join its group chat too
@community_bp.route("/api/group-sessions/<int:group_session_id>/join", methods=["POST"])
def join_group_session(group_session_id):
    """Expected JSON body: { "user_id": 6 }"""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    user_id = data.get("user_id")
    if not user_id:
        return error_response("'user_id' is required", 400)

    try:
        group_session = db_client.get_group_session(group_session_id)
        if not group_session:
            return error_response(f"No group session found with group_session_id {group_session_id}", 404)

        if group_session["status"] != "scheduled":
            return error_response("This group session is no longer open to join", 409)

        current_members = db_client.list_group_members(group_session_id)
        if len(current_members) >= group_session["max_participants"]:
            return error_response("This group session is already full", 409)

        if any(member["user_id"] == user_id for member in current_members):
            return error_response("You have already joined this group session", 409)

        db_client.insert_group_member(group_session_id, user_id)

        # Find the group chat tied to this session, then add the new member to it.
        conversations = db_client.list_user_conversations(group_session["teacher_id"])
        matching = next(
            (c for c in conversations if c.get("group_session_id") == group_session_id), None
        )
        if matching:
            db_client.add_conversation_participant(matching["conversation_id"], user_id)

        return jsonify({"message": "Joined group session", "group_session_id": group_session_id}), 200

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# mark a group session done, this empties its membership and deletes its chat
@community_bp.route("/api/group-sessions/<int:group_session_id>/complete", methods=["PATCH"])
def complete_group_session(group_session_id):
    try:
        group_session = db_client.get_group_session(group_session_id)
        if not group_session:
            return error_response(f"No group session found with group_session_id {group_session_id}", 404)

        db_client.update_group_session_status(group_session_id, "completed")
        db_client.clear_group_members(group_session_id)

        conversations = db_client.list_user_conversations(group_session["teacher_id"])
        matching = next(
            (c for c in conversations if c.get("group_session_id") == group_session_id), None
        )
        if matching:
            db_client.delete_conversation(matching["conversation_id"])

        return jsonify({"message": "Group session marked completed", "group_session_id": group_session_id}), 200

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)
