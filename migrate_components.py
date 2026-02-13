import sqlite3

def add_components_table():
    try:
        conn = sqlite3.connect("Hooker/hooker.db")
        c = conn.cursor()
        
        c.execute("CREATE TABLE IF NOT EXISTS components (id INTEGER PRIMARY KEY AUTOINCREMENT, part_number TEXT NOT NULL, description TEXT, stock INTEGER DEFAULT 0, datasheet_url TEXT, tags TEXT, created_at TEXT, updated_at TEXT)")
        
        conn.commit()
        conn.close()
        print("Components table added.")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    add_components_table()
