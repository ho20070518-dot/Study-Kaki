# app.py - Study Kaki Core System
# Developer: Frontend & UI Lead

from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from functools import wraps
from flask import jsonify

# ==========================================
# 1. 绝对路径锁死（彻底解决外围生成问题）
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = 'studykaki_secret_key_123'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================
# 2. 角色与权限管理
# ==========================================
def get_user_role(student_id):
    # 🟢 彻底拔掉数据库连接和报错的 SQL 语句
    # 不管谁来查，一律安全、无公害地返回默认身份 'mentee'
    return 'mentee'

def mentor_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'role' not in session or session['role'] != 'mentor':
            flash("Access denied: Mentor only.")
            return redirect(url_for('resources_list'))
        return f(*args, **kwargs)
    return wrapper

# ==========================================
# 3. 数据库连接与初始化 (统一使用 DB_PATH)
# ==========================================
def get_db_connection():
    """全项目获取数据库连接的唯一入口"""
    conn = sqlite3.connect(DB_PATH) # 🌟 必须使用绝对路径
    conn.row_factory = sqlite3.Row
    return conn

def is_mentor(student_id):

    conn = get_db_connection()

    mentor = conn.execute(
        """
        SELECT id
        FROM sessions
        WHERE created_by = ?
        LIMIT 1
        """,
        (str(student_id),)
    ).fetchone()

    conn.close()

    return mentor is not None

def init_db():
    conn = get_db_connection() # 直接调用上面的统一连接
    c = conn.cursor()

    # 1. Users 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            student_id TEXT NOT NULL, 
            password TEXT NOT NULL,
            bio TEXT,
            tech_stack TEXT,
            exp_1 TEXT,
            exp_2 TEXT,
            role TEXT DEFAULT 'mentee'
        )
    ''')

    # 2. Sessions 表
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

    # 3. Resources 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            subject TEXT NOT NULL,
            file_name TEXT,
            uploaded_by TEXT,
            post_type TEXT DEFAULT 'resource',
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0  
        )
    ''')

    try:
        c.execute("""
            ALTER TABLE resources
            ADD COLUMN subject TEXT DEFAULT 'Uncategorized'
        """)
    except sqlite3.OperationalError:
        pass

    c.execute("""
        UPDATE resources
        SET subject = 'Uncategorized'
        WHERE subject IS NULL
        OR TRIM(subject) = ''
    """)

    try:
        c.execute("""
            ALTER TABLE resources
            ADD COLUMN uploaded_by TEXT
        """)
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""
            ALTER TABLE resources
            ADD COLUMN post_type TEXT DEFAULT 'resource'
        """)
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""
            ALTER TABLE resources
            ADD COLUMN upvotes INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("""
            ALTER TABLE resources
            ADD COLUMN downvotes INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            resource_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_by TEXT NOT NULL
        )
        ''')


    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL,
            answered_by TEXT NOT NULL,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0
        )
        ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS answer_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            vote_type TEXT NOT NULL
        )
    ''')
    
    # 4. Notifications 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            is_cleared INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            link TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS session_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(session_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()
    # 这一行打印很重要，启动时你能立刻看到数据库真正生成在了哪里
    print(f"✅ 数据库初始化完成！当前锁定路径: {DB_PATH}")

# 确保应用启动时强制执行建表
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

        conn = get_db_connection()
        
        # 🌟 1. 改为 conn.execute，并直接在后面加上 .fetchone()
        result = conn.execute("SELECT id, student_id, password FROM users WHERE username = ? OR student_id = ?", (u, u)).fetchone()
        conn.close()

        if result and result[2] == p: # 密码现在是索引 2
            # 🌟 2. 核心修改：存入真实的 student_id
            session['user_id'] = result[1]  
            session['username'] = u
            if is_mentor(result[1]):
                session['role'] = 'mentor'
            else:
                session['role'] = 'mentee'
            
            return redirect(url_for('dashboard')) # 确保你有 dashboard 这个路由，没有的话改成 home
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
        u = request.form.get('username')   # 对应 HTML 的 fullname
        sid = request.form.get('studentid') # 对应 HTML 的 studentid
        p = request.form.get('password')

        conn = get_db_connection()

        # 🌟 1. 改为 conn.execute，检查是否已注册
        existing_user = conn.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        if existing_user is not None:
            conn.close()
            return render_template('register.html', error="User already exists!")

        # 🌟 2. 改为 conn.execute，写入数据库
        conn.execute('''
            INSERT INTO users (username, student_id, password) 
            VALUES (?, ?, ?)
        ''', (u, sid, p))
        conn.commit()
        conn.close()

        print(f"🎉 注册成功: {u}")
        return redirect(url_for('home')) # 注册成功后跳转

    return render_template('register.html')

