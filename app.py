import os
from helpers import Database
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
db = Database('database.db')
app.secret_key = os.environ.get('SECRET_KEY', '123')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        if not username or not password or not confirmation:
            return render_template('register.html', error="All fields are required.")
        if password != confirmation:
            return render_template('register.html', error="Passwords do not match.")
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return render_template('register.html', error="Username already taken.")
        password_hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", username, password_hash)
        session['user_id'] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]['id']
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.clear()
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('register.html', error="All fields are required.")
        if not check_password_hash(db.execute("SELECT password_hash FROM users WHERE username = ?", username)[0]['password_hash'], password):
            return render_template('register.html', error="Passwords do not match.")
        session['user_id'] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]['id']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
