CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE
);

CREATE TABLE words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    translation TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    UNIQUE(word, translation, language)
);

CREATE TABLE user_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    ease_factor REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 0,
    next_review TEXT,
    count INTEGER DEFAULT 0,
    learning INTEGER DEFAULT 2,
    repetitions INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0,
    context TEXT,
    UNIQUE(user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT DEFAULT 'general',
    UNIQUE(user_id, name),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE user_word_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_word_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    UNIQUE(user_word_id, tag_id),
    FOREIGN KEY (user_word_id) REFERENCES user_words(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);