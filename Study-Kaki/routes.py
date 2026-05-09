from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3

study_session_routes = Blueprint("study_session_routes", __name__)


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@study_session_routes.route("/sessions")
def sessions():
    # Get current logged-in user from login system
    # If login system not ready yet, it will use "guest"
    current_user = session.get("user_id", "guest")

    conn = get_db_connection()
    sessions = conn.execute("""
        SELECT * FROM sessions
        ORDER BY session_date, session_time
    """).fetchall()
    conn.close()

    return render_template(
        "sessions.html",
        sessions=sessions,
        current_user=current_user
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
        return "Session not found", 404

    # Only creator can edit
    if study_session["created_by"] != current_user:
        conn.close()
        return "You are not allowed to edit this session.", 403

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
        return "Session not found", 404

    # Only creator can delete
    if study_session["created_by"] != current_user:
        conn.close()
        return "You are not allowed to delete this session.", 403

    conn.execute(
        "DELETE FROM sessions WHERE id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()

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
        return "Session not found", 404

    # Creator cannot join own session
    if study_session["created_by"] == current_user:
        conn.close()
        return redirect(url_for("study_session_routes.sessions"))

    conn.execute(
        "UPDATE sessions SET joined = 1 WHERE id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()

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
        return "Session not found", 404

    # Creator cannot leave own session
    if study_session["created_by"] == current_user:
        conn.close()
        return redirect(url_for("study_session_routes.sessions"))

    conn.execute(
        "UPDATE sessions SET joined = 0 WHERE id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("study_session_routes.sessions"))