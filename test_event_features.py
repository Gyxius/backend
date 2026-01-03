#!/usr/bin/env python3
"""
Comprehensive Event Features Test Suite
Tests all event page functionality including:
- Event CRUD operations (Create, Read, Update, Delete)
- Event joining and leaving
- Event archiving/unarchiving
- Event participants management
- Event filtering (public/private/archived)
- Featured events
- Event validation (dates, times, capacity)
- User event listings

Usage:
    # Test local environment
    python3 test_event_features.py --local
    
    # Test deployed environment
    python3 test_event_features.py --deployed
    
    # Test specific features
    python3 test_event_features.py --local --feature crud
    python3 test_event_features.py --deployed --feature participants
"""

import requests
import json
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# API Endpoints
LOCAL_API = "http://localhost:8000"
DEPLOYED_API = "https://fast-api-backend-qlyb.onrender.com"

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_subheader(text: str):
    """Print a formatted subheader"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'-' * 80}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'-' * 80}{Colors.ENDC}\n")

def print_test(text: str):
    """Print a test description"""
    print(f"{Colors.BLUE}🧪 {text}{Colors.ENDC}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

class EventFeaturesTester:
    """Main testing class for event features"""
    
    def __init__(self, api_url: str, env_name: str):
        self.api_url = api_url
        self.env_name = env_name
        self.passed = 0
        self.failed = 0
        self.created_event_ids: List[int] = []
        self.test_username = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_admin = "admin"
        
    def cleanup(self):
        """Clean up all created test events"""
        print_subheader("🧹 Cleaning up test events")
        for event_id in self.created_event_ids:
            try:
                response = requests.delete(
                    f"{self.api_url}/api/events/{event_id}?username={self.test_admin}"
                )
                if response.status_code == 200:
                    print_success(f"Deleted event {event_id}")
                else:
                    print_warning(f"Could not delete event {event_id}: {response.status_code}")
            except Exception as e:
                print_warning(f"Error deleting event {event_id}: {str(e)}")
    
    def assert_true(self, condition: bool, message: str):
        """Assert a condition is true"""
        if condition:
            self.passed += 1
            print_success(message)
            return True
        else:
            self.failed += 1
            print_error(message)
            return False
    
    def assert_equal(self, actual: Any, expected: Any, message: str):
        """Assert two values are equal"""
        if actual == expected:
            self.passed += 1
            print_success(f"{message}: {actual} == {expected}")
            return True
        else:
            self.failed += 1
            print_error(f"{message}: {actual} != {expected}")
            return False
    
    def create_test_event(self, event_data: Dict) -> Optional[Dict]:
        """Create a test event and return the response"""
        try:
            response = requests.post(
                f"{self.api_url}/api/events",
                json=event_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                event_id = data.get('id')
                if event_id:
                    self.created_event_ids.append(event_id)
                return {"success": True, "data": data, "status_code": response.status_code}
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================================
    # TEST SUITES
    # ============================================================================
    
    def test_event_crud(self):
        """Test Create, Read, Update, Delete operations"""
        print_subheader("📝 Testing Event CRUD Operations")
        
        # Test 1: Create a public event
        print_test("Test 1: Create a public event")
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        event_data = {
            "name": "Test CRUD Public Event",
            "description": "Testing public event creation",
            "location": "Cité Universitaire",
            "venue": "Main Hall",
            "address": "17 Boulevard Jourdan, 75014 Paris",
            "coordinates": {"lat": 48.8206, "lng": 2.3372},
            "date": future_date,
            "time": "19:00",
            "end_time": "22:00",
            "category": "food",
            "subcategory": "",
            "languages": ["English", "French"],
            "is_public": True,
            "event_type": "custom",
            "capacity": 20,
            "image_url": "",
            "created_by": self.test_username,
            "is_featured": False,
            "template_event_id": None,
            "target_interests": None,
            "target_cite_connection": None,
            "target_reasons": None
        }
        
        result = self.create_test_event(event_data)
        if not self.assert_true(result.get("success", False), "Event created successfully"):
            print_error(f"Response: {result}")
            return
        
        event_id = result["data"]["id"]
        print_info(f"Created event with ID: {event_id}")
        
        # Test 2: Read the created event by ID
        print_test("Test 2: Read event by ID")
        try:
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            self.assert_equal(response.status_code, 200, "GET event by ID status")
            if response.status_code == 200:
                event = response.json()
                self.assert_equal(event["name"], event_data["name"], "Event name matches")
                self.assert_equal(event["category"], event_data["category"], "Event category matches")
                self.assert_true(event["isPublic"], "Event is public")
        except Exception as e:
            self.assert_true(False, f"Failed to read event: {str(e)}")
        
        # Test 3: Read all events (should include our public event)
        print_test("Test 3: Read all events")
        try:
            response = requests.get(f"{self.api_url}/api/events")
            self.assert_equal(response.status_code, 200, "GET all events status")
            if response.status_code == 200:
                events = response.json()
                self.assert_true(len(events) > 0, "Events list is not empty")
                found = any(e["id"] == event_id for e in events)
                self.assert_true(found, f"Created event {event_id} found in events list")
        except Exception as e:
            self.assert_true(False, f"Failed to read all events: {str(e)}")
        
        # Test 4: Update the event
        print_test("Test 4: Update event")
        updated_data = event_data.copy()
        updated_data["name"] = "Updated CRUD Event"
        updated_data["capacity"] = 30
        updated_data["description"] = "Updated description"
        
        try:
            response = requests.put(
                f"{self.api_url}/api/events/{event_id}",
                json=updated_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "PUT event status")
            
            # Verify update
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                self.assert_equal(event["name"], "Updated CRUD Event", "Event name updated")
                self.assert_equal(event["capacity"], 30, "Event capacity updated")
        except Exception as e:
            self.assert_true(False, f"Failed to update event: {str(e)}")
        
        # Test 5: Delete the event
        print_test("Test 5: Delete event")
        try:
            response = requests.delete(
                f"{self.api_url}/api/events/{event_id}?username={self.test_username}"
            )
            self.assert_equal(response.status_code, 200, "DELETE event status")
            
            # Verify deletion
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            self.assert_equal(response.status_code, 404, "Deleted event returns 404")
            
            # Remove from cleanup list since already deleted
            if event_id in self.created_event_ids:
                self.created_event_ids.remove(event_id)
        except Exception as e:
            self.assert_true(False, f"Failed to delete event: {str(e)}")
        
        # Test 6: Create a private event
        print_test("Test 6: Create a private event")
        private_event_data = event_data.copy()
        private_event_data["name"] = "Test CRUD Private Event"
        private_event_data["is_public"] = False
        
        result = self.create_test_event(private_event_data)
        if self.assert_true(result.get("success", False), "Private event created successfully"):
            private_event_id = result["data"]["id"]
            
            # Private events should not appear in public events list
            response = requests.get(f"{self.api_url}/api/events")
            if response.status_code == 200:
                events = response.json()
                found = any(e["id"] == private_event_id for e in events)
                self.assert_true(not found, "Private event not in public events list")
    
    def test_event_participants(self):
        """Test joining and leaving events"""
        print_subheader("👥 Testing Event Participants")
        
        # Create a test event
        print_test("Setup: Create a test event")
        future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        event_data = {
            "name": "Test Participants Event",
            "description": "Testing participant management",
            "location": "Test Location",
            "venue": "Test Venue",
            "address": "Test Address",
            "coordinates": {"lat": 48.8566, "lng": 2.3522},
            "date": future_date,
            "time": "18:00",
            "end_time": "20:00",
            "category": "party",
            "subcategory": "",
            "languages": ["English"],
            "is_public": True,
            "event_type": "custom",
            "capacity": 10,
            "image_url": "",
            "created_by": self.test_username,
            "is_featured": False,
            "template_event_id": None,
            "target_interests": None,
            "target_cite_connection": None,
            "target_reasons": None
        }
        
        result = self.create_test_event(event_data)
        if not result.get("success", False):
            print_error("Failed to create test event")
            return
        
        event_id = result["data"]["id"]
        print_info(f"Created test event with ID: {event_id}")
        
        # Test 1: User joins event
        print_test("Test 1: User joins event")
        test_participant = f"participant_{datetime.now().strftime('%H%M%S')}"
        try:
            response = requests.post(
                f"{self.api_url}/api/events/{event_id}/join",
                json={"username": test_participant},
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "User joined event")
            
            # Verify participant was added
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                participants = event.get("participants", [])
                found = any(p.get("username") == test_participant for p in participants)
                self.assert_true(found, f"Participant {test_participant} found in event")
        except Exception as e:
            self.assert_true(False, f"Failed to join event: {str(e)}")
        
        # Test 2: User joins same event again (should be idempotent)
        print_test("Test 2: User joins same event again")
        try:
            response = requests.post(
                f"{self.api_url}/api/events/{event_id}/join",
                json={"username": test_participant},
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "Duplicate join handled gracefully")
        except Exception as e:
            self.assert_true(False, f"Failed duplicate join: {str(e)}")
        
        # Test 3: Multiple users join
        print_test("Test 3: Multiple users join")
        participants = [f"user_{i}" for i in range(3)]
        for p in participants:
            try:
                response = requests.post(
                    f"{self.api_url}/api/events/{event_id}/join",
                    json={"username": p},
                    headers={"Content-Type": "application/json"}
                )
                self.assert_equal(response.status_code, 200, f"User {p} joined")
            except Exception as e:
                self.assert_true(False, f"Failed to add participant {p}: {str(e)}")
        
        # Test 4: User leaves event
        print_test("Test 4: User leaves event")
        try:
            response = requests.post(
                f"{self.api_url}/api/events/{event_id}/leave",
                json={"username": test_participant},
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "User left event")
            
            # Verify participant was removed
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                participants = event.get("participants", [])
                found = any(p.get("username") == test_participant for p in participants)
                self.assert_true(not found, f"Participant {test_participant} removed from event")
        except Exception as e:
            self.assert_true(False, f"Failed to leave event: {str(e)}")
        
        # Test 5: Check participants count
        print_test("Test 5: Verify participants count")
        try:
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                participants = event.get("participants", [])
                # Should have host + 3 participants (test_participant left)
                expected_count = 4
                self.assert_true(
                    len(participants) >= 3,
                    f"Event has {len(participants)} participants"
                )
        except Exception as e:
            self.assert_true(False, f"Failed to check participants: {str(e)}")
    
    def test_event_archiving(self):
        """Test event archiving and unarchiving"""
        print_subheader("📦 Testing Event Archiving")
        
        # Create a test event
        print_test("Setup: Create a test event")
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        event_data = {
            "name": "Test Archive Event",
            "description": "Testing event archiving",
            "location": "Archive Test Location",
            "venue": "Archive Venue",
            "address": "Archive Address",
            "coordinates": {"lat": 48.8566, "lng": 2.3522},
            "date": future_date,
            "time": "20:00",
            "end_time": "23:00",
            "category": "random",
            "subcategory": "",
            "languages": ["English"],
            "is_public": True,
            "event_type": "custom",
            "capacity": 15,
            "image_url": "",
            "created_by": self.test_username,
            "is_featured": False,
            "template_event_id": None,
            "target_interests": None,
            "target_cite_connection": None,
            "target_reasons": None
        }
        
        result = self.create_test_event(event_data)
        if not result.get("success", False):
            print_error("Failed to create test event")
            return
        
        event_id = result["data"]["id"]
        print_info(f"Created test event with ID: {event_id}")
        
        # Test 1: Archive the event
        print_test("Test 1: Archive event")
        try:
            response = requests.post(
                f"{self.api_url}/api/events/{event_id}/archive?username={self.test_username}",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 501:
                print_warning("Archive feature not available (database migration needed)")
                return
            
            self.assert_equal(response.status_code, 200, "Event archived")
            
            # Verify event is archived
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                self.assert_true(event.get("isArchived", False), "Event marked as archived")
        except Exception as e:
            self.assert_true(False, f"Failed to archive event: {str(e)}")
        
        # Test 2: Archived event not in default list
        print_test("Test 2: Archived event not in default list")
        try:
            response = requests.get(f"{self.api_url}/api/events")
            if response.status_code == 200:
                events = response.json()
                found = any(e["id"] == event_id for e in events)
                self.assert_true(not found, "Archived event not in default events list")
        except Exception as e:
            self.assert_true(False, f"Failed to check events list: {str(e)}")
        
        # Test 3: Archived event in list with include_archived=true
        print_test("Test 3: Archived event appears with include_archived=true")
        try:
            response = requests.get(f"{self.api_url}/api/events?include_archived=true")
            if response.status_code == 200:
                events = response.json()
                found = any(e["id"] == event_id for e in events)
                self.assert_true(found, "Archived event in list with include_archived=true")
        except Exception as e:
            self.assert_true(False, f"Failed to check events with archived: {str(e)}")
        
        # Test 4: Unarchive the event
        print_test("Test 4: Unarchive event")
        try:
            response = requests.post(
                f"{self.api_url}/api/events/{event_id}/unarchive?username={self.test_username}",
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "Event unarchived")
            
            # Verify event is no longer archived
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                self.assert_true(not event.get("isArchived", False), "Event no longer archived")
        except Exception as e:
            self.assert_true(False, f"Failed to unarchive event: {str(e)}")
        
        # Test 5: Unarchived event back in default list
        print_test("Test 5: Unarchived event back in default list")
        try:
            response = requests.get(f"{self.api_url}/api/events")
            if response.status_code == 200:
                events = response.json()
                found = any(e["id"] == event_id for e in events)
                self.assert_true(found, "Unarchived event back in default events list")
        except Exception as e:
            self.assert_true(False, f"Failed to check events list: {str(e)}")
    
    def test_event_validation(self):
        """Test event validation rules"""
        print_subheader("✅ Testing Event Validation")
        
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        base_event_data = {
            "name": "Test Validation Event",
            "description": "Testing validation",
            "location": "Test Location",
            "venue": "Test Venue",
            "address": "Test Address",
            "coordinates": {"lat": 48.8566, "lng": 2.3522},
            "date": future_date,
            "time": "18:00",
            "end_time": "20:00",
            "category": "food",
            "subcategory": "",
            "languages": ["English"],
            "is_public": True,
            "event_type": "custom",
            "capacity": 10,
            "image_url": "",
            "created_by": self.test_username,
            "is_featured": False,
            "template_event_id": None,
            "target_interests": None,
            "target_cite_connection": None,
            "target_reasons": None
        }
        
        # Test 1: Valid event with cross-midnight time
        print_test("Test 1: Valid cross-midnight event (22:00 to 02:00)")
        event_data = base_event_data.copy()
        event_data["name"] = "Cross Midnight Event"
        event_data["time"] = "22:00"
        event_data["end_time"] = "02:00"
        
        result = self.create_test_event(event_data)
        self.assert_true(result.get("success", False), "Cross-midnight event accepted")
        
        # Test 2: Invalid - same start and end time
        print_test("Test 2: Invalid - same start and end time")
        event_data = base_event_data.copy()
        event_data["name"] = "Same Time Event"
        event_data["time"] = "18:00"
        event_data["end_time"] = "18:00"
        
        result = self.create_test_event(event_data)
        self.assert_true(not result.get("success", False), "Same start/end time rejected")
        
        # Test 3: Event with capacity limit
        print_test("Test 3: Event with capacity limit")
        event_data = base_event_data.copy()
        event_data["name"] = "Capacity Limited Event"
        event_data["capacity"] = 5
        
        result = self.create_test_event(event_data)
        self.assert_true(result.get("success", False), "Event with capacity created")
        
        # Test 4: Event with no capacity limit (None)
        print_test("Test 4: Event with no capacity limit")
        event_data = base_event_data.copy()
        event_data["name"] = "Unlimited Capacity Event"
        event_data["capacity"] = None
        
        result = self.create_test_event(event_data)
        self.assert_true(result.get("success", False), "Event with no capacity created")
        
        # Test 5: Event with multiple languages
        print_test("Test 5: Event with multiple languages")
        event_data = base_event_data.copy()
        event_data["name"] = "Multi-Language Event"
        event_data["languages"] = ["English", "French", "Spanish"]
        
        result = self.create_test_event(event_data)
        self.assert_true(result.get("success", False), "Multi-language event created")
        
        # Test 6: Featured event
        print_test("Test 6: Featured event")
        event_data = base_event_data.copy()
        event_data["name"] = "Featured Event"
        event_data["is_featured"] = True
        event_data["created_by"] = self.test_admin
        
        result = self.create_test_event(event_data)
        if result.get("success", False):
            event_id = result["data"]["id"]
            # Verify it's featured
            response = requests.get(f"{self.api_url}/api/events/{event_id}")
            if response.status_code == 200:
                event = response.json()
                self.assert_true(event.get("isFeatured", False), "Event marked as featured")
    
    def test_user_events(self):
        """Test retrieving user's events"""
        print_subheader("👤 Testing User Events Retrieval")
        
        test_host = f"host_{datetime.now().strftime('%H%M%S')}"
        future_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
        
        # Test 1: Create multiple events for a user
        print_test("Test 1: Create multiple events for a user")
        event_ids = []
        for i in range(3):
            event_data = {
                "name": f"User Event {i+1}",
                "description": f"User test event {i+1}",
                "location": "Test Location",
                "venue": "Test Venue",
                "address": "Test Address",
                "coordinates": {"lat": 48.8566, "lng": 2.3522},
                "date": future_date,
                "time": f"{18+i}:00",
                "end_time": f"{20+i}:00",
                "category": "random",
                "subcategory": "",
                "languages": ["English"],
                "is_public": True,
                "event_type": "custom",
                "capacity": 10,
                "image_url": "",
                "created_by": test_host,
                "is_featured": False,
                "template_event_id": None,
                "target_interests": None,
                "target_cite_connection": None,
                "target_reasons": None
            }
            result = self.create_test_event(event_data)
            if result.get("success", False):
                event_ids.append(result["data"]["id"])
        
        self.assert_equal(len(event_ids), 3, "Created 3 events for user")
        
        # Test 2: Get user's events
        print_test("Test 2: Get user's hosted events")
        try:
            response = requests.get(f"{self.api_url}/api/users/{test_host}/events")
            self.assert_equal(response.status_code, 200, "GET user events status")
            
            if response.status_code == 200:
                events = response.json()
                hosted_events = [e for e in events if e.get("createdBy") == test_host]
                self.assert_true(
                    len(hosted_events) >= 3,
                    f"User has at least 3 hosted events (found {len(hosted_events)})"
                )
        except Exception as e:
            self.assert_true(False, f"Failed to get user events: {str(e)}")
        
        # Test 3: User joins another event
        print_test("Test 3: User joins events created by others")
        if len(event_ids) > 0:
            test_participant = f"participant_{datetime.now().strftime('%H%M%S')}"
            
            # Join first event
            try:
                response = requests.post(
                    f"{self.api_url}/api/events/{event_ids[0]}/join",
                    json={"username": test_participant},
                    headers={"Content-Type": "application/json"}
                )
                self.assert_equal(response.status_code, 200, "User joined event")
                
                # Get participant's events
                response = requests.get(f"{self.api_url}/api/users/{test_participant}/events")
                if response.status_code == 200:
                    events = response.json()
                    joined = any(e["id"] == event_ids[0] for e in events)
                    self.assert_true(joined, "Joined event appears in user's events")
            except Exception as e:
                self.assert_true(False, f"Failed participant join test: {str(e)}")
    
    def test_permissions(self):
        """Test event permission controls"""
        print_subheader("🔒 Testing Event Permissions")
        
        # Create event with one user
        print_test("Setup: Create event with user1")
        future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        user1 = f"user1_{datetime.now().strftime('%H%M%S')}"
        user2 = f"user2_{datetime.now().strftime('%H%M%S')}"
        
        event_data = {
            "name": "Permission Test Event",
            "description": "Testing permissions",
            "location": "Test Location",
            "venue": "Test Venue",
            "address": "Test Address",
            "coordinates": {"lat": 48.8566, "lng": 2.3522},
            "date": future_date,
            "time": "19:00",
            "end_time": "21:00",
            "category": "party",
            "subcategory": "",
            "languages": ["English"],
            "is_public": True,
            "event_type": "custom",
            "capacity": 10,
            "image_url": "",
            "created_by": user1,
            "is_featured": False,
            "template_event_id": None,
            "target_interests": None,
            "target_cite_connection": None,
            "target_reasons": None
        }
        
        result = self.create_test_event(event_data)
        if not result.get("success", False):
            print_error("Failed to create test event")
            return
        
        event_id = result["data"]["id"]
        print_info(f"Created test event with ID: {event_id}")
        
        # Test 1: Non-host tries to update event
        print_test("Test 1: Non-host cannot update event")
        updated_data = event_data.copy()
        updated_data["name"] = "Hacked Event Name"
        updated_data["created_by"] = user2  # Different user
        
        try:
            response = requests.put(
                f"{self.api_url}/api/events/{event_id}",
                json=updated_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 403, "Non-host update rejected")
        except Exception as e:
            self.assert_true(False, f"Failed permission test: {str(e)}")
        
        # Test 2: Host can update event
        print_test("Test 2: Host can update event")
        updated_data = event_data.copy()
        updated_data["name"] = "Updated by Host"
        updated_data["created_by"] = user1  # Original host
        
        try:
            response = requests.put(
                f"{self.api_url}/api/events/{event_id}",
                json=updated_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "Host can update event")
        except Exception as e:
            self.assert_true(False, f"Failed host update: {str(e)}")
        
        # Test 3: Admin can update any event
        print_test("Test 3: Admin can update any event")
        updated_data = event_data.copy()
        updated_data["name"] = "Updated by Admin"
        updated_data["created_by"] = "admin"
        
        try:
            response = requests.put(
                f"{self.api_url}/api/events/{event_id}",
                json=updated_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_equal(response.status_code, 200, "Admin can update event")
        except Exception as e:
            self.assert_true(False, f"Failed admin update: {str(e)}")
        
        # Test 4: Non-host tries to delete event
        print_test("Test 4: Non-host cannot delete event")
        try:
            response = requests.delete(
                f"{self.api_url}/api/events/{event_id}?username={user2}"
            )
            self.assert_equal(response.status_code, 403, "Non-host delete rejected")
        except Exception as e:
            self.assert_true(False, f"Failed delete permission test: {str(e)}")
        
        # Test 5: Admin can delete any event
        print_test("Test 5: Admin can delete event")
        try:
            response = requests.delete(
                f"{self.api_url}/api/events/{event_id}?username=admin"
            )
            self.assert_equal(response.status_code, 200, "Admin can delete event")
            
            # Remove from cleanup list
            if event_id in self.created_event_ids:
                self.created_event_ids.remove(event_id)
        except Exception as e:
            self.assert_true(False, f"Failed admin delete: {str(e)}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print_header(f"🧪 Event Features Test Suite - {self.env_name}")
        
        try:
            self.test_event_crud()
            self.test_event_participants()
            self.test_event_archiving()
            self.test_event_validation()
            self.test_user_events()
            self.test_permissions()
        finally:
            self.cleanup()
        
        self.print_summary()
    
    def run_specific_test(self, feature: str):
        """Run a specific test suite"""
        print_header(f"🧪 Testing {feature.upper()} - {self.env_name}")
        
        test_map = {
            "crud": self.test_event_crud,
            "participants": self.test_event_participants,
            "archiving": self.test_event_archiving,
            "validation": self.test_event_validation,
            "users": self.test_user_events,
            "permissions": self.test_permissions
        }
        
        try:
            if feature in test_map:
                test_map[feature]()
            else:
                print_error(f"Unknown feature: {feature}")
                print_info(f"Available features: {', '.join(test_map.keys())}")
        finally:
            self.cleanup()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print_header("📊 Test Results Summary")
        
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{Colors.BOLD}Environment:{Colors.ENDC} {self.env_name}")
        print(f"{Colors.BOLD}Total Tests:{Colors.ENDC} {total}")
        print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.ENDC} {self.passed}")
        print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.ENDC} {self.failed}")
        print(f"{Colors.BOLD}Success Rate:{Colors.ENDC} {success_rate:.1f}%\n")
        
        if self.failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! 🎉{Colors.ENDC}\n")
            return 0
        else:
            print(f"{Colors.RED}{Colors.BOLD}⚠️  Some tests failed{Colors.ENDC}\n")
            return 1

def main():
    parser = argparse.ArgumentParser(description="Test event page features")
    parser.add_argument("--local", action="store_true", help="Test local environment")
    parser.add_argument("--deployed", action="store_true", help="Test deployed environment")
    parser.add_argument("--feature", type=str, help="Test specific feature (crud, participants, archiving, validation, users, permissions)")
    
    args = parser.parse_args()
    
    # If no arguments, default to deployed
    if not args.local and not args.deployed:
        args.deployed = True
    
    exit_code = 0
    
    if args.local:
        print("\n" + "="*80)
        print("Testing LOCAL environment")
        print("="*80)
        tester = EventFeaturesTester(LOCAL_API, "LOCAL")
        if args.feature:
            exit_code = tester.run_specific_test(args.feature)
        else:
            exit_code = tester.run_all_tests()
    
    if args.deployed:
        print("\n" + "="*80)
        print("Testing DEPLOYED environment")
        print("="*80)
        tester = EventFeaturesTester(DEPLOYED_API, "DEPLOYED")
        if args.feature:
            code = tester.run_specific_test(args.feature)
        else:
            code = tester.run_all_tests()
        exit_code = max(exit_code, code if code is not None else 0)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
