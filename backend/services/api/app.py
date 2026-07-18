"""
The api service's entry point. This file only wires blueprints together,
it does not contain any routes itself. Every feature area lives in its
own routes_*.py file, for example everything about sessions is in
routes_sessions.py, everything about group sessions is in
routes_community.py, and so on.
"""

from flask import Flask
from flask_cors import CORS

from routes_users import users_bp
from routes_skills import skills_bp
from routes_sessions import sessions_bp
from routes_community import community_bp
from routes_messages import messages_bp
from routes_notifications import notifications_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(users_bp)
app.register_blueprint(skills_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(community_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(notifications_bp)


@app.route("/api/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "api"}, 200


if __name__ == "__main__":
    app.run(debug=True, port=5001, use_reloader=False)
