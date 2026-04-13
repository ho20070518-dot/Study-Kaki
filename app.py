from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return "Study Kaki is running successfully!"

if __name__ == '__main__':
    app.run(debug=True)