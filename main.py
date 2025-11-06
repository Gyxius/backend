from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
import os
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Optional S3 support for persistent image storage
try:
    import boto3  # type: ignore
except Exception:
    boto3 = None

app = FastAPI()

# Create static/uploads directory if it doesn't exist
try:
    static_dir = Path("./static")
    static_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir = static_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    # Serve static files (logo, icon, etc.)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✅ Static files mounted successfully")
except Exception as e:
    print(f"⚠️  Warning: Could not mount static files: {e}")

def _get_allowed_origins():
    """Return CORS allowed origins list from env FRONTEND_ORIGINS/FRONTEND_ORIGIN.
    Defaults to ["*"] for dev.
    """
    origins = os.environ.get("FRONTEND_ORIGINS") or os.environ.get("FRONTEND_ORIGIN")
    if origins:
        origins_list = [o.strip() for o in origins.split(",") if o.strip()]
        print(f"🔒 CORS: Allowing origins: {origins_list}")
        return origins_list
    print("⚠️  CORS: No FRONTEND_ORIGINS set, allowing all origins (*)")
    return ["*"]

allowed_origins = _get_allowed_origins()
print(f"🌐 Starting with CORS origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint: echo request headers so we can see the incoming Origin header.

    Use this to verify what origin the backend sees from the browser or a curl command.
    """
    try:
        hdrs = {k: v for k, v in request.headers.items()}
    except Exception:
        hdrs = {}
    print("🔍 [DEBUG] /debug/headers request headers:", hdrs)
    return {"headers": hdrs}


# Database configuration - use PostgreSQL in production, SQLite for local dev
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

# For local development without PostgreSQL
SQLITE_PATH = "./social.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def normalize_image_url(image_url: str) -> str:
    """Convert relative image URLs to absolute URLs for cross-origin access"""
    if not image_url:
        return ""
    # Pass through data URLs (base64) or blob URLs untouched
    if image_url.startswith("data:") or image_url.startswith("blob:"):
        return image_url
    # If already absolute, return as-is
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    # Convert relative URL to absolute
    backend_url = os.environ.get("BACKEND_URL", "https://fast-api-backend-qlyb.onrender.com")
    # Remove leading slash if present to avoid double slashes
    if image_url.startswith("/"):
        return f"{backend_url}{image_url}"
    return f"{backend_url}/{image_url}"

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
        bool_col_false = "BOOLEAN DEFAULT FALSE"
        timestamp_col = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    else:
        # SQLite syntax
        id_col = "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_col = "INTEGER DEFAULT 1"
        bool_col_false = "INTEGER DEFAULT 0"
        timestamp_col = "TEXT DEFAULT CURRENT_TIMESTAMP"
    
    # Users table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_col},
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT
        )
    """)
    # Ensure invite_code column exists on users table
    try:
        if USE_POSTGRES:
            c.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='invite_code') THEN
                        ALTER TABLE users ADD COLUMN invite_code TEXT UNIQUE;
                    END IF;
                END$$;
                """
            )
            conn.commit()
        else:
            c.execute("PRAGMA table_info(users);")
            cols = [row[1] for row in c.fetchall()]
            if 'invite_code' not in cols:
                execute_query(c, "ALTER TABLE users ADD COLUMN invite_code TEXT")
                execute_query(c, "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_invite_code ON users(invite_code)")
                conn.commit()
    except Exception as e:
        print(f"[init_db] invite_code migration notice: {e}")
    
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
            is_featured {bool_col} DEFAULT {'FALSE' if USE_POSTGRES else '0'},
            template_event_id INTEGER,
            created_at {timestamp_col}
        )
    """)
    
    # Follows table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS follows (
            user1 TEXT,
            user2 TEXT,
            created_at {timestamp_col},
            PRIMARY KEY (user1, user2)
        )
    """)
    
    # Follow requests table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS follow_requests (
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
    
    # Notifications table for unread messages
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS notifications (
            id {id_col},
            user_id TEXT,
            event_id INTEGER,
            message_id INTEGER,
            is_read {bool_col_false},
            created_at {timestamp_col}
        )
    """)
    
    # Search requests table
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS search_requests (
            id {id_col},
            user_id TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            budget INTEGER,
            type TEXT,
            category TEXT,
            language TEXT
        )
    """)

    # User profiles stored as raw JSON (per username)
    execute_query(c, f"""
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            profile_json TEXT,
            updated_at {timestamp_col}
        )
    """)

    conn.commit()
    
    # Migration: Add is_featured column if it doesn't exist (for existing databases)
    if USE_POSTGRES:
        try:
            c2 = conn.cursor()
            c2.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='events' AND column_name='is_featured'
            """)
            if not c2.fetchone():
                print("📝 Running migration: Adding is_featured column...")
                c2.execute("ALTER TABLE events ADD COLUMN is_featured BOOLEAN DEFAULT FALSE")
                c2.execute("UPDATE events SET is_featured = TRUE WHERE created_by = 'admin' AND capacity IS NULL")
                conn.commit()
                print("✅ Migration complete: is_featured column added")
            else:
                print("✅ is_featured column already exists")
            
            # Migration: Ensure template_event_id is INTEGER
            c2.execute("""
                SELECT data_type
                FROM information_schema.columns 
                WHERE table_schema = current_schema()
                  AND table_name='events' 
                  AND column_name='template_event_id'
            """)
            result = c2.fetchone()
            if not result:
                print("📝 Running migration: Adding template_event_id column (INTEGER)...")
                c2.execute("ALTER TABLE events ADD COLUMN template_event_id INTEGER")
                conn.commit()
                print("✅ Migration complete: template_event_id column (INTEGER) added")
            else:
                dt = str(list(result.values())[0] if isinstance(result, dict) else result[0]).lower()
                if dt not in ("integer", "bigint", "smallint"):
                    print(f"📝 Running migration: Converting template_event_id from {dt} to INTEGER...")
                    # Safer approach: rename old column, add new integer column, drop old
                    try:
                        c2.execute("ALTER TABLE events RENAME COLUMN template_event_id TO template_event_id_old")
                        c2.execute("ALTER TABLE events ADD COLUMN template_event_id INTEGER")
                        # No data transfer because types don't match meaningfully; null is fine
                        c2.execute("ALTER TABLE events DROP COLUMN template_event_id_old")
                        conn.commit()
                        print("✅ Migration complete: template_event_id column type converted to INTEGER")
                    except Exception as inner_e:
                        conn.rollback()
                        print(f"⚠️  Migration step failed, retrying with DROP/ADD: {inner_e}")
                        try:
                            c2.execute("ALTER TABLE events DROP COLUMN IF EXISTS template_event_id CASCADE")
                            c2.execute("ALTER TABLE events ADD COLUMN template_event_id INTEGER")
                            conn.commit()
                            print("✅ Migration complete: template_event_id column recreated as INTEGER")
                        except Exception as inner_e2:
                            conn.rollback()
                            print(f"❌ Migration failed to fix template_event_id type: {inner_e2}")
                else:
                    print("✅ template_event_id column already INTEGER-compatible")
            
            c2.close()
        except Exception as e:
            print(f"⚠️  Migration check failed: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
    
    conn.close()

@app.get("/debug/env")
def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "FRONTEND_ORIGINS": os.environ.get("FRONTEND_ORIGINS", "NOT SET"),
        "FRONTEND_ORIGIN": os.environ.get("FRONTEND_ORIGIN", "NOT SET"),
        "DATABASE_URL": "SET" if os.environ.get("DATABASE_URL") else "NOT SET",
        "USE_POSTGRES": USE_POSTGRES,
    }

