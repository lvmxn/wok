import os
import sqlite3
from math import ceil
from json import dumps
from helpers import (
    Database,
    TranslationError,
    login_required,
    translate,
    start,
    now,
    next_r,
)
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
db = Database("database.db")
app.secret_key = os.environ.get("SECRET_KEY", "123")


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", error_code=404, error_message="Not found"), 404


@app.errorhandler(500)
def server_error(error):
    return (
        render_template("error.html", error_code=500, error_message="Server error"),
        500,
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.context_processor
def inject_user():
    if session.get("user_id") is None:
        return {"username": ""}
    try:
        username = db.execute(
            "SELECT username FROM users WHERE id = ?", session["user_id"]
        )[0]["username"]
    except (IndexError, sqlite3.Error):
        username = ""
    return {"username": username}


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        if password != confirmation:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        try:
            existing_user = db.execute(
                "SELECT * FROM users WHERE username = ?", username
            )
            if existing_user:
                flash("Username already taken.", "danger")
                return redirect(url_for("register"))
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
        except sqlite3.Error:
            flash("Could not create your account right now.", "danger")
            return redirect(url_for("register"))
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("login"))
        try:
            user_rows = db.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                username,
            )
        except sqlite3.Error:
            flash("Login is temporarily unavailable.", "danger")
            return redirect(url_for("login"))
        if not user_rows or not check_password_hash(
            user_rows[0]["password_hash"], password
        ):
            flash("Passwords do not match.", "danger")
            return redirect(url_for("login"))
        session["user_id"] = user_rows[0]["id"]
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
        if not isinstance(data_j, dict):
            return jsonify({"status": "error", "message": "Invalid request body"}), 400
        word = data_j.get("word")
        quality = data_j.get("quality")
        try:
            data_db = db.execute(
                "SELECT ease_factor, interval FROM user_words WHERE user_id = ? AND word_id in (SELECT id FROM words WHERE word = ?)",
                session["user_id"],
                word,
            )
        except sqlite3.Error:
            return (
                jsonify({"status": "error", "message": "Could not update review"}),
                500,
            )
        if not data_db:
            return jsonify({"status": "error", "message": "Word not found"}), 404
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
        try:
            db.execute(
                "UPDATE user_words SET ease_factor = ?, interval = ?, next_review = ?, count = count + 1 WHERE user_id = ? AND word_id in (SELECT id FROM words WHERE word = ?)",
                ease_factor,
                interval,
                next_review,
                session["user_id"],
                word,
            )
        except sqlite3.Error:
            return jsonify({"status": "error", "message": "Could not save review"}), 500
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


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        word = request.form.get("word")
        if not word:
            flash("All fields are required.", "danger")
            return redirect(url_for("add"))
        w = word.strip().lower()
        try:
            translation = translate(w)
            word_id = db.execute(
                """INSERT INTO words (word, translation)
                VALUES (?, ?)
                ON CONFLICT(word) DO UPDATE SET word = words.word
                RETURNING id""",
                w,
                translation,
            )[0]["id"]
            db.execute(
                """INSERT INTO user_words (user_id, word_id, next_review)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, word_id) DO NOTHING""",
                session["user_id"],
                word_id,
                now(),
            )
        except (TranslationError, sqlite3.Error):
            flash("Could not add that word right now.", "danger")
            return redirect(url_for("add"))
        return render_template("add.html", word=w, translation=translation)
    return render_template("add.html")


@app.route("/my_words")
@login_required
def my_words():
    words = db.execute(
        """SELECT 
        w.word, 
        w.translation, 
        uw.next_review,
        uw.count               
        FROM words w
        JOIN user_words uw ON w.id = uw.word_id
        WHERE uw.user_id = ? 
        ORDER BY uw.next_review ASC""",
        session["user_id"],
    )
    return render_template("my_words.html", words=words)


if __name__ == "__main__":
    app.run(debug=True)
