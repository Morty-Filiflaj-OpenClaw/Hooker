import uvicorn
from backend import app

if __name__ == "__main__":
    print("🚀 Starting Hooker on http://localhost:8000")
    print("📊 Kanban Dashboard: http://localhost:8000/static/index.html")
    uvicorn.run(app, host="0.0.0.0", port=8000)
