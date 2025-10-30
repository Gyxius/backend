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
    
    # Enhanced events table with all fields
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            venue TEXT,
            address TEXT,
            coordinates TEXT,
            date TEXT,
            time TEXT,
            category TEXT,
            languages TEXT,
            is_public INTEGER DEFAULT 1,
            event_type TEXT,
            capacity INTEGER,
            image_url TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Friends table
    c.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            user1 TEXT,
            user2 TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user1, user2)
        )
    """)
    
    # Friend requests table
    c.execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user TEXT,
            to_user TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Event participants (replaces joined_events with more info)
    c.execute("""
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id INTEGER,
            username TEXT,
            is_host INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (event_id, username),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    
    # Suggested events
    c.execute("""
        CREATE TABLE IF NOT EXISTS suggested_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            event_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    
    # Chat messages
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    conn.commit()
    conn.close()

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

# ===== NEW COMPREHENSIVE EVENT MANAGEMENT ENDPOINTS =====

import json
from datetime import datetime

class FullEvent(BaseModel):
    id: int
    name: str
    description: str = ""
    location: str = ""
    venue: str = ""
    address: str = ""
    coordinates: dict = None
    date: str = ""
    time: str = ""
    category: str = ""
    languages: List[str] = []
    isPublic: bool = True
    type: str = "custom"
    capacity: int = None
    imageUrl: str = ""
    host: dict = None

@app.get("/api/events")
def get_all_events():
    """Get all public events with participants"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, description, location, venue, address, coordinates, 
               date, time, category, languages, is_public, event_type, capacity, image_url, created_by
        FROM events
        WHERE is_public = 1
    """)
    events = []
    for row in c.fetchall():
        event_id = row[0]
        # Get participants
        c.execute("SELECT username, is_host FROM event_participants WHERE event_id = ?", (event_id,))
        participants = []
        crew = []
        host = None
        for p in c.fetchall():
            if p[1]:  # is_host
                host = {"name": p[0]}
            else:
                participants.append(p[0])
                crew.append(p[0])
        
        events.append({
            "id": event_id,
            "name": row[1],
            "description": row[2] or "",
            "location": row[3] or "",
            "venue": row[4] or "",
            "address": row[5] or "",
            "coordinates": json.loads(row[6]) if row[6] else None,
            "date": row[7] or "",
            "time": row[8] or "",
            "category": row[9] or "",
            "languages": json.loads(row[10]) if row[10] else [],
            "isPublic": bool(row[11]),
            "type": row[12] or "custom",
            "capacity": row[13],
            "imageUrl": row[14] or "",
            "createdBy": row[15],
            "host": host,
            "participants": participants,
            "crew": crew
        })
    conn.close()
    return events

@app.post("/api/events")
def create_full_event(event: FullEvent):
    """Create a new event"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO events (id, name, description, location, venue, address, coordinates, 
                          date, time, category, languages, is_public, event_type, capacity, image_url, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.id,
        event.name,
        event.description,
        event.location,
        event.venue,
        event.address,
        json.dumps(event.coordinates) if event.coordinates else None,
        event.date,
        event.time,
        event.category,
        json.dumps(event.languages),
        1 if event.isPublic else 0,
        event.type,
        event.capacity,
        event.imageUrl,
        event.host.get("name") if event.host else None
    ))
    
    # Add host as participant
    if event.host:
        c.execute("""
            INSERT INTO event_participants (event_id, username, is_host)
            VALUES (?, ?, 1)
        """, (event.id, event.host.get("name")))
    
    conn.commit()
    conn.close()
    return {"id": event.id, "message": "Event created"}

@app.post("/api/events/{event_id}/join")
def join_full_event(event_id: int, username: str = Body(..., embed=True)):
    """User joins an event"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO event_participants (event_id, username, is_host)
        VALUES (?, ?, 0)
    """, (event_id, username))
    conn.commit()
    conn.close()
    return {"message": "Joined event"}

@app.post("/api/events/{event_id}/leave")
def leave_event(event_id: int, username: str = Body(..., embed=True)):
    """User leaves an event"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM event_participants WHERE event_id = ? AND username = ?", (event_id, username))
    conn.commit()
    conn.close()
    return {"message": "Left event"}

@app.get("/api/users/{username}/events")
def get_user_events(username: str):
    """Get all events a user has joined or is hosting"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT e.id, e.name, e.description, e.location, e.venue, e.address, e.coordinates,
               e.date, e.time, e.category, e.languages, e.is_public, e.event_type, e.capacity, e.image_url, e.created_by
        FROM events e
        JOIN event_participants ep ON e.id = ep.event_id
        WHERE ep.username = ?
    """, (username,))
    events = []
    for row in c.fetchall():
        event_id = row[0]
        # Get all participants for this event
        c.execute("SELECT username, is_host FROM event_participants WHERE event_id = ?", (event_id,))
        participants = []
        crew = []
        host = None
        for p in c.fetchall():
            if p[1]:
                host = {"name": p[0]}
            else:
                participants.append(p[0])
                crew.append(p[0])
        
        events.append({
            "id": event_id,
            "name": row[1],
            "description": row[2] or "",
            "location": row[3] or "",
            "venue": row[4] or "",
            "address": row[5] or "",
            "coordinates": json.loads(row[6]) if row[6] else None,
            "date": row[7] or "",
            "time": row[8] or "",
            "category": row[9] or "",
            "languages": json.loads(row[10]) if row[10] else [],
            "isPublic": bool(row[11]),
            "type": row[12] or "custom",
            "capacity": row[13],
            "imageUrl": row[14] or "",
            "createdBy": row[15],
            "host": host,
            "participants": participants,
            "crew": crew
        })
    conn.close()
    return events

@app.get("/api/friends/{username}")
def get_friends(username: str):
    """Get user's friends list"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user2 FROM friends WHERE user1 = ?
        UNION
        SELECT user1 FROM friends WHERE user2 = ?
    """, (username, username))
    friends = [row[0] for row in c.fetchall()]
    conn.close()
    return friends

@app.post("/api/friends")
def add_friend(user1: str = Body(...), user2: str = Body(...)):
    """Add a friendship"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO friends (user1, user2) VALUES (?, ?)", (user1, user2))
    conn.commit()
    conn.close()
    return {"message": "Friend added"}

@app.get("/api/chat/{event_id}")
def get_chat_messages(event_id: int):
    """Get chat messages for an event"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT username, message, timestamp
        FROM chat_messages
        WHERE event_id = ?
        ORDER BY timestamp ASC
    """, (event_id,))
    messages = [{"username": row[0], "message": row[1], "timestamp": row[2]} for row in c.fetchall()]
    conn.close()
    return messages

@app.post("/api/chat/{event_id}")
def send_chat_message(event_id: int, username: str = Body(...), message: str = Body(...)):
    """Send a chat message"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO chat_messages (event_id, username, message)
        VALUES (?, ?, ?)
    """, (event_id, username, message))
    conn.commit()
    conn.close()
    return {"message": "Message sent"}
