class ComponentCreate(BaseModel):
    part_number: str
    description: Optional[str] = ""
    stock: int = 0
    datasheet_url: Optional[str] = ""
    tags: List[str] = []

class ComponentUpdate(BaseModel):
    part_number: Optional[str] = None
    description: Optional[str] = None
    stock: Optional[int] = None
    datasheet_url: Optional[str] = None
    tags: Optional[List[str]] = None

class Component(BaseModel):
    id: int
    part_number: str
    description: str
    stock: int
    datasheet_url: str
    tags: List[str]
    created_at: str

@app.post("/components", response_model=Component)
def create_component(comp: ComponentCreate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    tags_json = json.dumps(comp.tags)
    
    c.execute("""INSERT INTO components 
                 (part_number, description, stock, datasheet_url, tags, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (comp.part_number, comp.description, comp.stock, comp.datasheet_url, tags_json, now))
    cid = c.lastrowid
    conn.commit()
    conn.close()
    
    return {
        **comp.dict(), 
        "id": cid, 
        "created_at": now
    }

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
        try:
            r['tags'] = json.loads(r['tags']) if r['tags'] else []
        except:
            r['tags'] = []
        comps.append(r)
    return comps

@app.put("/components/{comp_id}", response_model=Component)
def update_component(comp_id: int, comp: ComponentUpdate):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    updates = []
    params = []
    
    if comp.part_number is not None: updates.append("part_number = ?"); params.append(comp.part_number)
    if comp.description is not None: updates.append("description = ?"); params.append(comp.description)
    if comp.stock is not None: updates.append("stock = ?"); params.append(comp.stock)
    if comp.datasheet_url is not None: updates.append("datasheet_url = ?"); params.append(comp.datasheet_url)
    if comp.tags is not None: 
        updates.append("tags = ?")
        params.append(json.dumps(comp.tags))
    
    params.append(comp_id)
    
    query = f"UPDATE components SET {', '.join(updates)} WHERE id = ?"
    c.execute(query, params)
    conn.commit()
    
    c.execute("SELECT * FROM components WHERE id = ?", (comp_id,))
    updated_row = c.fetchone()
    conn.close()
    
    r = dict(updated_row)
    try:
        r['tags'] = json.loads(r['tags']) if r['tags'] else []
    except:
        r['tags'] = []
    return r

@app.delete("/components/{comp_id}")
def delete_component(comp_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM components WHERE id = ?", (comp_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
