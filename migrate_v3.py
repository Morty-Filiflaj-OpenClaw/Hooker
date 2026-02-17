#!/usr/bin/env python3
"""
Migration script for Hooker v3
Creates activity_log and subagents tables
"""

import sqlite3
import sys

DB_FILE = "hooker.db"

def migrate():
    """Run migrations"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    print("🔄 Running Hooker v3 migrations...")
    
    try:
        # Activity Log table
        c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                     (id TEXT PRIMARY KEY,
                      timestamp TEXT NOT NULL,
                      actor TEXT NOT NULL,
                      action TEXT NOT NULL,
                      status TEXT DEFAULT 'pending',
                      description TEXT,
                      duration_ms INTEGER DEFAULT 0,
                      metadata TEXT,
                      created_at TEXT)''')
        print("✅ Created activity_log table")
        
        # Sub-agents tracking table
        c.execute('''CREATE TABLE IF NOT EXISTS subagents
                     (id TEXT PRIMARY KEY,
                      name TEXT NOT NULL,
                      status TEXT DEFAULT 'spawned',
                      started_at TEXT NOT NULL,
                      completed_at TEXT,
                      stdout TEXT,
                      stderr TEXT,
                      created_at TEXT)''')
        print("✅ Created subagents table")
        
        # Analytics snapshots table (for future)
        c.execute('''CREATE TABLE IF NOT EXISTS analytics_snapshots
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT UNIQUE NOT NULL,
                      tasks_completed INTEGER DEFAULT 0,
                      avg_completion_time_ms INTEGER DEFAULT 0,
                      total_activities INTEGER DEFAULT 0,
                      agents_active TEXT,
                      most_active_agent TEXT,
                      errors_count INTEGER DEFAULT 0,
                      created_at TEXT)''')
        print("✅ Created analytics_snapshots table")
        
        conn.commit()
        print("\n✅ Migration complete! Ready for Hooker v3")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