@app.get("/debug/profiles")
def debug_profiles():
    """Debug endpoint to check what's in user_profiles table"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "SELECT username, profile_json, updated_at FROM user_profiles LIMIT 10")
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        if USE_POSTGRES:
            # RealDictCursor returns dict
            result.append({
                "username": row['username'],
                "profile_json_preview": str(row['profile_json'])[:200] if row['profile_json'] else "NULL",
                "updated_at": str(row['updated_at'])
            })
        else:
            # SQLite returns tuple
            result.append({
                "username": row[0],
                "profile_json_preview": str(row[1])[:200] if row[1] else "NULL",
                "updated_at": str(row[2]) if len(row) > 2 else "N/A"
            })
    return {"profiles": result, "count": len(result)}

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
    inviteCode: Optional[str] = None

class Event(BaseModel):
    name: str
    description: str = ""

class UserProfilePayload(BaseModel):
    data: dict

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
    # Validate invite code if provided
    try:
        code = (user.inviteCode or '').strip()
    except Exception:
        code = ''
    if code:
        if USE_POSTGRES:
            c.execute("SELECT username FROM users WHERE invite_code = %s", (code,))
        else:
            execute_query(c, "SELECT username FROM users WHERE invite_code = ?", (code,))
        owner = c.fetchone()
        if not owner:
            conn.close()
            raise HTTPException(status_code=400, detail="Invalid invite code")
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
        INSERT INTO search_requests (user_id, date, start_time, end_time, budget, type, category, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.userId, req.date, req.start, req.end, req.budget, req.type, req.category, req.language))
    conn.commit()
    conn.close()
    return {"message": "Search request created"}

@app.get("/search_requests")
def get_search_requests():
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, "SELECT user_id, date, start_time, end_time, budget, type, category, language FROM search_requests")
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
import random
import string

# -------------------- Invite Code APIs --------------------
def _generate_invite_segment(length: int = 4) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_invite_code() -> str:
    return f"LEMI-{_generate_invite_segment()}-{_generate_invite_segment()}"

def _get_unique_invite_code(c) -> str:
    while True:
        code = generate_invite_code()
        if USE_POSTGRES:
            c.execute("SELECT 1 FROM users WHERE invite_code = %s", (code,))
        else:
            execute_query(c, "SELECT 1 FROM users WHERE invite_code = ?", (code,))
        if not c.fetchone():
            return code

@app.get("/api/users/{username}/invite-code")
def get_user_invite_code(username: str):
    conn = get_db_connection()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT invite_code FROM users WHERE lower(username)=lower(%s)", (username,))
        row = c.fetchone()
        invite_code = row["invite_code"] if row and (hasattr(row, "keys") or isinstance(row, dict)) else (row[0] if row else None)
    else:
        execute_query(c, "SELECT invite_code FROM users WHERE lower(username)=lower(?)", (username,))
        r = c.fetchone()
        invite_code = r[0] if r else None
    conn.close()
    if invite_code is None:
        # Return explicitly null if no code yet
        return {"invite_code": None}
    return {"invite_code": invite_code}

@app.post("/api/users/{username}/invite-code")
def create_or_rotate_invite_code(username: str):
    conn = get_db_connection()
    c = conn.cursor()
    # Ensure user exists
    if USE_POSTGRES:
        c.execute("SELECT id FROM users WHERE lower(username)=lower(%s)", (username,))
    else:
        execute_query(c, "SELECT id FROM users WHERE lower(username)=lower(?)", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    code = _get_unique_invite_code(c)
    if USE_POSTGRES:
        c.execute("UPDATE users SET invite_code=%s WHERE lower(username)=lower(%s)", (code, username))
    else:
        execute_query(c, "UPDATE users SET invite_code=? WHERE lower(username)=lower(?)", (code, username))
    conn.commit()
    conn.close()
    return {"invite_code": code}

@app.get("/api/invites/validate")
def validate_invite(code: str):
    conn = get_db_connection()
    c = conn.cursor()
    inviter = None
    if USE_POSTGRES:
        c.execute("SELECT username FROM users WHERE invite_code = %s", (code,))
        row = c.fetchone()
        if row:
            inviter = row["username"] if (hasattr(row, "keys") or isinstance(row, dict)) else row[0]
    else:
        execute_query(c, "SELECT username FROM users WHERE invite_code = ?", (code,))
        r = c.fetchone()
        inviter = r[0] if r else None
    conn.close()
    return {"valid": inviter is not None, "inviter": inviter}

# ===== User Profile Endpoints =====
@app.get("/api/users/{username}/profile")
def get_user_profile(username: str):
    conn = get_db_connection()
    c = conn.cursor()
    # Fetch profile JSON; ignore case on username
    execute_query(c, "SELECT profile_json FROM user_profiles WHERE lower(username) = lower(?)", (username,))
    row = c.fetchone()
    print(f"📥 [PROFILE] Fetching profile for {username}: row={row}")
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        # RealDictCursor returns dict for Postgres, tuple for SQLite
        raw = row['profile_json'] if USE_POSTGRES else row[0]
        import json
        result = json.loads(raw) if raw else {}
        print(f"📥 [PROFILE] Returning: {str(result)[:200]}...")
        return result
    except Exception as e:
        print(f"❌ [PROFILE] Error parsing: {e}")
        return {}

@app.post("/api/users/{username}/profile")
def upsert_user_profile(username: str, payload: UserProfilePayload):
    import json
    print(f"💾 [PROFILE] Saving profile for {username}: {payload.data}")
    conn = get_db_connection()
    c = conn.cursor()
    # Ensure user exists (create stub if not)
    execute_query(c, "SELECT id FROM users WHERE lower(username) = lower(?)", (username,))
    exists = c.fetchone()
    if not exists:
        execute_query(c, "INSERT INTO users (username) VALUES (?)", (username,))
    # Upsert profile JSON
    profile_json = json.dumps(payload.data or {})
    print(f"💾 [PROFILE] JSON to save: {profile_json[:200]}...")
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO user_profiles (username, profile_json, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (username) DO UPDATE SET profile_json = EXCLUDED.profile_json, updated_at = CURRENT_TIMESTAMP
            """,
            (username, profile_json),
        )
    else:
        execute_query(
            c,
            "INSERT OR REPLACE INTO user_profiles (username, profile_json, updated_at) VALUES (?, ?, datetime('now'))",
            (username, profile_json),
        )
    conn.commit()
    conn.close()
    return {"ok": True}

