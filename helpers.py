import sqlite3
from flask import redirect, session
from functools import wraps
import translators as ts


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
            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return cursor.rowcount

def translate(word):        
    query_text = word
    result = ts.translate_text(query_text, translator='bing', from_language='en', to_language='ru')
    return(result)
