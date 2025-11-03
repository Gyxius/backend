#!/usr/bin/env python3
"""
Migration script to add is_featured column to PostgreSQL database
Run this once on Render to update the production database schema
"""
import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    exit(1)

print(f"🔗 Connecting to database...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("✅ Connected to database")
    
    # Check if column already exists
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='events' AND column_name='is_featured';
    """)
    
    if cursor.fetchone():
        print("✅ Column 'is_featured' already exists!")
    else:
        print("📝 Adding 'is_featured' column to events table...")
        
        # Add the column
        cursor.execute("""
            ALTER TABLE events 
            ADD COLUMN is_featured INTEGER DEFAULT 0;
        """)
        
        # Update existing admin-created events to be featured
        cursor.execute("""
            UPDATE events 
            SET is_featured = 1 
            WHERE created_by = 'admin' AND capacity IS NULL;
        """)
        
        conn.commit()
        print("✅ Successfully added 'is_featured' column!")
        print("✅ Updated admin-created events to be featured")
    
    cursor.close()
    conn.close()
    print("✅ Migration complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
