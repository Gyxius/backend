#!/usr/bin/env python3
"""
Script to call the API endpoint to archive TestUser events
Usage: python3 archive_test_events_api.py [API_URL]
Example: python3 archive_test_events_api.py https://your-backend.onrender.com
"""
import requests
import sys

def archive_test_events(api_url):
    """Call the API to archive test events"""
    endpoint = f"{api_url}/api/admin/archive-test-events"
    
    print(f"🔗 Calling endpoint: {endpoint}")
    print(f"📦 Archiving events created by TestUser...")
    
    try:
        response = requests.post(
            endpoint,
            params={"admin_username": "admin"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            print(f"📊 Archived {data['archived_count']} events")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        api_url = sys.argv[1].rstrip('/')
    else:
        # Prompt for URL
        print("Enter your backend API URL (e.g., https://your-backend.onrender.com):")
        api_url = input().strip().rstrip('/')
    
    if not api_url:
        print("❌ No API URL provided")
        sys.exit(1)
    
    archive_test_events(api_url)