class FullEvent(BaseModel):
    name: str
    description: str = ""
    location: str = ""
    venue: str = ""
    address: str = ""
    coordinates: Optional[dict] = None
    date: str = ""
    time: str = ""
    category: str = ""
    languages: List[str] = []
    is_public: bool = True
    event_type: str = "custom"
    capacity: Optional[int] = None
    image_url: str = ""
    created_by: Optional[str] = None
    is_featured: bool = False
    template_event_id: Optional[int] = None

@app.get("/api/events")
def get_all_events():
    """Get all public events with participants"""
    conn = get_db_connection()
    c = conn.cursor()
    query = (
        """
        SELECT id, name, description, location, venue, address, coordinates,
               date, time, category, languages, is_public, event_type, capacity, image_url, created_by, is_featured, template_event_id
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
                "imageUrl": normalize_image_url(row["image_url"] or ""),
                "createdBy": row["created_by"],
                "isFeatured": bool(row["is_featured"]),
                "templateEventId": row["template_event_id"],
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
                "imageUrl": normalize_image_url(row[14] or ""),
                "createdBy": row[15],
                "isFeatured": bool(row[16]),
                "templateEventId": row[17],
                "host": host,
                "participants": participants,
                "crew": crew
            })
    conn.close()
    return events

@app.get("/api/events/{event_id}")
def get_event_by_id(event_id: int):
    """Get a single event by ID with all details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT id, name, description, location, venue, address, coordinates, 
                   date, time, category, languages, is_public, event_type, capacity, image_url, created_by, is_featured, template_event_id
            FROM events WHERE id = %s
        """, (event_id,))
    else:
        cursor.execute("""
            SELECT id, name, description, location, venue, address, coordinates, 
                   date, time, category, languages, is_public, event_type, capacity, image_url, created_by, is_featured, template_event_id
            FROM events WHERE id = ?
        """, (event_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get participants and host
    if USE_POSTGRES:
        cursor.execute("SELECT username, is_host FROM event_participants WHERE event_id = %s", (event_id,))
    else:
        cursor.execute("SELECT username, is_host FROM event_participants WHERE event_id = ?", (event_id,))
    
    participants = []
    crew = []
    host = None
    for p in cursor.fetchall():
        if USE_POSTGRES:
            is_host = p["is_host"]
            uname = p["username"]
        else:
            uname = p[0]
            is_host = p[1]
        
        if is_host:
            host = {"name": uname}
        else:
            participants.append(uname)
            crew.append(uname)
    
    conn.close()

    if USE_POSTGRES:
        event_data = {
            "id": row["id"],
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
            "imageUrl": normalize_image_url(row["image_url"] or ""),
            "createdBy": row["created_by"],
            "isFeatured": bool(row["is_featured"]),
            "templateEventId": row["template_event_id"],
            "host": host,
            "participants": participants,
            "crew": crew
        }
    else:
        event_data = {
            "id": row[0],
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
            "imageUrl": normalize_image_url(row[14] or ""),
            "createdBy": row[15],
            "isFeatured": bool(row[16]),
            "templateEventId": row[17],
            "host": host,
            "participants": participants,
            "crew": crew
        }

    return event_data

@app.post("/api/events")
def create_full_event(event: FullEvent):
    """Create a new event"""
    conn = get_db_connection()
    c = conn.cursor()
    # Safety: if running on Postgres and the template_event_id column is of wrong type (e.g., uuid),
    # avoid 500 by sending NULL until migration fixes it.
    tpl_value = getattr(event, 'template_event_id', None)
    if USE_POSTGRES:
        try:
            c.execute(
                """
                SELECT data_type
                FROM information_schema.columns 
                WHERE table_schema = current_schema()
                  AND table_name='events' 
                  AND column_name='template_event_id'
                """
            )
            r = c.fetchone()
            if r:
                dt = str(list(r.values())[0] if isinstance(r, dict) else r[0]).lower()
                if dt not in ("integer", "bigint", "smallint"):
                    # Log once per process start would be nicer, but print here is fine.
                    print("⚠️  template_event_id column is not INTEGER yet; inserting NULL to avoid failure.")
                    tpl_value = None
        except Exception as _e:
            # If introspection fails, proceed without blocking creation
            pass
    # Insert event and get the new id for both SQLite and PostgreSQL
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO events (name, description, location, venue, address, coordinates,
                              date, time, category, languages, is_public, event_type, capacity, image_url, created_by, is_featured, template_event_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                getattr(event, 'is_featured', False),
                tpl_value,
            ),
        )
        row = c.fetchone()
        event_id = row["id"] if (hasattr(row, "keys") or isinstance(row, dict)) else row[0]
    else:
        execute_query(c, """
            INSERT INTO events (name, description, location, venue, address, coordinates, 
                              date, time, category, languages, is_public, event_type, capacity, image_url, created_by, is_featured, template_event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            event.created_by,
            1 if getattr(event, 'is_featured', False) else 0,
            getattr(event, 'template_event_id', None)
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

@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: FullEvent):
    """Update an event (only the host can update)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if the user is the host of the event or is admin
    execute_query(c, "SELECT created_by FROM events WHERE id = ?", (event_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_creator = result[0] if not USE_POSTGRES else result["created_by"]
    # Allow update if user is the host OR if user is admin
    if event_creator != event.created_by and event.created_by.lower() != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Only the event host or admin can update this event")
    
    # Update the event
    if USE_POSTGRES:
        c.execute(
            """
            UPDATE events SET
                name = %s,
                description = %s,
                location = %s,
                venue = %s,
                address = %s,
                coordinates = %s,
                date = %s,
                time = %s,
                category = %s,
                languages = %s,
                capacity = %s,
                image_url = %s
            WHERE id = %s
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
                event.capacity,
                event.image_url,
                event_id,
            ),
        )
    else:
        execute_query(c, """
            UPDATE events SET
                name = ?,
                description = ?,
                location = ?,
                venue = ?,
                address = ?,
                coordinates = ?,
                date = ?,
                time = ?,
                category = ?,
                languages = ?,
                capacity = ?,
                image_url = ?
            WHERE id = ?
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
            event.capacity,
            event.image_url,
            event_id,
        ))
    
    conn.commit()
    conn.close()
    return {"id": event_id, "message": "Event updated"}

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, username: str):
    """Delete an event (only the host can delete)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if the user is the host of the event or is admin
    execute_query(c, "SELECT created_by FROM events WHERE id = ?", (event_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    created_by = result["created_by"] if USE_POSTGRES else result[0]
    
    # Allow deletion if user is the host OR if user is admin
    if created_by != username and username.lower() != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Only the host or admin can delete this event")
    
    # Delete all participants first (foreign key constraint)
    execute_query(c, "DELETE FROM event_participants WHERE event_id = ?", (event_id,))
    
    # Delete the event
    execute_query(c, "DELETE FROM events WHERE id = ?", (event_id,))
    
    conn.commit()
    conn.close()
    return {"message": "Event deleted successfully"}

@app.get("/api/users/{username}/events")
def get_user_events(username: str):
    """Get all events a user has joined or is hosting"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
        SELECT DISTINCT e.id, e.name, e.description, e.location, e.venue, e.address, e.coordinates,
               e.date, e.time, e.category, e.languages, e.is_public, e.event_type, e.capacity, e.image_url, e.created_by, e.is_featured, e.template_event_id
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
                "imageUrl": normalize_image_url(row["image_url"] or ""),
                "createdBy": row["created_by"],
                "isFeatured": bool(row["is_featured"]),
                "templateEventId": row["template_event_id"],
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
                "imageUrl": normalize_image_url(row[14] or ""),
                "createdBy": row[15],
                "isFeatured": bool(row[16]),
                "templateEventId": row[17],
                "host": host,
                "participants": participants,
                "crew": crew
            })
    conn.close()
    return events

@app.get("/api/follows/{username}")
def get_follows(username: str):
    """Get user's follows list"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
        SELECT user2 FROM follows WHERE user1 = ?
        UNION
        SELECT user1 FROM follows WHERE user2 = ?
    """, (username, username))
    follows = [row[0] for row in c.fetchall()]
    conn.close()
    return follows

@app.post("/api/follows")
def add_follow(user1: str = Body(...), user2: str = Body(...)):
    """Add a follow"""
    conn = get_db_connection()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute(
            """
            INSERT INTO follows (user1, user2)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (user1, user2),
        )
    else:
        execute_query(c, "INSERT OR IGNORE INTO follows (user1, user2) VALUES (?, ?)", (user1, user2))
    conn.commit()
    conn.close()
    return {"message": "Follow added"}

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
    messages = []
    for row in c.fetchall():
        if USE_POSTGRES:
            messages.append({"username": row["username"], "message": row["message"], "timestamp": str(row["timestamp"])})
        else:
            messages.append({"username": row[0], "message": row[1], "timestamp": row[2]})
    conn.close()
    return messages

@app.post("/api/chat/{event_id}")
def send_chat_message(event_id: int, username: str = Body(...), message: str = Body(...)):
    """Send a chat message and create notifications for other participants"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Insert the message
    execute_query(c, """
        INSERT INTO chat_messages (event_id, username, message)
        VALUES (?, ?, ?)
    """, (event_id, username, message))
    
    # Get the message ID
    if USE_POSTGRES:
        execute_query(c, "SELECT lastval()")
        message_id = c.fetchone()[0]
    else:
        message_id = c.lastrowid
    
    # Get all participants of the event (including host)
    execute_query(c, """
        SELECT username FROM event_participants WHERE event_id = ?
    """, (event_id,))
    
    participants = []
    for row in c.fetchall():
        participant_name = row["username"] if USE_POSTGRES else row[0]
        # Don't notify the sender
        if participant_name != username:
            participants.append(participant_name)
    
    # Create notifications for all other participants
    for participant in participants:
        execute_query(c, """
            INSERT INTO notifications (user_id, event_id, message_id, is_read)
            VALUES (?, ?, ?, ?)
        """, (participant, event_id, message_id, False if USE_POSTGRES else 0))
    
    conn.commit()
    conn.close()
    return {"message": "Message sent", "notifications_created": len(participants)}

@app.get("/api/notifications/{username}")
def get_notifications(username: str):
    """Get unread notification count and details for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get unread notifications grouped by event
    execute_query(c, """
        SELECT event_id, COUNT(*) as unread_count
        FROM notifications
        WHERE user_id = ? AND is_read = ?
        GROUP BY event_id
    """, (username, False if USE_POSTGRES else 0))
    
    notifications = {}
    for row in c.fetchall():
        if USE_POSTGRES:
            notifications[row["event_id"]] = row["unread_count"]
        else:
            notifications[row[0]] = row[1]
    
    # Get total unread count
    total_unread = sum(notifications.values())
    
    conn.close()
    return {
        "total_unread": total_unread,
        "by_event": notifications
    }

@app.post("/api/notifications/{username}/mark-read")
def mark_notifications_read(username: str, request: dict = Body(...)):
    """Mark notifications as read for a user. If event_id provided, mark only for that event."""
    event_id = request.get("event_id", None)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if event_id is not None:
        # Mark notifications for specific event as read
        execute_query(c, """
            UPDATE notifications
            SET is_read = ?
            WHERE user_id = ? AND event_id = ?
        """, (True if USE_POSTGRES else 1, username, event_id))
    else:
        # Mark all notifications as read
        execute_query(c, """
            UPDATE notifications
            SET is_read = ?
            WHERE user_id = ?
        """, (True if USE_POSTGRES else 1, username))
    
    conn.commit()
    rows_affected = c.rowcount
    conn.close()
    return {"message": "Notifications marked as read", "count": rows_affected}

# Simple geocoding cache to reduce API calls
geocode_cache = {}

@app.get("/api/geocode")
async def geocode_proxy(q: str, limit: int = 5, countrycodes: str = "fr"):
    """Proxy endpoint for OpenStreetMap Nominatim to avoid CORS issues"""
    import httpx
    
    # Check cache first
    cache_key = f"{q.lower()}_{limit}_{countrycodes}"
    if cache_key in geocode_cache:
        print(f"📦 Returning cached geocoding result for: {q}")
        return geocode_cache[cache_key]
    
    # Fallback results for common Paris locations
    fallback_results = {
        "fleurus": [{
            "place_id": 1,
            "lat": "48.8486",
            "lon": "2.3286",
            "display_name": "Rue de Fleurus, Quartier de l'Odéon, Paris 6e Arrondissement, Paris, Île-de-France, France métropolitaine, 75006, France",
            "address": {
                "road": "Rue de Fleurus",
                "suburb": "Quartier de l'Odéon",
                "city": "Paris",
                "postcode": "75006",
                "country": "France"
            }
        }],
        "le fleurus": [{
            "place_id": 2,
            "lat": "48.8486",
            "lon": "2.3286",
            "display_name": "Le Fleurus, Rue de Fleurus, Quartier de l'Odéon, Paris 6e Arrondissement, Paris, France métropolitaine, 75006, France",
            "address": {
                "road": "Rue de Fleurus",
                "suburb": "Quartier de l'Odéon",
                "city": "Paris",
                "postcode": "75006",
                "country": "France"
            }
        }],
        "cité": [{
            "place_id": 3,
            "lat": "48.8499",
            "lon": "2.3464",
            "display_name": "Cité Internationale Universitaire de Paris, Paris, Île-de-France, France",
            "address": {
                "city": "Paris",
                "country": "France"
            }
        }]
    }
    
    # Check if we have a fallback for this query
    query_lower = q.lower().strip()
    if query_lower in fallback_results:
        print(f"🎯 Using fallback geocoding result for: {q}")
        return fallback_results[query_lower]
    
    try:
        print(f"🔍 Geocoding request: q={q}, limit={limit}, countrycodes={countrycodes}")
        
        # Add delay to respect Nominatim rate limit (1 request per second)
        import time
        import asyncio
        await asyncio.sleep(1.1)  # Wait 1.1 seconds between requests
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": q + ", Paris, France",  # Add context to improve results
                    "format": "json",
                    "addressdetails": 1,
                    "limit": limit,
                    "countrycodes": countrycodes
                },
                headers={
                    "User-Agent": "LemiCite/1.0 (contact@lemi-cite.app)",
                    "Referer": "https://lemi-cite.netlify.app"
                },
                timeout=10.0
            )
            print(f"✅ Geocoding response status: {response.status_code}")
            if response.status_code != 200:
                print(f"❌ Nominatim error: {response.text}")
                return []
            
            result = response.json()
            # Cache successful results
            if result:
                geocode_cache[cache_key] = result
            return result
            
    except httpx.TimeoutException as e:
        print(f"⏱️ Geocoding timeout: {e}")
        # Return empty array instead of error if timeout
        return []
    except httpx.HTTPError as e:
        print(f"🌐 HTTP error during geocoding: {e}")
        # Return empty array instead of error
        return []
    except Exception as e:
        print(f"❌ Error proxying geocode request: {e}")
        # Return empty array instead of error
        return []

