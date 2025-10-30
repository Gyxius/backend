"""
Database wrapper to abstract SQLite vs PostgreSQL differences
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Check if we're using PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None
SQLITE_PATH = "./social.db"

def get_connection():
    """Get database connection"""
    if USE_POSTGRES:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        import sqlite3
        return sqlite3.connect(SQLITE_PATH)

def execute_query(query, params=None):
    """Execute a query and return cursor - automatically converts ? to %s for PostgreSQL"""
    conn = get_connection()
    c = conn.cursor()
    
    # Convert SQLite ? placeholders to PostgreSQL %s
    if USE_POSTGRES and query:
        # Count ? placeholders
        query = query.replace("?", "%s")
        # Handle INSERT OR IGNORE -> INSERT ... ON CONFLICT DO NOTHING
        if "INSERT OR IGNORE" in query.upper():
            query = query.replace("INSERT OR IGNORE", "INSERT").replace("INSERT or ignore", "INSERT")
            # Add ON CONFLICT clause if not present
            if "ON CONFLICT" not in query.upper():
                # This is a simple conversion - might need adjustment for specific cases
                query = query.rstrip(";") + " ON CONFLICT DO NOTHING"
    
    if params:
        c.execute(query, params)
    else:
        c.execute(query)
    
    conn.commit()
    return conn, c

def fetch_all(query, params=None):
    """Execute query and fetch all results"""
    conn, c = execute_query(query, params)
    results = c.fetchall()
    conn.close()
    return results

def fetch_one(query, params=None):
    """Execute query and fetch one result"""
    conn, c = execute_query(query, params)
    result = c.fetchone()
    conn.close()
    return result

def get_lastrowid(cursor):
    """Get last inserted row ID (works for both databases)"""
    if USE_POSTGRES:
        return cursor.fetchone()[0] if cursor.description else None
    else:
        return cursor.lastrowid
