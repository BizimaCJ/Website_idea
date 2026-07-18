"""
database_service
=================
This is the single service allowed to open the SQLite file and run SQL.
`api/` and `auth/` no longer import sqlite3 at all - they call the small
HTTP endpoints defined here instead.

Every route here is a thin, purpose-built wrapper around one parametrized
SQL statement (or a couple of related ones). It does NOT contain business
rules like "has this teacher already been asked five times today" - that
kind of decision-making and the associated HTTP status codes still live in
api/ and auth/. This service's only job is: take simple JSON in, run safe
parametrized SQL, return simple JSON out.
"""

from flask import Flask, request, jsonify
import sqlite3
from config import DATABASE, PORT

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_or_none(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(row) for row in rows]


def error_response(message, status_code=500):
    return jsonify({"error": message}), status_code


# ── Users ──

@app.route("/users", methods=["POST"])
def insert_user():
    """
    Body: { name, email, password_hash, bio, avatar_url, degree_id,
            class_year, verification_method, verification_status,
            verification_document_path }
    Caller (auth service) already decided verification_method and
    verification_status before calling this, based on whether the email
    matched the school domain.
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    password_hash = data.get("password_hash")
    verification_method = data.get("verification_method")
    verification_status = data.get("verification_status", "pending")

    if not name or not email or not password_hash or not verification_method:
        return error_response(
            "'name', 'email', 'password_hash', and 'verification_method' are required", 400
        )

    try:
        conn = get_db()
        cur = conn.execute(
            """
            INSERT INTO Users
                (name, email, password_hash, bio, avatar_url, degree_id, class_year,
                 verification_method, verification_status, verification_document_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, email, password_hash,
                data.get("bio"), data.get("avatar_url"), data.get("degree_id"),
                data.get("class_year"), verification_method, verification_status,
                data.get("verification_document_path"),
            ),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return jsonify({"user_id": user_id}), 201
    except sqlite3.IntegrityError as e:
        return error_response(str(e), 409)
    except Exception as e:
        return error_response(str(e))


