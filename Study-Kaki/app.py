# app.py - Study Kaki Core System 
# Developer: Frontend & UI Lead

from flask import Flask, render_template, redirect, url_for
import sqlite3
from flask import request

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


# ==========================================
# 1. Public Interface Module
# ==========================================
@app.route('/')
def home():
    return redirect(url_for('login'))


# ==========================================
# 2. Authentication Module - UI & Routing
# Note: POST methods are reserved here for future form submissions
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    # TODO: Backend team will integrate Student ID validation logic here
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # TODO: Backend team will integrate user data storage logic here
    return render_template('register.html')


# ==========================================
# 3. Core Application Module
# ==========================================
@app.route('/dashboard')
def dashboard():
    # Main dashboard: Displays user analytics charts and recent sessions
    # TODO: Fetch real user progress data from the database to pass to the frontend
    return render_template('dashboard.html')

@app.route('/profile')
def profile():
    # Profile page: Displays the MMU student's academic expertise and badges
    return render_template('profile.html')

# ==========================================
# 4. Resource Board Module (Member 3)
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

    c.execute("INSERT INTO resources (title, description) VALUES (?, ?)",
              (title, description))

    conn.commit()
    conn.close()

    return "Resource saved!"

@app.route('/resources-list')
def resources_list():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM resources")
    data = c.fetchall()

    conn.close()

    return render_template("resources_list.html", resources=data)

@app.route('/delete-resource/<int:id>')
def delete_resource(id):
    print("DELETE ID:", id)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM resources WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return "DELETED"

# ==========================================
# Server Initialization
# ==========================================
if __name__ == '__main__':
    # debug=True allows for real-time updates during the development phase
    app.run(debug=True)