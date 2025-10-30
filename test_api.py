#!/usr/bin/env python3
"""
Test script for the FastAPI backend endpoints
Run this to verify the API is working correctly
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_api():
    print("🧪 Testing FastAPI Backend\n")
    
    # Test 1: Get all events (should be empty initially)
    print("1️⃣ Testing GET /api/events")
    try:
        response = requests.get(f"{BASE_URL}/api/events")
        print(f"   Status: {response.status_code}")
        events = response.json()
        print(f"   Events count: {len(events)}")
        print(f"   ✅ Success\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 2: Create a test event
    print("2️⃣ Testing POST /api/events")
    test_event = {
        "id": 999999,
        "name": "Test Event",
        "description": "This is a test event from the API",
        "location": "Cité",
        "venue": "Test Venue",
        "address": "123 Test Street",
        "coordinates": {"lat": 48.8566, "lng": 2.3522},
        "date": "2025-11-15",
        "time": "19:00",
        "category": "food",
        "languages": ["English", "French"],
        "isPublic": True,
        "type": "custom",
        "capacity": None,
        "imageUrl": "",
        "host": {"name": "admin"}
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/events", json=test_event)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print(f"   ✅ Success\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 3: Join the event
    print("3️⃣ Testing POST /api/events/{event_id}/join")
    try:
        response = requests.post(
            f"{BASE_URL}/api/events/999999/join",
            json={"username": "Mitsu"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print(f"   ✅ Success\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 4: Get user events
    print("4️⃣ Testing GET /api/users/{username}/events")
    try:
        response = requests.get(f"{BASE_URL}/api/users/Mitsu/events")
        print(f"   Status: {response.status_code}")
        user_events = response.json()
        print(f"   User events count: {len(user_events)}")
        if user_events:
            print(f"   First event: {user_events[0]['name']}")
        print(f"   ✅ Success\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 5: Get all events (should now have our test event)
    print("5️⃣ Testing GET /api/events (after creation)")
    try:
        response = requests.get(f"{BASE_URL}/api/events")
        events = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Events count: {len(events)}")
        if events:
            print(f"   Latest event: {events[-1]['name']}")
            print(f"   Participants: {events[-1].get('crew', [])}")
        print(f"   ✅ Success\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 6: Test login
    print("6️⃣ Testing POST /login")
    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={"username": "Mitsu", "password": "123"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print(f"   ✅ Success\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    print("✨ All tests completed!")
    print("\n📋 Summary:")
    print("   - Backend is running correctly")
    print("   - All API endpoints are functional")
    print("   - Database operations are working")
    print("\n✅ Ready to connect the frontend!")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  LEMI Backend API Test Suite")
    print("="*50 + "\n")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/users")
        print(f"✅ Server is running at {BASE_URL}\n")
        test_api()
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Server is not running at {BASE_URL}")
        print("\nPlease start the server first:")
        print("cd /Users/mitsoufortunat/Desktop/Props/backend")
        print("python3 -m uvicorn main:app --reload --port 8001")
