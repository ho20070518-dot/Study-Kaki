from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

study_session_routes = Blueprint("study_session_routes", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    print("Using database:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# Login checking helper
# =========================
def get_current_user_id():
    # In this project, session["user_id"] stores student_id
    return session.get("user_id")


def get_current_username():
    # Member 1 uses student_id as session["user_id"]
    student_id = session.get("user_id")

    if not student_id:
        return "Unknown User"

    conn = get_db_connection()

    user = conn.execute("""
        SELECT username
        FROM users
        WHERE student_id = ?
    """, (student_id,)).fetchone()

    conn.close()

    if user:
        return user["username"]

    return session.get("username", "Unknown User")


def require_login():
    if "user_id" not in session:
        flash("Please login first.")
        return False
    return True


# =========================
# Notifications database table
# =========================
def create_notifications_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            is_cleared INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            link TEXT
        )
    """)

    try:
        conn.execute("ALTER TABLE notifications ADD COLUMN is_read INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE notifications ADD COLUMN is_cleared INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE notifications ADD COLUMN link TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def add_notification(user_id, message, link="/sessions"):
    create_notifications_table()

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO notifications 
        (user_id, message, is_read, is_cleared, created_at, link)
        VALUES (?, ?, 0, 0, ?, ?)
    """, (
        str(user_id),
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        link
    ))

    conn.commit()
    conn.close()


