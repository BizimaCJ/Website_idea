-- Ubuntu Skills database schema
-- This file is the single source of truth for the data model.
-- Only backend/services/database_service ever opens this database directly.

PRAGMA foreign_keys = ON;

-- Degrees is an admin curated list of programs offered at the pilot school.
-- Users pick one from a dropdown rather than typing it in, so filtering by
-- degree in search always matches cleanly.
CREATE TABLE Degrees (
    degree_id INTEGER PRIMARY KEY AUTOINCREMENT,
    degree_name TEXT NOT NULL UNIQUE
);

-- Users holds one row per student, including everything needed for the
-- school email or manual document verification flow.
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    degree_id INTEGER REFERENCES Degrees(degree_id),
    class_year INTEGER,

    -- verification_method records which path the user signed up through.
    -- school_email means their address matched the trusted student domain
    -- and they were verified automatically. document means they uploaded
    -- proof for a person to review manually.
    verification_method TEXT NOT NULL CHECK (verification_method IN ('school_email', 'document')),
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verification_document_path TEXT,

    -- These two are kept as cached values so the profile page and search
    -- results can show a rating instantly without recalculating an average
    -- across every review on every page load. They are recalculated and
    -- rewritten every time a new review is inserted.
    credits_average REAL NOT NULL DEFAULT 0,
    credits_count INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- SkillCategories is the admin curated master list, for example Front End
-- Development, UI and UX, or Public Speaking. Students cannot add new
-- categories themselves, they can only choose one and describe their own
-- angle on it in UserSkills.description.
CREATE TABLE SkillCategories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);

-- UserSkills links a student to a category twice over, once for what they
-- can teach and once for what they want to learn. description is the short
-- free text the student adds to say what exactly within that category they
-- mean, for example Category equals Public Speaking, description equals
-- Storytelling and pitch framing.
CREATE TABLE UserSkills (
    user_skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES Users(user_id),
    category_id INTEGER NOT NULL REFERENCES SkillCategories(category_id),
    description TEXT NOT NULL,
    skill_type TEXT NOT NULL CHECK (skill_type IN ('teach', 'learn')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sessions is a one to one match between a learner and a teacher for a
-- specific thing the teacher listed. Status moves from pending, to either
-- approved or declined by the teacher, and an approved session can later
-- become cancelled by either side or completed once both sides confirm it.
-- Declined and cancelled are kept as separate values on purpose, even
-- though the current frontend only shows one Declined tab, because the
-- app still needs to know whether the teacher said no up front or someone
-- backed out after already agreeing to it.
CREATE TABLE Sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES Users(user_id),
    learner_id INTEGER NOT NULL REFERENCES Users(user_id),
    user_skill_id INTEGER NOT NULL REFERENCES UserSkills(user_skill_id),
    scheduled_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'declined', 'cancelled', 'completed')),

    -- Records who cancelled an approved session, so a notification can be
    -- sent to the other person. Left null for every other status.
    cancelled_by INTEGER REFERENCES Users(user_id),

    -- A session only truly counts as completed once both people confirm
    -- it happened. The review prompt only appears once both flags are 1.
    completed_by_teacher INTEGER NOT NULL DEFAULT 0,
    completed_by_learner INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Reviews are written by the learner about the teacher after a session
-- reaches completed status. weight defaults to 1 but the api layer may
-- write a smaller value for repeat reviews between the same two people,
-- so two friends rating each other over and over cannot inflate a score
-- as fast as genuine reviews from different people can.
CREATE TABLE Reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL UNIQUE REFERENCES Sessions(session_id),
    reviewer_id INTEGER NOT NULL REFERENCES Users(user_id),
    reviewee_id INTEGER NOT NULL REFERENCES Users(user_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    weight REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- GroupSessions are the Community feature. max_participants includes the
-- teacher, so a cap of 5 means the teacher plus four learners at most.
-- Status moves to completed once the scheduled session has happened, at
-- which point the api layer removes its GroupSessionMembers rows and its
-- linked Conversation, while leaving this row in place for history.
CREATE TABLE GroupSessions (
    group_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES Users(user_id),
    category_id INTEGER NOT NULL REFERENCES SkillCategories(category_id),
    topic TEXT NOT NULL,
    scheduled_time TEXT NOT NULL,
    max_participants INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- GroupSessionMembers tracks who joined a given group session. The teacher
-- is inserted here automatically the moment the group session is created,
-- so the count of rows for a group session doubles as its current seat
-- count against max_participants.
CREATE TABLE GroupSessionMembers (
    group_session_id INTEGER NOT NULL REFERENCES GroupSessions(group_session_id),
    user_id INTEGER NOT NULL REFERENCES Users(user_id),
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (group_session_id, user_id)
);

-- Conversations backs both one to one messaging and group chat with the
-- same table, rather than keeping two separate messaging systems. A
-- conversation created for a group session links back to it through
-- group_session_id, so deleting that link is how the group chat gets
-- cleaned up once the session is marked completed.
CREATE TABLE Conversations (
    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_group INTEGER NOT NULL DEFAULT 0,
    group_session_id INTEGER REFERENCES GroupSessions(group_session_id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE ConversationParticipants (
    conversation_id INTEGER NOT NULL REFERENCES Conversations(conversation_id),
    user_id INTEGER NOT NULL REFERENCES Users(user_id),
    PRIMARY KEY (conversation_id, user_id)
);

CREATE TABLE Messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES Conversations(conversation_id),
    sender_id INTEGER NOT NULL REFERENCES Users(user_id),
    message_text TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Notifications covers every event that should alert a user, including
-- session requests, reminders, someone cancelling a session on them, and
-- new group session announcements for a skill they want to learn.
-- related_session_id and related_group_session_id are both nullable and
-- only one of them is filled in depending on notification_type, so the
-- frontend knows which page to link the notification to.
CREATE TABLE Notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES Users(user_id),
    notification_type TEXT NOT NULL CHECK (notification_type IN (
        'session_requested',
        'session_approved',
        'session_declined',
        'session_cancelled',
        'session_reminder',
        'review_prompt',
        'group_session_announced',
        'new_message'
    )),
    message TEXT NOT NULL,
    related_session_id INTEGER REFERENCES Sessions(session_id),
    related_group_session_id INTEGER REFERENCES GroupSessions(group_session_id),
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