# ==========================================
# 3. Core Application Module
# ==========================================
@app.route('/profile')
def profile():
    # 1. 如果连 session 都没有，踢回登录
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 🌟 核心修改：使用统一的绝对路径连接
    conn = get_db_connection() 
    # 删掉了 row_factory，因为 get_db_connection() 里面已经帮你写过了
    
    # 2. 去数据库找人 (直接用 conn.execute)
    user_data = conn.execute("SELECT * FROM users WHERE student_id = ? OR id = ?", (session['user_id'], session['user_id'])).fetchone()
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

        # 🌟 2. 更新到数据库：使用统一的绝对路径连接
        conn = get_db_connection()
        conn.execute("""
            UPDATE users 
            SET username = ?, bio = ?, tech_stack = ?, exp_1 = ?, exp_2 = ?
            WHERE student_id = ?
        """, (new_name, new_bio, new_tech, new_stats, new_hobbies, session['user_id']))
        
        conn.commit()
        conn.close()
        
        # 3. 存完之后，跳回展示页
        return redirect(url_for('profile'))

    # 如果是 GET 请求（刚点开编辑页面），我们要先把旧数据查出来，填在输入框里
    # 🌟 再次使用统一连接，并简化查询语句
    conn = get_db_connection()
    user_data = conn.execute("SELECT * FROM users WHERE student_id = ?", (session['user_id'],)).fetchone()
    conn.close()

    return render_template('edit_profile.html', user_data=user_data)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    # 1. 检查是否登录
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # 2. 连接数据库，执行删除命令
    conn = get_db_connection()
    # 彻底从 users 表里删掉这个人
    conn.execute("DELETE FROM users WHERE student_id = ? OR id = ?", (user_id, user_id))
    conn.commit()
    conn.close()

    # 3. 清空该用户的登录记忆（Session）
    session.clear()
    
    # 4. 跳转回登录页面
    flash("Your account has been successfully deleted.", "success")
    return redirect(url_for('login'))

# ==========================================
# 4. Resource Board Module - Member 3
# ==========================================
@app.route('/resources')
def resources():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    if is_mentor(session['user_id']):
        session['role'] = 'mentor'
    else:
        session['role'] = 'mentee'

    conn = get_db_connection()

    subjects = conn.execute("""
        SELECT DISTINCT subject
        FROM sessions
        WHERE created_by = ?
        ORDER BY subject
    """, (session['user_id'],)).fetchall()

    conn.close()

    return render_template(
        'resources.html',
        subjects=subjects
    )


