# app.py - Study Kaki Core System
# Developer: Frontend & UI Lead

from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

def get_user_role(student_id):
    # 🟢 彻底拔掉数据库连接和报错的 SQL 语句
    # 不管谁来查，一律安全、无公害地返回默认身份 'mentee'（或者 'Student'）
    return 'mentee'

# 下面的代码保持不动
from functools import wraps

from functools import wraps

def mentor_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'role' not in session or session['role'] != 'mentor':
            flash("Access denied: Mentor only.")
            return redirect(url_for('resources_list'))
        return f(*args, **kwargs)
    return wrapper

app = Flask(__name__)
app.secret_key = 'studykaki_secret_key_123'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            subject TEXT NOT NULL,
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
            username TEXT NOT NULL,
            student_id TEXT NOT NULL, 
            password TEXT NOT NULL,
            bio TEXT,
            tech_stack TEXT,
            exp_1 TEXT,
            exp_2 TEXT
            role TEXT DEFAULT 'mentee'
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
        
        # 🌟 1. 修改修改：把 student_id 也查出来
        # 现在 result[0]是id, result[1]是student_id, result[2]是password
        db.execute("SELECT id, student_id, password FROM users WHERE username = ? OR student_id = ?", (u, u))
        result = db.fetchone()
        conn.close()

        if result and result[2] == p: # 密码现在是索引 2
            # 🌟 2. 核心修改：把你朋友要的“真实学号/名字”存进 session['user_id']
            session['user_id'] = result[1]  # 👈 以前这里存的是 result[0](数字)，现在改成 result[1](学号/名字)
            session['username'] = u
            session['role'] = get_user_role(result[1])
            
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid Student ID or Password!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 🌟 名字必须和 HTML 里的 name="xxx" 一模一样
        u = request.form.get('username')   # 对应 HTML 的 fullname
        sid = request.form.get('studentid') # 对应 HTML 的 studentid
        p = request.form.get('password')

        # 既然你的 HTML 删掉了“确认密码”，我们就先把那个 if p != cp 删掉
        # 或者你在 HTML 里加一个 confirm_password 的输入框

        conn = sqlite3.connect('database.db')
        db = conn.cursor()

        # 检查是否已注册 (用 Student ID 检查更准)
        db.execute("SELECT * FROM users WHERE username = ?", (u,))
        if db.fetchone() is not None:
            conn.close()
            return render_template('register.html', error="User already exists!")

        # 写入数据库
        db.execute('''
            INSERT INTO users (username, student_id, password) 
            VALUES (?, ?, ?)
        ''', (u, sid, p))
        conn.commit()
        conn.close()

        print(f"🎉 注册成功: {u}")
        return redirect(url_for('home')) # 或者跳到 login

    return render_template('register.html')

# ==========================================
# 3. Core Application Module
# ==========================================
@app.route('/profile')
def profile():
    # 1. 如果连 session 都没有，踢回登录
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()
    
    # 2. 去数据库找人
    db.execute("SELECT * FROM users WHERE student_id = ? OR id = ?", (session['user_id'], session['user_id']))
    user_data = db.fetchone()
    conn.close()

    # 🌟 3. 核心防爆机制：如果数据库查不到这个人（比如删库重造了）
    if user_data is None:
        session.clear() # 清空旧的错误记忆
        flash("Session expired or user not found. Please login again.", "danger")
        return redirect(url_for('login')) # 踢回登录页重新注册/登录

    return render_template('profile.html', user_data=user_data)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 1. 接收前端表单发来的所有数据
        new_name = request.form.get('name')
        new_bio = request.form.get('bio')
        new_tech = request.form.get('tech_stack')
        new_stats = request.form.get('stats')
        new_hobbies = request.form.get('hobbies')

        # 2. 更新到数据库
        conn = sqlite3.connect('database.db')
        db = conn.cursor()
        db.execute("""
            UPDATE users 
            SET username = ?, bio = ?, tech_stack = ?, exp_1 = ?, exp_2 = ?
            WHERE student_id = ?
        """, (new_name, new_bio, new_tech, new_stats, new_hobbies, session['user_id']))
        
        conn.commit()
        conn.close()
        
        # 3. 存完之后，跳回展示页
        return redirect(url_for('profile'))

    # 如果是 GET 请求（刚点开编辑页面），我们要先把旧数据查出来，填在输入框里
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()
    db.execute("SELECT * FROM users WHERE student_id = ?", (session['user_id'],))
    user_data = db.fetchone()
    conn.close()

    return render_template('edit_profile.html', user_data=user_data)