@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image and return the URL"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.")

        # If S3/R2 is configured, upload to cloud storage for persistence; otherwise save to local disk (ephemeral)
        s3_bucket = os.environ.get("S3_BUCKET")
        s3_region = os.environ.get("S3_REGION", "auto")
        s3_prefix = os.environ.get("S3_PREFIX", "uploads/")
        s3_endpoint = os.environ.get("S3_ENDPOINT_URL")  # For R2, B2, or other S3-compatible
        s3_public_url = os.environ.get("S3_PUBLIC_URL")  # Optional: custom public URL base (e.g., R2 custom domain or .r2.dev)

        # Build a safe unique key/filename
        original = file.filename or "upload"
        safe_name = original.replace("/", "_").replace("\\", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
        key = f"{s3_prefix}{timestamp}_{safe_name}"

        if s3_bucket:
            if boto3 is None:
                raise HTTPException(status_code=500, detail="S3 upload requested but boto3 is not installed.")
            try:
                # Create S3 client with optional endpoint (for R2, B2, etc.)
                client_kwargs = {"region_name": s3_region}
                if s3_endpoint:
                    client_kwargs["endpoint_url"] = s3_endpoint
                s3_client = boto3.client("s3", **client_kwargs)
                
                # Upload with public-read ACL (skip ACL if unsupported by provider)
                extra = {"ContentType": file.content_type}
                try:
                    extra["ACL"] = "public-read"
                    s3_client.upload_fileobj(file.file, s3_bucket, key, ExtraArgs=extra)
                except Exception as acl_err:
                    # Some providers (R2) don't support ACL; retry without it
                    print(f"ACL not supported, uploading without ACL: {acl_err}")
                    del extra["ACL"]
                    file.file.seek(0)  # Reset file pointer
                    s3_client.upload_fileobj(file.file, s3_bucket, key, ExtraArgs=extra)
                
                # Construct public URL
                if s3_public_url:
                    # Use custom public URL base (e.g., https://pub-xxxxx.r2.dev or custom domain)
                    image_url = f"{s3_public_url.rstrip('/')}/{key}"
                elif s3_endpoint:
                    # For R2/B2 with endpoint: construct URL from endpoint + bucket + key
                    # R2 format: https://<bucket>.<account-id>.r2.cloudflarestorage.com/<key>
                    # Fallback: endpoint/bucket/key
                    base = s3_endpoint.rstrip("/")
                    image_url = f"{base}/{s3_bucket}/{key}"
                elif s3_region and s3_region != "auto":
                    image_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{key}"
                else:
                    image_url = f"https://{s3_bucket}.s3.amazonaws.com/{key}"
                return {"url": image_url}
            except HTTPException:
                raise
            except Exception as s3e:
                print(f"Error uploading to S3/R2: {s3e}")
                import traceback
                traceback.print_exc()
                # Fallback to local disk if S3 fails

        # Local disk fallback (WARNING: ephemeral on many hosts)
        upload_dir = Path("./static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / key.split("/")[-1]
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        backend_url = os.environ.get("BACKEND_URL", "https://fast-api-backend-qlyb.onrender.com")
        image_url = f"{backend_url}/static/uploads/{file_path.name}"
        return {"url": image_url}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/pending-requests")
def get_pending_requests():
    """Get all pending search requests for admin assignment"""
    conn = get_db_connection()
    c = conn.cursor()
    execute_query(c, """
        SELECT id, user_id, date, start_time, end_time, budget, type, category, language
        FROM search_requests
        ORDER BY id DESC
    """)
    requests = []
    for row in c.fetchall():
        if USE_POSTGRES:
            requests.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "date": row["date"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "budget": row["budget"],
                "type": row["type"],
                "category": row["category"],
                "language": row["language"]
            })
        else:
            requests.append({
                "id": row[0],
                "user_id": row[1],
                "date": row[2],
                "start_time": row[3],
                "end_time": row[4],
                "budget": row[5],
                "type": row[6],
                "category": row[7],
                "language": row[8]
            })
    conn.close()
    return requests
