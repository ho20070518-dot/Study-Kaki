# app.py - Study Kaki Core System
# Developer: Frontend & UI Lead

from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'studykaki_secret_key_123'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'png', 'jpg', 'jpeg'}

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
            description TEXT NOT NULL,
            file_name TEXT
        )
    ''')

    try:
        c.execute("ALTER TABLE resources ADD COLUMN file_name TEXT")
    except sqlite3.OperationalError:
        pass

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

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            bio TEXT DEFAULT 'New Kaki here!'
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
    return render_template('index.html')


# ==========================================
# 2. Authentication Module
# ==========================================
@app.route('/') # 访问主域名时触发
def index():
    # 直接渲染，不要重定向到文件名
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')

        conn = sqlite3.connect('database.db')
        db = conn.cursor()
        # 🌟 查出密码和 ID
        db.execute("SELECT id, password FROM users WHERE username = ?", (u,))
        result = db.fetchone()
        conn.close()

        # 检查用户是否存在且密码正确
        if result and result[1] == p:
            # 🌟 关键：登录成功，把名字存进 session 
            session['user_id'] = result[0]
            session['username'] = u
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password!")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        cp = request.form.get('confirm_password')

        # 1. 基础逻辑检查：两次密码对吗？
        if p != cp:
            return render_template('register.html', error="Passwords do not match!")

        conn = sqlite3.connect('database.db')
        db = conn.cursor()

        # 2. 检查：这个名字是不是被人取了？
        db.execute("SELECT * FROM users WHERE username = ?", (u,))
        if db.fetchone() is not None:
            conn.close()
            return render_template('register.html', error="Username already exists!")

        # 3. 🌟 核心动作：把新用户塞进数据库
        # 注意：这里用的是 INSERT INTO 而不是 SELECT
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
        
        # 4. 🚀 关键：必须 COMMIT 才会真的写入硬盘！
        conn.commit() 
        conn.close()

        # 注册成功，送他去登录页面
        return redirect(url_for('login'))

    return render_template('register.html')

# ==========================================
# 3. Core Application Module
# ==========================================
@app.route('/profile')
def profile():
    # 1. 拦截未登录用户：没登录的人不准看 profile
    if 'username' not in session:
        return redirect(url_for('login'))

    # 2. 从数据库抓取当前登录用户的最新资料
    conn = sqlite3.connect('database.db')
    db = conn.cursor()
    db.execute("SELECT username, bio FROM users WHERE username = ?", (session['username'],))
    user = db.fetchone()
    conn.close()

    # 3. 将真实数据传给模板
    current_user_info = {
        "name": user[0],
        "bio": user[1]
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
    file = request.files['file']

    if title.strip() == "" or description.strip() == "":
        return "Fields cannot be empty"

    filename = None

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute(
        "INSERT INTO resources (title, description, file_name) VALUES (?, ?, ?)",
        (title, description, filename)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('resources_list', success=1))

@app.route('/edit-resource/<int:id>')
def edit_resource(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM resources WHERE id = ?", (id,))
    resource = c.fetchone()

    conn.close()

    return render_template("edit_resources.html", resource=resource)

@app.route('/update-resource/<int:id>', methods=['POST'])
def update_resource(id):
    title = request.form['title']
    description = request.form['description']
    
    if title.strip() == "" or description.strip() == "":
        return "Fields cannot be empty"

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute(
        "UPDATE resources SET title=?, description=? WHERE id=?",
        (title, description, id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('resources_list', updated=1))


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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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