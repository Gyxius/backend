#!/usr/bin/env python3
import requests, time, json
BASE = "http://127.0.0.1:8001"

# Create event with end_time
create_payload = {
  "name": "Admin HTTP EndTime Test",
  "description": "HTTP test for end_time (same-day)",
  "location": "Test Hall",
  "venue": "Room A",
  "address": "1 Test Way",
  "coordinates": {"lat": 48.8566, "lng": 2.3522},
  "date": "2025-11-21",
  "time": "19:00",
  "end_time": "22:15",  # same-day end time to pass current backend validation
  "category": "music",
  "languages": ["English"],
  "is_public": True,
  "event_type": "custom",
  "capacity": 25,
  "image_url": "",
  "created_by": "admin",
  "is_featured": False
}

r = requests.post(f"{BASE}/api/events", json=create_payload)
print("Create status:", r.status_code, r.text)
assert r.ok, r.text
new_id = r.json().get("id")

# Fetch by id
r2 = requests.get(f"{BASE}/api/events/{new_id}")
print("Get status:", r2.status_code)
print("Get body:", json.dumps(r2.json(), indent=2))
assert r2.ok
assert r2.json().get("endTime") == "22:15", f"endTime mismatch after create: {r2.json().get('endTime')}"

# Update end_time
body = r2.json()
update_payload = {
  "name": body["name"],
  "description": body["description"],
  "location": body["location"],
  "venue": body["venue"],
  "address": body["address"],
  "coordinates": body.get("coordinates"),
  "date": body["date"],
  "time": body["time"],
  "end_time": "22:30",
  "category": body["category"],
  "languages": body["languages"],
  "is_public": body["isPublic"],
  "event_type": body["type"],
  "capacity": body.get("capacity"),
  "image_url": body["imageUrl"],
  "created_by": body["createdBy"],
  "is_featured": body.get("isFeatured", False),
  "template_event_id": body.get("templateEventId"),
  "target_interests": body.get("targetInterests"),
  "target_cite_connection": body.get("targetCiteConnection"),
  "target_reasons": body.get("targetReasons"),
}

r3 = requests.put(f"{BASE}/api/events/{new_id}", json=update_payload)
print("Update status:", r3.status_code, r3.text)
assert r3.ok, r3.text

# Fetch again
r4 = requests.get(f"{BASE}/api/events/{new_id}")
print("Get2 status:", r4.status_code)
print("Get2 body:", json.dumps(r4.json(), indent=2))
assert r4.ok
assert r4.json().get("endTime") == "22:30", f"endTime mismatch after update: {r4.json().get('endTime')}"

print("\n✅ HTTP flow: end_time persisted and updated successfully.")