# ==========================================
# 4. Resource Board Module - Member 3
# ==========================================
@app.route('/resources')
def resources():
    return render_template('resources.html')


@app.route('/add-resource', methods=['POST'])
@mentor_only
def add_resource():
    subject = request.form['subject']
    title = request.form['title']
    description = request.form['description']
    file = request.files['file']

    if subject.strip() == "" or title.strip() == "" or description.strip() == "":
        error = "Please fill in all required fields"

        return render_template(
            "resources.html",
            error=error,
            old_subject=subject,
            old_title=title,
            old_description=description
        )

    filename = None

    if file and file.filename != "":

        if not allowed_file(file.filename):
            flash("Invalid file type. Only PDF, DOCX, PPTX, PNG, JPG and JPEG are allowed.")
            return redirect(url_for('resources'))

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute(
            "INSERT INTO resources (subject, title, description, file_name) VALUES (?, ?, ?, ?)",
            (subject, title, description, filename)
        )

        conn.commit()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return redirect(url_for('resources_list', success=1))

@app.route('/edit-resource/<int:id>')
@mentor_only
def edit_resource(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM resources WHERE id = ?", (id,))
    resource = c.fetchone()

    conn.close()
 
    if resource is None:
        return "Resource not found"

    return render_template("edit_resources.html", resource=resource)

@app.route('/update-resource/<int:id>', methods=['POST'])
@mentor_only
def update_resource(id):
    title = request.form['title']
    description = request.form['description']
    
    if title.strip() == "" or description.strip() == "":
        flash("Fields cannot be empty")
        return redirect(url_for('edit_resource', id=id))

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute(
            "UPDATE resources SET title=?, description=? WHERE id=?",
            (title, description, id)
        )

        conn.commit()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return redirect(url_for('resources_list', updated=1))


@app.route('/resources-list')
def resources_list():
    query = request.args.get('q')
    subject_filter = request.args.get('subject')

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        if subject_filter:
            c.execute(
                "SELECT * FROM resources WHERE subject = ?",
                (subject_filter,)
            )

        elif query:
            c.execute(
                "SELECT * FROM resources WHERE title LIKE ? OR description LIKE ? OR subject LIKE ?",
                ('%' + query + '%',
                 '%' + query + '%',
                 '%' + query + '%')
            )

        else:
            c.execute("SELECT * FROM resources")

        data = c.fetchall()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return render_template(
        "resources_list.html",
        resources=data,
        query=query
    )

@app.route('/subject/<subject_name>')
def subject_folder(subject_name):

    query = request.args.get('q')
    sort = request.args.get('sort', 'newest')

    order_by = "id DESC"

    if sort == "oldest":
        order_by = "id ASC"

    elif sort == "az":
        order_by = "title ASC"

    elif sort == "za":
        order_by = "title DESC"

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        if query:

            c.execute(
                f"""
                SELECT * FROM resources
                WHERE subject = ?
                AND (
                    title LIKE ?
                    OR description LIKE ?
                )
                ORDER BY {order_by}
                """,
                (
                    subject_name,
                    '%' + query + '%',
                    '%' + query + '%'
                )
            )

        else:

            c.execute(
                f"SELECT * FROM resources WHERE subject=? ORDER BY {order_by}",
                (subject_name,)
            )

        resources = c.fetchall()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return render_template(
        "subject_folder.html",
        resources=resources,
        subject=subject_name,
        query=query,
        sort=sort
    )

@app.route('/delete-resource/<int:id>')
@mentor_only
def delete_resource(id):

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute(
            "SELECT file_name FROM resources WHERE id=?",
            (id,)
        )

        resource = c.fetchone()

        if resource and resource[0]:
            filepath = os.path.join(
                app.config['UPLOAD_FOLDER'],
                resource[0]
            )

            if os.path.exists(filepath):
                os.remove(filepath)

        c.execute(
            "DELETE FROM resources WHERE id=?",
            (id,)
        )

        conn.commit()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return redirect(url_for('resources_list'))

@app.route('/sessions')
def sessions():

    return render_template('sessions.html') 


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