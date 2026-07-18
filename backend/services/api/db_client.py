"""
Thin HTTP client for database_service.
Route files under api/ should never import sqlite3 - every read/write
goes through here.
"""

import requests
from config import DB_SERVICE_URL


class DBServiceError(Exception):
    """Raised when database_service is unreachable or returns an error."""
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _request(method, path, **kwargs):
    try:
        resp = requests.request(method, f"{DB_SERVICE_URL}{path}", timeout=5, **kwargs)
    except requests.exceptions.RequestException:
        raise DBServiceError("Could not reach database service", 503)

    try:
        body = resp.json()
    except ValueError:
        body = {}

    if resp.status_code >= 400:
        raise DBServiceError(body.get("error", "Database service error"), resp.status_code)

    return body


# ── Users ──

def get_user(user_id):
    return _request("GET", f"/users/{user_id}")["user"]


def get_user_by_email(email):
    return _request("GET", f"/users/by-email/{email}")["user"]


def update_user(user_id, fields):
    return _request("PATCH", f"/users/{user_id}", json=fields)["user"]


def update_credits(user_id, credits_average, credits_count):
    return _request(
        "PATCH", f"/users/{user_id}/credits",
        json={"credits_average": credits_average, "credits_count": credits_count},
    )


def search_users(q=None):
    params = {"q": q} if q else {}
    return _request("GET", "/users", params=params)["users"]


# ── Degrees and SkillCategories ──

def list_degrees():
    return _request("GET", "/degrees")["degrees"]


def list_categories():
    return _request("GET", "/skill-categories")["categories"]


def category_learners(category_id):
    return _request("GET", f"/skill-categories/{category_id}/learners")["user_ids"]


# ── UserSkills ──

def insert_user_skill(user_id, category_id, description, skill_type):
    return _request(
        "POST", "/user-skills",
        json={"user_id": user_id, "category_id": category_id, "description": description, "skill_type": skill_type},
    )


def get_user_skill(user_skill_id):
    return _request("GET", f"/user-skills/{user_skill_id}")["user_skill"]


def get_user_skills(user_id, type_filter=None):
    params = {"type": type_filter} if type_filter else {}
    return _request("GET", f"/users/{user_id}/skills", params=params)["skills"]


def delete_user_skill(user_id, user_skill_id):
    return _request("DELETE", f"/users/{user_id}/skills/{user_skill_id}")["removed_count"]


def search_user_skills(type_filter=None, category_id=None, degree_id=None, class_year=None):
    params = {}
    if type_filter:
        params["type"] = type_filter
    if category_id:
        params["category_id"] = category_id
    if degree_id:
        params["degree_id"] = degree_id
    if class_year:
        params["class_year"] = class_year
    return _request("GET", "/search/user-skills", params=params)["results"]


# ── Sessions ──

def insert_session(teacher_id, learner_id, user_skill_id, scheduled_time):
    return _request(
        "POST", "/sessions",
        json={
            "teacher_id": teacher_id, "learner_id": learner_id,
            "user_skill_id": user_skill_id, "scheduled_time": scheduled_time,
        },
    )["session_id"]


def get_session(session_id):
    return _request("GET", f"/sessions/{session_id}")["session"]


def update_session_status(session_id, status, cancelled_by=None):
    return _request(
        "PATCH", f"/sessions/{session_id}",
        json={"status": status, "cancelled_by": cancelled_by},
    )["session"]


def mark_session_completed(session_id, role):
    return _request("PATCH", f"/sessions/{session_id}/complete", json={"role": role})["session"]


def get_user_sessions(user_id, status_filter=None, role_filter=None):
    params = {}
    if status_filter:
        params["status"] = status_filter
    if role_filter:
        params["role"] = role_filter
    return _request("GET", f"/users/{user_id}/sessions", params=params)["sessions"]


# ── Reviews ──

def insert_review(session_id, reviewer_id, reviewee_id, rating, comment, weight):
    return _request(
        "POST", "/reviews",
        json={
            "session_id": session_id, "reviewer_id": reviewer_id, "reviewee_id": reviewee_id,
            "rating": rating, "comment": comment, "weight": weight,
        },
    )["review_id"]


def get_user_reviews(user_id):
    return _request("GET", f"/users/{user_id}/reviews")["reviews"]


def count_reviews_between(reviewer_id, reviewee_id):
    return _request(
        "GET", "/reviews/count-between",
        params={"reviewer_id": reviewer_id, "reviewee_id": reviewee_id},
    )["count"]


# ── GroupSessions ──

def insert_group_session(teacher_id, category_id, topic, scheduled_time, max_participants=5):
    return _request(
        "POST", "/group-sessions",
        json={
            "teacher_id": teacher_id, "category_id": category_id, "topic": topic,
            "scheduled_time": scheduled_time, "max_participants": max_participants,
        },
    )["group_session_id"]


def list_group_sessions(status_filter="scheduled"):
    return _request("GET", "/group-sessions", params={"status": status_filter})["group_sessions"]


def get_group_session(group_session_id):
    return _request("GET", f"/group-sessions/{group_session_id}")["group_session"]


def update_group_session_status(group_session_id, status):
    return _request("PATCH", f"/group-sessions/{group_session_id}/status", json={"status": status})


def insert_group_member(group_session_id, user_id):
    return _request("POST", f"/group-sessions/{group_session_id}/members", json={"user_id": user_id})


def list_group_members(group_session_id):
    return _request("GET", f"/group-sessions/{group_session_id}/members")["members"]


def clear_group_members(group_session_id):
    return _request("DELETE", f"/group-sessions/{group_session_id}/members")


# ── Conversations and Messages ──

def insert_conversation(participant_ids, is_group=False, group_session_id=None):
    return _request(
        "POST", "/conversations",
        json={"participant_ids": participant_ids, "is_group": is_group, "group_session_id": group_session_id},
    )["conversation_id"]


def add_conversation_participant(conversation_id, user_id):
    return _request("POST", f"/conversations/{conversation_id}/participants", json={"user_id": user_id})


def list_user_conversations(user_id):
    return _request("GET", f"/users/{user_id}/conversations")["conversations"]


def get_conversation_participants(conversation_id):
    return _request("GET", f"/conversations/{conversation_id}/participants")["participants"]


def delete_conversation(conversation_id):
    return _request("DELETE", f"/conversations/{conversation_id}")


def insert_message(conversation_id, sender_id, message_text):
    return _request(
        "POST", f"/conversations/{conversation_id}/messages",
        json={"sender_id": sender_id, "message_text": message_text},
    )["message"]


def list_messages(conversation_id):
    return _request("GET", f"/conversations/{conversation_id}/messages")["messages"]


# ── Notifications ──

def insert_notification(user_id, notification_type, message, related_session_id=None, related_group_session_id=None):
    return _request(
        "POST", "/notifications",
        json={
            "user_id": user_id, "notification_type": notification_type, "message": message,
            "related_session_id": related_session_id, "related_group_session_id": related_group_session_id,
        },
    )["notification_id"]


def list_notifications(user_id, unread_only=False):
    params = {"unread_only": "true"} if unread_only else {}
    return _request("GET", f"/users/{user_id}/notifications", params=params)["notifications"]


def mark_notification_read(notification_id):
    return _request("PATCH", f"/notifications/{notification_id}/read")


def mark_all_notifications_read(user_id):
    return _request("PATCH", f"/users/{user_id}/notifications/read-all")
