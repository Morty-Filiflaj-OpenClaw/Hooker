import typer
import requests
from rich.console import Console
from rich.table import Table
from typing import Optional

app = typer.Typer()
console = Console()

API_URL = "http://localhost:8000"

@app.command()
def add(title: str, assignee: str = "Morty", priority: str = "NORMAL"):
    """Create a new task."""
    payload = {"title": title, "assignee": assignee, "priority": priority}
    try:
        r = requests.post(f"{API_URL}/tasks", json=payload)
        r.raise_for_status()
        data = r.json()
        console.print(f"[green]Task created![/green] ID: {data['id']}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def list(status: Optional[str] = None):
    """List all tasks."""
    try:
        params = {"status": status} if status else {}
        r = requests.get(f"{API_URL}/tasks", params=params)
        r.raise_for_status()
        tasks = r.json()
        
        table = Table(title="Hooker Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Assignee", style="yellow")
        table.add_column("Priority")
        
        for t in tasks:
            table.add_row(str(t['id']), t['title'], t['status'], t['assignee'], t['priority'])
            
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error connecting to Hooker API. Is it running?[/red]")

@app.command()
def update(task_id: int, status: str):
    """Update task status (TODO, DOING, DONE)."""
    payload = {"status": status}
    try:
        r = requests.put(f"{API_URL}/tasks/{task_id}", json=payload)
        r.raise_for_status()
        console.print(f"[green]Task {task_id} updated to {status}![/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

if __name__ == "__main__":
    app()
