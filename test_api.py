import requests
import sys

API_URL = "http://localhost:8000"

def log(msg, success=True):
    icon = "✅" if success else "❌"
    print(f"{icon} {msg}")

def test_health():
    try:
        r = requests.get(f"{API_URL}/")
        if r.status_code == 200:
            log("API is reachable")
            return True
        else:
            log(f"API returned {r.status_code}", False)
            return False
    except:
        log("API is NOT running (Connection Error)", False)
        return False

def test_tasks():
    # Create
    payload = {"title": "Test Task", "priority": "HIGH", "tags": ["test"]}
    r = requests.post(f"{API_URL}/tasks", json=payload)
    if r.status_code != 200:
        log("Create Task Failed", False)
        return
    tid = r.json()['id']
    log(f"Created Task ID {tid}")

    # List
    r = requests.get(f"{API_URL}/tasks")
    tasks = r.json()
    if len(tasks) > 0:
        log(f"Listed {len(tasks)} tasks")
    else:
        log("List Tasks Empty", False)

    # Delete
    r = requests.delete(f"{API_URL}/tasks/{tid}")
    if r.status_code == 200:
        log(f"Deleted Task ID {tid}")
    else:
        log("Delete Task Failed", False)

def test_components():
    # Create
    payload = {"part_number": "TEST-CHIP-01", "stock": 100, "tags": ["smd"]}
    r = requests.post(f"{API_URL}/components", json=payload)
    if r.status_code != 200:
        log("Create Component Failed", False)
        return
    cid = r.json()['id']
    log(f"Created Component ID {cid}")

    # List
    r = requests.get(f"{API_URL}/components")
    comps = r.json()
    if len(comps) > 0:
        log(f"Listed {len(comps)} components")
    else:
        log("List Components Empty", False)
        
    # Delete
    r = requests.delete(f"{API_URL}/components/{cid}")
    if r.status_code == 200:
        log(f"Deleted Component ID {cid}")
    else:
        log("Delete Component Failed", False)

if __name__ == "__main__":
    print("--- Hooker API Self-Test ---")
    if test_health():
        test_tasks()
        test_components()
    else:
        print("Skipping tests because API is down.")
        sys.exit(1)
