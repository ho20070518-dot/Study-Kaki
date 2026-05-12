from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

study_session_routes = Blueprint("study_session_routes", __name__)


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_notifications_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_notification(user_id, message):
    create_notifications_table()

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO notifications (user_id, message, created_at)
        VALUES (?, ?, ?)
    """, (
        user_id,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    conn.close()


@study_session_routes.route("/sessions")
def sessions():
    create_notifications_table()

    current_user = session.get("user_id", "guest")
    search_query = request.args.get("search", "").strip()

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

    conn.close()

    return render_template(
        "sessions.html",
        sessions=sessions,
        current_user=current_user,
        search_query=search_query
    )


@study_session_routes.route("/create_session", methods=["GET", "POST"])
def create_session():
    current_user = session.get("user_id", "guest")

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

    return render_template("create_session.html")


@study_session_routes.route("/edit_session/<int:session_id>", methods=["GET", "POST"])
def edit_session(session_id):
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
    return render_template("edit_session.html", session=study_session)


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


@study_session_routes.route("/notifications")
def notifications():
    create_notifications_table()

    current_user = session.get("user_id", "guest")

    conn = get_db_connection()

    notifications = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (current_user,)).fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications,
        current_user=current_user
    )


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