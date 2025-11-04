#!/usr/bin/env python3
"""
Quick script to add is_featured column to Render PostgreSQL database
"""
import psycopg2

DATABASE_URL = "postgresql://lemi:RK018pVqX9cI4FwNihHghLsX4EdvBlvk@dpg-d43t122li9vc73dfrq10-a.frankfurt-postgres.render.com/lemi"

print("🔗 Connecting to Render PostgreSQL database...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("✅ Connected!")
    
    # Check if column exists
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='events' AND column_name='is_featured'
    """)
    
    if cursor.fetchone():
        print("✅ Column 'is_featured' already exists!")
    else:
        print("📝 Adding 'is_featured' column...")
        
        cursor.execute("ALTER TABLE events ADD COLUMN is_featured BOOLEAN DEFAULT FALSE")
        cursor.execute("UPDATE events SET is_featured = TRUE WHERE created_by = 'admin' AND capacity IS NULL")
        
        conn.commit()
        print("✅ Successfully added 'is_featured' column!")
        print("✅ Updated admin events to be featured")
    
    cursor.close()
    conn.close()
    print("✅ Done!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
