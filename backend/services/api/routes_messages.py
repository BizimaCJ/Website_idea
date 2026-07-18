from flask import Blueprint, request, jsonify
import db_client
from db_client import DBServiceError

messages_bp = Blueprint("messages", __name__)


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def handle_db_error(e: DBServiceError):
    return error_response(e.message, e.status_code)


# start a 1:1 conversation, for example from the Message button on a profile
@messages_bp.route("/api/conversations", methods=["POST"])
def start_conversation():
    """Expected JSON body: { "participant_ids": [4, 9] }"""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    participant_ids = data.get("participant_ids")
    if not participant_ids or len(participant_ids) < 2:
        return error_response("'participant_ids' must include at least two users", 400)

    try:
        conversation_id = db_client.insert_conversation(participant_ids, is_group=False)
        return jsonify({"message": "Conversation started", "conversation_id": conversation_id}), 201
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# list every conversation a user is part of, for the Messages page's left panel
@messages_bp.route("/api/users/<int:user_id>/conversations", methods=["GET"])
def get_user_conversations(user_id):
    try:
        conversations = db_client.list_user_conversations(user_id)

        for conversation in conversations:
            conversation["participants"] = db_client.get_conversation_participants(
                conversation["conversation_id"]
            )

        return jsonify({"user_id": user_id, "count": len(conversations), "conversations": conversations}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# send a message into a conversation, works the same for 1:1 and group chat
@messages_bp.route("/api/conversations/<int:conversation_id>/messages", methods=["POST"])
def send_message(conversation_id):
    """Expected JSON body: { "sender_id": 4, "message_text": "Hey, are we still on for Tuesday?" }"""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    sender_id = data.get("sender_id")
    message_text = data.get("message_text")

    if not sender_id or not message_text:
        return error_response("'sender_id' and 'message_text' are required", 400)

    try:
        message = db_client.insert_message(conversation_id, sender_id, message_text)

        participants = db_client.get_conversation_participants(conversation_id)
        for participant in participants:
            if participant["user_id"] != sender_id:
                db_client.insert_notification(
                    user_id=participant["user_id"],
                    notification_type="new_message",
                    message="You have a new message",
                )

        return jsonify({"message_sent": message}), 201
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# load the full history of a conversation
@messages_bp.route("/api/conversations/<int:conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    try:
        messages = db_client.list_messages(conversation_id)
        return jsonify({"conversation_id": conversation_id, "count": len(messages), "messages": messages}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)
