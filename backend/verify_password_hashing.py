"""
Test script to verify password hashing is working correctly.
Run this to validate the bcrypt implementation before testing with the web app.

Usage:
    python verify_password_hashing.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from utils.password_util import hash_password, verify_password

def test_password_hashing():
    """Test password hashing and verification"""
    
    print("\n" + "="*60)
    print("PASSWORD HASHING TEST 🔐")
    print("="*60)
    
    # Test case 1: Basic hashing
    print("\n✓ Test 1: Hash a password")
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    print(f"  Plain:  {password}")
    print(f"  Hash:   {hashed[:20]}...{hashed[-10:]}")
    print(f"  Length: {len(hashed)} characters")
    
    # Verify hash format
    if hashed.startswith('$2b$'):
        print("  ✓ Valid bcrypt hash format")
    else:
        print("  ✗ Invalid hash format!")
        return False
    
    # Test case 2: Verify correct password
    print("\n✓ Test 2: Verify correct password")
    if verify_password(password, hashed):
        print(f"  ✓ Password verified correctly")
    else:
        print(f"  ✗ Password verification FAILED!")
        return False
    
    # Test case 3: Reject wrong password
    print("\n✓ Test 3: Reject wrong password")
    wrong_password = "WrongPassword123!"
    if not verify_password(wrong_password, hashed):
        print(f"  ✓ Correctly rejected wrong password")
    else:
        print(f"  ✗ Wrong password was accepted!")
        return False
    
    # Test case 4: Hash consistency (different hash each time)
    print("\n✓ Test 4: Hash randomness (same password, different hash)")
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    if hash1 != hash2:
        print(f"  Hash 1: {hash1[:20]}...{hash1[-10:]}")
        print(f"  Hash 2: {hash2[:20]}...{hash2[-10:]}")
        print(f"  ✓ Different hashes (due to random salt)")
        # But both should verify with original password
        if verify_password(password, hash1) and verify_password(password, hash2):
            print(f"  ✓ Both hashes verify against original password")
        else:
            print(f"  ✗ One of the hashes doesn't verify!")
            return False
    else:
        print(f"  ✗ Hashes are identical (should be different)!")
        return False
    
    # Test case 5: Empty password handling
    print("\n✓ Test 5: Empty password")
    try:
        empty_hash = hash_password("")
        print(f"  Empty hash: {empty_hash[:20]}...{empty_hash[-10:]}")
        if verify_password("", empty_hash):
            print(f"  ✓ Empty password handled correctly")
        else:
            print(f"  ✗ Empty password verification failed!")
            return False
    except Exception as e:
        print(f"  ✗ Error with empty password: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\nThe password hashing implementation is working correctly.")
    print("You can now:")
    print("  1. Run: python scripts/cleanup_users.py")
    print("  2. Start: python app.py")
    print("  3. Sign up with a password")
    print("  4. The password will be hashed automatically! 🎉")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    success = test_password_hashing()
    sys.exit(0 if success else 1)
