# Hooker: System Task Manager 🪝

Hooker is a lightweight, FastAPI-powered task and component management system designed for hardware engineers and autonomous agents. It provides a Trello-like Kanban interface for tasks and a simple inventory tracker for components.

## Architecture

- **Backend**: FastAPI (Python 3)
- **Database**: SQLite (local `hooker.db`)
- **Frontend**: Vanilla JavaScript + Bootstrap 5 (Dashboard & Kanban)
- **Deployment**: Local web server or Docker

## API Usage

Hooker provides a RESTful API for integration with other tools (like OpenClaw).

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List all tasks (supports `?status=TODO` filter) |
| POST | `/tasks` | Create a new task |
| PUT | `/tasks/{id}` | Update task (status, description, etc.) |
| DELETE | `/tasks/{id}` | Remove a task |

**Create Task Example (JSON):**
```json
{
  "title": "Fix PCB trace",
  "description": "Short on 3V3 rail",
  "assignee": "Morty",
  "priority": "HIGH",
  "tags": ["hardware", "bug"]
}
```

### Components

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/components` | List inventory |
| POST | `/components` | Add new component |
| DELETE | `/components/{id}` | Remove from inventory |

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   python3 -m pip install fastapi uvicorn
   ```

2. **Run the Server**:
   ```bash
   uvicorn backend:app --host 0.0.0.0 --port 8000
   ```

3. **Access the Frontend**:
   Open `http://localhost:8000/static/index.html` in your browser.

## OpenClaw Integration

Hooker is built to be "Agent-Friendly". OpenClaw agents can use the `web_fetch` or `browser` tools to interact with the API to track their own progress or update the human on hardware status.

### Consistent API Rules
- All timestamps are UTC ISO format.
- Tags are always lists of strings.
- Statuses: `TODO`, `DOING`, `BLOCKED`, `DONE`.
