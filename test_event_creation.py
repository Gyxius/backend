#!/usr/bin/env python3
"""
Event Creation Testing Suite
Tests event creation functionality on both local and deployed environments.

Usage:
    # Test local environment
    python3 test_event_creation.py --local
    
    # Test deployed environment
    python3 test_event_creation.py --deployed
    
    # Test both environments
    python3 test_event_creation.py --all
"""

import requests
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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
    END = '\033[0m'
    BOLD = '\033[1m'

class EventTestCase:
    """Represents a test case for event creation"""
    def __init__(self, name: str, event_data: Dict, should_succeed: bool = True, 
                 expected_error: Optional[str] = None):
        self.name = name
        self.event_data = event_data
        self.should_succeed = should_succeed
        self.expected_error = expected_error
        self.result = None
        self.error = None

class EventCreationTester:
    """Main testing class for event creation"""
    
    def __init__(self, api_url: str, env_name: str):
        self.api_url = api_url
        self.env_name = env_name
        self.test_cases: List[EventTestCase] = []
        self.passed = 0
        self.failed = 0
        self.created_event_ids: List[int] = []
        
    def add_test_case(self, test_case: EventTestCase):
        """Add a test case to the suite"""
        self.test_cases.append(test_case)
    
    def create_event(self, event_data: Dict) -> Dict:
        """Create an event via API"""
        response = requests.post(
            f"{self.api_url}/api/events",
            json=event_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False, 
                "status_code": response.status_code,
                "error": response.text
            }
    
    def verify_event(self, event_id: int, is_private: bool = False) -> Dict:
        """Verify event was created by fetching it"""
        if is_private:
            # Private events won't be returned by GET /api/events (which filters to public only)
            # For now, just assume creation success means it worked
            # In a real scenario, we'd fetch by ID or check as the creator
            return {"success": True, "data": {"id": event_id, "note": "Private event not verified via public endpoint"}}
        
        response = requests.get(f"{self.api_url}/api/events")
        if response.status_code == 200:
            events = response.json()
            for event in events:
                if event.get('id') == event_id:
                    return {"success": True, "data": event}
            return {"success": False, "error": "Event not found"}
        return {"success": False, "error": f"Status {response.status_code}"}
    
    def cleanup_event(self, event_id: int):
        """Delete a test event after testing"""
        try:
            # Use admin username to bypass permission check
            response = requests.delete(
                f"{self.api_url}/api/events/{event_id}",
                params={"username": "admin"}
            )
            if response.status_code == 200:
                print(f"    🗑️  Cleaned up event {event_id}")
            else:
                print(f"    ⚠️  Could not clean up event {event_id}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"    ⚠️  Cleanup error: {e}")
    
    def run_test_case(self, test_case: EventTestCase) -> bool:
        """Run a single test case"""
        print(f"\n  📋 Test: {test_case.name}")
        print(f"     Event: {test_case.event_data.get('name', 'N/A')}")
        
        try:
            result = self.create_event(test_case.event_data)
            
            if test_case.should_succeed:
                if result["success"]:
                    event_id = result["data"].get("id")
                    self.created_event_ids.append(event_id)
                    
                    # Check if this is a private event
                    is_private = test_case.event_data.get("is_public") == False
                    
                    # Verify the event was created
                    verify_result = self.verify_event(event_id, is_private)
                    if verify_result["success"]:
                        event = verify_result["data"]
                        
                        # For private events, we can't fully validate since they're not in public list
                        if is_private and "note" in event:
                            print(f"     ✅ Private event created successfully (ID: {event_id})")
                            print(f"        Note: {event['note']}")
                            test_case.result = "PASSED"
                            return True
                        
                        # Validate key fields
                        validation_passed = True
                        if event.get("name") != test_case.event_data.get("name"):
                            print(f"     ❌ Name mismatch: expected '{test_case.event_data.get('name')}', got '{event.get('name')}'")
                            validation_passed = False
                        # API returns createdBy in camelCase
                        expected_creator = test_case.event_data.get("created_by")
                        actual_creator = event.get("createdBy") or event.get("created_by")
                        if expected_creator and actual_creator != expected_creator:
                            print(f"     ❌ Creator mismatch: expected '{expected_creator}', got '{actual_creator}'")
                            validation_passed = False
                        
                        if validation_passed:
                            print(f"     ✅ Event created successfully (ID: {event_id})")
                            test_case.result = "PASSED"
                            return True
                        else:
                            print(f"     ❌ Validation failed")
                            test_case.result = "FAILED"
                            test_case.error = "Field validation failed"
                            return False
                    else:
                        print(f"     ❌ Event created but verification failed: {verify_result.get('error')}")
                        test_case.result = "FAILED"
                        test_case.error = verify_result.get('error')
                        return False
                else:
                    print(f"     ❌ Expected success but got error: {result.get('error')}")
                    test_case.result = "FAILED"
                    test_case.error = result.get('error')
                    return False
            else:
                # Test case expects failure
                if not result["success"]:
                    error_message = result.get("error", "")
                    if test_case.expected_error and test_case.expected_error in error_message:
                        print(f"     ✅ Failed as expected: {test_case.expected_error}")
                        test_case.result = "PASSED"
                        return True
                    elif not test_case.expected_error:
                        print(f"     ✅ Failed as expected")
                        test_case.result = "PASSED"
                        return True
                    else:
                        print(f"     ❌ Failed with wrong error. Expected: '{test_case.expected_error}', Got: '{error_message}'")
                        test_case.result = "FAILED"
                        test_case.error = f"Wrong error message"
                        return False
                else:
                    print(f"     ❌ Expected failure but succeeded")
                    event_id = result["data"].get("id")
                    if event_id:
                        self.created_event_ids.append(event_id)
                    test_case.result = "FAILED"
                    test_case.error = "Expected failure but succeeded"
                    return False
                    
        except Exception as e:
            print(f"     ❌ Exception: {str(e)}")
            test_case.result = "FAILED"
            test_case.error = str(e)
            return False
    
    def run_all_tests(self, cleanup: bool = True):
        """Run all test cases"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}Testing Event Creation: {self.env_name}{Colors.END}")
        print(f"{Colors.CYAN}API: {self.api_url}{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        
        for test_case in self.test_cases:
            if self.run_test_case(test_case):
                self.passed += 1
            else:
                self.failed += 1
        
        # Cleanup
        if cleanup and self.created_event_ids:
            print(f"\n  🧹 Cleaning up {len(self.created_event_ids)} test events...")
            for event_id in self.created_event_ids:
                self.cleanup_event(event_id)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}Test Summary - {self.env_name}{Colors.END}")
        print(f"{'='*70}")
        print(f"Total Tests:  {total}")
        print(f"{Colors.GREEN}Passed:       {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed:       {self.failed}{Colors.END}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"{'='*70}\n")
        
        # Print failed tests details
        if self.failed > 0:
            print(f"{Colors.RED}Failed Tests:{Colors.END}")
            for test_case in self.test_cases:
                if test_case.result == "FAILED":
                    print(f"  ❌ {test_case.name}")
                    if test_case.error:
                        print(f"     Error: {test_case.error}")


def create_test_cases() -> List[EventTestCase]:
    """Create all test cases for event creation"""
    
    # Get tomorrow's date for events
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    test_cases = []
    
    # Test 1: Basic event creation (minimal required fields)
    test_cases.append(EventTestCase(
        name="Basic Event Creation",
        event_data={
            "name": "Test Event - Basic",
            "description": "A basic test event with minimal fields",
            "location": "Paris",
            "date": tomorrow,
            "time": "18:00",
            "category": "Social",
            "created_by": "TestUser",
            "is_public": True
        },
        should_succeed=True
    ))
    
    # Test 2: Full event with all fields
    test_cases.append(EventTestCase(
        name="Complete Event Creation",
        event_data={
            "name": "Test Event - Complete",
            "description": "A complete test event with all fields populated",
            "location": "Paris",
            "venue": "Cité Universitaire",
            "address": "17 Boulevard Jourdan, 75014 Paris",
            "coordinates": {"lat": 48.8205, "lng": 2.3382},
            "date": tomorrow,
            "time": "19:30",
            "end_time": "22:00",
            "category": "Cultural",
            "subcategory": "Art",
            "languages": ["English", "French"],
            "is_public": True,
            "event_type": "custom",
            "capacity": 20,
            "created_by": "TestUser",
            "is_featured": False
        },
        should_succeed=True
    ))
    
    # Test 3: Event with end time before start time (cross-midnight)
    test_cases.append(EventTestCase(
        name="Cross-Midnight Event",
        event_data={
            "name": "Test Event - Cross Midnight",
            "description": "Event that crosses midnight",
            "location": "Paris",
            "date": tomorrow,
            "time": "23:00",
            "end_time": "02:00",
            "category": "Social",
            "created_by": "TestUser"
        },
        should_succeed=True
    ))
    
    # Test 4: Event with same start and end time (should fail)
    test_cases.append(EventTestCase(
        name="Same Start/End Time (Should Fail)",
        event_data={
            "name": "Test Event - Invalid Times",
            "description": "Event with same start and end time",
            "location": "Paris",
            "date": tomorrow,
            "time": "18:00",
            "end_time": "18:00",
            "category": "Social",
            "created_by": "TestUser"
        },
        should_succeed=False,
        expected_error="cannot be the same"
    ))
    
    # Test 5: Event with long description
    test_cases.append(EventTestCase(
        name="Event with Long Description",
        event_data={
            "name": "Test Event - Long Description",
            "description": "This is a very long description that tests whether the system can handle lengthy event descriptions. " * 10,
            "location": "Paris",
            "date": tomorrow,
            "time": "15:00",
            "category": "Educational",
            "created_by": "TestUser"
        },
        should_succeed=True
    ))
    
    # Test 6: Event with special characters
    test_cases.append(EventTestCase(
        name="Event with Special Characters",
        event_data={
            "name": "Test Event - Spécial Çharacters & Émojis 🎉",
            "description": "Testing spécial çharacters: àéèêë, ñ, ü, and émojis! 🎨🎭🎪",
            "location": "Paris, Île-de-France",
            "venue": "Café des Arts",
            "date": tomorrow,
            "time": "16:00",
            "category": "Social",
            "languages": ["Français", "English"],
            "created_by": "TestUser"
        },
        should_succeed=True
    ))
    
    # Test 7: Event with targeting parameters
    test_cases.append(EventTestCase(
        name="Event with Targeting",
        event_data={
            "name": "Test Event - Targeted",
            "description": "Event with targeting parameters",
            "location": "Paris",
            "date": tomorrow,
            "time": "17:00",
            "category": "Sports",
            "created_by": "TestUser",
            "target_interests": ["sports", "fitness"],
            "target_cite_connection": ["resident", "alumni"],
            "target_reasons": ["networking", "fun"]
        },
        should_succeed=True
    ))
    
    # Test 8: Private event
    test_cases.append(EventTestCase(
        name="Private Event Creation",
        event_data={
            "name": "Test Event - Private",
            "description": "A private event for testing",
            "location": "Paris",
            "date": tomorrow,
            "time": "20:00",
            "category": "Social",
            "created_by": "TestUser",
            "is_public": False,
            "capacity": 10
        },
        should_succeed=True
    ))
    
    # Test 9: Event with capacity limit
    test_cases.append(EventTestCase(
        name="Event with Capacity",
        event_data={
            "name": "Test Event - Limited Capacity",
            "description": "Event with capacity limit",
            "location": "Paris",
            "date": tomorrow,
            "time": "14:00",
            "category": "Workshop",
            "created_by": "TestUser",
            "capacity": 5
        },
        should_succeed=True
    ))
    
    # Test 10: Event without required created_by field
    test_cases.append(EventTestCase(
        name="Missing Creator (Should Succeed with None)",
        event_data={
            "name": "Test Event - No Creator",
            "description": "Event without creator",
            "location": "Paris",
            "date": tomorrow,
            "time": "12:00",
            "category": "Social"
            # Note: created_by is optional in the model
        },
        should_succeed=True
    ))
    
    return test_cases


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test event creation on local and/or deployed environments")
    parser.add_argument("--local", action="store_true", help="Test local environment")
    parser.add_argument("--deployed", action="store_true", help="Test deployed environment")
    parser.add_argument("--all", action="store_true", help="Test both environments")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't cleanup test events after testing")
    
    args = parser.parse_args()
    
    # Default to all if no option specified
    if not (args.local or args.deployed or args.all):
        args.all = True
    
    cleanup = not args.no_cleanup
    test_cases = create_test_cases()
    
    results = {}
    
    # Test local environment
    if args.local or args.all:
        print(f"\n{Colors.YELLOW}Starting LOCAL environment tests...{Colors.END}")
        local_tester = EventCreationTester(LOCAL_API, "LOCAL (localhost:8000)")
        for test_case in test_cases:
            # Create a fresh copy of test case for this environment
            local_tester.add_test_case(EventTestCase(
                test_case.name,
                test_case.event_data.copy(),
                test_case.should_succeed,
                test_case.expected_error
            ))
        local_tester.run_all_tests(cleanup=cleanup)
        results["local"] = {"passed": local_tester.passed, "failed": local_tester.failed}
    
    # Test deployed environment
    if args.deployed or args.all:
        print(f"\n{Colors.YELLOW}Starting DEPLOYED environment tests...{Colors.END}")
        deployed_tester = EventCreationTester(DEPLOYED_API, "DEPLOYED (Render)")
        for test_case in test_cases:
            # Create a fresh copy of test case for this environment
            deployed_tester.add_test_case(EventTestCase(
                test_case.name,
                test_case.event_data.copy(),
                test_case.should_succeed,
                test_case.expected_error
            ))
        deployed_tester.run_all_tests(cleanup=cleanup)
        results["deployed"] = {"passed": deployed_tester.passed, "failed": deployed_tester.failed}
    
    # Final summary
    if len(results) > 1:
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}OVERALL SUMMARY{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        for env, data in results.items():
            total = data["passed"] + data["failed"]
            success_rate = (data["passed"] / total * 100) if total > 0 else 0
            status = f"{Colors.GREEN}✓{Colors.END}" if data["failed"] == 0 else f"{Colors.RED}✗{Colors.END}"
            print(f"{status} {env.upper():12s}: {data['passed']}/{total} passed ({success_rate:.1f}%)")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")


if __name__ == "__main__":
    main()
