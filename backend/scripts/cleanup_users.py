"""
Cleanup script to remove old users so they can re-register with hashed passwords.
This is needed because the password_util.py now uses bcrypt hashing.

Usage:
    python cleanup_users.py
"""

import sqlite3
import os
from pathlib import Path

# Get database path
backend_dir = Path(__file__).parent.parent
db_path = backend_dir / "instance" / "biometric_app.db"

def cleanup_users():
    """Delete old users to allow re-registration with hashed passwords"""
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get existing users before cleanup
        cursor.execute("SELECT user_id, name FROM user")
        existing_users = cursor.fetchall()
        
        print("\n📋 EXISTING USERS BEFORE CLEANUP:")
        print("=" * 60)
        for user_id, name in existing_users:
            print(f"  - {name} (ID: {user_id})")
        
        # Delete records in reverse foreign key order
        print("\n🗑️  CLEANING UP...")
        
        tables_to_clean = [
            "login_session",
            "biometric_profile",
            "user_registration",
            "user"
        ]
        
        for table in tables_to_clean:
            cursor.execute(f"DELETE FROM {table}")
            count = cursor.rowcount
            print(f"  ✓ Cleared {table}: {count} records deleted")
        
        conn.commit()
        conn.close()
        
        print("\n✅ CLEANUP COMPLETE!")
        print("All users have been removed. You can now re-register with hashed passwords.")
        print("\nNext steps:")
        print("1. Start the Flask backend: python app.py")
        print("2. Go to http://localhost:5173 (frontend)")
        print("3. Sign up with a new username, email, and password")
        print("4. Complete 5 keystroke samples")
        print("\nThe password will now be hashed using bcrypt before storage! 🔐")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    cleanup_users()
