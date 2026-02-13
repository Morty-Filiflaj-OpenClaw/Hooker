from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import datetime
import json

app = FastAPI(title="Hooker API", description="Systematic Task Management for Hardware Engineers")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

DB_FILE = "hooker.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tasks
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
    # Components
    c.execute('''CREATE TABLE IF NOT EXISTS components 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  part_number TEXT NOT NULL, 
                  description TEXT, 
                  stock INTEGER DEFAULT 0, 
                  datasheet_url TEXT, 
                  tags TEXT, 
                  created_at TEXT)''')
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

class ComponentCreate(BaseModel):
    part_number: str
    description: Optional[str] = ""
    stock: int = 0
    datasheet_url: Optional[str] = ""
    tags: List[str] = []

class Component(BaseModel):
    id: int
    part_number: str
    description: str
    stock: int
    datasheet_url: str
    tags: List[str]
    created_at: str

# --- Routes: TASKS ---
@app.get("/")
def read_root():
    return {"message": "Welcome to Hooker API. Visit /static/index.html"}

@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    tags_json = json.dumps(task.tags)
    c.execute("""INSERT INTO tasks (title, description, status, assignee, priority, tags, due_date, created_at, updated_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (task.title, task.description, "TODO", task.assignee, task.priority, tags_json, task.due_date, now, now))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return {**task.dict(), "id": tid, "status": "TODO", "created_at": now, "updated_at": now}

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
        try: r['tags'] = json.loads(r['tags']) if r['tags'] else []
        except: r['tags'] = []
        tasks.append(r)
    return tasks

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskUpdate):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    updates = []; params = []
    if task.title: updates.append("title = ?"); params.append(task.title)
    if task.description: updates.append("description = ?"); params.append(task.description)
    if task.status: updates.append("status = ?"); params.append(task.status)
    if task.assignee: updates.append("assignee = ?"); params.append(task.assignee)
    if task.priority: updates.append("priority = ?"); params.append(task.priority)
    if task.due_date: updates.append("due_date = ?"); params.append(task.due_date)
    if task.tags is not None: updates.append("tags = ?"); params.append(json.dumps(task.tags))
    updates.append("updated_at = ?"); params.append(datetime.datetime.utcnow().isoformat())
    params.append(task_id)
    
    c.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = c.fetchone()
    conn.close()
    r = dict(updated)
    try: r['tags'] = json.loads(r['tags']) if r['tags'] else []
    except: r['tags'] = []
    return r

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- Routes: COMPONENTS ---
@app.post("/components", response_model=Component)
def create_component(comp: ComponentCreate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    tags_json = json.dumps(comp.tags)
    c.execute("""INSERT INTO components (part_number, description, stock, datasheet_url, tags, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (comp.part_number, comp.description, comp.stock, comp.datasheet_url, tags_json, now))
    cid = c.lastrowid
    conn.commit()
    conn.close()
    return {**comp.dict(), "id": cid, "created_at": now}

@app.get("/components", response_model=List[Component])
def list_components():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM components")
    rows = c.fetchall()
    conn.close()
    comps = []
    for row in rows:
        r = dict(row)
        try: r['tags'] = json.loads(r['tags']) if r['tags'] else []
        except: r['tags'] = []
        comps.append(r)
    return comps

@app.delete("/components/{comp_id}")
def delete_component(comp_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM components WHERE id = ?", (comp_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
