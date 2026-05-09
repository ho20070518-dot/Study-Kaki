# app.py - Study Kaki Core System
# Developer: Frontend & UI Lead

from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3

app = Flask(__name__)

# Needed for Flask session
app.secret_key = "study_kaki_secret_key"


def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # ==========================================
    # Resource Board Table - Member 3
    # ==========================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')

    # ==========================================
    # Study Session Table - Member 2
    # ==========================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            session_date TEXT NOT NULL,
            session_time TEXT,
            end_time TEXT,
            location_type TEXT NOT NULL,
            physical_location TEXT,
            meeting_link TEXT,
            joined INTEGER DEFAULT 0,
            created_by TEXT
        )
    ''')

    # Add session_time column if old database does not have it
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN session_time TEXT")
    except sqlite3.OperationalError:
        pass

    # Add end_time column if old database does not have it
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN end_time TEXT")
    except sqlite3.OperationalError:
        pass

    # Add joined column if old database does not have it
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN joined INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Add created_by column if old database does not have it
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN created_by TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()


# ==========================================
# 1. Public Interface Module
# ==========================================
@app.route('/')
def home():
    return render_template('dashboard.html')


# ==========================================
# 2. Authentication Module
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']

        # Save current user into Flask session
        session['user_id'] = username

        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')


# ==========================================
# 3. Core Application Module
# ==========================================
@app.route('/profile')
def profile():
    current_user_info = {
        "name": session.get("user_id", "Alex Chen"),
        "student_id": session.get("user_id", "TP088123"),
        "bio": "Deep thinker. Looking for study buddies to discuss Python, Flask, and maybe plan a weekend hike at Broga Hill!"
    }

    return render_template('profile.html', user_data=current_user_info)


@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    current_user_info = {
        "name": session.get("user_id", "Alex Chen"),
        "student_id": session.get("user_id", "TP088123"),
        "bio": "Deep thinker. Looking for study buddies to discuss Python, Flask, and maybe plan a weekend hike at Broga Hill!"
    }

    return render_template('edit_profile.html', user_data=current_user_info)


# ==========================================
# 4. Resource Board Module - Member 3
# ==========================================
@app.route('/resources')
def resources():
    return render_template('resources.html')


@app.route('/add-resource', methods=['POST'])
def add_resource():
    title = request.form['title']
    description = request.form['description']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute(
        "INSERT INTO resources (title, description) VALUES (?, ?)",
        (title, description)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('resources_list', success=1))


@app.route('/resources-list')
def resources_list():
    query = request.args.get('q')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if query:
        c.execute(
            "SELECT * FROM resources WHERE title LIKE ? OR description LIKE ?",
            ('%' + query + '%', '%' + query + '%')
        )
    else:
        c.execute("SELECT * FROM resources")

    data = c.fetchall()
    conn.close()

    return render_template("resources_list.html", resources=data, query=query)


@app.route('/delete-resource/<int:id>')
def delete_resource(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM resources WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('resources_list'))


@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM resources")
    total = c.fetchone()[0]

    conn.close()

    return render_template("dashboard.html", total_resources=total)


# ==========================================
# Register Member 2 Study Session Routes
# ==========================================
from routes import study_session_routes
app.register_blueprint(study_session_routes)


# ==========================================
# Server Initialization
# ==========================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True)