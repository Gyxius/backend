#!/usr/bin/env python3
"""
Script to hide/archive events created by TestUser
This sets is_archived = TRUE for all events created by 'TestUser'
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from db_wrapper import get_connection, USE_POSTGRES

def hide_test_events():
    """Archive all events created by TestUser"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # First, check how many events will be affected
        if USE_POSTGRES:
            cursor.execute("""
                SELECT id, name, created_by 
                FROM events 
                WHERE created_by = %s AND is_archived = FALSE
            """, ('TestUser',))
        else:
            cursor.execute("""
                SELECT id, name, created_by 
                FROM events 
                WHERE created_by = ? AND is_archived = 0
            """, ('TestUser',))
        
        events = cursor.fetchall()
        
        if not events:
            print("✅ No test events found to archive (or they're already archived)")
            conn.close()
            return
        
        print(f"📋 Found {len(events)} test events to archive:")
        for event in events:
            if USE_POSTGRES:
                print(f"   - ID: {event['id']}, Name: {event['name']}")
            else:
                print(f"   - ID: {event[0]}, Name: {event[1]}")
        
        # Ask for confirmation
        confirm = input("\n⚠️  Archive these events? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("❌ Cancelled")
            conn.close()
            return
        
        # Archive the events
        if USE_POSTGRES:
            cursor.execute("""
                UPDATE events 
                SET is_archived = TRUE 
                WHERE created_by = %s
            """, ('TestUser',))
        else:
            cursor.execute("""
                UPDATE events 
                SET is_archived = 1 
                WHERE created_by = ?
            """, ('TestUser',))
        
        conn.commit()
        print(f"✅ Successfully archived {cursor.rowcount} events created by TestUser")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

def unhide_test_events():
    """Unarchive all events created by TestUser (in case you need to undo)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                UPDATE events 
                SET is_archived = FALSE 
                WHERE created_by = %s
            """, ('TestUser',))
        else:
            cursor.execute("""
                UPDATE events 
                SET is_archived = 0 
                WHERE created_by = ?
            """, ('TestUser',))
        
        conn.commit()
        print(f"✅ Successfully unarchived {cursor.rowcount} events created by TestUser")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "unhide":
        print("🔄 Unarchiving test events...")
        unhide_test_events()
    else:
        print("📦 Archiving test events...")
        hide_test_events()
