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
@app.route('/profile')
def profile():
    # 模拟从数据库里抓取了当前登录用户的数据
    # (以后我们会用真正的 SQLite 来替换这里)
    current_user_info = {
        "name": "Alex Chen",
        "student_id": "TP088123",
        "bio": "Deep thinker. Looking for study buddies to discuss Python, Flask, and maybe plan a weekend hike at Broga Hill!"
    }
    
    # 关键点：把 current_user_info 这个字典，打包命名为 user_data 发给 profile.html
    return render_template('profile.html', user_data=current_user_info)

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

    return redirect(url_for('resources_list', success=1))

@app.route('/resources-list')
def resources_list():
    query = request.args.get('q')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if query:
        c.execute("SELECT * FROM resources WHERE title LIKE ? OR description LIKE ?",
                  ('%' + query + '%', '%' + query + '%'))
    else:
        c.execute("SELECT * FROM resources")

    data = c.fetchall()
    conn.close()

    return render_template("resources_list.html", resources=data, query=query)

@app.route('/delete-resource/<int:id>')
def delete_resource(id):
    print("DELETE ID:", id)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM resources WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return "DELETED"

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM resources")
    total = c.fetchone()[0]

    conn.close()

    return render_template("dashboard.html", total_resources=total)

# ==========================================
# Server Initialization
# ==========================================
if __name__ == '__main__':
    # debug=True allows for real-time updates during the development phase
    app.run(debug=True)