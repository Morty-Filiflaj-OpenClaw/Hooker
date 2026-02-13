import sqlite3

def add_columns():
    try:
        conn = sqlite3.connect("Hooker/hooker.db") # Adjusted path relative to workspace
        c = conn.cursor()
        
        # Check existing columns
        c.execute("PRAGMA table_info(tasks)")
        rows = c.fetchall()
        
        if not rows:
            print("Table 'tasks' does not exist yet. It will be created on first run.")
            return

        columns = [row[1] for row in rows]
        
        if 'description' not in columns:
            print("Adding description column...")
            c.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
            
        if 'tags' not in columns:
            print("Adding tags column...")
            c.execute("ALTER TABLE tasks ADD COLUMN tags TEXT")
            
        if 'due_date' not in columns:
            print("Adding due_date column...")
            c.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
            
        conn.commit()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    add_columns()