@app.route('/add-resource', methods=['POST'])
@mentor_only
def add_resource():
    subject = request.form['subject'].strip()
    title = request.form['title'].strip()
    description = request.form['description'].strip()
    file = request.files['file']

    conn = get_db_connection()

    allowed_subject = conn.execute("""
        SELECT 1
        FROM sessions
        WHERE created_by = ?
        AND subject = ?
        LIMIT 1
    """, (
        session['user_id'],
        subject
    )).fetchone()

    conn.close()

    if not allowed_subject:
        flash("You can only upload resources for subjects you mentor.")
        return redirect(url_for('resources'))

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
        # 🌟 1. 改用我们统一的绝对路径连接函数
        conn = get_db_connection()
        
        # 🌟 2. 直接使用 conn.execute
        conn.execute(
            """
            INSERT INTO resources
            (subject, title, description, file_name, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                subject,
                title,
                description,
                filename,
                session['user_id']
            )
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
    conn = get_db_connection()

    resource = conn.execute(
        "SELECT * FROM resources WHERE id = ?",
        (id,)
    ).fetchone()
    
    if resource is None:
        conn.close()
        return "Resource not found"

    if resource[5] != session['user_id']:
        conn.close()
        flash("You are not allowed to edit this resource.")
        return redirect(url_for('resources_list'))

    conn.close()

    return render_template("edit_resources.html", resource=resource)

@app.route('/update-resource/<int:id>', methods=['POST'])
@mentor_only
def update_resource(id):
    title = request.form['title'].strip()
    description = request.form['description'].strip()
    
    if title.strip() == "" or description.strip() == "":
        flash("Fields cannot be empty")
        return redirect(url_for('edit_resource', id=id))

    try:
        conn = get_db_connection()

        resource = conn.execute(
            "SELECT uploaded_by FROM resources WHERE id=?",
            (id,)
        ).fetchone()

        if resource is None:
            conn.close()
            return "Resource not found"

        if resource[0] != session['user_id']:
            conn.close()
            flash("You are not allowed to update this resource.")
            return redirect(url_for('resources_list'))

        conn.execute(
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
        conn = get_db_connection()

        if subject_filter:
            data = conn.execute(
                "SELECT * FROM resources WHERE subject = ?",
                (subject_filter,)
            ).fetchall()

        elif query:
            data = conn.execute(
                "SELECT * FROM resources WHERE title LIKE ? OR description LIKE ? OR subject LIKE ?",
                ('%' + query + '%',
                 '%' + query + '%',
                 '%' + query + '%')
            ).fetchall()

        else:
            data = conn.execute(
                "SELECT * FROM resources"
            ).fetchall()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return render_template(
        "resources_list.html",
        resources=data,
        query=query
    )

@app.route('/questions')
def questions():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    sort = request.args.get('sort', 'newest')
    search = request.args.get('search', '').strip()

    page = request.args.get('page', 1, type=int)
    per_page = 5

    offset = (page - 1) * per_page

    conn = get_db_connection()

    sql = "SELECT * FROM questions"
    count_sql = "SELECT COUNT(*) FROM questions"

    params = []

    if search:

        sql += """
        WHERE title LIKE ?
        OR content LIKE ?
        OR subject LIKE ?
        OR topic LIKE ?
        """

        count_sql += """
        WHERE title LIKE ?
        OR content LIKE ?
        OR subject LIKE ?
        OR topic LIKE ?
        """

        keyword = f"%{search}%"

        params = [
            keyword,
            keyword,
            keyword,
            keyword
        ]

    if sort == "oldest":
        sql += " ORDER BY id ASC"

    elif sort == "az":
        sql += " ORDER BY title ASC"

    elif sort == "za":
        sql += " ORDER BY title DESC"

    else:
        sql += " ORDER BY id DESC"

    sql += " LIMIT ? OFFSET ?"

    questions = conn.execute(
        sql,
        params + [per_page, offset]
    ).fetchall()

    total_questions = conn.execute(
        count_sql,
        params
    ).fetchone()[0]

    conn.close()

    total_pages = (total_questions + per_page - 1) // per_page

    return render_template(
        "questions.html",
        questions=questions,
        sort=sort,
        search=search,
        page=page,
        total_pages=total_pages
    )

@app.route('/question/<int:id>')
def question_detail(id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    question = conn.execute("""
        SELECT *
        FROM questions
        WHERE id = ?
    """, (id,)).fetchone()

    if question is None:
        conn.close()
        return "Question not found"

    answers = conn.execute("""
        SELECT *
        FROM answers
        WHERE question_id = ?
        ORDER BY id DESC
    """, (id,)).fetchall()

    conn.close()

    return render_template(
        "question_detail.html",
        question=question,
        answers=answers
    )

@app.route('/add-answer/<int:question_id>', methods=['POST'])
def add_answer(question_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    answer_text = request.form['answer_text']

    if answer_text.strip() == "":
        flash("Reply cannot be empty.")
        return redirect(url_for(
            'question_detail',
            id=question_id
        ))

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO answers
        (
            question_id,
            answer_text,
            answered_by
        )
        VALUES (?, ?, ?)
    """,
    (
        question_id,
        answer_text,
        session['user_id']
    ))

    conn.commit()
    conn.close()

    return redirect(url_for(
        'question_detail',
        id=question_id
    ))

@app.route('/edit-answer/<int:answer_id>', methods=['GET', 'POST'])
def edit_answer(answer_id):

    conn = get_db_connection()

    answer = conn.execute("""
        SELECT *
        FROM answers
        WHERE id = ?
    """, (answer_id,)).fetchone()

    if not answer:
        conn.close()
        flash("Reply not found.")
        return redirect('/questions')

    if answer['answered_by'] != session.get('user_id'):
        conn.close()
        flash("You can only edit your own reply.")
        return redirect(f"/question/{answer['question_id']}")

    if request.method == 'POST':

        new_text = request.form['answer_text']

        conn.execute("""
            UPDATE answers
            SET answer_text = ?
            WHERE id = ?
        """, (new_text, answer_id))

        conn.commit()
        conn.close()

        flash("Reply updated successfully.")
        return redirect(f"/question/{answer['question_id']}")

    conn.close()

    return render_template(
        'edit_answer.html',
        answer=answer
    )

