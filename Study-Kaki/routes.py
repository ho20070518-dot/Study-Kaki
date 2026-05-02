# routes.py - Member 2 Study Session Routes

from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

study_session_routes = Blueprint("study_session_routes", __name__)


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# READ - Display all study sessions
# ==========================================
@study_session_routes.route("/sessions")
def sessions():
    search = request.args.get("search", "")

    conn = get_db_connection()
    c = conn.cursor()

    if search:
        c.execute("""
            SELECT * FROM sessions
            WHERE subject LIKE ?
               OR topic LIKE ?
               OR physical_location LIKE ?
               OR meeting_link LIKE ?
            ORDER BY id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))
    else:
        c.execute("SELECT * FROM sessions ORDER BY id DESC")

    sessions_data = c.fetchall()
    conn.close()

    return render_template(
        "sessions.html",
        sessions=sessions_data,
        search=search
    )


# ==========================================
# CREATE - Create new study session
# ==========================================
@study_session_routes.route("/create-session", methods=["GET", "POST"])
def create_session():
    if request.method == "POST":
        subject = request.form["subject"]
        topic = request.form["topic"]
        session_date = request.form["session_date"]
        session_time = request.form["session_time"]
        end_time = request.form.get("end_time", "")
        location_type = request.form["location_type"]

        physical_location = request.form.get("physical_location", "")
        meeting_link = request.form.get("meeting_link", "")

        if location_type == "Physical":
            meeting_link = ""
        elif location_type == "Online":
            physical_location = ""

        conn = get_db_connection()
        c = conn.cursor()

        c.execute("""
            INSERT INTO sessions
            (subject, topic, session_date, session_time, end_time, location_type, physical_location, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subject,
            topic,
            session_date,
            session_time,
            end_time,
            location_type,
            physical_location,
            meeting_link
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("study_session_routes.sessions"))

    return render_template("create_session.html")


# ==========================================
# UPDATE - Edit study session
# ==========================================
@study_session_routes.route("/edit-session/<int:id>", methods=["GET", "POST"])
def edit_session(id):
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == "POST":
        subject = request.form["subject"]
        topic = request.form["topic"]
        session_date = request.form["session_date"]
        session_time = request.form["session_time"]
        end_time = request.form.get("end_time", "")
        location_type = request.form["location_type"]

        physical_location = request.form.get("physical_location", "")
        meeting_link = request.form.get("meeting_link", "")

        if location_type == "Physical":
            meeting_link = ""
        elif location_type == "Online":
            physical_location = ""

        c.execute("""
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
            id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("study_session_routes.sessions"))

    c.execute("SELECT * FROM sessions WHERE id = ?", (id,))
    study_session = c.fetchone()
    conn.close()

    return render_template("edit_session.html", session=study_session)


# ==========================================
# DELETE - Delete study session
# ==========================================
@study_session_routes.route("/delete-session/<int:id>", methods=["POST"])
def delete_session(id):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("DELETE FROM sessions WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("study_session_routes.sessions"))


# ==========================================
# JOIN - Join study session
# ==========================================
@study_session_routes.route("/join-session/<int:id>", methods=["POST"])
def join_session(id):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("UPDATE sessions SET joined = 1 WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("study_session_routes.sessions"))


# ==========================================
# LEAVE - Leave study session
# ==========================================
@study_session_routes.route("/leave-session/<int:id>", methods=["POST"])
def leave_session(id):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("UPDATE sessions SET joined = 0 WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("study_session_routes.sessions"))