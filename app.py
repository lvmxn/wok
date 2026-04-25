import os
from math import ceil
from json import dumps
from helpers import Database, login_required, translate, start, now, next_r
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
db = Database("database.db")
app.secret_key = os.environ.get("SECRET_KEY", "123")


@app.route("/")
def index():
    try:
        username = db.execute(
            "SELECT username FROM users WHERE id = ?", session["user_id"]
        )[0]["username"]
    except:
        username = ""
    return render_template("index.html", username=username)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            return render_template("register.html", error="All fields are required.")
        if password != confirmation:
            return render_template("register.html", error="Passwords do not match.")
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return render_template("register.html", error="Username already taken.")
        password_hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            username,
            password_hash,
        )
        session["user_id"] = db.execute(
            "SELECT id FROM users WHERE username = ?", username
        )[0]["id"]
        start(db, session["user_id"])
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return render_template("register.html", error="All fields are required.")
        if not check_password_hash(
            db.execute("SELECT password_hash FROM users WHERE username = ?", username)[
                0
            ]["password_hash"],
            password,
        ):
            return render_template("register.html", error="Passwords do not match.")
        session["user_id"] = db.execute(
            "SELECT id FROM users WHERE username = ?", username
        )[0]["id"]
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/tasks")
@login_required
def tasks():
    return render_template("tasks.html")


@app.route("/flashcards", methods=["GET", "POST"])
@login_required
def flashcards():
    if request.method == "POST":
        data_j = request.get_json()
        word = data_j.get("word")
        quality = data_j.get("quality")
        data_db = db.execute(
            "SELECT ease_factor, interval FROM user_words WHERE user_id = ? AND word_id in (SELECT id FROM words WHERE word = ?)",
            session["user_id"],
            word,
        )
        ease_factor = data_db[0]["ease_factor"]
        interval = data_db[0]["interval"]
        match quality:
            case "forgot":
                ease_factor -= 0.2
                interval = 1
            case "hard":
                ease_factor -= 0.15
                interval *= 1.2
            case "normal":
                interval *= ease_factor
            case "easy":
                ease_factor += 0.15
                interval *= ease_factor * 1.3
        ease_factor = round(ease_factor, 2)
        if ease_factor < 1.3:
            ease_factor = 1.3
        if interval < 4:
            interval = max(1, round(interval))
        else:
            interval = max(1, ceil(interval))
        next_review = next_r(interval)
        db.execute(
            "UPDATE user_words SET ease_factor = ?, interval = ?, next_review = ? WHERE user_id = ? AND word_id in (SELECT id FROM words WHERE word = ?)",
            ease_factor,
            interval,
            next_review,
            session["user_id"],
            word
        )
        return jsonify({"status": "success"}), 200
    words = db.execute(
        """SELECT 
            w.id, 
            w.word, 
            w.translation 
            FROM words w
            JOIN user_words uw ON w.id = uw.word_id
            WHERE uw.user_id = ? 
            AND uw.next_review <= ?
            ORDER BY uw.next_review ASC
            LIMIT 50""",
        session["user_id"],
        now(),
    )
    return render_template("flashcards.html", words=dumps(words))


if __name__ == "__main__":
    app.run(debug=True)
