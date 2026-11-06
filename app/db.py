import sqlite3
from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS size_charts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    chart_type TEXT NOT NULL CHECK(chart_type IN ('body', 'garment')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS size_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_id INTEGER NOT NULL REFERENCES size_charts(id) ON DELETE CASCADE,
    size_label TEXT NOT NULL,
    measurement TEXT NOT NULL,
    min_cm REAL NOT NULL,
    max_cm REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS size_availability (
    chart_id INTEGER NOT NULL REFERENCES size_charts(id) ON DELETE CASCADE,
    size_label TEXT NOT NULL,
    in_stock INTEGER NOT NULL DEFAULT 1 CHECK(in_stock IN (0, 1)),
    PRIMARY KEY (chart_id, size_label)
);

CREATE TABLE IF NOT EXISTS category_weights (
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    measurement TEXT NOT NULL,
    weight REAL NOT NULL,
    ease_cm REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (category_id, measurement)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    height REAL,
    chest REAL,
    shoulder REAL,
    waist REAL,
    hip REAL,
    inseam REAL
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    chart_id INTEGER NOT NULL REFERENCES size_charts(id) ON DELETE CASCADE,
    size_label TEXT NOT NULL,
    score REAL NOT NULL,
    fit_pref TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_db():
    """Get or create database connection for current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(conn=None):
    """Initialize database tables from SCHEMA."""
    if conn is None:
        conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()

def init_app(app):
    """Register database functions with application."""
    app.teardown_appcontext(close_db)
