"""
Migration script to add is_archived column to events table
Run this with: python3 migrate_add_is_archived.py
"""

import os
import sys

# Add the backend directory to the path so we can import db_wrapper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Determine database type
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

def migrate():
    if USE_POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        import sqlite3
        conn = sqlite3.connect("./social.db")
    
    c = conn.cursor()
    
    try:
        # Check if column already exists
        if USE_POSTGRES:
            c.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'events' AND column_name = 'is_archived'
            """)
            existing = c.fetchone()
            if existing:
                print("✓ Column is_archived already exists")
                conn.close()
                return
            
            # Add the column
            c.execute("ALTER TABLE events ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
        else:
            c.execute("PRAGMA table_info(events)")
            columns = [row[1] for row in c.fetchall()]
            if 'is_archived' in columns:
                print("✓ Column is_archived already exists")
                conn.close()
                return
            
            # Add the column
            c.execute("ALTER TABLE events ADD COLUMN is_archived INTEGER DEFAULT 0")
        
        conn.commit()
        print("✓ Successfully added is_archived column to events table")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
