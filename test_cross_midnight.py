#!/usr/bin/env python3
"""Test cross-midnight end_time (e.g., 22:30 → 02:00)."""
import requests, json
BASE = "http://127.0.0.1:8001"

# Create event with cross-midnight end_time
payload = {
  "name": "Cross-Midnight Event",
  "description": "Event ending past midnight",
  "location": "Test Hall",
  "venue": "Room B",
  "address": "2 Test Way",
  "coordinates": {"lat": 48.8566, "lng": 2.3522},
  "date": "2025-11-22",
  "time": "22:30",
  "end_time": "02:00",  # next day
  "category": "nightlife",
  "languages": ["English"],
  "is_public": True,
  "event_type": "custom",
  "capacity": 50,
  "image_url": "",
  "created_by": "admin",
  "is_featured": False
}

r = requests.post(f"{BASE}/api/events", json=payload)
print("Create status:", r.status_code, r.text)
assert r.ok, f"Failed: {r.text}"
new_id = r.json().get("id")

# Fetch to confirm
r2 = requests.get(f"{BASE}/api/events/{new_id}")
print("Fetched event:", json.dumps(r2.json(), indent=2))
assert r2.json()["time"] == "22:30"
assert r2.json()["endTime"] == "02:00"

print("\n✅ Cross-midnight event created and persisted successfully!")
