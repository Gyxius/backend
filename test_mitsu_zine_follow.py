#!/usr/bin/env python3
"""
Test the follow system with Mitsu and Zine
Scenario:
1. Mitsu follows Zine
2. Zine accepts and follows Mitsu back (mutual follow)
3. Zine unfollows Mitsu
Expected final state:
- Zine: 0 follows, 1 follower (Mitsu)
- Mitsu: 1 follow (Zine), 0 followers
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def print_step(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.YELLOW}📊 {text}{Colors.ENDC}")

def get_follows(username):
    """Get who the user follows"""
    response = requests.get(f"{BASE_URL}/api/follows/{username}")
    if response.status_code == 200:
        return response.json()
    return []

def get_followers(username):
    """Get who follows the user"""
    response = requests.get(f"{BASE_URL}/api/followers/{username}")
    if response.status_code == 200:
        return response.json()
    return []

def add_follow(user1, user2):
    """User1 follows User2"""
    response = requests.post(
        f"{BASE_URL}/api/follows",
        json={"user1": user1, "user2": user2}
    )
    return response.status_code in [200, 201]

def remove_follow(user1, user2):
    """User1 unfollows User2"""
    response = requests.delete(
        f"{BASE_URL}/api/follows",
        json={"user1": user1, "user2": user2}
    )
    return response.status_code in [200, 201]

def print_status(username):
    """Print the follow/follower status of a user"""
    follows = get_follows(username)
    followers = get_followers(username)
    print_info(f"{username}:")
    print(f"   Follows: {len(follows)} → {follows}")
    print(f"   Followers: {len(followers)} → {followers}")

def verify_counts(username, expected_follows, expected_followers):
    """Verify the follow/follower counts"""
    follows = get_follows(username)
    followers = get_followers(username)
    
    follows_ok = len(follows) == expected_follows
    followers_ok = len(followers) == expected_followers
    
    if follows_ok and followers_ok:
        print_success(f"{username}: {len(follows)} follows, {len(followers)} followers ✓")
        return True
    else:
        print_error(f"{username}: Expected {expected_follows} follows/{expected_followers} followers, got {len(follows)} follows/{len(followers)} followers")
        return False

def main():
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'MITSU & ZINE FOLLOW TEST'.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

    # Check API
    try:
        response = requests.get(f"{BASE_URL}/api/events", timeout=5)
        print_success("API is available\n")
    except:
        print_error("Cannot connect to API. Is the backend running on port 8001?")
        sys.exit(1)

    # STEP 1: Mitsu follows Zine
    print_step("STEP 1: Mitsu follows Zine")
    success = add_follow("Mitsu", "Zine")
    if success:
        print_success("Mitsu now follows Zine")
    else:
        print_error("Failed to add follow")
        sys.exit(1)
    
    print_status("Mitsu")
    print_status("Zine")
    
    # Verify Step 1
    print("\n🔍 Verifying Step 1...")
    mitsu_ok = verify_counts("Mitsu", 1, 0)  # Mitsu: 1 follow, 0 followers
    zine_ok = verify_counts("Zine", 0, 1)     # Zine: 0 follows, 1 follower
    
    if not (mitsu_ok and zine_ok):
        print_error("Step 1 verification failed!")
        sys.exit(1)

    # STEP 2: Zine follows Mitsu back (mutual follow)
    print_step("STEP 2: Zine follows Mitsu back (mutual follow)")
    success = add_follow("Zine", "Mitsu")
    if success:
        print_success("Zine now follows Mitsu (mutual follow)")
    else:
        print_error("Failed to add follow")
        sys.exit(1)
    
    print_status("Mitsu")
    print_status("Zine")
    
    # Verify Step 2
    print("\n🔍 Verifying Step 2...")
    mitsu_ok = verify_counts("Mitsu", 1, 1)  # Mitsu: 1 follow, 1 follower
    zine_ok = verify_counts("Zine", 1, 1)     # Zine: 1 follow, 1 follower
    
    if not (mitsu_ok and zine_ok):
        print_error("Step 2 verification failed!")
        sys.exit(1)

    # STEP 3: Zine unfollows Mitsu
    print_step("STEP 3: Zine unfollows Mitsu")
    success = remove_follow("Zine", "Mitsu")
    if success:
        print_success("Zine unfollowed Mitsu")
    else:
        print_error("Failed to unfollow")
        sys.exit(1)
    
    print_status("Mitsu")
    print_status("Zine")
    
    # Verify Final State
    print_step("FINAL VERIFICATION")
    print("Expected:")
    print("  • Zine: 0 follows, 1 follower (Mitsu still follows Zine)")
    print("  • Mitsu: 1 follow (Zine), 0 followers (Zine unfollowed)\n")
    
    zine_ok = verify_counts("Zine", 0, 1)     # Zine: 0 follows, 1 follower
    mitsu_ok = verify_counts("Mitsu", 1, 0)   # Mitsu: 1 follow, 0 followers
    
    # Final detailed status
    print("\n" + "="*70)
    print_step("FINAL STATUS")
    
    mitsu_follows = get_follows("Mitsu")
    mitsu_followers = get_followers("Mitsu")
    zine_follows = get_follows("Zine")
    zine_followers = get_followers("Zine")
    
    print_info("Mitsu:")
    print(f"   Follows: {mitsu_follows}")
    print(f"   Followers: {mitsu_followers}")
    print()
    print_info("Zine:")
    print(f"   Follows: {zine_follows}")
    print(f"   Followers: {zine_followers}")
    
    # Summary
    print("\n" + "="*70)
    if zine_ok and mitsu_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Unfollow is working correctly (one-directional){Colors.ENDC}\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ TEST FAILED{Colors.ENDC}")
        print(f"{Colors.RED}The follow counts don't match expected values{Colors.ENDC}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
