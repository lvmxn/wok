import sqlite3
from flask import redirect, session
from functools import wraps
import translators as ts
from datetime import date, timedelta

RANDOM_WORD_START_COUNT = 50


class TranslationError(RuntimeError):
    pass


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    def execute(self, query, *args):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, args)
            if cursor.description is not None:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return cursor.rowcount


def translate(word):
    ts_list = ["google", "yandex", "bing", "deepl"]
    has_cyr = any("а" <= ch <= "я" or ch == "ё" or ch == " " for ch in word)
    has_lat = any("a" <= ch <= "z" or ch == " " for ch in word)
    f_lang = ""
    t_lang = ""

    if has_cyr and not has_lat:
        f_lang = "ru"
        t_lang = "en"
    elif has_lat and not has_cyr:
        f_lang = "en"
        t_lang = "ru"
    else:
        raise TranslationError("Unsupported word language")

    last_error = None
    for i in ts_list:
        try:
            result = ts.translate_text(
                word, translator=i, from_language=f_lang, to_language=t_lang
            )
            return result
        except Exception as error:
            last_error = error

    if last_error is None:
        raise TranslationError("Translation failed")
    raise last_error


def now():
    return date.today().strftime("%Y-%m-%d")


def next_r(interval):
    new_date = date.today() + timedelta(days=interval)
    return new_date.strftime("%Y-%m-%d")


def start(db, user_id):
    db.execute(
        """
        INSERT INTO user_words (user_id, next_review, word_id)
        SELECT ?, ?, id FROM words 
        ORDER BY RANDOM() 
        LIMIT ?
    """,
        user_id,
        now(),
        RANDOM_WORD_START_COUNT,
    )
