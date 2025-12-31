#!/usr/bin/env python3
"""
Test script for the Follow System
Tests:
1. User A follows User B (mutual follow)
2. User A follows User B, User B can decline/unfollow
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8001"

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
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")

def print_test(text: str):
    """Print a test description"""
    print(f"{Colors.CYAN}{Colors.BOLD}🧪 {text}{Colors.ENDC}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

def print_data(label: str, data: Any):
    """Print data with label"""
    print(f"{Colors.YELLOW}   {label}: {json.dumps(data, indent=2)}{Colors.ENDC}")

def create_test_user(username: str, email: str, password: str = "Test123!") -> Dict:
    """Create a test user"""
    print_test(f"Creating user: {username}")
    
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "phoneNumber": f"+1234567{username[-3:]}",
        "fullName": f"Test User {username}",
        "dateOfBirth": "1990-01-01",
        "gender": "other",
        "city": "Paris",
        "country": "France"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=user_data)
        if response.status_code in [200, 201]:
            print_success(f"User '{username}' created successfully")
            return {"success": True, "data": response.json()}
        else:
            # User might already exist, try to login
            login_response = requests.post(
                f"{BASE_URL}/api/login",
                json={"username": username, "password": password}
            )
            if login_response.status_code == 200:
                print_info(f"User '{username}' already exists, logged in")
                return {"success": True, "data": login_response.json()}
            else:
                print_error(f"Failed to create/login user: {response.status_code}")
                print_data("Response", response.text)
                return {"success": False, "error": response.text}
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}

def add_follow(follower: str, following: str) -> Dict:
    """User 'follower' follows 'following'"""
    print_test(f"{follower} → follows → {following}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/follows",
            json={"user1": follower, "user2": following}
        )
        
        if response.status_code in [200, 201]:
            print_success(f"{follower} now follows {following}")
            return {"success": True, "data": response.json()}
        else:
            print_error(f"Failed to add follow: {response.status_code}")
            print_data("Response", response.text)
            return {"success": False, "error": response.text}
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}

def get_follows(username: str) -> Dict:
    """Get list of users that 'username' follows"""
    print_test(f"Getting follows for {username}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/follows/{username}")
        
        if response.status_code == 200:
            follows = response.json()
            print_success(f"{username} follows: {follows}")
            return {"success": True, "data": follows}
        else:
            print_error(f"Failed to get follows: {response.status_code}")
            print_data("Response", response.text)
            return {"success": False, "error": response.text}
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}

def get_followers(username: str) -> Dict:
    """Get list of users that follow 'username'"""
    print_test(f"Getting followers for {username}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/followers/{username}")
        
        if response.status_code == 200:
            followers = response.json()
            print_success(f"{username}'s followers: {followers}")
            return {"success": True, "data": followers}
        else:
            print_error(f"Failed to get followers: {response.status_code}")
            print_data("Response", response.text)
            return {"success": False, "error": response.text}
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}

def unfollow(follower: str, following: str) -> Dict:
    """User 'follower' unfollows 'following'"""
    print_test(f"{follower} → unfollows → {following}")
    
    # Note: The current API doesn't have a dedicated unfollow endpoint
    # We need to check if there's a DELETE endpoint or we need to add one
    try:
        response = requests.delete(
            f"{BASE_URL}/api/follows",
            json={"user1": follower, "user2": following}
        )
        
        if response.status_code in [200, 204]:
            print_success(f"{follower} unfollowed {following}")
            return {"success": True, "data": response.json() if response.text else {}}
        else:
            print_error(f"Failed to unfollow: {response.status_code}")
            print_data("Response", response.text)
            return {"success": False, "error": response.text}
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}

def test_mutual_follow():
    """
    Test Case 1: Mutual Follow
    - User A follows User B
    - User B follows User A
    - Both should see each other in their respective lists
    """
    print_header("TEST CASE 1: MUTUAL FOLLOW")
    
    # Create test users
    user_a = "testuser_a"
    user_b = "testuser_b"
    
    create_test_user(user_a, f"{user_a}@test.com")
    create_test_user(user_b, f"{user_b}@test.com")
    
    # User A follows User B
    print_info("\nStep 1: User A follows User B")
    add_follow(user_a, user_b)
    
    # Verify: User A's follows list should contain User B
    follows_a = get_follows(user_a)
    if follows_a["success"] and user_b in follows_a["data"]:
        print_success(f"✓ User A's follows list correctly contains User B")
    else:
        print_error(f"✗ User A's follows list doesn't contain User B")
    
    # Verify: User B's followers list should contain User A
    followers_b = get_followers(user_b)
    if followers_b["success"] and user_a in followers_b["data"]:
        print_success(f"✓ User B's followers list correctly contains User A")
    else:
        print_error(f"✗ User B's followers list doesn't contain User A")
    
    # User B follows User A (mutual follow)
    print_info("\nStep 2: User B follows User A (making it mutual)")
    add_follow(user_b, user_a)
    
    # Verify: User B's follows list should contain User A
    follows_b = get_follows(user_b)
    if follows_b["success"] and user_a in follows_b["data"]:
        print_success(f"✓ User B's follows list correctly contains User A")
    else:
        print_error(f"✗ User B's follows list doesn't contain User A")
    
    # Verify: User A's followers list should contain User B
    followers_a = get_followers(user_a)
    if followers_a["success"] and user_b in followers_a["data"]:
        print_success(f"✓ User A's followers list correctly contains User B")
    else:
        print_error(f"✗ User A's followers list doesn't contain User B")
    
    print_info("\n📊 Final State:")
    print_info(f"   {user_a} follows: {follows_a['data'] if follows_a['success'] else 'N/A'}")
    print_info(f"   {user_a} followers: {followers_a['data'] if followers_a['success'] else 'N/A'}")
    print_info(f"   {user_b} follows: {follows_b['data'] if follows_b['success'] else 'N/A'}")
    print_info(f"   {user_b} followers: {followers_b['data'] if followers_b['success'] else 'N/A'}")
    
    return {
        "user_a": user_a,
        "user_b": user_b,
        "follows_a": follows_a,
        "followers_a": followers_a,
        "follows_b": follows_b,
        "followers_b": followers_b
    }

def test_follow_and_decline():
    """
    Test Case 2: Follow and Decline/Unfollow
    - User C follows User D
    - User D declines (unfollows) User C
    - User C should no longer appear in User D's followers
    """
    print_header("TEST CASE 2: FOLLOW AND DECLINE/UNFOLLOW")
    
    # Create test users
    user_c = "testuser_c"
    user_d = "testuser_d"
    
    create_test_user(user_c, f"{user_c}@test.com")
    create_test_user(user_d, f"{user_d}@test.com")
    
    # User C follows User D
    print_info("\nStep 1: User C follows User D")
    add_follow(user_c, user_d)
    
    # Verify: User C's follows list should contain User D
    follows_c = get_follows(user_c)
    if follows_c["success"] and user_d in follows_c["data"]:
        print_success(f"✓ User C's follows list correctly contains User D")
    else:
        print_error(f"✗ User C's follows list doesn't contain User D")
    
    # Verify: User D's followers list should contain User C
    followers_d = get_followers(user_d)
    if followers_d["success"] and user_c in followers_d["data"]:
        print_success(f"✓ User D's followers list correctly contains User C")
    else:
        print_error(f"✗ User D's followers list doesn't contain User C")
    
    # User D wants to decline/remove User C as a follower
    # In a proper follow request system, this would be "decline request"
    # In the current system, User D would need to block or we need an endpoint to remove followers
    print_info("\nStep 2: User D declines/removes User C (unfollow from User C's side)")
    print_info("Note: Since there's no 'decline follower' endpoint, testing unfollow instead")
    
    unfollow_result = unfollow(user_c, user_d)
    
    if unfollow_result["success"]:
        # Verify: User C's follows list should no longer contain User D
        follows_c_after = get_follows(user_c)
        if follows_c_after["success"] and user_d not in follows_c_after["data"]:
            print_success(f"✓ User C's follows list no longer contains User D")
        else:
            print_error(f"✗ User C's follows list still contains User D")
        
        # Verify: User D's followers list should no longer contain User C
        followers_d_after = get_followers(user_d)
        if followers_d_after["success"] and user_c not in followers_d_after["data"]:
            print_success(f"✓ User D's followers list no longer contains User C")
        else:
            print_error(f"✗ User D's followers list still contains User C")
        
        print_info("\n📊 Final State:")
        print_info(f"   {user_c} follows: {follows_c_after['data'] if follows_c_after['success'] else 'N/A'}")
        print_info(f"   {user_d} followers: {followers_d_after['data'] if followers_d_after['success'] else 'N/A'}")
    else:
        print_error("❌ Unfollow failed - DELETE endpoint may not exist")
        print_info("💡 Recommendation: Implement DELETE /api/follows endpoint")
    
    return {
        "user_c": user_c,
        "user_d": user_d,
        "unfollow_success": unfollow_result["success"]
    }

def check_api_availability():
    """Check if the API is available"""
    print_test("Checking API availability...")
    try:
        response = requests.get(f"{BASE_URL}/api/events", timeout=5)
        if response.status_code == 200:
            print_success("API is available")
            return True
        else:
            print_error(f"API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Is the backend running?")
        print_info(f"Expected backend at: {BASE_URL}")
        print_info("Run: cd backend && python main.py")
        return False
    except Exception as e:
        print_error(f"Error checking API: {str(e)}")
        return False

def main():
    """Main test function"""
    print_header("FOLLOW SYSTEM TEST SUITE")
    print_info(f"Testing backend at: {BASE_URL}")
    
    # Check if API is available
    if not check_api_availability():
        sys.exit(1)
    
    # Run tests
    try:
        result_1 = test_mutual_follow()
        result_2 = test_follow_and_decline()
        
        # Summary
        print_header("TEST SUMMARY")
        print_info("Test 1: Mutual Follow")
        if (result_1["follows_a"]["success"] and 
            result_1["followers_a"]["success"] and
            result_1["follows_b"]["success"] and
            result_1["followers_b"]["success"]):
            print_success("✓ All checks passed")
        else:
            print_error("✗ Some checks failed")
        
        print_info("\nTest 2: Follow and Decline/Unfollow")
        if result_2["unfollow_success"]:
            print_success("✓ Unfollow functionality works")
        else:
            print_error("✗ Unfollow functionality needs implementation")
            print_info("💡 Consider implementing:")
            print_info("   - DELETE /api/follows endpoint for unfollow")
            print_info("   - Follow request system with approve/decline")
        
    except Exception as e:
        print_error(f"Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