@app.route('/delete-answer/<int:answer_id>')
def delete_answer(answer_id):

    conn = get_db_connection()

    answer = conn.execute("""
        SELECT *
        FROM answers
        WHERE id = ?
    """, (answer_id,)).fetchone()

    if not answer:
        conn.close()
        flash("Reply not found.")
        return redirect('/questions')

    if answer['answered_by'] != session.get('user_id'):
        conn.close()
        flash("You can only delete your own reply.")
        return redirect(f"/question/{answer['question_id']}")

    question_id = answer['question_id']

    conn.execute("""
        DELETE FROM answers
        WHERE id = ?
    """, (answer_id,))

    conn.commit()
    conn.close()

    flash("Reply deleted successfully.")

    return redirect(f"/question/{question_id}")

@app.route('/vote-answer/<int:answer_id>/<vote_type>')
def vote_answer(answer_id, vote_type):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    answer = conn.execute("""
        SELECT question_id
        FROM answers
        WHERE id = ?
    """, (answer_id,)).fetchone()

    if answer is None:
        conn.close()
        return redirect(url_for('questions'))

    existing_vote = conn.execute("""
        SELECT *
        FROM answer_votes
        WHERE answer_id = ?
        AND user_id = ?
    """,
    (
        answer_id,
        session['user_id']
    )).fetchone()

    if existing_vote:

        if existing_vote['vote_type'] == vote_type:

            conn.execute("""
                DELETE FROM answer_votes
                WHERE id = ?
            """, (existing_vote['id'],))

            if vote_type == "up":

                conn.execute("""
                    UPDATE answers
                    SET upvotes = upvotes - 1
                    WHERE id = ?
                """, (answer_id,))

            else:

                conn.execute("""
                    UPDATE answers
                    SET downvotes = downvotes - 1
                    WHERE id = ?
                """, (answer_id,))

        else:

            conn.execute("""
                UPDATE answer_votes
                SET vote_type = ?
                WHERE id = ?
            """,
            (
                vote_type,
                existing_vote['id']
            ))

            if vote_type == "up":

                conn.execute("""
                    UPDATE answers
                    SET upvotes = upvotes + 1,
                        downvotes = downvotes - 1
                    WHERE id = ?
                """, (answer_id,))

            else:

                conn.execute("""
                    UPDATE answers
                    SET downvotes = downvotes + 1,
                        upvotes = upvotes - 1
                    WHERE id = ?
                """, (answer_id,))

    else:

        conn.execute("""
            INSERT INTO answer_votes
            (
                answer_id,
                user_id,
                vote_type
            )
            VALUES (?, ?, ?)
        """,
        (
            answer_id,
            session['user_id'],
            vote_type
        ))

        if vote_type == "up":

            conn.execute("""
                UPDATE answers
                SET upvotes = upvotes + 1
                WHERE id = ?
            """, (answer_id,))

        else:

            conn.execute("""
                UPDATE answers
                SET downvotes = downvotes + 1
                WHERE id = ?
            """, (answer_id,))

    conn.commit()

    question_id = answer['question_id']

    conn.close()

    return redirect(
        url_for(
            'question_detail',
            id=question_id
        )
    )

@app.route('/ask-question')
def ask_question():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    subjects = conn.execute("""
        SELECT DISTINCT subject
        FROM resources
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''
        ORDER BY subject
    """).fetchall()

    conn.close()

    return render_template(
        "ask_question.html",
        subjects=subjects
    )

@app.route('/edit-question/<int:id>')
def edit_question(id):

    conn = get_db_connection()

    question = conn.execute("""
        SELECT *
        FROM questions
        WHERE id = ?
    """,(id,)).fetchone()

    if question["created_by"] != session["user_id"]:
        conn.close()
        flash("Permission denied")
        return redirect(url_for('questions'))

    conn.close()

    return render_template(
        "edit_question.html",
        question=question
    )

