# Hooker: Monitoring Hub 🪝 (v3)

Hooker v3 is a FastAPI-powered **monitoring and task management hub** designed for hardware engineers, AI assistants, and autonomous agents. It combines real-time activity logging, sub-agent tracking, and systematic task management on a single sleek interface.

## Architecture

- **Backend**: FastAPI (Python 3) + WebSocket support
- **Database**: SQLite (local `hooker.db`) with activity log and sub-agent tracking
- **Frontend**: Vanilla JavaScript + Bootstrap 5 (Dark mode, responsive design)
- **Deployment**: Local web server or Docker

## What's New in v3

### Core Features
- **Activity Feed**: Real-time log showing what agents/humans are doing
  - Actor name (Morty, Filip, SubAgent-X)
  - Task description + duration
  - Status badges (success ✅, pending 🟡, error 🔴, slow 🟠)
  - Sortable by timestamp and filterable by status/actor

- **Sub-agent Dashboard**: Real-time status grid
  - Agent name + status emoji (🟢 Done, 🟡 Running, ⚪ Queued, 🔴 Error)
  - Progress % and timeline
  - Click for detail view (logs, stdout/stderr)

- **Task Board**: Kanban with 4 columns
  - Inbox (external requests + manual tasks)
  - In Progress
  - Review
  - Done
  - Drag-drop, priority coloring, tags

- **Navigation**: Home, Activity Feed (fullscreen), Task Board (fullscreen), Stats, Me

- **Dark Mode**: Sleek, modern design (#0f0f0f + #00d9ff accents)

- **WebSocket Support**: Real-time push updates (no polling)

## API Usage

Hooker provides a comprehensive RESTful + WebSocket API.

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List all tasks (supports `?status=TODO` filter) |
| POST | `/tasks` | Create a new task |
| PUT | `/tasks/{id}` | Update task (status, description, etc.) |
| DELETE | `/tasks/{id}` | Remove a task |

### Activity Log (NEW - v3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/activity` | List activity entries (supports `?status=success&limit=50`) |
| GET | `/activity/{id}` | Get activity entry detail |
| POST | `/activity` | Create activity entry (internal) |

**Activity Entry Schema:**
```json
{
  "actor": "Morty",
  "action": "task.created",
  "description": "Created task #42",
  "status": "success",
  "duration_ms": 1240,
  "metadata": { "task_id": 42, "subagent_id": "abc123" }
}
```

### Sub-agents (NEW - v3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/subagents` | List all sub-agents |
| GET | `/subagents/{id}` | Get sub-agent detail + logs |
| POST | `/subagents` | Register a spawned sub-agent |
| PUT | `/subagents/{id}` | Update sub-agent status |

**Sub-agent Status Lifecycle:**
- `spawned` → `running` → `done` / `error`

### WebSocket (NEW - v3)

| Endpoint | Purpose |
|----------|---------|
| `/ws/activity` | Real-time activity log push + sub-agent updates |

### Components

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/components` | List inventory |
| POST | `/components` | Add new component |
| DELETE | `/components/{id}` | Remove from inventory |

## Installation & Setup

### 1. Install Dependencies
```bash
python3 -m pip install fastapi uvicorn python-multipart
```

### 2. Run Database Migration (v3)
```bash
python3 migrate_v3.py
```

### 3. Start the Server
```bash
# Development (auto-reload)
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload

# Or use the provided script
python3 run_app.py
```

### 4. Access the Frontend
- **v3 (New)**: http://localhost:8000/static/index_v3.html
- **v2 (Legacy)**: http://localhost:8000/static/index.html

## OpenClaw Integration

Hooker is built to be "Agent-Friendly". OpenClaw agents can use the `web_fetch` or `browser` tools to interact with the API to track their own progress or update the human on hardware status.

### Consistent API Rules
- All timestamps are UTC ISO format.
- Tags are always lists of strings.
- Statuses: `TODO`, `DOING`, `BLOCKED`, `DONE`.
