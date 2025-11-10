#!/usr/bin/env python3
"""Quick verification of end_time persistence for admin events using in-process TestClient.
Run: python test_end_time_admin.py
"""
from fastapi.testclient import TestClient
from main import app, FullEvent
import json

client = TestClient(app)

# 1. Create an event with an end_time as admin
create_payload = {
    "name": "Admin EndTime Test",
    "description": "Event to verify end_time persistence",
    "location": "Test Hall",
    "venue": "Main Room",
    "address": "123 Admin Ave",
    "coordinates": {"lat": 48.8566, "lng": 2.3522},
    "date": "2025-11-20",
    "time": "22:30",
    "end_time": "02:15",  # crosses midnight logical scenario
    "category": "music",
    "languages": ["English"],
    "is_public": True,
    "event_type": "custom",
    "capacity": 50,
    "image_url": "",
    "created_by": "admin",
    "is_featured": False,
}

r_create = client.post("/api/events", json=create_payload)
assert r_create.status_code == 200, f"Create failed: {r_create.status_code} {r_create.text}"
new_id = r_create.json().get("id")
print(f"Created event id={new_id}")

# 2. Fetch the event and confirm endTime returned
r_get = client.get(f"/api/events/{new_id}")
assert r_get.status_code == 200, f"Fetch failed: {r_get.status_code} {r_get.text}"
body = r_get.json()
print("Fetched event payload:", json.dumps(body, indent=2))
assert body.get("endTime") == "02:15", f"endTime mismatch after create: {body.get('endTime')}"

# 3. Update the event's end_time
update_payload = {
    "name": body["name"],
    "description": body["description"],
    "location": body["location"],
    "venue": body["venue"],
    "address": body["address"],
    "coordinates": body.get("coordinates"),
    "date": body["date"],
    "time": body["time"],
    "end_time": "03:00",  # new end time
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

r_update = client.put(f"/api/events/{new_id}", json=update_payload)
assert r_update.status_code == 200, f"Update failed: {r_update.status_code} {r_update.text}"
print("Update response:", r_update.json())

# 4. Fetch again to confirm updated endTime
r_get2 = client.get(f"/api/events/{new_id}")
assert r_get2.status_code == 200, f"Second fetch failed: {r_get2.status_code} {r_get2.text}"
body2 = r_get2.json()
print("Fetched updated event payload:", json.dumps(body2, indent=2))
assert body2.get("endTime") == "03:00", f"endTime mismatch after update: {body2.get('endTime')}"

print("\n✅ end_time persisted and updated successfully for admin event.")
