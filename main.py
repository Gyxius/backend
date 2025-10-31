from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
import os
import json
import sqlite3

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

# Database configuration - use PostgreSQL in production, SQLite for local dev
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

# For local development without PostgreSQL
SQLITE_PATH = "./social.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def param_placeholder():
    """Return the correct parameter placeholder for the database type"""
    return "%s" if USE_POSTGRES else "?"

def get_db_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if USE_POSTGRES:
        # Render provides DATABASE_URL starting with postgres://
        # psycopg2 needs postgresql://
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        # Local SQLite
        import sqlite3
        return sqlite3.connect(SQLITE_PATH)

def execute_query(cursor, query, params=None):
    """Execute query with automatic placeholder conversion for PostgreSQL"""
    if USE_POSTGRES and query:
        # Convert SQLite ? placeholders to PostgreSQL %s
        query = query.replace("?", "%s")
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

def init_db():
    """Initialize database tables (works with both PostgreSQL and SQLite)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Adjust syntax based on database type
    if USE_POSTGRES:
        # PostgreSQL syntax
        id_col = "SERIAL PRIMARY KEY"
        bool_col = "BOOLEAN DEFAULT TRUE"
        timestamp_col = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    else:
        # SQLite syntax
        id_col = "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_col = "INTEGER DEFAULT 1"
        timestamp_col = "TEXT DEFAULT CURRENT_TIMESTAMP"
    
    # Users table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_col},
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT
        )
    """)
    
    # Enhanced events table with all fields
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS events (
            id {id_col},
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
            is_public {bool_col},
            event_type TEXT,
            capacity INTEGER,
            image_url TEXT,
            created_by TEXT,
            created_at {timestamp_col}
        )
    """)
    
    # Friends table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS friends (
            user1 TEXT,
            user2 TEXT,
            created_at {timestamp_col},
            PRIMARY KEY (user1, user2)
        )
    """)
    
    # Friend requests table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id {id_col},
            from_user TEXT,
            to_user TEXT,
            created_at {timestamp_col}
        )
    """)
    
    # Event participants
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id INTEGER,
            username TEXT,
            is_host INTEGER DEFAULT 0,
            joined_at {timestamp_col},
            PRIMARY KEY (event_id, username)
        )
    """)
    
    # Suggested events
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS suggested_events (
            id {id_col},
            username TEXT,
            event_id INTEGER,
            created_at {timestamp_col}
        )
    """)
    
    # Chat messages
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id {id_col},
            event_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp {timestamp_col}
        )
    """)
    
    # Search requests table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS search_requests (
            id {id_col},
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

@app.get("/users")
def get_users():
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "SELECT id, username FROM users")
    users = []
    for row in c.fetchall():
        if USE_POSTGRES:
            users.append({"id": row["id"], "username": row["username"]})
        else:
            users.append({"id": row[0], "username": row[1]})
    conn.close()
    return users

