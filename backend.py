from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import datetime
import json
import secrets

app = FastAPI(title="Hooker API", description="Systematic Task Management for Hardware Engineers")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/index.html")

DB_FILE = "hooker.db"

# API Key storage (in production, use env vars or secure storage)
VALID_API_KEYS = {
    "demo_key_123": "demo_user",
    "": "anonymous"  # Allow empty key for backward compatibility
}

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Simple API key verification"""
    if x_api_key in VALID_API_KEYS or x_api_key is None or x_api_key == "":
        return VALID_API_KEYS.get(x_api_key, "anonymous")
    raise HTTPException(status_code=401, detail="Invalid API key")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tasks table with additional fields
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  status TEXT DEFAULT 'TODO',
                  assignee TEXT,
                  priority TEXT DEFAULT 'NORMAL',
                  tags TEXT,
                  due_date TEXT,
                  recurring INTEGER DEFAULT 0,
                  recurrence TEXT,
                  created_at TEXT,
                  updated_at TEXT)''')
    
    # Components table
    c.execute('''CREATE TABLE IF NOT EXISTS components 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  part_number TEXT NOT NULL, 
                  description TEXT, 
                  stock INTEGER DEFAULT 0, 
                  datasheet_url TEXT, 
                  tags TEXT, 
                  created_at TEXT)''')
    
    # Webhooks table
    c.execute('''CREATE TABLE IF NOT EXISTS webhooks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT NOT NULL,
                  events TEXT,
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
    recurring: Optional[bool] = False
    recurrence: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[str] = None
    recurring: Optional[bool] = None
    recurrence: Optional[str] = None

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    assignee: Optional[str]
    priority: str
    tags: List[str]
    due_date: Optional[str]
    recurring: bool
    recurrence: Optional[str]
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

class WebhookCreate(BaseModel):
    url: str
    events: List[str] = []

class Webhook(BaseModel):
    id: int
    url: str
    events: List[str]
    created_at: str

# --- Routes: TASKS ---
@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate, user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    tags_json = json.dumps(task.tags)
    
    c.execute("""INSERT INTO tasks (title, description, status, assignee, priority, tags, due_date, recurring, recurrence, created_at, updated_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (task.title, task.description, "TODO", task.assignee, task.priority, 
               tags_json, task.due_date, int(task.recurring or 0), task.recurrence, now, now))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    
    result = {**task.dict(), "id": tid, "status": "TODO", "created_at": now, "updated_at": now}
    trigger_webhooks("task_created", result)
    
    return result

@app.get("/tasks", response_model=List[Task])
def list_tasks(status: Optional[str] = None, user: str = Depends(verify_api_key)):
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
        r['recurring'] = bool(r.get('recurring', 0))
        tasks.append(r)
    return tasks

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskUpdate, user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    updates = []; params = []
    if task.title: updates.append("title = ?"); params.append(task.title)
    if task.description is not None: updates.append("description = ?"); params.append(task.description)
    if task.status: updates.append("status = ?"); params.append(task.status)
    if task.assignee: updates.append("assignee = ?"); params.append(task.assignee)
    if task.priority: updates.append("priority = ?"); params.append(task.priority)
    if task.due_date is not None: updates.append("due_date = ?"); params.append(task.due_date)
    if task.tags is not None: updates.append("tags = ?"); params.append(json.dumps(task.tags))
    if task.recurring is not None: updates.append("recurring = ?"); params.append(int(task.recurring))
    if task.recurrence is not None: updates.append("recurrence = ?"); params.append(task.recurrence)
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
    r['recurring'] = bool(r.get('recurring', 0))
    
    trigger_webhooks("task_updated", r)
    
    return r

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    
    trigger_webhooks("task_deleted", {"id": task_id})
    
    return {"status": "success"}

# --- Routes: COMPONENTS ---
@app.post("/components", response_model=Component)
def create_component(comp: ComponentCreate, user: str = Depends(verify_api_key)):
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
def list_components(user: str = Depends(verify_api_key)):
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
def delete_component(comp_id: int, user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM components WHERE id = ?", (comp_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- Routes: WEBHOOKS ---
@app.post("/webhooks", response_model=Webhook)
def create_webhook(webhook: WebhookCreate, user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    events_json = json.dumps(webhook.events)
    c.execute("""INSERT INTO webhooks (url, events, created_at) VALUES (?, ?, ?)""",
              (webhook.url, events_json, now))
    wid = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": wid, "url": webhook.url, "events": webhook.events, "created_at": now}

@app.get("/webhooks", response_model=List[Webhook])
def list_webhooks(user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM webhooks")
    rows = c.fetchall()
    conn.close()
    webhooks = []
    for row in rows:
        r = dict(row)
        try: r['events'] = json.loads(r['events']) if r['events'] else []
        except: r['events'] = []
        webhooks.append(r)
    return webhooks

@app.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, user: str = Depends(verify_api_key)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

def trigger_webhooks(event: str, data: dict):
    """Trigger registered webhooks (simplified - in production use async/queue)"""
    import requests
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM webhooks")
    webhooks = c.fetchall()
    conn.close()
    
    for wh in webhooks:
        try:
            events = json.loads(wh['events']) if wh['events'] else []
            if not events or event in events:
                payload = {"event": event, "data": data, "timestamp": datetime.datetime.utcnow().isoformat()}
                requests.post(wh['url'], json=payload, timeout=5)
        except Exception as e:
            print(f"Webhook error: {e}")

# --- API Key Management ---
@app.get("/api-keys/generate")
def generate_api_key(user: str = Depends(verify_api_key)):
    """Generate a new API key"""
    new_key = secrets.token_urlsafe(32)
    # In production, store this in database
    return {"api_key": new_key, "note": "Store this key securely"}
