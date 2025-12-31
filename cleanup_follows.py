#!/usr/bin/env python3
"""
Clean up all follows for Mitsu and Zine before testing
"""

import requests

BASE_URL = "http://localhost:8000"

def remove_follow(user1, user2):
    """User1 unfollows User2"""
    try:
        response = requests.delete(
            f"{BASE_URL}/api/follows",
            json={"user1": user1, "user2": user2}
        )
        return response.status_code in [200, 201]
    except:
        return False

def get_follows(username):
    """Get who the user follows"""
    try:
        response = requests.get(f"{BASE_URL}/api/follows/{username}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def cleanup_user_follows(username):
    """Remove all follows for a user"""
    follows = get_follows(username)
    for followed_user in follows:
        if remove_follow(username, followed_user):
            print(f"✓ Removed: {username} → {followed_user}")
        else:
            print(f"✗ Failed to remove: {username} → {followed_user}")

if __name__ == "__main__":
    print("Cleaning up follows for Mitsu and Zine...\n")
    cleanup_user_follows("Mitsu")
    cleanup_user_follows("Zine")
    print("\nCleanup complete!")
