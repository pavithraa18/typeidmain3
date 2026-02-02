"""
User service for managing user data
"""
import sqlite3
import json
from datetime import datetime


def _get_db_paths():
    """
    Compute DB + schema paths relative to the backend folder.

    backend/
      services/user_service.py   (this file)
      instance/biometric_app.db
      instance/typing_biometric.sql
    """
    import os

    services_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(services_dir)
    instance_dir = os.path.join(backend_dir, "instance")
    db_path = os.path.join(instance_dir, "biometric_app.db")
    schema_path = os.path.join(instance_dir, "typing_biometric.sql")
    return instance_dir, db_path, schema_path


def _is_sqlite_db_file(path: str) -> bool:
    """Return True if file looks like a SQLite DB."""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
        return header.startswith(b"SQLite format 3\x00")
    except Exception:
        return False


def _initialize_sqlite_db(db_path: str, schema_path: str) -> None:
    """Create a fresh sqlite database using the provided schema file."""
    import os

    if not os.path.exists(schema_path):
        raise RuntimeError(
            f"Schema file not found at {schema_path}. "
            "Cannot initialize database."
        )

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def _ensure_database_ready() -> str:
    """
    Ensure the DB file exists and is a valid SQLite database.

    This repo includes a placeholder `biometric_app.db` that is not a real
    SQLite file (often a Git LFS pointer). In that case we create a fresh DB
    from `typing_biometric.sql`.
    """
    import os

    instance_dir, db_path, schema_path = _get_db_paths()
    os.makedirs(instance_dir, exist_ok=True)

    if os.path.exists(db_path) and not _is_sqlite_db_file(db_path):
        # Keep the existing file for debugging, then recreate a real DB.
        broken_path = db_path + ".broken"
        try:
            if os.path.exists(broken_path):
                os.remove(broken_path)
            os.replace(db_path, broken_path)
        except Exception:
            # If rename fails, we'll still try to recreate (sqlite3 will error if blocked).
            pass

    if (not os.path.exists(db_path)) or (not _is_sqlite_db_file(db_path)):
        _initialize_sqlite_db(db_path, schema_path)

    return db_path

