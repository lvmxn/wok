import sqlite3

def init_db(db_path='database.db'):
    with open('schema.sql', encoding='utf-8') as f:
        schema = f.read()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
        print(f"Database initialized: {db_path}")

if __name__ == "__main__":
    init_db()