def upsert_user_with_password(c, username: str, password: str):
    # Ensure a user exists with a password (set or update password_hash), case-insensitive on username
    if USE_POSTGRES:
        execute_query(c, "SELECT id, password_hash, username FROM users WHERE lower(username) = lower(%s)", (username,))
    else:
        execute_query(c, "SELECT id, password_hash, username FROM users WHERE lower(username) = lower(?)", (username,))
    row = c.fetchone()
    ph = pwd_context.hash(password)
    
    if USE_POSTGRES:
        if row:
            execute_query(c, "UPDATE users SET password_hash = %s WHERE lower(username) = lower(%s)", (ph, username))
        else:
            execute_query(c, "INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, ph))
    else:
        if row:
            execute_query(c, "UPDATE users SET password_hash = ? WHERE lower(username) = lower(?)", (ph, username))
        else:
            execute_query(c, "INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, ph))

init_db()
# Seed default users with password '123' for dev
conn_seed = get_db_connection()
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
    conn = get_db_connection()
    c = conn.cursor()
    # Case-insensitive lookup
    execute_query(c, "SELECT id, password_hash, username FROM users WHERE lower(username) = lower(?)", (user.username,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found. Please contact admin or use an existing account.")
    if USE_POSTGRES:
        user_id = row["id"]
        password_hash = row["password_hash"]
        username_val = row["username"]
    else:
        user_id, password_hash = row[0], row[1]
        username_val = row[2]
    if not password_hash or not pwd_context.verify(user.password, password_hash):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    conn.close()
    return {"id": user_id, "username": username_val}

@app.post("/register")
def register(user: RegisterRequest):
    conn = get_db_connection()
    c = conn.cursor()
    # Enforce case-insensitive uniqueness
    execute_query(c, "SELECT id FROM users WHERE lower(username) = lower(?)", (user.username,))
    row = c.fetchone()
    if row:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    ph = pwd_context.hash(user.password)
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
            RETURNING id
            """,
            (user.username, ph),
        )
        row = c.fetchone()
        user_id = row["id"] if (hasattr(row, "keys") or isinstance(row, dict)) else row[0]
        conn.commit()
    else:
        execute_query(c, "INSERT INTO users (username, password_hash) VALUES (?, ?)", (user.username, ph))
        conn.commit()
        user_id = c.lastrowid
    conn.close()
    return {"id": user_id, "username": user.username}


@app.get("/events")
def get_events():
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "SELECT id, name, description FROM events")
    events = [
        {"id": row[0], "name": row[1], "description": row[2]} for row in c.fetchall()
    ]
    conn.close()
    return events

@app.post("/events")
def create_event(event: Event):
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "INSERT INTO events (name, description) VALUES (?, ?)", (event.name, event.description))
    conn.commit()
    event_id = c.lastrowid
    conn.close()
    return {"id": event_id, "name": event.name, "description": event.description}

@app.post("/join_event")
def join_event(user_id: int, event_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "INSERT OR IGNORE INTO joined_events (user_id, event_id) VALUES (?, ?)", (user_id, event_id))
    conn.commit()
    conn.close()
    return {"message": "User joined event"}

@app.get("/user_joined_events/{user_id}")
def get_user_joined_events(user_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
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
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
        INSERT INTO search_requests (user_id, date, start, end, budget, type, category, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.userId, req.date, req.start, req.end, req.budget, req.type, req.category, req.language))
    conn.commit()
    conn.close()
    return {"message": "Search request created"}

@app.get("/search_requests")
def get_search_requests():
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "SELECT user_id, date, start, end, budget, type, category, language FROM search_requests")
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
    is_public: bool = True
    event_type: str = "custom"
    capacity: int = None
    image_url: str = ""
    created_by: str = None

@app.get("/api/events")
def get_all_events():
    """Get all public events with participants"""
    conn = get_db_connection()
    c = conn.cursor()
    query = (
        """
        SELECT id, name, description, location, venue, address, coordinates,
               date, time, category, languages, is_public, event_type, capacity, image_url, created_by
        FROM events
        WHERE is_public = 1
        """
    )
    if USE_POSTGRES:
        query = query.replace("is_public = 1", "is_public = TRUE")
    execute_query(c, query)
    events = []
    for row in c.fetchall():
        # Support both SQLite tuple rows and Postgres dict rows
        event_id = row["id"] if USE_POSTGRES else row[0]
        # Get participants
        execute_query(c, "SELECT username, is_host FROM event_participants WHERE event_id = ?", (event_id,))
        participants = []
        crew = []
        host = None
        for p in c.fetchall():
            is_host = p["is_host"] if USE_POSTGRES else p[1]
            uname = p["username"] if USE_POSTGRES else p[0]
            if is_host:  # is_host
                host = {"name": uname}
            else:
                participants.append(uname)
                crew.append(uname)
        
        if USE_POSTGRES:
            events.append({
                "id": event_id,
                "name": row["name"],
                "description": row["description"] or "",
                "location": row["location"] or "",
                "venue": row["venue"] or "",
                "address": row["address"] or "",
                "coordinates": json.loads(row["coordinates"]) if row["coordinates"] else None,
                "date": row["date"] or "",
                "time": row["time"] or "",
                "category": row["category"] or "",
                "languages": json.loads(row["languages"]) if row["languages"] else [],
                "isPublic": bool(row["is_public"]),
                "type": row["event_type"] or "custom",
                "capacity": row["capacity"],
                "imageUrl": row["image_url"] or "",
                "createdBy": row["created_by"],
                "host": host,
                "participants": participants,
                "crew": crew
            })
        else:
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
    conn = get_db_connection()
    c = conn.cursor()
    # Insert event and get the new id for both SQLite and PostgreSQL
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO events (name, description, location, venue, address, coordinates,
                              date, time, category, languages, is_public, event_type, capacity, image_url, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
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
                True if event.is_public else False,
                event.event_type,
                event.capacity,
                event.image_url,
                event.created_by,
            ),
        )
        row = c.fetchone()
        event_id = row["id"] if (hasattr(row, "keys") or isinstance(row, dict)) else row[0]
    else:
        execute_query(c, """
            INSERT INTO events (name, description, location, venue, address, coordinates, 
                              date, time, category, languages, is_public, event_type, capacity, image_url, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
            1 if event.is_public else 0,
            event.event_type,
            event.capacity,
            event.image_url,
            event.created_by
        ))
        event_id = c.lastrowid
    
    # Add creator as host/participant
    if event.created_by:
        if USE_POSTGRES:
            c.execute(
                """
                INSERT INTO event_participants (event_id, username, is_host)
                VALUES (%s, %s, 1)
                ON CONFLICT DO NOTHING
                """,
                (event_id, event.created_by),
            )
        else:
            execute_query(c, """
                INSERT OR IGNORE INTO event_participants (event_id, username, is_host)
                VALUES (?, ?, 1)
            """, (event_id, event.created_by))
    
    conn.commit()
    conn.close()
    return {"id": event_id, "message": "Event created"}

@app.post("/api/events/{event_id}/join")
def join_full_event(event_id: int, username: str = Body(..., embed=True)):
    """User joins an event"""
    conn = get_db_connection()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO event_participants (event_id, username, is_host)
            VALUES (%s, %s, 0)
            ON CONFLICT DO NOTHING
            """,
            (event_id, username),
        )
    else:
        execute_query(c, """
            INSERT OR IGNORE INTO event_participants (event_id, username, is_host)
            VALUES (?, ?, 0)
        """, (event_id, username))
    conn.commit()
    conn.close()
    return {"message": "Joined event"}

@app.post("/api/events/{event_id}/leave")
def leave_event(event_id: int, username: str = Body(..., embed=True)):
    """User leaves an event"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "DELETE FROM event_participants WHERE event_id = ? AND username = ?", (event_id, username))
    conn.commit()
    conn.close()
    return {"message": "Left event"}

@app.get("/api/users/{username}/events")
def get_user_events(username: str):
    """Get all events a user has joined or is hosting"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
        SELECT DISTINCT e.id, e.name, e.description, e.location, e.venue, e.address, e.coordinates,
               e.date, e.time, e.category, e.languages, e.is_public, e.event_type, e.capacity, e.image_url, e.created_by
        FROM events e
        JOIN event_participants ep ON e.id = ep.event_id
        WHERE ep.username = ?
    """, (username,))
    events = []
    for row in c.fetchall():
        event_id = row["id"] if USE_POSTGRES else row[0]
        # Get all participants for this event
        execute_query(c, "SELECT username, is_host FROM event_participants WHERE event_id = ?", (event_id,))
        participants = []
        crew = []
        host = None
        for p in c.fetchall():
            is_host = p["is_host"] if USE_POSTGRES else p[1]
            uname = p["username"] if USE_POSTGRES else p[0]
            if is_host:
                host = {"name": uname}
            else:
                participants.append(uname)
                crew.append(uname)

        if USE_POSTGRES:
            events.append({
                "id": event_id,
                "name": row["name"],
                "description": row["description"] or "",
                "location": row["location"] or "",
                "venue": row["venue"] or "",
                "address": row["address"] or "",
                "coordinates": json.loads(row["coordinates"]) if row["coordinates"] else None,
                "date": row["date"] or "",
                "time": row["time"] or "",
                "category": row["category"] or "",
                "languages": json.loads(row["languages"]) if row["languages"] else [],
                "isPublic": bool(row["is_public"]),
                "type": row["event_type"] or "custom",
                "capacity": row["capacity"],
                "imageUrl": row["image_url"] or "",
                "createdBy": row["created_by"],
                "host": host,
                "participants": participants,
                "crew": crew
            })
        else:
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
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
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
    conn = get_db_connection()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO friends (user1, user2)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (user1, user2),
        )
    else:
        execute_query(c, "INSERT OR IGNORE INTO friends (user1, user2) VALUES (?, ?)", (user1, user2))
    conn.commit()
    conn.close()
    return {"message": "Friend added"}

@app.get("/api/chat/{event_id}")
def get_chat_messages(event_id: int):
    """Get chat messages for an event"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
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
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
        INSERT INTO chat_messages (event_id, username, message)
        VALUES (?, ?, ?)
    """, (event_id, username, message))
    conn.commit()
    conn.close()
    return {"message": "Message sent"}
