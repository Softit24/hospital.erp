import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "hospital.db"

def setup_users():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    user = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if user:
        print("Admin account already exists.")
    else:
        password = input("Create Admin password (12+ characters): ")

        if len(password) < 12:
            print("Password must be at least 12 characters.")
        else:
            conn.execute(
                """INSERT INTO users
                   (username, password_hash, role)
                   VALUES (?, ?, ?)""",
                (
                    "admin",
                    generate_password_hash(password),
                    "Admin"
                )
            )
            conn.commit()
            print("Admin account created successfully.")

    conn.close()

if __name__ == "__main__":
    setup_users()
