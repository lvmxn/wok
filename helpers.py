import sqlite3
from flask import redirect, session
from functools import wraps
import translators as ts
from datetime import datetime, timedelta

RANDOM_WORD_START_COUNT = 40
DAY = 86400


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
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            cursor.execute(query, args)
            if cursor.description is not None:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return cursor.rowcount


def translate(word, lang):
    ts_list = ["google", "yandex", "bing", "deepl"]
    word = word.strip().lower()
    has_cyr = any("а" <= ch <= "я" or ch == "ё" for ch in word)
    f_lang = ""
    t_lang = ""

    if has_cyr:
        f_lang = "ru"
        t_lang = lang
    else:
        f_lang = lang
        t_lang = "ru"

    last_error = None
    for i in ts_list:
        try:
            result = ts.translate_text(
                word, translator=i, from_language=f_lang, to_language=t_lang
            )
            if f_lang == "ru":
                return [result, word]
            else:
                return [word, result]
        except Exception as error:
            last_error = error

    if last_error is None:
        raise TranslationError("Translation failed")
    raise last_error


def calculate_next_review(interval_seconds):
    now = datetime.now().replace(second=0, microsecond=0)
    next_date = now + timedelta(seconds=interval_seconds)
    if interval_seconds >= 86400:
        return next_date.replace(hour=4, minute=0)
    return next_date


def start(db, user_id):
    db.execute(
        """
        INSERT INTO user_words (user_id, next_review, word_id, learning, repetitions, lapses)
        SELECT ?, ?, id, 2, 0, 0 FROM words
        WHERE id <= 500
        ORDER BY RANDOM() 
        LIMIT ? 
    """,
        user_id,
        calculate_next_review(0),
        RANDOM_WORD_START_COUNT,
    )


def schedule_review(ease_factor, interval, learning, repetitions, lapses, quality):
    next_ease = ease_factor
    next_interval = interval
    next_learning = learning
    next_repetitions = repetitions
    next_lapses = lapses

    if quality == "forgot":
        next_ease = max(1.3, round(next_ease - 0.2, 2))
        next_learning = 2
        next_repetitions = 0
        next_lapses += 1
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            calculate_next_review(0),
        )

    if learning == 2:
        if quality == "hard":
            next_ease = max(1.3, round(next_ease - 0.05, 2))
            next_learning = 2
            return (
                next_ease,
                next_interval,
                next_learning,
                next_repetitions + 1,
                next_lapses,
                calculate_next_review(30 * 60),
            )

        if quality == "easy":
            next_ease = round(next_ease + 0.15, 2)
            next_learning = 0
            next_repetitions += 1
            if interval >= 10 * DAY:
                next_interval = 5 * DAY
            else:
                next_interval = 24 * DAY
            return (
                next_ease,
                next_interval,
                next_learning,
                next_repetitions,
                next_lapses,
                calculate_next_review(next_interval),
            )

        next_learning = 1
        next_repetitions += 1
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            calculate_next_review(30 * 60),
        )

    if learning == 1:
        if quality == "hard":
            next_ease = max(1.3, round(next_ease - 0.05, 2))
            return (
                next_ease,
                next_interval,
                1,
                next_repetitions + 1,
                next_lapses,
                calculate_next_review(30 * 60),
            )

        if interval >= 10 * DAY:
            next_interval = 5 * DAY
        else:
            next_interval = DAY
        next_learning = 0
        next_repetitions += 1
        if quality == "easy":
            next_ease = round(next_ease + 0.15, 2)
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            calculate_next_review(next_interval),
        )

    if quality == "hard":
        next_ease = max(1.3, round(next_ease - 0.15, 2))
        next_interval = max(1, round((next_interval // DAY) * 1.2)) * DAY
    elif quality == "normal":
        next_interval = max(1, round((next_interval // DAY) * next_ease)) * DAY
    elif quality == "easy":
        next_ease = round(next_ease + 0.15, 2)
        next_interval = max(1, round((next_interval // DAY) * next_ease * 1.3)) * DAY

    if next_ease < 1.3:
        next_ease = 1.3
    next_repetitions += 1
    return (
        next_ease,
        next_interval,
        0,
        next_repetitions,
        next_lapses,
        calculate_next_review(next_interval),
    )
