import os
import sqlite3
from json import dumps
from helpers import (
    Database,
    TranslationError,
    login_required,
    translate,
    start,
    calculate_next_review,
    schedule_review,
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
    send_file,
)
import io
from gtts import gTTS
from werkzeug.security import check_password_hash, generate_password_hash
import secrets


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


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        mode = request.form.get("mode")
        if not mode:
            flash("Mode is required.", "danger")
            return redirect(url_for("profile"))
        session["mode"] = mode
        return redirect(url_for("index"))
    return render_template("profile.html", token=session.get("token"), mode=session.get("mode"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/api/tts')
def get_tts():
    text = request.args.get('word', '')
    if not text:
        return "Missing word", 400
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return send_file(fp, mimetype='audio/mp3')


@app.route("/api/capture_word", methods=["POST"])
def capture_word():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid request body"}), 400
    token = data.get("token")
    word = data.get("word")
    context = data.get("context")
    if not token:
        return jsonify({"status": "error", "message": "Missing token"}), 400
    if not word:
        return jsonify({"status": "error", "message": "Missing word"}), 400
    if isinstance(context, str):
        context = context.strip()
    if not context:
        context = None
    try:
        user_rows = db.execute(
            "SELECT id FROM users WHERE token = ?",
            token,
        )
    except sqlite3.Error:
        return jsonify({"status": "error", "message": "Api is temporarily unavailable"}), 500
    if not user_rows:
        return jsonify({"status": "error", "message": "Invalid token"}), 401
    id = user_rows[0]["id"]
    w = word.strip().lower()
    try:
        q = translate(w)
    except TranslationError:
        return jsonify({"status": "error", "message": "Could not translate word"}), 422
    w = q[0]
    translation = q[1]
    try:
        word_id = db.execute(
            """
            INSERT INTO words (word, translation)
            VALUES (?, ?)
            ON CONFLICT(word, translation) DO UPDATE SET
                translation = excluded.translation
            RETURNING id
            """,
            w, translation,
        )[0]["id"]
        db.execute(
            """
            INSERT INTO user_words (user_id, word_id, context, next_review, learning, repetitions, lapses)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, word_id) DO UPDATE SET
                context = CASE 
                    WHEN EXCLUDED.context IS NOT NULL THEN EXCLUDED.context 
                    ELSE user_words.context 
                END
            """,
            id,
            word_id,
            context,
            calculate_next_review(0),
            2,
            0,
            0,
        )
    except (TranslationError, sqlite3.Error):
        return jsonify({"status": "error", "message": "Failed to save word"}), 500
        
    return jsonify({"status": "success", "word": w, "translation": translation}), 200

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
        starter = request.form.get("starter") == 'true'
        token = secrets.token_urlsafe(32)
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
                "INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)",
                username,
                password_hash,
                token,
            )
            session["user_id"] = db.execute(
                "SELECT id FROM users WHERE username = ?", username
            )[0]["id"]
            session["token"] = token
            session["mode"] = "en"
            if starter:
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
                "SELECT id, password_hash, token FROM users WHERE username = ?",
                username,
            )
        except sqlite3.Error:
            flash("Login is temporarily unavailable.", "danger")
            return redirect(url_for("login"))
        if not user_rows or not check_password_hash(
            user_rows[0]["password_hash"], password
        ):
            flash("Invalid username and/or password.", "danger")
            return redirect(url_for("login"))
        session["user_id"] = user_rows[0]["id"]
        session["token"] = user_rows[0]["token"]
        session["mode"] = "en"
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
    free = request.args.get('mode') == "free"

    if request.method == "POST":
        if free:
            return jsonify({"status": "success", "message": "Free mode: review not saved"}), 200
        data_j = request.get_json()
        if not isinstance(data_j, dict):
            return jsonify({"status": "error", "message": "Invalid request body"}), 400
        id = data_j.get("id")
        quality = data_j.get("quality")
        try:
            data_db = db.execute(
                "SELECT ease_factor, interval, learning, repetitions, lapses FROM user_words WHERE user_id = ? AND word_id = ?",
                session["user_id"],
                id,
            )
        except sqlite3.Error:
            return (
                jsonify({"status": "error", "message": "Could not update review"}),
                500,
            )
        if not data_db:
            return jsonify({"status": "error", "message": "Word not found"}), 404

        ease_factor, interval, learning, repetitions, lapses, next_review = schedule_review(
            data_db[0]["ease_factor"],
            data_db[0]["interval"],
            data_db[0]["learning"],
            data_db[0]["repetitions"],
            data_db[0]["lapses"],
            quality,
        )

        try:
            db.execute(
                "UPDATE user_words SET ease_factor = ?, interval = ?, learning = ?, repetitions = ?, lapses = ?, next_review = ?, count = count + 1 WHERE user_id = ? AND word_id = ?",
                ease_factor,
                interval,
                learning,
                repetitions,
                lapses,
                next_review,
                session["user_id"],
                id,
            )
        except sqlite3.Error:
            return jsonify({"status": "error", "message": "Could not save review"}), 500
        return jsonify({"status": "success"}), 200
    if not free:
        words = db.execute(
            """SELECT 
                w.id, 
                w.word, 
                w.translation,
                uw.context AS context
                FROM words w
                JOIN user_words uw ON w.id = uw.word_id
                WHERE uw.user_id = ? 
                AND uw.next_review <= ?
                AND w.language = ?
                ORDER BY uw.next_review ASC
                LIMIT 20""",
            session["user_id"],
            calculate_next_review(0),
            session["mode"],
        )
    else:
        words = db.execute(
            """SELECT 
                w.id, 
                w.word, 
                w.translation,
                uw.context AS context
                FROM words w
                JOIN user_words uw ON w.id = uw.word_id
                WHERE uw.user_id = ?
                AND w.language = ?
                ORDER BY RANDOM()
                LIMIT 20""",
            session["user_id"],
            session["mode"],
        )
    return render_template("flashcards.html", words=dumps(words))


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        word = request.form.get("word")
        translation = request.form.get("translation")
        context = request.form.get("context")
        if not word:
            flash("Word field is required.", "danger")
            return redirect(url_for("add"))
        w = word.strip().lower()
        try:
            if not translation:
                q = translate(w, session["mode"])
                w = q[0]
                translation = q[1]
            if not context:  
                context = None
            word_id = db.execute(
                """
                INSERT INTO words (word, translation, language)
                VALUES (?, ?, ?)
                ON CONFLICT(word, translation, language) DO UPDATE SET
                    translation = excluded.translation
                RETURNING id
                """,
                w, translation, session["mode"],
            )[0]["id"]
            db.execute(
                """
                INSERT INTO user_words (user_id, word_id, context, next_review, learning, repetitions, lapses)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word_id) DO UPDATE SET
                    context = CASE 
                        WHEN EXCLUDED.context IS NOT NULL THEN EXCLUDED.context 
                        ELSE user_words.context 
                    END
                """,
                session["user_id"],
                word_id,
                context,
                calculate_next_review(0),
                2,
                0,
                0,
            )
        except (TranslationError, sqlite3.Error):
            flash("Could not add that word right now.", "danger")
            return redirect(url_for("add"))
        return render_template("add.html", word=w, translation=translation)
    return render_template("add.html")


@app.route("/my_words", methods=["GET", "POST"])
@login_required
def my_words():
    if request.method == "POST":
        data_j = request.get_json()
        if not isinstance(data_j, dict):
            return jsonify({"status": "error", "message": "Invalid request body"}), 400
        id = data_j.get("id")
        try:
            data_db = db.execute(
                "DELETE FROM user_words WHERE user_id = ? AND word_id = ?",
                session["user_id"],
                id,
            )
        except sqlite3.Error:
            return (
                jsonify({"status": "error", "message": "Could not delete word"}),
                500,
            )
        return jsonify({"status": "success", "message": "Word deleted successfully"}), 200
    words = db.execute(
        """SELECT 
        w.word,
        w.id,
        w.translation, 
        uw.next_review,
        uw.count               
        FROM words w
        JOIN user_words uw ON w.id = uw.word_id
        WHERE uw.user_id = ?
        AND w.language = ?
        ORDER BY uw.next_review ASC""",
        session["user_id"],
        session["mode"],
    )
    return render_template("my_words.html", words=words)


if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000, debug=True)