@app.route('/update-question/<int:id>', methods=['POST'])
def update_question(id):

    conn = get_db_connection()

    question = conn.execute("""
        SELECT *
        FROM questions
        WHERE id = ?
    """,(id,)).fetchone()

    if question["created_by"] != session["user_id"]:
        conn.close()
        return redirect(url_for('questions'))

    conn.execute("""
        UPDATE questions
        SET title = ?,
            content = ?
        WHERE id = ?
    """,
    (
        request.form["title"],
        request.form["content"],
        id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('questions'))

@app.route('/delete-question/<int:id>')
def delete_question(id):

    conn = get_db_connection()

    question = conn.execute("""
        SELECT *
        FROM questions
        WHERE id = ?
    """,(id,)).fetchone()

    if question["created_by"] != session["user_id"]:
        conn.close()
        return redirect(url_for('questions'))

    conn.execute("""
        DELETE FROM answers
        WHERE question_id = ?
    """,(id,))

    conn.execute("""
        DELETE FROM questions
        WHERE id = ?
    """,(id,))

    conn.commit()
    conn.close()

    return redirect(url_for('questions'))

@app.route('/get-topics/<subject>')
def get_topics(subject):

    conn = get_db_connection()

    topics = conn.execute("""
        SELECT id, title
        FROM resources
        WHERE subject = ?
        ORDER BY title
    """, (subject,)).fetchall()

    conn.close()

    return jsonify([
        {
            "id": row["id"],
            "title": row["title"]
        }
        for row in topics
    ])

@app.route('/add-question', methods=['POST'])
def add_question():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    resource_id = request.form['resource_id']
    title = request.form['title']
    content = request.form['content']

    conn = get_db_connection()

    resource = conn.execute("""
        SELECT subject, title
        FROM resources
        WHERE id = ?
    """, (resource_id,)).fetchone()

    if resource is None:
        conn.close()
        flash("Topic not found.")
        return redirect(url_for('ask_question'))

    subject = resource["subject"]
    topic = resource["title"]

    conn.execute("""
        INSERT INTO questions
        (
            subject,
            topic,
            resource_id,
            title,
            content,
            created_by
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """,
    (
        subject,
        topic,
        resource_id,
        title,
        content,
        session['user_id']
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('questions'))

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
        conn = get_db_connection()

        if query:

           resources = conn.execute(
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
            ).fetchall()

        else:

            resources = conn.execute(
                f"SELECT * FROM resources WHERE subject=? ORDER BY {order_by}",
                (subject_name,)
            ).fetchall()

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
        conn = get_db_connection()

        resource = conn.execute(
            """
            SELECT file_name, uploaded_by
            FROM resources
            WHERE id=?
            """,
            (id,)
        ).fetchone()


        if resource is None:
            conn.close()
            return "Resource not found"

        if resource[1] != session['user_id']:
            conn.close()
            flash("You are not allowed to delete this resource.")
            return redirect(url_for('resources_list'))

        if resource and resource[0]:
            filepath = os.path.join(
                app.config['UPLOAD_FOLDER'],
                resource[0]
            )

            if os.path.exists(filepath):
                os.remove(filepath)

        conn.execute(
            "DELETE FROM resources WHERE id=?",
            (id,)
        )

        conn.commit()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return redirect(url_for('resources_list'))

@app.route('/upvote/<int:id>')
def upvote_resource(id):

    conn = get_db_connection()

    conn.execute(
        """
        UPDATE resources
        SET upvotes = upvotes + 1
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(request.referrer)

@app.route('/downvote/<int:id>')
def downvote_resource(id):

    conn = get_db_connection()

    conn.execute(
        """
        UPDATE resources
        SET downvotes = downvotes + 1
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(request.referrer)

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):

    flash(
        "File size exceeds 16 MB limit.",
        "danger"
    )

    return redirect(url_for('resources'))

@app.route('/dashboard')
def dashboard():
    # 1. 检查用户是否已登录 (必须要有，否则下面获取 user_id 会报错)
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    conn = get_db_connection()
    c = conn.cursor()

    # 2. 保留你原本的逻辑：获取全站所有资源总数 (保留以防你原本的 HTML 里还有用到)
    c.execute("SELECT COUNT(*) FROM resources")
    total_resources = c.fetchone()[0]

    # 3. 新增：计算【当前用户】上传的资源总数
    c.execute("SELECT COUNT(*) FROM resources WHERE uploaded_by = ?", (user_id,))
    resources_uploaded_count = c.fetchone()[0]

    # 4. 新增：计算【当前用户】相关的 Session 数量
    # (目前计算的是用户创建的 Session，因为数据库当前没有追踪具体的参与者)
    c.execute("SELECT COUNT(*) FROM sessions WHERE created_by = ?", (str(user_id),))
    sessions_joined_count = c.fetchone()[0]

    conn.close()

    # 5. 将这三个变量一起传给前端
    return render_template(
        "dashboard.html", 
        total_resources=total_resources,
        resources_uploaded_count=resources_uploaded_count,
        sessions_joined_count=sessions_joined_count
    )

# 下面这个保持原样即可
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
