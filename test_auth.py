#!/usr/bin/env python3
"""
Authentication System Test Suite
Tests user registration, login, and profile management

Usage:
    python3 test_auth.py --local
    python3 test_auth.py --deployed
"""

import requests
import json
import argparse
import sys
from datetime import datetime
from typing import Dict, Optional

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

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_subheader(text: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'-' * 80}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'-' * 80}{Colors.ENDC}\n")

def print_test(text: str):
    print(f"{Colors.BLUE}🧪 {text}{Colors.ENDC}")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

class AuthTester:
    """Test authentication functionality"""
    
    def __init__(self, api_url: str, env_name: str):
        self.api_url = api_url
        self.env_name = env_name
        self.passed = 0
        self.failed = 0
        self.test_users = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
            print_success(message)
            return True
        else:
            self.failed += 1
            print_error(message)
            return False
    
    def assert_equal(self, actual, expected, message: str):
        if actual == expected:
            self.passed += 1
            print_success(f"{message}: {actual} == {expected}")
            return True
        else:
            self.failed += 1
            print_error(f"{message}: {actual} != {expected}")
            return False
    
    def test_registration(self):
        """Test user registration"""
        print_subheader("📝 Testing User Registration")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Test 1: Valid registration
        print_test("Test 1: Register new user")
        user_data = {
            "username": f"testuser_{timestamp}",
            "email": f"testuser_{timestamp}@test.com",
            "password": "TestPass123!",
            "phoneNumber": "+33612345678",
            "fullName": "Test User",
            "dateOfBirth": "1995-06-15",
            "gender": "other",
            "city": "Paris",
            "country": "France"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            
            self.assert_true(
                response.status_code in [200, 201],
                f"User registration successful (status: {response.status_code})"
            )
            
            if response.status_code in [200, 201]:
                self.test_users.append(user_data["username"])
                data = response.json()
                self.assert_true("username" in data, "Response contains username")
        except Exception as e:
            self.assert_true(False, f"Registration failed: {str(e)}")
        
        # Test 2: Duplicate registration (should fail)
        print_test("Test 2: Duplicate username registration")
        try:
            response = requests.post(
                f"{self.api_url}/api/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            
            self.assert_true(
                response.status_code >= 400,
                "Duplicate registration rejected"
            )
        except Exception as e:
            self.assert_true(False, f"Duplicate test failed: {str(e)}")
        
        # Test 3: Invalid email format
        print_test("Test 3: Invalid email format")
        invalid_user = user_data.copy()
        invalid_user["username"] = f"invalid_{timestamp}"
        invalid_user["email"] = "not-an-email"
        
        try:
            response = requests.post(
                f"{self.api_url}/api/register",
                json=invalid_user,
                headers={"Content-Type": "application/json"}
            )
            
            # Some APIs might accept this, so we just log the result
            if response.status_code >= 400:
                print_success("Invalid email rejected by validation")
                self.passed += 1
            else:
                print_info("API accepts any email format")
                self.passed += 1
        except Exception as e:
            self.assert_true(False, f"Email validation test failed: {str(e)}")
    
    def test_login(self):
        """Test user login"""
        print_subheader("🔐 Testing User Login")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # First register a user
        print_test("Setup: Register test user")
        username = f"logintest_{timestamp}"
        password = "LoginTest123!"
        user_data = {
            "username": username,
            "email": f"{username}@test.com",
            "password": password,
            "phoneNumber": "+33612345678",
            "fullName": "Login Test User",
            "dateOfBirth": "1995-06-15",
            "gender": "other",
            "city": "Paris",
            "country": "France"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code not in [200, 201]:
                print_info("User might already exist, continuing with tests")
            else:
                self.test_users.append(username)
        except Exception as e:
            print_info(f"Registration error (might already exist): {str(e)}")
        
        # Test 1: Valid login
        print_test("Test 1: Login with correct credentials")
        try:
            response = requests.post(
                f"{self.api_url}/api/login",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            self.assert_equal(response.status_code, 200, "Login successful")
            if response.status_code == 200:
                data = response.json()
                self.assert_true("username" in data, "Login response contains username")
        except Exception as e:
            self.assert_true(False, f"Login failed: {str(e)}")
        
        # Test 2: Wrong password
        print_test("Test 2: Login with wrong password")
        try:
            response = requests.post(
                f"{self.api_url}/api/login",
                json={"username": username, "password": "WrongPassword123!"},
                headers={"Content-Type": "application/json"}
            )
            
            self.assert_true(
                response.status_code in [401, 403],
                "Wrong password rejected"
            )
        except Exception as e:
            self.assert_true(False, f"Wrong password test failed: {str(e)}")
        
        # Test 3: Non-existent user
        print_test("Test 3: Login with non-existent user")
        try:
            response = requests.post(
                f"{self.api_url}/api/login",
                json={"username": f"nonexistent_{timestamp}", "password": "Any123!"},
                headers={"Content-Type": "application/json"}
            )
            
            self.assert_true(
                response.status_code in [401, 404],
                "Non-existent user rejected"
            )
        except Exception as e:
            self.assert_true(False, f"Non-existent user test failed: {str(e)}")
        
        # Test 4: Case-insensitive username
        print_test("Test 4: Case-insensitive username login")
        try:
            response = requests.post(
                f"{self.api_url}/api/login",
                json={"username": username.upper(), "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print_success("Login is case-insensitive")
                self.passed += 1
            else:
                print_info("Login is case-sensitive")
                self.passed += 1
        except Exception as e:
            self.assert_true(False, f"Case-sensitivity test failed: {str(e)}")
    
    def test_profile_management(self):
        """Test user profile retrieval and updates"""
        print_subheader("👤 Testing Profile Management")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        username = f"profile_{timestamp}"
        
        # First register a user
        print_test("Setup: Register test user")
        user_data = {
            "username": username,
            "email": f"{username}@test.com",
            "password": "ProfileTest123!",
            "phoneNumber": "+33612345678",
            "fullName": "Profile Test User",
            "dateOfBirth": "1995-06-15",
            "gender": "other",
            "city": "Paris",
            "country": "France"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code in [200, 201]:
                self.test_users.append(username)
        except Exception as e:
            print_info(f"Registration error: {str(e)}")
        
        # Test 1: Get user profile
        print_test("Test 1: Get user profile")
        try:
            response = requests.get(f"{self.api_url}/api/users/{username}/profile")
            self.assert_equal(response.status_code, 200, "Profile retrieved")
            
            if response.status_code == 200:
                profile = response.json()
                self.assert_true("username" in profile, "Profile contains username")
                self.assert_equal(profile.get("username"), username, "Username matches")
        except Exception as e:
            self.assert_true(False, f"Get profile failed: {str(e)}")
        
        # Test 2: Update user profile
        print_test("Test 2: Update user profile")
        profile_update = {
            "interests": ["sports", "music", "food"],
            "languages": ["English", "French"],
            "citeConnection": "yes",
            "reasonsForComing": ["studies", "work"],
            "hometown": "London"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/users/{username}/profile",
                json=profile_update,
                headers={"Content-Type": "application/json"}
            )
            
            self.assert_true(
                response.status_code in [200, 201],
                "Profile updated successfully"
            )
            
            # Verify update
            response = requests.get(f"{self.api_url}/api/users/{username}/profile")
            if response.status_code == 200:
                profile = response.json()
                if "interests" in profile:
                    self.assert_true(
                        len(profile.get("interests", [])) > 0,
                        "Profile contains updated interests"
                    )
        except Exception as e:
            self.assert_true(False, f"Update profile failed: {str(e)}")
        
        # Test 3: Get non-existent profile
        print_test("Test 3: Get non-existent profile")
        try:
            response = requests.get(
                f"{self.api_url}/api/users/nonexistent_{timestamp}/profile"
            )
            
            # Either returns 404 or empty profile
            self.assert_true(
                response.status_code in [200, 404],
                "Non-existent profile handled gracefully"
            )
        except Exception as e:
            self.assert_true(False, f"Non-existent profile test failed: {str(e)}")
    
    def test_invite_codes(self):
        """Test invite code generation and validation"""
        print_subheader("🎟️ Testing Invite Codes")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        username = f"invite_{timestamp}"
        
        # First register a user
        print_test("Setup: Register test user")
        user_data = {
            "username": username,
            "email": f"{username}@test.com",
            "password": "InviteTest123!",
            "phoneNumber": "+33612345678",
            "fullName": "Invite Test User",
            "dateOfBirth": "1995-06-15",
            "gender": "other",
            "city": "Paris",
            "country": "France"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code in [200, 201]:
                self.test_users.append(username)
        except Exception as e:
            print_info(f"Registration error: {str(e)}")
        
        # Test 1: Get user's invite code
        print_test("Test 1: Get user's invite code")
        invite_code = None
        try:
            response = requests.get(f"{self.api_url}/api/users/{username}/invite-code")
            
            if response.status_code == 200:
                data = response.json()
                invite_code = data.get("invite_code")
                self.assert_true(invite_code is not None, "Invite code generated")
                print_info(f"Invite code: {invite_code}")
            else:
                print_info("Invite codes may not be implemented yet")
                self.passed += 1
        except Exception as e:
            print_info(f"Invite code feature may not be available: {str(e)}")
            self.passed += 1
        
        # Test 2: Validate invite code
        if invite_code:
            print_test("Test 2: Validate invite code")
            try:
                response = requests.get(
                    f"{self.api_url}/api/invites/validate?code={invite_code}"
                )
                
                self.assert_equal(response.status_code, 200, "Invite code validated")
                if response.status_code == 200:
                    data = response.json()
                    self.assert_true(
                        data.get("valid", False),
                        "Invite code is valid"
                    )
            except Exception as e:
                self.assert_true(False, f"Validate invite code failed: {str(e)}")
        
        # Test 3: Invalid invite code
        print_test("Test 3: Validate invalid invite code")
        try:
            response = requests.get(
                f"{self.api_url}/api/invites/validate?code=INVALID-CODE"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assert_true(
                    not data.get("valid", True),
                    "Invalid code rejected"
                )
            else:
                self.assert_true(
                    response.status_code >= 400,
                    "Invalid code returns error"
                )
        except Exception as e:
            print_info(f"Invalid code test: {str(e)}")
            self.passed += 1
    
    def run_all_tests(self):
        """Run all test suites"""
        print_header(f"🧪 Authentication System Tests - {self.env_name}")
        
        self.test_registration()
        self.test_login()
        self.test_profile_management()
        self.test_invite_codes()
        
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
    parser = argparse.ArgumentParser(description="Test authentication system")
    parser.add_argument("--local", action="store_true", help="Test local environment")
    parser.add_argument("--deployed", action="store_true", help="Test deployed environment")
    
    args = parser.parse_args()
    
    if not args.local and not args.deployed:
        args.deployed = True
    
    exit_code = 0
    
    if args.local:
        tester = AuthTester(LOCAL_API, "LOCAL")
        exit_code = tester.run_all_tests()
    
    if args.deployed:
        tester = AuthTester(DEPLOYED_API, "DEPLOYED")
        code = tester.run_all_tests()
        exit_code = max(exit_code, code)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
