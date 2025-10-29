from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import sqlite3
from passlib.context import CryptContext
import os

app = FastAPI()

# Serve static files (logo, icon, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

def _get_allowed_origins():
    """Return CORS allowed origins list from env FRONTEND_ORIGINS/FRONTEND_ORIGIN.
    Defaults to ["*"] for dev.
    """
    origins = os.environ.get("FRONTEND_ORIGINS") or os.environ.get("FRONTEND_ORIGIN")
    if origins:
        return [o.strip() for o in origins.split(",") if o.strip()]
    return ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "./social.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT
        )
    """)
    # Add column if migrating older DB
    try:
        c.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    except Exception:
        pass

@app.get("/users")
def get_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    users = []
    for row in c.fetchall():
        users.append({
            "id": row[0],
            "username": row[1],
        })
    conn.close()
    return users
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS joined_events (
            user_id INTEGER,
            event_id INTEGER,
            PRIMARY KEY (user_id, event_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS search_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT,
            start TEXT,
            end TEXT,
            budget INTEGER,
            type TEXT,
            category TEXT,
            language TEXT
        )
    """)
    conn.commit()
    conn.close()

def upsert_user_with_password(c, username: str, password: str):
    # Ensure a user exists with a password (set or update password_hash), case-insensitive on username
    c.execute("SELECT id, password_hash, username FROM users WHERE lower(username) = lower(?)", (username,))
    row = c.fetchone()
    ph = pwd_context.hash(password)
    if row:
        # Set the password hash for ALL rows matching case-insensitive username to avoid duplicates mismatch
        c.execute("UPDATE users SET password_hash = ? WHERE lower(username) = lower(?)", (ph, username))
    else:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, ph))

init_db()
# Seed defaults with password '123' for dev
conn_seed = sqlite3.connect(DB_PATH)
c_seed = conn_seed.cursor()
for uname in ["admin", "Mitsu", "Zine", "Kat"]:
    try:
        upsert_user_with_password(c_seed, uname, "123")
    except Exception:
        pass
conn_seed.commit()
conn_seed.close()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class Event(BaseModel):
    name: str
    description: str = ""

@app.post("/login")
def login(user: LoginRequest):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Case-insensitive lookup
    c.execute("SELECT id, password_hash, username FROM users WHERE lower(username) = lower(?)", (user.username,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found. Please contact admin or use an existing account.")
    user_id, password_hash = row[0], row[1]
    if not password_hash or not pwd_context.verify(user.password, password_hash):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    conn.close()
    return {"id": user_id, "username": row[2]}

@app.post("/register")
def register(user: RegisterRequest):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Enforce case-insensitive uniqueness
    c.execute("SELECT id FROM users WHERE lower(username) = lower(?)", (user.username,))
    row = c.fetchone()
    if row:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    ph = pwd_context.hash(user.password)
    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (user.username, ph))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return {"id": user_id, "username": user.username}


@app.get("/events")
def get_events():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, description FROM events")
    events = [
        {"id": row[0], "name": row[1], "description": row[2]} for row in c.fetchall()
    ]
    conn.close()
    return events

@app.post("/events")
def create_event(event: Event):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO events (name, description) VALUES (?, ?)", (event.name, event.description))
    conn.commit()
    event_id = c.lastrowid
    conn.close()
    return {"id": event_id, "name": event.name, "description": event.description}

@app.post("/join_event")
def join_event(user_id: int, event_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO joined_events (user_id, event_id) VALUES (?, ?)", (user_id, event_id))
    conn.commit()
    conn.close()
    return {"message": "User joined event"}

@app.get("/user_joined_events/{user_id}")
def get_user_joined_events(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT events.id, events.name, events.description
        FROM events
        JOIN joined_events ON events.id = joined_events.event_id
        WHERE joined_events.user_id = ?
    """, (user_id,))
    events = [
        {"id": row[0], "name": row[1], "description": row[2]} for row in c.fetchall()
    ]
    conn.close()
    return events


# --- New endpoints for search requests ---
from fastapi import Body

class SearchRequest(BaseModel):
    userId: str
    date: str
    start: str
    end: str
    budget: int
    type: str
    category: str
    language: str

@app.post("/search_requests")
def create_search_request(req: SearchRequest):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO search_requests (user_id, date, start, end, budget, type, category, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.userId, req.date, req.start, req.end, req.budget, req.type, req.category, req.language))
    conn.commit()
    conn.close()
    return {"message": "Search request created"}

@app.get("/search_requests")
def get_search_requests():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, date, start, end, budget, type, category, language FROM search_requests")
    requests = []
    for row in c.fetchall():
        requests.append({
            "userId": row[0],
            "date": row[1],
            "start": row[2],
            "end": row[3],
            "budget": row[4],
            "type": row[5],
            "category": row[6],
            "language": row[7],
        })
    conn.close()
    return requests
