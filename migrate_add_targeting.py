#!/usr/bin/env python3
"""
Migration: Add targeting columns to events table
"""
import os
from db_wrapper import get_connection

def migrate():
    """Add targeting columns to events table"""
    conn = get_connection()
    c = conn.cursor()
    
    USE_POSTGRES = os.getenv("DATABASE_URL", "").startswith("postgres")
    
    try:
        if USE_POSTGRES:
            # Check and add target_interests column
            c.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='events' AND column_name='target_interests'
            """)
            if not c.fetchone():
                print("📝 Adding target_interests column...")
                c.execute("ALTER TABLE events ADD COLUMN target_interests TEXT")
                print("✅ target_interests column added")
            else:
                print("✅ target_interests column already exists")
            
            # Check and add target_cite_connection column
            c.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='events' AND column_name='target_cite_connection'
            """)
            if not c.fetchone():
                print("📝 Adding target_cite_connection column...")
                c.execute("ALTER TABLE events ADD COLUMN target_cite_connection TEXT")
                print("✅ target_cite_connection column added")
            else:
                print("✅ target_cite_connection column already exists")
            
            # Check and add target_reasons column
            c.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='events' AND column_name='target_reasons'
            """)
            if not c.fetchone():
                print("📝 Adding target_reasons column...")
                c.execute("ALTER TABLE events ADD COLUMN target_reasons TEXT")
                print("✅ target_reasons column added")
            else:
                print("✅ target_reasons column already exists")
        else:
            # SQLite: Check existing columns
            c.execute("PRAGMA table_info(events)")
            existing_cols = [row[1] for row in c.fetchall()]
            
            if 'target_interests' not in existing_cols:
                print("📝 Adding target_interests column...")
                c.execute("ALTER TABLE events ADD COLUMN target_interests TEXT")
                print("✅ target_interests column added")
            else:
                print("✅ target_interests column already exists")
            
            if 'target_cite_connection' not in existing_cols:
                print("📝 Adding target_cite_connection column...")
                c.execute("ALTER TABLE events ADD COLUMN target_cite_connection TEXT")
                print("✅ target_cite_connection column added")
            else:
                print("✅ target_cite_connection column already exists")
            
            if 'target_reasons' not in existing_cols:
                print("📝 Adding target_reasons column...")
                c.execute("ALTER TABLE events ADD COLUMN target_reasons TEXT")
                print("✅ target_reasons column added")
            else:
                print("✅ target_reasons column already exists")
        
        conn.commit()
        print("\n✅ Migration complete!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
