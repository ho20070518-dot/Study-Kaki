# routes.py - Member 2 Study Session Module

from app import app
from flask import render_template, request, redirect, url_for
import sqlite3


# ==========================================
# Display Study Sessions
# ==========================================
@app.route('/sessions')
def sessions():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM sessions")
    data = c.fetchall()

    conn.close()

    return render_template('sessions.html', sessions=data)


# ==========================================
# Create Study Session
# ==========================================
@app.route('/create_session', methods=['GET', 'POST'])
def create_session():
    if request.method == 'POST':
        subject = request.form['subject']
        topic = request.form['topic']
        session_date = request.form['date']
        location_type = request.form['location_type']
        physical_location = request.form.get('physical_location')
        meeting_link = request.form.get('meeting_link')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO sessions 
            (subject, topic, session_date, location_type, physical_location, meeting_link)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (subject, topic, session_date, location_type, physical_location, meeting_link))

        conn.commit()
        conn.close()

        return redirect(url_for('sessions'))

    return render_template('create_session.html')


# ==========================================
# Future Features - Week 6 and Later
# ==========================================
@app.route('/join_session')
def join_session():
    return "Join session feature coming soon"


@app.route('/leave_session')
def leave_session():
    return "Leave session feature coming soon"


@app.route('/filter_sessions')
def filter_sessions():
    return "Session filtering feature coming soon"


@app.route('/notifications')
def notifications():
    return "Notifications feature coming soon"