def get_unread_notification_count(user_id):
    create_notifications_table()

    conn = get_db_connection()

    unread_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
        AND is_cleared = 0
    """, (str(user_id),)).fetchone()["total"]

    conn.close()
    return unread_count


# =========================
# Sessions page
# =========================
@study_session_routes.route("/sessions")
def sessions():
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = get_current_user_id()
    current_username = get_current_username()
    search_query = request.args.get("search", "").strip()
    unread_count = get_unread_notification_count(current_user_id)

    conn = get_db_connection()

    if search_query:
        sessions = conn.execute("""
            SELECT 
                sessions.*,
                users.username AS creator_name
            FROM sessions
            LEFT JOIN users 
            ON CAST(sessions.created_by AS TEXT) = CAST(users.student_id AS TEXT)
            WHERE sessions.subject LIKE ?
            OR sessions.topic LIKE ?
            OR sessions.session_date LIKE ?
            OR sessions.session_time LIKE ?
            OR sessions.end_time LIKE ?
            OR sessions.location_type LIKE ?
            OR sessions.physical_location LIKE ?
            OR sessions.meeting_link LIKE ?
            OR users.username LIKE ?
            OR users.student_id LIKE ?
            ORDER BY sessions.session_date, sessions.session_time
        """, (
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%"
        )).fetchall()
    else:
        sessions = conn.execute("""
            SELECT 
                sessions.*,
                users.username AS creator_name
            FROM sessions
            LEFT JOIN users 
            ON CAST(sessions.created_by AS TEXT) = CAST(users.student_id AS TEXT)
            ORDER BY sessions.session_date, sessions.session_time
        """).fetchall()

    conn.close()

    return render_template(
        "sessions.html",
        sessions=sessions,
        current_user_id=str(current_user_id),
        current_user=current_username,
        search_query=search_query,
        unread_count=unread_count
    )


# =========================
# Create session
# =========================
@study_session_routes.route("/create_session", methods=["GET", "POST"])
def create_session():
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = get_current_user_id()
    unread_count = get_unread_notification_count(current_user_id)

    if request.method == "POST":
        subject = request.form["subject"]
        topic = request.form["topic"]
        session_date = request.form["session_date"]
        session_time = request.form["session_time"]
        end_time = request.form["end_time"]
        location_type = request.form["location_type"]
        physical_location = request.form.get("physical_location")
        meeting_link = request.form.get("meeting_link")

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO sessions
            (subject, topic, session_date, session_time, end_time, location_type, physical_location, meeting_link, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subject,
            topic,
            session_date,
            session_time,
            end_time,
            location_type,
            physical_location,
            meeting_link,
            str(current_user_id)
        ))

        conn.commit()
        conn.close()

        flash("Study session created successfully.")
        return redirect(url_for("study_session_routes.sessions"))

    return render_template(
        "create_session.html",
        unread_count=unread_count
    )


# =========================
# Edit session
# =========================
@study_session_routes.route("/edit_session/<int:session_id>", methods=["GET", "POST"])
def edit_session(session_id):
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())
    unread_count = get_unread_notification_count(current_user_id)

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if str(study_session["created_by"]) != current_user_id:
        conn.close()
        flash("You are not allowed to edit this session.")
        return redirect(url_for("study_session_routes.sessions"))

    if request.method == "POST":
        subject = request.form["subject"]
        topic = request.form["topic"]
        session_date = request.form["session_date"]
        session_time = request.form["session_time"]
        end_time = request.form["end_time"]
        location_type = request.form["location_type"]
        physical_location = request.form.get("physical_location")
        meeting_link = request.form.get("meeting_link")

        conn.execute("""
            UPDATE sessions
            SET subject = ?,
                topic = ?,
                session_date = ?,
                session_time = ?,
                end_time = ?,
                location_type = ?,
                physical_location = ?,
                meeting_link = ?
            WHERE id = ?
        """, (
            subject,
            topic,
            session_date,
            session_time,
            end_time,
            location_type,
            physical_location,
            meeting_link,
            session_id
        ))

        conn.commit()
        conn.close()

        flash("Study session updated successfully.")
        return redirect(url_for("study_session_routes.sessions"))

    conn.close()

    return render_template(
        "edit_session.html",
        session=study_session,
        unread_count=unread_count
    )


# =========================
# Delete session
# =========================
@study_session_routes.route("/delete_session/<int:session_id>")
def delete_session(session_id):
    if not require_login():
        return redirect("/login")

    current_user_id = str(get_current_user_id())

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if str(study_session["created_by"]) != current_user_id:
        conn.close()
        flash("You are not allowed to delete this session.")
        return redirect(url_for("study_session_routes.sessions"))

    conn.execute(
        "DELETE FROM sessions WHERE id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()

    flash("Study session deleted successfully.")
    return redirect(url_for("study_session_routes.sessions"))


# =========================
# Join session
# =========================
@study_session_routes.route("/join_session/<int:session_id>")
def join_session(session_id):
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if str(study_session["created_by"]) == current_user_id:
        conn.close()
        flash("You cannot join your own study session.")
        return redirect(url_for("study_session_routes.sessions"))

    conn.execute(
        "UPDATE sessions SET joined = 1 WHERE id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()

    if study_session["location_type"] == "Physical":
        location_text = study_session["physical_location"]
    else:
        location_text = study_session["meeting_link"]

    reminder_message = (
        f"You joined {study_session['subject']} study session. "
        f"Topic: {study_session['topic']}. "
        f"Date: {study_session['session_date']}. "
        f"Time: {study_session['session_time']} - {study_session['end_time']}. "
        f"Location: {location_text}."
    )

    add_notification(
        current_user_id,
        reminder_message,
        "/sessions"
    )

    flash("You have joined this study session. A reminder notification has been added.")
    return redirect(url_for("study_session_routes.sessions"))


# =========================
# Leave session
# =========================
@study_session_routes.route("/leave_session/<int:session_id>")
def leave_session(session_id):
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if str(study_session["created_by"]) == current_user_id:
        conn.close()
        flash("You cannot leave your own study session.")
        return redirect(url_for("study_session_routes.sessions"))

    conn.execute(
        "UPDATE sessions SET joined = 0 WHERE id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()

    add_notification(
        current_user_id,
        f"You left {study_session['subject']} study session.",
        "/sessions"
    )

    flash("You have left this study session.")
    return redirect(url_for("study_session_routes.sessions"))


# =========================
# Notifications page
# =========================
@study_session_routes.route("/notifications")
def notifications():
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())
    current_username = get_current_username()
    unread_count = get_unread_notification_count(current_user_id)

    conn = get_db_connection()

    notifications = conn.execute("""
        SELECT id, message, is_read, created_at, link
        FROM notifications
        WHERE user_id = ?
        AND is_cleared = 0
        ORDER BY id DESC
    """, (current_user_id,)).fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications,
        current_user=current_username,
        unread_count=unread_count
    )


# =========================
# Read one notification
# =========================
@study_session_routes.route("/notification/read/<int:notification_id>")
def read_notification(notification_id):
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())

    conn = get_db_connection()

    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE id = ?
        AND user_id = ?
    """, (notification_id, current_user_id))

    conn.commit()

    notification = conn.execute("""
        SELECT link
        FROM notifications
        WHERE id = ?
        AND user_id = ?
    """, (notification_id, current_user_id)).fetchone()

    conn.close()

    if notification and notification["link"]:
        return redirect(notification["link"])

    return redirect(url_for("study_session_routes.sessions"))


# =========================
# Mark all notifications as read
# =========================
@study_session_routes.route("/mark_notifications_read", methods=["POST"])
def mark_notifications_read():
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())

    conn = get_db_connection()

    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
        AND is_cleared = 0
    """, (current_user_id,))

    conn.commit()
    conn.close()

    flash("All notifications marked as read.")
    return redirect(url_for("study_session_routes.notifications"))


# =========================
# Clear all notifications
# This does NOT delete database rows
# It only hides notifications from the page
# =========================
@study_session_routes.route("/notifications/clear", methods=["POST"])
def clear_notifications():
    if not require_login():
        return redirect("/login")

    create_notifications_table()

    current_user_id = str(get_current_user_id())

    conn = get_db_connection()

    conn.execute("""
        UPDATE notifications
        SET is_cleared = 1
        WHERE user_id = ?
    """, (current_user_id,))

    conn.commit()
    conn.close()

    flash("All notifications cleared.")
    return redirect(url_for("study_session_routes.notifications"))