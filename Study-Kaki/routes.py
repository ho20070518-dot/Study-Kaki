# routes.py - Member 2 Study Session Module
# Create, Read, Join, Leave, Delete Study Sessions

from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta

study_session_routes = Blueprint('study_session_routes', __name__)


# ==========================================
# Display Study Sessions
# ==========================================
@study_session_routes.route('/sessions')
def sessions():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Do not use SELECT *
    # This keeps the order correct for sessions.html
    c.execute("""
        SELECT 
            id,
            subject,
            topic,
            session_date,
            session_time,
            end_time,
            location_type,
            physical_location,
            meeting_link,
            joined
        FROM sessions
    """)

    data = c.fetchall()

    conn.close()

    return render_template('sessions.html', sessions=data)


# ==========================================
# Create Study Session
# ==========================================
@study_session_routes.route('/create_session', methods=['GET', 'POST'])
def create_session():
    if request.method == 'POST':
        subject = request.form['subject']
        topic = request.form['topic']
        session_date = request.form['date']
        session_time = request.form['time']
        location_type = request.form['location_type']
        physical_location = request.form.get('physical_location')
        meeting_link = request.form.get('meeting_link')

        # Automatically set fixed 2-hour duration
        start_time = datetime.strptime(session_time, "%H:%M")
        end_time = start_time + timedelta(hours=2)
        end_time = end_time.strftime("%H:%M")

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO sessions 
            (subject, topic, session_date, session_time, end_time, location_type, physical_location, meeting_link, joined)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            subject,
            topic,
            session_date,
            session_time,
            end_time,
            location_type,
            physical_location,
            meeting_link,
            0
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('study_session_routes.sessions'))

    return render_template('create_session.html')


# ==========================================
# Join Study Session
# ==========================================
@study_session_routes.route('/join_session/<int:id>')
def join_session(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("UPDATE sessions SET joined = 1 WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('study_session_routes.sessions'))


# ==========================================
# Leave Study Session
# ==========================================
@study_session_routes.route('/leave_session/<int:id>')
def leave_session(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("UPDATE sessions SET joined = 0 WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('study_session_routes.sessions'))


# ==========================================
# Delete Study Session
# ==========================================
@study_session_routes.route('/delete_session/<int:id>')
def delete_session(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM sessions WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('study_session_routes.sessions'))


# ==========================================
# Future Feature: Filter Sessions
# ==========================================
@study_session_routes.route('/filter_sessions')
def filter_sessions():
    return "Session filtering feature coming soon"


# ==========================================
# Future Feature: Notifications
# ==========================================
@study_session_routes.route('/notifications')
def notifications():
    return "Notifications feature coming soon"