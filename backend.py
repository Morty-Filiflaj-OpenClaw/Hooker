from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import sqlite3
import datetime
import json

app = FastAPI(title="Hooker API", description="Systematic Task Management for Hardware Engineers")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Database ---
DB_FILE = "hooker.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Check if we need to migrate/add columns (simple approach: create if not exists)
    # For a real app, use Alembic. Here, we might just drop/recreate for dev speed if schema changes drastically
    # or use IF NOT EXISTS.
    # Updated schema:
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  status TEXT DEFAULT 'TODO',
                  assignee TEXT,
                  priority TEXT DEFAULT 'NORMAL',
                  tags TEXT,
                  due_date TEXT,
                  created_at TEXT,
                  updated_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Models ---
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    assignee: Optional[str] = "Unassigned"
    priority: Optional[str] = "NORMAL"
    tags: Optional[List[str]] = []
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[str] = None

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    assignee: Optional[str]
    priority: str
    tags: List[str]
    due_date: Optional[str]
    created_at: str
    updated_at: str

# --- Routes ---
@app.get("/")
def read_root():
    return {"message": "Welcome to Hooker API. Visit /static/index.html for the board."}

@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    tags_json = json.dumps(task.tags)
    
    c.execute("""INSERT INTO tasks 
                 (title, description, status, assignee, priority, tags, due_date, created_at, updated_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (task.title, task.description, "TODO", task.assignee, task.priority, tags_json, task.due_date, now, now))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return {
        **task.dict(), 
        "id": task_id, 
        "status": "TODO", 
        "created_at": now, 
        "updated_at": now
    }

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
    
    tasks = []
    for row in rows:
        r = dict(row)
        # Parse JSON tags safely
        try:
            r['tags'] = json.loads(r['tags']) if r['tags'] else []
        except:
            r['tags'] = []
        tasks.append(r)
        
    return tasks

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
        
    r = dict(row)
    try:
        r['tags'] = json.loads(r['tags']) if r['tags'] else []
    except:
        r['tags'] = []
    return r

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
    
    if task.title is not None: updates.append("title = ?"); params.append(task.title)
    if task.description is not None: updates.append("description = ?"); params.append(task.description)
    if task.status is not None: updates.append("status = ?"); params.append(task.status)
    if task.assignee is not None: updates.append("assignee = ?"); params.append(task.assignee)
    if task.priority is not None: updates.append("priority = ?"); params.append(task.priority)
    if task.due_date is not None: updates.append("due_date = ?"); params.append(task.due_date)
    if task.tags is not None: 
        updates.append("tags = ?")
        params.append(json.dumps(task.tags))
    
    updates.append("updated_at = ?"); params.append(now)
    params.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    c.execute(query, params)
    conn.commit()
    
    # Return updated
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_row = c.fetchone()
    conn.close()
    
    r = dict(updated_row)
    try:
        r['tags'] = json.loads(r['tags']) if r['tags'] else []
    except:
        r['tags'] = []
    return r

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    conn.close()
    return {"status": "success", "message": "Task deleted"}
