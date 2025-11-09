#!/usr/bin/env python3
"""
Create an Admin user profile in the database.
This profile is used for admin-created events to have a valid host.
"""
import os
import sys
import json
from db_wrapper import get_connection

def create_admin_profile():
    """Create an Admin user with a complete profile."""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Check if Admin user already exists
        c.execute("SELECT id FROM users WHERE username = ?", ("Admin",))
        existing = c.fetchone()
        
        if existing:
            print("Admin user already exists.")
            admin_id = existing[0]
        else:
            # Create Admin user
            c.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
            """, ("Admin", "SYSTEM_ADMIN_NO_PASSWORD"))
            admin_id = c.lastrowid
            print(f"Created Admin user with ID: {admin_id}")
        
        # Check if profile exists
        c.execute("SELECT username FROM user_profiles WHERE username = ?", ("Admin",))
        profile_exists = c.fetchone()
        
        # Create profile JSON
        profile_data = {
            "name": "Cité Internationale Admin",
            "age": None,
            "gender": "System",
            "nationality": ["International"],
            "homeCountries": ["International"],
            "bio": "Official Cité Internationale event organizer and administrator.",
            "interests": ["Events", "Community", "Culture"],
            "languages": ["French", "English"],
            "profile_pic": None,
            "citeConnection": "staff",
            "reasonsForStay": ["work"]
        }
        
        profile_json = json.dumps(profile_data)
        
        if profile_exists:
            print("Admin profile already exists. Updating...")
            c.execute("""
                UPDATE user_profiles 
                SET profile_json = ?
                WHERE username = ?
            """, (profile_json, "Admin"))
            print("Admin profile updated.")
        else:
            # Create Admin profile
            c.execute("""
                INSERT INTO user_profiles (username, profile_json)
                VALUES (?, ?)
            """, ("Admin", profile_json))
            print("Admin profile created.")
        
        conn.commit()
        print("\n✅ Admin profile setup complete!")
        
        # Verify the profile
        c.execute("SELECT * FROM user_profiles WHERE username = ?", ("Admin",))
        profile = c.fetchone()
        if profile:
            print("\nAdmin profile details:")
            print(f"  Username: {profile[0]}")
            profile_obj = json.loads(profile[1])
            print(f"  Name: {profile_obj.get('name')}")
            print(f"  Bio: {profile_obj.get('bio')}")
        
    except Exception as e:
        print(f"❌ Error creating Admin profile: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin_profile()
