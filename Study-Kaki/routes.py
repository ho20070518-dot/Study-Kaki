from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

study_session_routes = Blueprint("study_session_routes", __name__)

# =========================
# Fixed database path
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    print("Using database:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
            created_at TEXT NOT NULL
        )
    """)

    try:
        conn.execute("ALTER TABLE notifications ADD COLUMN is_read INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def add_notification(user_id, message):
    create_notifications_table()

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO notifications (user_id, message, is_read, created_at)
        VALUES (?, ?, 0, ?)
    """, (
        user_id,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()


def get_unread_notification_count(user_id):
    create_notifications_table()

    conn = get_db_connection()

    unread_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE user_id = ? AND is_read = 0
    """, (user_id,)).fetchone()["total"]

    conn.close()
    return unread_count


# =========================
# Sessions page
# =========================
@study_session_routes.route("/sessions")
def sessions():
    create_notifications_table()

    current_user = session.get("user_id", "guest")
    search_query = request.args.get("search", "").strip()
    unread_count = get_unread_notification_count(current_user)

    conn = get_db_connection()

    if search_query:
        sessions = conn.execute("""
            SELECT * FROM sessions
            WHERE subject LIKE ?
            OR topic LIKE ?
            OR session_date LIKE ?
            OR session_time LIKE ?
            OR end_time LIKE ?
            OR location_type LIKE ?
            OR physical_location LIKE ?
            OR meeting_link LIKE ?
            OR created_by LIKE ?
            ORDER BY session_date, session_time
        """, (
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
            SELECT * FROM sessions
            ORDER BY session_date, session_time
        """).fetchall()

    print("Total sessions found:", len(sessions))

    for s in sessions:
        print(dict(s))

    conn.close()

    return render_template(
        "sessions.html",
        sessions=sessions,
        current_user=current_user,
        search_query=search_query,
        unread_count=unread_count
    )


# =========================
# Create session
# =========================
@study_session_routes.route("/create_session", methods=["GET", "POST"])
def create_session():
    current_user = session.get("user_id", "guest")
    unread_count = get_unread_notification_count(current_user)

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
            current_user
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
    current_user = session.get("user_id", "guest")
    unread_count = get_unread_notification_count(current_user)

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if study_session["created_by"] != current_user:
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
    current_user = session.get("user_id", "guest")

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if study_session["created_by"] != current_user:
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
    current_user = session.get("user_id", "guest")

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if study_session["created_by"] == current_user:
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

    add_notification(current_user, reminder_message)

    flash("You have joined this study session. A reminder notification has been added.")
    return redirect(url_for("study_session_routes.sessions"))


# =========================
# Leave session
# =========================
@study_session_routes.route("/leave_session/<int:session_id>")
def leave_session(session_id):
    current_user = session.get("user_id", "guest")

    conn = get_db_connection()

    study_session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    if study_session is None:
        conn.close()
        flash("Session not found.")
        return redirect(url_for("study_session_routes.sessions"))

    if study_session["created_by"] == current_user:
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
        current_user,
        f"You left {study_session['subject']} study session."
    )

    flash("You have left this study session.")
    return redirect(url_for("study_session_routes.sessions"))


# =========================
# Notifications page
# =========================
@study_session_routes.route("/notifications")
def notifications():
    create_notifications_table()

    current_user = session.get("user_id", "guest")
    unread_count = get_unread_notification_count(current_user)

    conn = get_db_connection()

    notifications = conn.execute("""
        SELECT id, message, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (current_user,)).fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications,
        current_user=current_user,
        unread_count=unread_count
    )


# =========================
# Mark all notifications as read
# =========================
@study_session_routes.route("/mark_notifications_read", methods=["POST"])
def mark_notifications_read():
    current_user = session.get("user_id", "guest")

    conn = get_db_connection()

    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (current_user,))

    conn.commit()
    conn.close()

    flash("All notifications marked as read.")
    return redirect(url_for("study_session_routes.notifications"))


# =========================
# Clear all notifications
# =========================
@study_session_routes.route("/clear_notifications")
def clear_notifications():
    current_user = session.get("user_id", "guest")

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM notifications WHERE user_id = ?",
        (current_user,)
    )

    conn.commit()
    conn.close()

    flash("All notifications cleared.")
    return redirect(url_for("study_session_routes.notifications"))