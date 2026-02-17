from fastapi import FastAPI, HTTPException, Header, Depends, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Set
import sqlite3
import datetime
import json
import secrets
import uuid
from contextlib import asynccontextmanager

# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

app = FastAPI(title="Hooker API", description="Systematic Task Management for Hardware Engineers + Activity Monitoring")

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
    
    # Activity Log table (NEW)
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
    
    # Sub-agents tracking table (NEW)
    c.execute('''CREATE TABLE IF NOT EXISTS subagents
                 (id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  status TEXT DEFAULT 'spawned',
                  started_at TEXT NOT NULL,
                  completed_at TEXT,
                  stdout TEXT,
                  stderr TEXT,
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

# Activity & Sub-agent Models (NEW)
class ActivityEntry(BaseModel):
    id: str
    timestamp: str
    actor: str
    action: str
    status: str
    description: str
    duration_ms: int
    metadata: dict

class ActivityCreate(BaseModel):
    actor: str
    action: str
    description: str
    status: str = "success"
    duration_ms: int = 0
    metadata: dict = {}

class SubAgent(BaseModel):
    id: str
    name: str
    status: str
    started_at: str
    completed_at: Optional[str]
    stdout: Optional[str]
    stderr: Optional[str]
    created_at: str

class SubAgentCreate(BaseModel):
    name: str
    status: str = "spawned"

class SubAgentUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

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

# --- Routes: ACTIVITY LOG (NEW) ---
@app.post("/activity", response_model=ActivityEntry)
def create_activity(activity: ActivityCreate, user: str = Depends(verify_api_key)):
    """Create a new activity log entry"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    activity_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    metadata_json = json.dumps(activity.metadata)
    
    c.execute("""INSERT INTO activity_log 
                 (id, timestamp, actor, action, status, description, duration_ms, metadata, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (activity_id, now, activity.actor, activity.action, activity.status,
               activity.description, activity.duration_ms, metadata_json, now))
    
    conn.commit()
    conn.close()
    
    # Broadcast to WebSocket clients
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "activity_created",
        "data": {
            "id": activity_id,
            "timestamp": now,
            "actor": activity.actor,
            "action": activity.action,
            "status": activity.status,
            "description": activity.description,
            "duration_ms": activity.duration_ms,
            "metadata": activity.metadata
        }
    }))
    
    return {
        "id": activity_id,
        "timestamp": now,
        "actor": activity.actor,
        "action": activity.action,
        "status": activity.status,
        "description": activity.description,
        "duration_ms": activity.duration_ms,
        "metadata": activity.metadata
    }

@app.get("/activity", response_model=List[ActivityEntry])
def list_activity(status: Optional[str] = None, actor: Optional[str] = None, 
                  limit: int = 100, user: str = Depends(verify_api_key)):
    """List activity log entries with optional filters"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = "SELECT * FROM activity_log WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if actor:
        query += " AND actor = ?"
        params.append(actor)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    entries = []
    for row in rows:
        r = dict(row)
        try:
            r['metadata'] = json.loads(r['metadata']) if r['metadata'] else {}
        except:
            r['metadata'] = {}
        entries.append(r)
    
    return entries

@app.get("/activity/{activity_id}", response_model=ActivityEntry)
def get_activity(activity_id: str, user: str = Depends(verify_api_key)):
    """Get a specific activity log entry"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM activity_log WHERE id = ?", (activity_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    r = dict(row)
    try:
        r['metadata'] = json.loads(r['metadata']) if r['metadata'] else {}
    except:
        r['metadata'] = {}
    
    return r

# --- Routes: SUB-AGENTS (NEW) ---
@app.post("/subagents", response_model=SubAgent)
def create_subagent(subagent: SubAgentCreate, user: str = Depends(verify_api_key)):
    """Register a spawned sub-agent"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    subagent_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    
    c.execute("""INSERT INTO subagents 
                 (id, name, status, started_at, created_at)
                 VALUES (?, ?, ?, ?, ?)""",
              (subagent_id, subagent.name, subagent.status, now, now))
    
    conn.commit()
    conn.close()
    
    # Log activity
    asyncio.create_task(manager.broadcast({
        "type": "subagent_spawned",
        "data": {
            "id": subagent_id,
            "name": subagent.name,
            "status": subagent.status
        }
    }))
    
    return {
        "id": subagent_id,
        "name": subagent.name,
        "status": subagent.status,
        "started_at": now,
        "completed_at": None,
        "stdout": None,
        "stderr": None,
        "created_at": now
    }

@app.get("/subagents", response_model=List[SubAgent])
def list_subagents(status: Optional[str] = None, user: str = Depends(verify_api_key)):
    """List all sub-agents"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = "SELECT * FROM subagents WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY started_at DESC"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.get("/subagents/{subagent_id}", response_model=SubAgent)
def get_subagent(subagent_id: str, user: str = Depends(verify_api_key)):
    """Get a specific sub-agent"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM subagents WHERE id = ?", (subagent_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Sub-agent not found")
    
    return dict(row)

@app.put("/subagents/{subagent_id}", response_model=SubAgent)
def update_subagent(subagent_id: str, subagent: SubAgentUpdate, user: str = Depends(verify_api_key)):
    """Update sub-agent status"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM subagents WHERE id = ?", (subagent_id,))
    
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Sub-agent not found")
    
    updates = []
    params = []
    
    if subagent.status:
        updates.append("status = ?")
        params.append(subagent.status)
    if subagent.completed_at:
        updates.append("completed_at = ?")
        params.append(subagent.completed_at)
    if subagent.stdout:
        updates.append("stdout = ?")
        params.append(subagent.stdout)
    if subagent.stderr:
        updates.append("stderr = ?")
        params.append(subagent.stderr)
    
    if updates:
        params.append(subagent_id)
        c.execute(f"UPDATE subagents SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    
    c.execute("SELECT * FROM subagents WHERE id = ?", (subagent_id,))
    updated = c.fetchone()
    conn.close()
    
    # Broadcast update
    asyncio.create_task(manager.broadcast({
        "type": "subagent_updated",
        "data": dict(updated)
    }))
    
    return dict(updated)

# --- Routes: WEBSOCKET (NEW) ---
@app.websocket("/ws/activity")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time activity updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
