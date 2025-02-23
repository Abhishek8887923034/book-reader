import sqlite3

# Database connection
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Admin Table Create Karna
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')

# Default Admin Insert Karna (Agar pehle se nahi hai)
cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO admin (username, password) VALUES ('admin', 'password123')")
    conn.commit()

conn.close()
print("Database setup complete!")