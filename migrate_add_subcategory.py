#!/usr/bin/env python3
"""
Migration script to add subcategory column to events table
"""
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

def migrate_sqlite():
    """Add subcategory column to SQLite database"""
    conn = sqlite3.connect("social.db")
    c = conn.cursor()
    
    try:
        # Check if column already exists
        c.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in c.fetchall()]
        
        if "subcategory" not in columns:
            print("Adding subcategory column to events table...")
            c.execute("ALTER TABLE events ADD COLUMN subcategory TEXT DEFAULT ''")
            conn.commit()
            print("✅ Successfully added subcategory column to SQLite database")
        else:
            print("ℹ️  subcategory column already exists in SQLite database")
    
    except Exception as e:
        print(f"❌ Error migrating SQLite: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_postgres():
    """Add subcategory column to PostgreSQL database"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set for PostgreSQL")
        return
    
    # Fix Render's postgres:// to postgresql://
    db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    c = conn.cursor()
    
    try:
        # Check if column already exists
        c.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events' AND column_name = 'subcategory'
        """)
        exists = c.fetchone()
        
        if not exists:
            print("Adding subcategory column to events table...")
            c.execute("ALTER TABLE events ADD COLUMN subcategory TEXT DEFAULT ''")
            conn.commit()
            print("✅ Successfully added subcategory column to PostgreSQL database")
        else:
            print("ℹ️  subcategory column already exists in PostgreSQL database")
    
    except Exception as e:
        print(f"❌ Error migrating PostgreSQL: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting migration to add subcategory column...")
    
    if USE_POSTGRES:
        print("Using PostgreSQL database")
        migrate_postgres()
    else:
        print("Using SQLite database")
        migrate_sqlite()
    
    print("Migration complete!")
