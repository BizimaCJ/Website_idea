"""
Seeds the Ubuntu Skills database with sample data for local development
and demos.

Run it from anywhere with:
    python3 backend/database/seed_sample_data.py

It is safe to re-run: it clears the tables it seeds first, so you always
end up with the same clean sample set instead of duplicates on top of
duplicates.

Every sample account uses the password: pw123
"""

import os
import sqlite3
import bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "ubuntuskills.db")

SAMPLE_PASSWORD = "pw123"

DEGREES = [
    "Computer Science",
    "Economics",
    "Business Administration",
    "Biology",
    "Physics",
    "Art History",
    "Music",
    "Civil Engineering",
]

CATEGORIES = [
    "Front End Development",
    "Back End Development",
    "UI and UX",
    "Data Analysis",
    "Public Speaking",
    "Languages",
    "Music",
    "Visual Arts",
    "Mathematics",
    "Chemistry",
]

# name, email, degree name, class year, bio, teach:[(category, description)], learn:[(category, description)]
USERS = [
    {
        "name": "Sofia Marchetti",
        "email": "sofia.marchetti@sample.edu",
        "degree": "Art History",
        "class_year": 2027,
        "bio": "Painter and part-time Italian tutor. Happy to swap watercolor tips for coding help.",
        "teach": [("Visual Arts", "Watercolor painting"), ("Languages", "Italian conversation")],
        "learn": [("Front End Development", "Photography portfolio site")],
    },
    {
        "name": "Noah Fischer",
        "email": "noah.fischer@sample.edu",
        "degree": "Computer Science",
        "class_year": 2028,
        "bio": "First year CS student building small web apps. Looking to pick up guitar in my spare time.",
        "teach": [("Front End Development", "HTML, CSS, and vanilla JavaScript")],
        "learn": [("Music", "Guitar basics"), ("Languages", "French for beginners")],
    },
    {
        "name": "Lin Wei",
        "email": "lin.wei@sample.edu",
        "degree": "Physics",
        "class_year": 2026,
        "bio": "Physics major, piano player, and calculus tutor for anyone prepping for midterms.",
        "teach": [("Mathematics", "Calculus I"), ("Music", "Piano fundamentals")],
        "learn": [("Languages", "Mandarin tutoring exchange")],
    },
    {
        "name": "Kwame Boateng",
        "email": "kwame.boateng@sample.edu",
        "degree": "Economics",
        "class_year": 2026,
        "bio": "Econ senior, comfortable with spreadsheets and public speaking prep for case competitions.",
        "teach": [("Data Analysis", "Excel modeling"), ("Public Speaking", "Pitch and presentation coaching")],
        "learn": [("Mathematics", "Chess strategy")],
    },
    {
        "name": "Aicha Ndiaye",
        "email": "aicha.ndiaye@sample.edu",
        "degree": "Biology",
        "class_year": 2027,
        "bio": "Bio major who tutors organic chemistry and is trying to finally learn to dance.",
        "teach": [("Chemistry", "Organic chemistry")],
        "learn": [("Music", "Salsa dancing")],
    },
    {
        "name": "Marco Silva",
        "email": "marco.silva@sample.edu",
        "degree": "Music",
        "class_year": 2028,
        "bio": "Music student teaching guitar basics and music theory, working on my calculus in return.",
        "teach": [("Music", "Guitar basics"), ("Music", "Music theory")],
        "learn": [("Mathematics", "Calculus I")],
    },
    {
        "name": "Isabelle Moreau",
        "email": "isabelle.moreau@sample.edu",
        "degree": "Business Administration",
        "class_year": 2027,
        "bio": "Business student interested in data storytelling and pitching startup ideas.",
        "teach": [("Public Speaking", "Storytelling and pitch framing")],
        "learn": [("Data Analysis", "SQL for beginners")],
    },
    {
        "name": "Daniel Kowalski",
        "email": "daniel.kowalski@sample.edu",
        "degree": "Civil Engineering",
        "class_year": 2026,
        "bio": "Engineering student who codes on the side. Can help with backend basics and Python.",
        "teach": [("Back End Development", "Python and Flask basics")],
        "learn": [("UI and UX", "Design fundamentals")],
    },
]


