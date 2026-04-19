import sqlite3
import json

def seed_db(db_path='database.db'):
    with open('seed_words.json', encoding='utf-8') as f:
        words = json.load(f)
    with sqlite3.connect(db_path) as conn:
        for word in words:
            conn.execute("INSERT INTO words (word, translation) VALUES(?, ?)",(word["word"],word["translation"]))
        conn.commit()
        print(f"Database seeded: {db_path}")

if __name__ == "__main__":
    seed_db()