@app.route("/users/by-email/<path:email>", methods=["GET"])
def get_user_by_email(email):
    try:
        conn = get_db()
        user = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()
        conn.close()
        return jsonify({"user": row_or_none(user)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        conn = get_db()
        user = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        return jsonify({"user": row_or_none(user)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    """
    Edits any subset of the editable profile fields. Only columns present
    in the request body get overwritten, everything else keeps its
    current value.
    """
    data = request.get_json(silent=True) or {}
    editable_fields = ("name", "bio", "avatar_url", "degree_id", "class_year")
    updates = {field: data[field] for field in editable_fields if field in data}

    if not updates:
        return error_response("No editable fields provided", 400)

    try:
        conn = get_db()
        set_clause = ", ".join(f"{field} = ?" for field in updates)
        conn.execute(
            f"UPDATE Users SET {set_clause} WHERE user_id = ?",
            (*updates.values(), user_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        return jsonify({"user": row_or_none(updated)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/verification", methods=["PATCH"])
def update_verification(user_id):
    """Used when a manually submitted document gets approved or rejected."""
    data = request.get_json(silent=True) or {}
    status = data.get("verification_status")
    if status not in ("pending", "verified", "rejected"):
        return error_response("'verification_status' must be pending, verified, or rejected", 400)

    try:
        conn = get_db()
        conn.execute(
            "UPDATE Users SET verification_status = ? WHERE user_id = ?",
            (status, user_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        return jsonify({"user": row_or_none(updated)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/credits", methods=["PATCH"])
def update_credits(user_id):
    """
    Overwrites the cached rating shown on a profile. The api layer computes
    the new weighted average and count after inserting a review, then
    writes the result here rather than this service doing the averaging.
    """
    data = request.get_json(silent=True) or {}
    credits_average = data.get("credits_average")
    credits_count = data.get("credits_count")

    if credits_average is None or credits_count is None:
        return error_response("'credits_average' and 'credits_count' are required", 400)

    try:
        conn = get_db()
        conn.execute(
            "UPDATE Users SET credits_average = ?, credits_count = ? WHERE user_id = ?",
            (credits_average, credits_count, user_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"user_id": user_id, "credits_average": credits_average, "credits_count": credits_count}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users", methods=["GET"])
def search_users():
    """
    Per the product spec, user search has no filters other than an
    optional name match, unlike skill search which is heavily filtered.
    Optional query string: ?q=partial_name
    """
    q = request.args.get("q")
    try:
        conn = get_db()
        if q:
            rows = conn.execute(
                "SELECT * FROM Users WHERE name LIKE ? ORDER BY name", (f"%{q}%",)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM Users ORDER BY name").fetchall()
        conn.close()
        return jsonify({"users": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


# ── Degrees ──

@app.route("/degrees", methods=["GET"])
def list_degrees():
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM Degrees ORDER BY degree_name").fetchall()
        conn.close()
        return jsonify({"degrees": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


# ── SkillCategories ──

@app.route("/skill-categories", methods=["GET"])
def list_categories():
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM SkillCategories ORDER BY category_name").fetchall()
        conn.close()
        return jsonify({"categories": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/skill-categories/<int:category_id>/learners", methods=["GET"])
def category_learners(category_id):
    """
    Every user who listed this category as something they want to learn.
    Used to decide who gets a group_session_announced notification.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT DISTINCT Users.user_id
            FROM UserSkills
            JOIN Users ON Users.user_id = UserSkills.user_id
            WHERE UserSkills.category_id = ? AND UserSkills.skill_type = 'learn'
            """,
            (category_id,),
        ).fetchall()
        conn.close()
        return jsonify({"user_ids": [row["user_id"] for row in rows]}), 200
    except Exception as e:
        return error_response(str(e))


# ── UserSkills ──

@app.route("/user-skills", methods=["POST"])
def insert_user_skill():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    category_id = data.get("category_id")
    description = data.get("description")
    skill_type = data.get("skill_type")

    if user_id is None or category_id is None or not description or skill_type not in ("teach", "learn"):
        return error_response(
            "'user_id', 'category_id', 'description', and 'skill_type' (teach/learn) are required", 400
        )

    try:
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO UserSkills (user_id, category_id, description, skill_type) VALUES (?, ?, ?, ?)",
            (user_id, category_id, description, skill_type),
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({
            "user_skill_id": new_id, "user_id": user_id, "category_id": category_id,
            "description": description, "skill_type": skill_type,
        }), 201
    except Exception as e:
        return error_response(str(e))


@app.route("/user-skills/<int:user_skill_id>", methods=["GET"])
def get_user_skill(user_skill_id):
    """
    Used when creating a session, to resolve which teacher and which
    exact listing a session request is about.
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM UserSkills WHERE user_skill_id = ?", (user_skill_id,)
        ).fetchone()
        conn.close()
        return jsonify({"user_skill": row_or_none(row)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/skills", methods=["GET"])
def get_user_skills(user_id):
    type_filter = request.args.get("type")
    try:
        conn = get_db()
        query = """
            SELECT UserSkills.*, SkillCategories.category_name
            FROM UserSkills
            JOIN SkillCategories ON SkillCategories.category_id = UserSkills.category_id
            WHERE UserSkills.user_id = ?
        """
        params = [user_id]
        if type_filter:
            query += " AND UserSkills.skill_type = ?"
            params.append(type_filter)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({"skills": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/skills/<int:user_skill_id>", methods=["DELETE"])
def delete_user_skill(user_id, user_skill_id):
    try:
        conn = get_db()
        cur = conn.execute(
            "DELETE FROM UserSkills WHERE user_id = ? AND user_skill_id = ?",
            (user_id, user_skill_id),
        )
        conn.commit()
        deleted_count = cur.rowcount
        conn.close()
        return jsonify({"removed_count": deleted_count}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/search/user-skills", methods=["GET"])
def search_user_skills():
    """
    The main Search page. Every filter is optional and combines with AND.
    Query string: ?type=teach|learn&category_id=&degree_id=&class_year=
    """
    type_filter = request.args.get("type")
    category_id = request.args.get("category_id")
    degree_id = request.args.get("degree_id")
    class_year = request.args.get("class_year")

    try:
        conn = get_db()
        query = """
            SELECT UserSkills.*, SkillCategories.category_name,
                   Users.name, Users.avatar_url, Users.degree_id, Users.class_year,
                   Users.credits_average, Users.credits_count
            FROM UserSkills
            JOIN Users ON Users.user_id = UserSkills.user_id
            JOIN SkillCategories ON SkillCategories.category_id = UserSkills.category_id
            WHERE 1 = 1
        """
        params = []
        if type_filter:
            query += " AND UserSkills.skill_type = ?"
            params.append(type_filter)
        if category_id:
            query += " AND UserSkills.category_id = ?"
            params.append(category_id)
        if degree_id:
            query += " AND Users.degree_id = ?"
            params.append(degree_id)
        if class_year:
            query += " AND Users.class_year = ?"
            params.append(class_year)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({"results": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


# ── Sessions ──

@app.route("/sessions", methods=["POST"])
def insert_session():
    data = request.get_json(silent=True) or {}
    teacher_id = data.get("teacher_id")
    learner_id = data.get("learner_id")
    user_skill_id = data.get("user_skill_id")
    scheduled_time = data.get("scheduled_time")

    if not all([teacher_id, learner_id, user_skill_id, scheduled_time]):
        return error_response(
            "'teacher_id', 'learner_id', 'user_skill_id', and 'scheduled_time' are required", 400
        )

    try:
        conn = get_db()
        cur = conn.execute(
            """
            INSERT INTO Sessions (teacher_id, learner_id, user_skill_id, scheduled_time, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (teacher_id, learner_id, user_skill_id, scheduled_time),
        )
        conn.commit()
        session_id = cur.lastrowid
        conn.close()
        return jsonify({"session_id": session_id}), 201
    except Exception as e:
        return error_response(str(e))


@app.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    try:
        conn = get_db()
        row = conn.execute("SELECT * FROM Sessions WHERE session_id = ?", (session_id,)).fetchone()
        conn.close()
        return jsonify({"session": row_or_none(row)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/sessions/<int:session_id>", methods=["PATCH"])
def update_session(session_id):
    """
    Generic status update, used for approve, decline, and cancel.
    Body: { status, cancelled_by } - cancelled_by is only relevant when
    status is 'cancelled'.
    """
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    cancelled_by = data.get("cancelled_by")

    if status not in ("pending", "approved", "declined", "cancelled", "completed"):
        return error_response("Invalid 'status' value", 400)

    try:
        conn = get_db()
        conn.execute(
            "UPDATE Sessions SET status = ?, cancelled_by = ? WHERE session_id = ?",
            (status, cancelled_by, session_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM Sessions WHERE session_id = ?", (session_id,)).fetchone()
        conn.close()
        return jsonify({"session": row_or_none(updated)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/sessions/<int:session_id>/complete", methods=["PATCH"])
def mark_session_completed(session_id):
    """
    Body: { role: "teacher" | "learner" }
    Sets that person's completion flag. If both flags end up true, the
    session's status also flips to 'completed' in the same update.
    """
    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in ("teacher", "learner"):
        return error_response("'role' must be 'teacher' or 'learner'", 400)

    column = "completed_by_teacher" if role == "teacher" else "completed_by_learner"

    try:
        conn = get_db()
        conn.execute(f"UPDATE Sessions SET {column} = 1 WHERE session_id = ?", (session_id,))
        row = conn.execute("SELECT * FROM Sessions WHERE session_id = ?", (session_id,)).fetchone()

        if row["completed_by_teacher"] and row["completed_by_learner"] and row["status"] != "completed":
            conn.execute("UPDATE Sessions SET status = 'completed' WHERE session_id = ?", (session_id,))

        conn.commit()
        updated = conn.execute("SELECT * FROM Sessions WHERE session_id = ?", (session_id,)).fetchone()
        conn.close()
        return jsonify({"session": row_or_none(updated)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/sessions", methods=["GET"])
def get_user_sessions(user_id):
    """Query string: ?status=&role=teacher|learner"""
    status_filter = request.args.get("status")
    role_filter = request.args.get("role")

    try:
        conn = get_db()
        query = "SELECT * FROM Sessions WHERE (teacher_id = ? OR learner_id = ?)"
        params = [user_id, user_id]

        if role_filter == "teacher":
            query = "SELECT * FROM Sessions WHERE teacher_id = ?"
            params = [user_id]
        elif role_filter == "learner":
            query = "SELECT * FROM Sessions WHERE learner_id = ?"
            params = [user_id]

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY scheduled_time DESC"

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({"sessions": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


# ── Reviews ──

@app.route("/reviews", methods=["POST"])
def insert_review():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    reviewer_id = data.get("reviewer_id")
    reviewee_id = data.get("reviewee_id")
    rating = data.get("rating")
    weight = data.get("weight", 1.0)

    if not all([session_id, reviewer_id, reviewee_id, rating]):
        return error_response(
            "'session_id', 'reviewer_id', 'reviewee_id', and 'rating' are required", 400
        )

    try:
        conn = get_db()
        cur = conn.execute(
            """
            INSERT INTO Reviews (session_id, reviewer_id, reviewee_id, rating, comment, weight)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, reviewer_id, reviewee_id, rating, data.get("comment"), weight),
        )
        conn.commit()
        review_id = cur.lastrowid
        conn.close()
        return jsonify({"review_id": review_id}), 201
    except sqlite3.IntegrityError as e:
        return error_response(str(e), 409)
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/reviews", methods=["GET"])
def get_user_reviews(user_id):
    """Reviews received by this user, newest first, for the profile page."""
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT Reviews.*, Users.name AS reviewer_name, Users.avatar_url AS reviewer_avatar_url
            FROM Reviews
            JOIN Users ON Users.user_id = Reviews.reviewer_id
            WHERE Reviews.reviewee_id = ?
            ORDER BY Reviews.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        conn.close()
        return jsonify({"reviews": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/reviews/count-between", methods=["GET"])
def count_reviews_between():
    """
    How many times reviewer_id has already reviewed reviewee_id before.
    The api layer uses this to shrink the weight of repeat reviews between
    the same two people, so friends cannot farm each other's rating.
    Query string: ?reviewer_id=&reviewee_id=
    """
    reviewer_id = request.args.get("reviewer_id")
    reviewee_id = request.args.get("reviewee_id")
    if not reviewer_id or not reviewee_id:
        return error_response("'reviewer_id' and 'reviewee_id' are required", 400)

    try:
        conn = get_db()
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM Reviews WHERE reviewer_id = ? AND reviewee_id = ?",
            (reviewer_id, reviewee_id),
        ).fetchone()["c"]
        conn.close()
        return jsonify({"count": count}), 200
    except Exception as e:
        return error_response(str(e))


# ── GroupSessions ──

@app.route("/group-sessions", methods=["POST"])
def insert_group_session():
    data = request.get_json(silent=True) or {}
    teacher_id = data.get("teacher_id")
    category_id = data.get("category_id")
    topic = data.get("topic")
    scheduled_time = data.get("scheduled_time")
    max_participants = data.get("max_participants", 5)

    if not all([teacher_id, category_id, topic, scheduled_time]):
        return error_response(
            "'teacher_id', 'category_id', 'topic', and 'scheduled_time' are required", 400
        )

    try:
        conn = get_db()
        cur = conn.execute(
            """
            INSERT INTO GroupSessions (teacher_id, category_id, topic, scheduled_time, max_participants, status)
            VALUES (?, ?, ?, ?, ?, 'scheduled')
            """,
            (teacher_id, category_id, topic, scheduled_time, max_participants),
        )
        conn.commit()
        group_session_id = cur.lastrowid
        conn.close()
        return jsonify({"group_session_id": group_session_id}), 201
    except Exception as e:
        return error_response(str(e))


@app.route("/group-sessions", methods=["GET"])
def list_group_sessions():
    status_filter = request.args.get("status", "scheduled")
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT GroupSessions.*, SkillCategories.category_name, Users.name AS teacher_name,
                   (SELECT COUNT(*) FROM GroupSessionMembers WHERE GroupSessionMembers.group_session_id = GroupSessions.group_session_id) AS current_members
            FROM GroupSessions
            JOIN SkillCategories ON SkillCategories.category_id = GroupSessions.category_id
            JOIN Users ON Users.user_id = GroupSessions.teacher_id
            WHERE GroupSessions.status = ?
            ORDER BY GroupSessions.scheduled_time ASC
            """,
            (status_filter,),
        ).fetchall()
        conn.close()
        return jsonify({"group_sessions": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/group-sessions/<int:group_session_id>", methods=["GET"])
def get_group_session(group_session_id):
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM GroupSessions WHERE group_session_id = ?", (group_session_id,)
        ).fetchone()
        conn.close()
        return jsonify({"group_session": row_or_none(row)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/group-sessions/<int:group_session_id>/status", methods=["PATCH"])
def update_group_session_status(group_session_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("scheduled", "completed", "cancelled"):
        return error_response("Invalid 'status' value", 400)

    try:
        conn = get_db()
        conn.execute(
            "UPDATE GroupSessions SET status = ? WHERE group_session_id = ?",
            (status, group_session_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"group_session_id": group_session_id, "status": status}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/group-sessions/<int:group_session_id>/members", methods=["POST"])
def insert_group_member(group_session_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return error_response("'user_id' is required", 400)

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO GroupSessionMembers (group_session_id, user_id) VALUES (?, ?)",
            (group_session_id, user_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"group_session_id": group_session_id, "user_id": user_id}), 201
    except sqlite3.IntegrityError as e:
        return error_response(str(e), 409)
    except Exception as e:
        return error_response(str(e))


@app.route("/group-sessions/<int:group_session_id>/members", methods=["GET"])
def list_group_members(group_session_id):
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT Users.user_id, Users.name, Users.avatar_url
            FROM GroupSessionMembers
            JOIN Users ON Users.user_id = GroupSessionMembers.user_id
            WHERE GroupSessionMembers.group_session_id = ?
            """,
            (group_session_id,),
        ).fetchall()
        conn.close()
        return jsonify({"members": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/group-sessions/<int:group_session_id>/members", methods=["DELETE"])
def clear_group_members(group_session_id):
    """Called once a group session is marked completed, to empty it out."""
    try:
        conn = get_db()
        conn.execute("DELETE FROM GroupSessionMembers WHERE group_session_id = ?", (group_session_id,))
        conn.commit()
        conn.close()
        return jsonify({"group_session_id": group_session_id, "cleared": True}), 200
    except Exception as e:
        return error_response(str(e))


# ── Conversations and Messages ──

@app.route("/conversations", methods=["POST"])
def insert_conversation():
    """
    Body: { is_group, participant_ids: [1, 2, 3], group_session_id }
    group_session_id is only set for conversations created automatically
    for a community group session.
    """
    data = request.get_json(silent=True) or {}
    is_group = 1 if data.get("is_group") else 0
    participant_ids = data.get("participant_ids", [])
    group_session_id = data.get("group_session_id")

    if not participant_ids:
        return error_response("'participant_ids' must be a non empty list", 400)

    try:
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO Conversations (is_group, group_session_id) VALUES (?, ?)",
            (is_group, group_session_id),
        )
        conversation_id = cur.lastrowid
        for user_id in participant_ids:
            conn.execute(
                "INSERT INTO ConversationParticipants (conversation_id, user_id) VALUES (?, ?)",
                (conversation_id, user_id),
            )
        conn.commit()
        conn.close()
        return jsonify({"conversation_id": conversation_id}), 201
    except Exception as e:
        return error_response(str(e))


@app.route("/conversations/<int:conversation_id>/participants", methods=["POST"])
def add_conversation_participant(conversation_id):
    """Used to add a new member to a group chat, for example on group session join."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return error_response("'user_id' is required", 400)

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO ConversationParticipants (conversation_id, user_id) VALUES (?, ?)",
            (conversation_id, user_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"conversation_id": conversation_id, "user_id": user_id}), 201
    except sqlite3.IntegrityError as e:
        return error_response(str(e), 409)
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/conversations", methods=["GET"])
def list_user_conversations(user_id):
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT Conversations.*
            FROM Conversations
            JOIN ConversationParticipants ON ConversationParticipants.conversation_id = Conversations.conversation_id
            WHERE ConversationParticipants.user_id = ?
            ORDER BY Conversations.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        conn.close()
        return jsonify({"conversations": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/conversations/<int:conversation_id>/participants", methods=["GET"])
def get_conversation_participants(conversation_id):
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT Users.user_id, Users.name, Users.avatar_url
            FROM ConversationParticipants
            JOIN Users ON Users.user_id = ConversationParticipants.user_id
            WHERE ConversationParticipants.conversation_id = ?
            """,
            (conversation_id,),
        ).fetchall()
        conn.close()
        return jsonify({"participants": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """
    Used when a group session completes, to delete its chat along with
    everyone in it and everything that was said in it.
    """
    try:
        conn = get_db()
        conn.execute("DELETE FROM Messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM ConversationParticipants WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM Conversations WHERE conversation_id = ?", (conversation_id,))
        conn.commit()
        conn.close()
        return jsonify({"conversation_id": conversation_id, "deleted": True}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/conversations/<int:conversation_id>/messages", methods=["POST"])
def insert_message(conversation_id):
    data = request.get_json(silent=True) or {}
    sender_id = data.get("sender_id")
    message_text = data.get("message_text")

    if not sender_id or not message_text:
        return error_response("'sender_id' and 'message_text' are required", 400)

    try:
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO Messages (conversation_id, sender_id, message_text) VALUES (?, ?, ?)",
            (conversation_id, sender_id, message_text),
        )
        conn.commit()
        message_id = cur.lastrowid
        row = conn.execute("SELECT * FROM Messages WHERE message_id = ?", (message_id,)).fetchone()
        conn.close()
        return jsonify({"message": row_or_none(row)}), 201
    except Exception as e:
        return error_response(str(e))


@app.route("/conversations/<int:conversation_id>/messages", methods=["GET"])
def list_messages(conversation_id):
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM Messages WHERE conversation_id = ? ORDER BY sent_at ASC",
            (conversation_id,),
        ).fetchall()
        conn.close()
        return jsonify({"messages": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


# ── Notifications ──

@app.route("/notifications", methods=["POST"])
def insert_notification():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    notification_type = data.get("notification_type")
    message = data.get("message")

    if not user_id or not notification_type or not message:
        return error_response("'user_id', 'notification_type', and 'message' are required", 400)

    try:
        conn = get_db()
        cur = conn.execute(
            """
            INSERT INTO Notifications
                (user_id, notification_type, message, related_session_id, related_group_session_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id, notification_type, message,
                data.get("related_session_id"), data.get("related_group_session_id"),
            ),
        )
        conn.commit()
        notification_id = cur.lastrowid
        conn.close()
        return jsonify({"notification_id": notification_id}), 201
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/notifications", methods=["GET"])
def list_notifications(user_id):
    unread_only = request.args.get("unread_only") == "true"
    try:
        conn = get_db()
        query = "SELECT * FROM Notifications WHERE user_id = ?"
        params = [user_id]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({"notifications": rows_to_list(rows)}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/notifications/<int:notification_id>/read", methods=["PATCH"])
def mark_notification_read(notification_id):
    try:
        conn = get_db()
        conn.execute("UPDATE Notifications SET is_read = 1 WHERE notification_id = ?", (notification_id,))
        conn.commit()
        conn.close()
        return jsonify({"notification_id": notification_id, "is_read": True}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/users/<int:user_id>/notifications/read-all", methods=["PATCH"])
def mark_all_notifications_read(user_id):
    try:
        conn = get_db()
        cur = conn.execute("UPDATE Notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
        conn.commit()
        updated_count = cur.rowcount
        conn.close()
        return jsonify({"user_id": user_id, "updated_count": updated_count}), 200
    except Exception as e:
        return error_response(str(e))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=PORT, use_reloader=False)
