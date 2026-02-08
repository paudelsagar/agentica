import os
import sqlite3


def create_sample_db():
    db_path = "data/chinook.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Users table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """
    )

    # Insert sample data
    users = [
        (1, "Alice", "alice@example.com", "admin"),
        (2, "Bob", "bob@example.com", "user"),
        (3, "Charlie", "charlie@example.com", "user"),
        (4, "David", "david@example.com", "user"),
        (5, "Eve", "eve@example.com", "admin"),
    ]

    cursor.executemany("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", users)

    # Create Orders table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        product TEXT,
        amount REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """
    )

    orders = [
        (101, 1, "Laptop", 1200.00),
        (102, 2, "Mouse", 25.00),
        (103, 1, "Monitor", 300.00),
        (104, 3, "Keyboard", 50.00),
    ]

    cursor.executemany("INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print(f"Sample database created at {db_path}")


if __name__ == "__main__":
    create_sample_db()
