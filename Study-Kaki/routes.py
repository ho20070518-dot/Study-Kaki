from app import app
from flask import render_template


@app.route('/sessions')
def sessions():
    return render_template('sessions.html')


@app.route('/create_session')
def create_session():
    return render_template('create_session.html')


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