from flask import Blueprint, request, jsonify
import db_client
from db_client import DBServiceError

sessions_bp = Blueprint("sessions", __name__)


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def handle_db_error(e: DBServiceError):
    return error_response(e.message, e.status_code)


def recalculate_credits(reviewee_id):
    """
    Recomputes the cached rating shown on a profile from every review the
    person has ever received, using each review's weight. A repeat review
    from the same reviewer carries a smaller weight, so it moves the
    average less than a review from someone new, which is what keeps two
    friends from farming each other's rating by reviewing over and over.
    """
    reviews = db_client.get_user_reviews(reviewee_id)
    if not reviews:
        db_client.update_credits(reviewee_id, 0, 0)
        return

    weighted_sum = sum(review["rating"] * review["weight"] for review in reviews)
    total_weight = sum(review["weight"] for review in reviews)
    average = round(weighted_sum / total_weight, 1) if total_weight else 0

    db_client.update_credits(reviewee_id, average, len(reviews))


# request a session with a teacher, for one specific thing they listed
@sessions_bp.route("/api/sessions", methods=["POST"])
def request_session():
    """
    Expected JSON body:
    { "learner_id": 4, "user_skill_id": 7, "scheduled_time": "2026-07-20T14:00" }
    teacher_id is not passed in directly, it is looked up from the teach
    listing itself, so a session can never point at the wrong teacher.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    learner_id = data.get("learner_id")
    user_skill_id = data.get("user_skill_id")
    scheduled_time = data.get("scheduled_time")

    if not all([learner_id, user_skill_id, scheduled_time]):
        return error_response("'learner_id', 'user_skill_id', and 'scheduled_time' are required", 400)

    try:
        listing = db_client.get_user_skill(user_skill_id)
        if not listing:
            return error_response(f"No skill listing found with user_skill_id {user_skill_id}", 404)

        if listing["skill_type"] != "teach":
            return error_response("A session can only be requested against a 'teach' listing", 400)

        teacher_id = listing["user_id"]
        if teacher_id == learner_id:
            return error_response("A user cannot request a session with themselves", 400)

        session_id = db_client.insert_session(teacher_id, learner_id, user_skill_id, scheduled_time)

        db_client.insert_notification(
            user_id=teacher_id,
            notification_type="session_requested",
            message="You have a new session request",
            related_session_id=session_id,
        )

        new_session = db_client.get_session(session_id)
        return jsonify({"message": "Session requested", "session": new_session}), 201

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# teacher approves or declines a pending session
@sessions_bp.route("/api/sessions/<int:session_id>/respond", methods=["PATCH"])
def respond_to_session(session_id):
    """Expected JSON body: { "status": "approved" } or { "status": "declined" }"""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    status = data.get("status")
    if status not in ("approved", "declined"):
        return error_response("'status' must be 'approved' or 'declined'", 400)

    try:
        session = db_client.get_session(session_id)
        if not session:
            return error_response(f"No session found with session_id {session_id}", 404)

        if session["status"] != "pending":
            return error_response("Only a pending session can be approved or declined", 409)

        updated = db_client.update_session_status(session_id, status)

        db_client.insert_notification(
            user_id=session["learner_id"],
            notification_type="session_approved" if status == "approved" else "session_declined",
            message=f"Your session request was {status}",
            related_session_id=session_id,
        )

        return jsonify({"message": f"Session {status}", "session": updated}), 200

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# either party cancels a session that was already approved, or a learner
# withdraws a request that is still pending
@sessions_bp.route("/api/sessions/<int:session_id>/cancel", methods=["PATCH"])
def cancel_session(session_id):
    """Expected JSON body: { "cancelled_by": 4 }"""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    cancelled_by = data.get("cancelled_by")
    if not cancelled_by:
        return error_response("'cancelled_by' is required", 400)

    try:
        session = db_client.get_session(session_id)
        if not session:
            return error_response(f"No session found with session_id {session_id}", 404)

        if session["status"] not in ("pending", "approved"):
            return error_response("Only a pending or approved session can be cancelled", 409)

        if cancelled_by not in (session["teacher_id"], session["learner_id"]):
            return error_response("Only the teacher or the learner on this session can cancel it", 403)

        updated = db_client.update_session_status(session_id, "cancelled", cancelled_by)

        other_user_id = session["learner_id"] if cancelled_by == session["teacher_id"] else session["teacher_id"]
        db_client.insert_notification(
            user_id=other_user_id,
            notification_type="session_cancelled",
            message="A session you had scheduled was cancelled",
            related_session_id=session_id,
        )

        return jsonify({"message": "Session cancelled", "session": updated}), 200

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# either party marks a session as completed once it actually happened
@sessions_bp.route("/api/sessions/<int:session_id>/complete", methods=["PATCH"])
def complete_session(session_id):
    """
    Expected JSON body: { "user_id": 4 }
    The session only becomes 'completed' once both the teacher and the
    learner have each confirmed it here.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    user_id = data.get("user_id")
    if not user_id:
        return error_response("'user_id' is required", 400)

    try:
        session = db_client.get_session(session_id)
        if not session:
            return error_response(f"No session found with session_id {session_id}", 404)

        if session["status"] != "approved":
            return error_response("Only an approved session can be marked completed", 409)

        if user_id == session["teacher_id"]:
            role = "teacher"
        elif user_id == session["learner_id"]:
            role = "learner"
        else:
            return error_response("Only the teacher or the learner on this session can mark it completed", 403)

        updated = db_client.mark_session_completed(session_id, role)

        if updated["status"] == "completed":
            db_client.insert_notification(
                user_id=session["learner_id"],
                notification_type="review_prompt",
                message="Leave a review for your last session",
                related_session_id=session_id,
            )

        return jsonify({"message": "Completion recorded", "session": updated}), 200

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# learner leaves a review for the teacher after a completed session
@sessions_bp.route("/api/sessions/<int:session_id>/review", methods=["POST"])
def leave_review(session_id):
    """
    Expected JSON body: { "rating": 5, "comment": "Explained it really well" }
    Only the learner on a completed session can call this, and only once.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON", 400)

    rating = data.get("rating")
    comment = data.get("comment")
    reviewer_id = data.get("reviewer_id")

    if not reviewer_id or rating is None:
        return error_response("'reviewer_id' and 'rating' are required", 400)

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return error_response("'rating' must be an integer from 1 to 5", 400)

    try:
        session = db_client.get_session(session_id)
        if not session:
            return error_response(f"No session found with session_id {session_id}", 404)

        if session["status"] != "completed":
            return error_response("A review can only be left on a completed session", 409)

        if reviewer_id != session["learner_id"]:
            return error_response("Only the learner on this session can leave a review", 403)

        reviewee_id = session["teacher_id"]

        prior_count = db_client.count_reviews_between(reviewer_id, reviewee_id)
        weight = round(1 / (prior_count + 1), 2)

        review_id = db_client.insert_review(session_id, reviewer_id, reviewee_id, rating, comment, weight)
        recalculate_credits(reviewee_id)

        return jsonify({"message": "Review submitted", "review_id": review_id}), 201

    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)


# a user's sessions, split by tab on the frontend
@sessions_bp.route("/api/users/<int:user_id>/sessions", methods=["GET"])
def get_user_sessions(user_id):
    """Optional query string: ?status=pending|approved|declined|cancelled|completed&role=teacher|learner"""
    status_filter = request.args.get("status")
    role_filter = request.args.get("role")

    try:
        sessions = db_client.get_user_sessions(user_id, status_filter, role_filter)
        return jsonify({"user_id": user_id, "count": len(sessions), "sessions": sessions}), 200
    except DBServiceError as e:
        return handle_db_error(e)
    except Exception as e:
        return error_response(str(e), 500)
