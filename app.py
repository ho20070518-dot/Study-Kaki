from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return "Study Kaki is running successfully!"

# Member 2: Study Session Module
@app.route('/sessions')
def sessions():
    return "Study Session module ready"

@app.route('/create_session')
def create_session():
    return "Create session feature coming soon"

@app.route('/join_session')
def join_session():
    return "Join session feature coming soon"

@app.route('/notifications')
def notifications():
    return "Notifications feature coming soon"


if __name__ == '__main__':
    app.run(debug=True)