def get_db_connection():
    """Get database connection with timeout to prevent locking"""
    db_path = _ensure_database_ready()
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)  # Increased timeout, autocommit mode
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class UserService:
    """Service for user operations"""
    
    def __init__(self):
        # Don't store connection - create fresh one for each operation
        pass
    
    def _get_conn(self):
        """Get a fresh database connection for each operation"""
        return get_db_connection()
    
    def find_user_by_name(self, username):
        """Find user by username"""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM user WHERE name = ?"
            cursor = conn.execute(query, (username,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[ERROR] Error finding user: {e}")
            return None
        finally:
            conn.close()
    
    def find_user_by_id(self, user_id):
        """Find user by user_id"""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM user WHERE user_id = ?"
            cursor = conn.execute(query, (user_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[ERROR] Error finding user: {e}")
            return None
        finally:
            conn.close()
    
    def create_user(self, name, email, password_hash=None):
        """Create a new user"""
        conn = self._get_conn()
        try:
            # First create user in user table
            query = """
            INSERT INTO user (name, email, created_at)
            VALUES (?, ?, ?)
            """
            cursor = conn.execute(query, (name, email, datetime.now().isoformat()))
            
            user_id = cursor.lastrowid
            user = self.find_user_by_id(user_id)
            
            # Also create entry in user_registration table with password hash
            if user:
                self.create_user_registration(user_id, password_hash)
            
            return user
        except Exception as e:
            print(f"[ERROR] Error creating user: {e}")
            return None
        finally:
            conn.close()
    
    def create_user_registration(self, user_id, password_hash=None):
        """Create user registration record"""
        conn = self._get_conn()
        try:
            query = """
            INSERT INTO user_registration (reg_id, user_id, password, biometriclogin, registration_date)
            VALUES (?, ?, ?, ?, ?)
            """
            # Use user_id as reg_id for simplicity
            conn.execute(query, (
                user_id,  # reg_id
                user_id,  # user_id
                password_hash or 'hashed_password_placeholder',  # password (hashed or placeholder)
                'enabled',  # biometriclogin
                datetime.now().isoformat()
            ))
            print(f"[OK] Created user_registration record for user_id {user_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Error creating user_registration: {e}")
            return False
        finally:
            conn.close()
    
    def create_login_session(self, user_id, reg_id, login_method='biometric', status='success'):
        """Create login session record"""
        conn = self._get_conn()
        try:
            query = """
            INSERT INTO login_session (user_id, reg_id, login_time, status, login_method)
            VALUES (?, ?, ?, ?, ?)
            """
            conn.execute(query, (
                user_id,
                reg_id,
                datetime.now().isoformat(),
                status,
                login_method
            ))
            print(f"[OK] Created login_session record for user_id {user_id} ({login_method}, {status})")
            return True
        except Exception as e:
            print(f"[ERROR] Error creating login_session: {e}")
            return False
        finally:
            conn.close()
    
    def save_keystroke_profile(self, user_id, reg_id, sample_text, typing_pattern):
        """Save keystroke profile to biometric_profile table"""
        conn = None
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                conn = self._get_conn()
                
                query = """
                INSERT INTO biometric_profile (user_id, reg_id, sample_text, typing_pattern, created_date)
                VALUES (?, ?, ?, ?, ?)
                """
                
                # Convert typing_pattern dict to JSON string
                typing_pattern_json = json.dumps(typing_pattern)
                
                conn.execute(query, (
                    user_id,
                    reg_id,
                    sample_text,
                    typing_pattern_json,
                    datetime.now().isoformat()
                ))
                
                print(f"[OK] Successfully saved keystroke profile to database for user_id {user_id}")
                return True
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    print(f"[WARNING] Database locked, retrying ({retry_count}/{max_retries})...")
                    import time
                    time.sleep(0.5)  # Wait 500ms before retry
                    continue
                else:
                    print(f"[ERROR] Error saving keystroke profile: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
                    
            except Exception as e:
                print(f"[ERROR] Error saving keystroke profile: {e}")
                import traceback
                traceback.print_exc()
                return False
                
            finally:
                if conn:
                    conn.close()
        
        return False
    
    def get_user_keystroke_samples(self, username):
        """
        Retrieve the registered keystroke samples for a user from biometric_profile table
        Returns list of feature dictionaries with keys:
        [ks_count, ks_rate, dwell_mean, dwell_std, flight_mean, flight_std,
         digraph_mean, digraph_std, backspace_rate, wps, wpm]
        """
        conn = self._get_conn()
        try:
            # Get user_id from username
            user = self.find_user_by_name(username)
            if not user:
                print(f"[ERROR] User '{username}' not found")
                return []
            
            user_id = user.get('user_id') or user.get('id')
            
            # Query biometric_profile table for this user's samples
            query = """
            SELECT typing_pattern 
            FROM biometric_profile 
            WHERE user_id = ? 
            ORDER BY created_date DESC
            """
            
            cursor = conn.execute(query, (user_id,))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"[WARNING] No keystroke samples found for user_id {user_id}")
                return []
            
            print(f"[STATS] Retrieved {len(rows)} samples from database for user '{username}'")
            
            # Parse typing_pattern (stored as JSON string)
            samples = []
            for i, row in enumerate(rows):
                typing_pattern = row[0]
                
                # Parse JSON if stored as string
                if isinstance(typing_pattern, str):
                    try:
                        pattern_data = json.loads(typing_pattern)
                    except json.JSONDecodeError as e:
                        print(f"[WARNING] Failed to parse JSON for sample {i+1}: {e}")
                        continue
                else:
                    pattern_data = typing_pattern
                
                samples.append(pattern_data)
                print(f"   Sample {i+1}: {list(pattern_data.keys())[:5]}... (showing first 5 keys)")
            
            return samples
            
        except Exception as e:
            print(f"[ERROR] Error retrieving keystroke samples: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()