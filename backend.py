from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import datetime

app = FastAPI(title="Hooker API", description="Systematic Task Management for Hardware Engineers")

# --- Database ---
DB_FILE = "hooker.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  status TEXT DEFAULT 'TODO',
                  assignee TEXT,
                  priority TEXT DEFAULT 'NORMAL',
                  created_at TEXT,
                  updated_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Models ---
class TaskCreate(BaseModel):
    title: str
    assignee: Optional[str] = None
    priority: Optional[str] = "NORMAL"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None

class Task(BaseModel):
    id: int
    title: str
    status: str
    assignee: Optional[str]
    priority: str
    created_at: str
    updated_at: str

# --- Routes ---
@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute("INSERT INTO tasks (title, status, assignee, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
              (task.title, "TODO", task.assignee, task.priority, now, now))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return {**task.dict(), "id": task_id, "status": "TODO", "created_at": now, "updated_at": now}

@app.get("/tasks", response_model=List[Task])
def list_tasks(status: Optional[str] = None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT * FROM tasks"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskUpdate):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Check if exists
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    existing = c.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    updates = []
    params = []
    now = datetime.datetime.utcnow().isoformat()
    
    if task.title: updates.append("title = ?"); params.append(task.title)
    if task.status: updates.append("status = ?"); params.append(task.status)
    if task.assignee: updates.append("assignee = ?"); params.append(task.assignee)
    if task.priority: updates.append("priority = ?"); params.append(task.priority)
    
    updates.append("updated_at = ?"); params.append(now)
    params.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    c.execute(query, params)
    conn.commit()
    
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_row = c.fetchone()
    conn.close()
    return dict(updated_row)
