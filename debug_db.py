#!/usr/bin/env python3
"""
Quick diagnostic to check what's in the PostgreSQL database
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "your-database-url-here")

if DATABASE_URL and DATABASE_URL != "your-database-url-here":
    # Fix postgres:// to postgresql://
    db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    c = conn.cursor()
    
    print("=" * 60)
    print("EVENTS TABLE")
    print("=" * 60)
    c.execute("SELECT id, name, created_by, is_public FROM events ORDER BY id")
    events = c.fetchall()
    for e in events:
        print(f"ID: {e['id']}, Name: {e['name']}, Created By: {e['created_by']}, Public: {e['is_public']}")
    
    print("\n" + "=" * 60)
    print("EVENT_PARTICIPANTS TABLE")
    print("=" * 60)
    c.execute("SELECT event_id, username, is_host FROM event_participants ORDER BY event_id")
    participants = c.fetchall()
    for p in participants:
        print(f"Event ID: {p['event_id']}, User: {p['username']}, Is Host: {p['is_host']}")
    
    conn.close()
else:
    print("Set DATABASE_URL environment variable to run this script")
    print("Get it from: https://dashboard.render.com -> Your Database -> Connection String")
