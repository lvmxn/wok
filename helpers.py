import sqlite3
from math import ceil
from flask import redirect, session
from functools import wraps
import translators as ts
from datetime import datetime, timedelta

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
    return datetime.now().replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")


def next_r(interval):
    new_date = datetime.now() + timedelta(days=interval)
    return new_date.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")


def next_minutes(minutes):
    new_date = datetime.now() + timedelta(minutes=minutes)
    return new_date.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")


def start(db, user_id):
    db.execute(
        """
        INSERT INTO user_words (user_id, next_review, word_id, learning, repetitions, lapses)
        SELECT ?, ?, id, 2, 0, 0 FROM words 
        ORDER BY RANDOM() 
        LIMIT ?
    """,
        user_id,
        next_minutes(1),
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
        next_interval = 1
        next_learning = 2
        next_repetitions = 0
        next_lapses += 1
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            next_minutes(1),
        )

    if learning == 2:
        if quality == "hard":
            next_ease = max(1.3, round(next_ease - 0.05, 2))
            next_interval = 1
            next_learning = 2
            return (
                next_ease,
                next_interval,
                next_learning,
                next_repetitions + 1,
                next_lapses,
                next_minutes(1),
            )

        next_interval = 10
        next_learning = 1
        next_repetitions += 1
        if quality == "easy":
            next_ease = round(next_ease + 0.15, 2)
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            next_minutes(10),
        )

    if learning == 1:
        if quality == "hard":
            next_ease = max(1.3, round(next_ease - 0.05, 2))
            next_interval = 10
            return (
                next_ease,
                next_interval,
                1,
                next_repetitions + 1,
                next_lapses,
                next_minutes(10),
            )

        next_interval = 1
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
            next_r(1),
        )

    if quality == "hard":
        next_ease = max(1.3, round(next_ease - 0.15, 2))
        next_interval = max(1, round(next_interval * 1.2))
    elif quality == "normal":
        next_interval = max(1, round(next_interval * next_ease))
    elif quality == "easy":
        next_ease = round(next_ease + 0.15, 2)
        next_interval = max(1, round(next_interval * next_ease * 1.3))

    if next_ease < 1.3:
        next_ease = 1.3
    next_repetitions += 1
    return next_ease, next_interval, 0, next_repetitions, next_lapses, next_r(next_interval)
