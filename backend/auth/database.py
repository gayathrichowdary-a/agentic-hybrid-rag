import sqlite3
import os

DB_FOLDER = "database"
DB_PATH = os.path.join(DB_FOLDER, "users.db")


def create_database():
    os.makedirs(DB_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -----------------------------
    # Users Table
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            full_name TEXT NOT NULL,

            username TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # -----------------------------
    # Documents Table
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            file_name TEXT NOT NULL,

            file_path TEXT NOT NULL,

            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id) REFERENCES users(id)

        )
    """)
    # -----------------------------
# Chat History Table
# -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            chat_name TEXT NOT NULL,

            query TEXT NOT NULL,

            answer TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id) REFERENCES users(id)

)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS memory(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    memory TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS profile_memory(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    key TEXT,

    value TEXT,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id) REFERENCES users(id)

)
""")

    conn.commit()
    conn.close()


def get_connection():
    return sqlite3.connect(DB_PATH)