def hash_password(password: str) -> str:
    # flask_bcrypt / bcrypt both produce and read standard $2b$ hashes,
    # so a hash generated here works fine with the auth service's checks.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def main():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Wipe just the sample-relevant tables so this script is re-runnable
    # without piling up duplicate rows. Real accounts you created by hand
    # (like the original test@anu.ac.rw user) are left alone as long as
    # their email isn't in the sample list below. Dependent rows have to
    # go first or the foreign keys on Users block the delete.
    sample_emails = tuple(u["email"] for u in USERS)
    placeholders = ",".join("?" * len(sample_emails))
    sample_ids = [
        row["user_id"]
        for row in cur.execute(f"SELECT user_id FROM Users WHERE email IN ({placeholders})", sample_emails)
    ]
    if sample_ids:
        id_placeholders = ",".join("?" * len(sample_ids))
        cur.execute(f"DELETE FROM Reviews WHERE reviewer_id IN ({id_placeholders}) OR reviewee_id IN ({id_placeholders})", sample_ids * 2)
        cur.execute(f"DELETE FROM Messages WHERE sender_id IN ({id_placeholders})", sample_ids)
        cur.execute(f"DELETE FROM ConversationParticipants WHERE user_id IN ({id_placeholders})", sample_ids)
        cur.execute(f"DELETE FROM GroupSessionMembers WHERE user_id IN ({id_placeholders})", sample_ids)
        cur.execute(f"DELETE FROM Notifications WHERE user_id IN ({id_placeholders})", sample_ids)
        cur.execute(f"DELETE FROM Sessions WHERE teacher_id IN ({id_placeholders}) OR learner_id IN ({id_placeholders})", sample_ids * 2)
        cur.execute(f"DELETE FROM GroupSessions WHERE teacher_id IN ({id_placeholders})", sample_ids)
        cur.execute(f"DELETE FROM UserSkills WHERE user_id IN ({id_placeholders})", sample_ids)
        cur.execute(f"DELETE FROM Users WHERE user_id IN ({id_placeholders})", sample_ids)

    # Degrees and categories are admin curated lookup tables, insert
    # whichever ones don't already exist rather than wiping them.
    degree_ids = {}
    for name in DEGREES:
        cur.execute("INSERT OR IGNORE INTO Degrees (degree_name) VALUES (?)", (name,))
        row = cur.execute("SELECT degree_id FROM Degrees WHERE degree_name = ?", (name,)).fetchone()
        degree_ids[name] = row["degree_id"]

    category_ids = {}
    for name in CATEGORIES:
        cur.execute("INSERT OR IGNORE INTO SkillCategories (category_name) VALUES (?)", (name,))
        row = cur.execute("SELECT category_id FROM SkillCategories WHERE category_name = ?", (name,)).fetchone()
        category_ids[name] = row["category_id"]

    password_hash = hash_password(SAMPLE_PASSWORD)

    created = []
    for u in USERS:
        cur.execute(
            """
            INSERT INTO Users (
                name, email, password_hash, bio, degree_id, class_year,
                verification_method, verification_status,
                credits_average, credits_count
            ) VALUES (?, ?, ?, ?, ?, ?, 'school_email', 'verified', ?, ?)
            """,
            (
                u["name"],
                u["email"],
                password_hash,
                u["bio"],
                degree_ids[u["degree"]],
                u["class_year"],
                round(4.2 + 0.1 * (len(u["name"]) % 8), 1),  # varied but deterministic sample rating
                6 + (len(u["name"]) % 20),
            ),
        )
        user_id = cur.lastrowid
        created.append((user_id, u["name"], u["email"]))

        for category_name, description in u["teach"]:
            cur.execute(
                "INSERT INTO UserSkills (user_id, category_id, description, skill_type) VALUES (?, ?, ?, 'teach')",
                (user_id, category_ids[category_name], description),
            )
        for category_name, description in u["learn"]:
            cur.execute(
                "INSERT INTO UserSkills (user_id, category_id, description, skill_type) VALUES (?, ?, ?, 'learn')",
                (user_id, category_ids[category_name], description),
            )

    con.commit()
    con.close()

    print(f"Seeded {len(DEGREES)} degrees, {len(CATEGORIES)} skill categories, and {len(created)} users.")
    print(f"Every sample account's password is: {SAMPLE_PASSWORD}")
    print("\nSample accounts:")
    for user_id, name, email in created:
        print(f"  #{user_id:<3} {name:<20} {email}")


if __name__ == "__main__":
    main()
