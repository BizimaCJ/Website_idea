from flask import Blueprint, request, jsonify
import db_client
from db_client import DBServiceError

notifications_bp = Blueprint("notifications", __name__)


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def handle_db_error(e: DBServiceError):
    return error_response(e.message, e.status_code)


# list a user's notifications, newest first
@notifications_bp.route("/api/users/<int:user_id>/notifications", methods=["GET"])
def get_notifications(user_id):
    """Optional query string: ?unread_only=true"""
    unread_only = request.args.get("unread_only") == "true"

    try:
        notifications = db_client.list_notifications(user_id, unread_only)
        return jsonify({
            "user_id": user_id,
            "count": len(notifications),
            "notifications": notifications,
        }), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# mark a single notification as read
@notifications_bp.route("/api/notifications/<int:notification_id>/read", methods=["PATCH"])
def read_notification(notification_id):
    try:
        db_client.mark_notification_read(notification_id)
        return jsonify({"notification_id": notification_id, "is_read": True}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# mark all as read, for the Notifications page's "mark all as read" button
@notifications_bp.route("/api/users/<int:user_id>/notifications/read-all", methods=["PATCH"])
def read_all_notifications(user_id):
    try:
        result = db_client.mark_all_notifications_read(user_id)
        return jsonify({
            "message": "All notifications marked as read",
            "updated_count": result.get("updated_count", 0),
        }), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)
