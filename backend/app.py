"""
Flask Backend for Typing Biometric Authentication
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from services.auth_service import AuthService
from services.user_service import UserService
from utils.password_util import hash_password, verify_password

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize services
auth_service = AuthService()
user_service = UserService()

print("Starting TypeID Backend")


@app.route('/api/register', methods=['POST'])
def register():
    """Register endpoint - saves keystroke samples to database"""
    try:
        data = request.get_json()
        
        # DEBUG: Print what we received
        print(f"\n{'='*60}")
        print(f"[RECEIVED] REGISTRATION REQUEST RECEIVED")
        print(f"{'='*60}")
        print(f"Full data: {data}")
        print(f"Username: {data.get('name')}")
        print(f"Email: {data.get('email')}")
        print(f"Keystroke features type: {type(data.get('keystroke_features'))}")
        print(f"Keystroke features: {data.get('keystroke_features')}")
        print(f"Sample text: {data.get('sample_text')}")
        print(f"Attempt number: {data.get('attempt')}")
        print(f"{'='*60}\n")
        
        # Get data - frontend sends 'name', not 'username'
        username = data.get('name') or data.get('username')
        email = data.get('email')
        password = data.get('password')
        keystroke_features = data.get('keystroke_features')
        sample_text = data.get('sample_text', 'The quick brown fox jumps over the lazy dog')
        attempt_number = data.get('attempt', 1)
        
        if not username or not email or not keystroke_features:
            return jsonify({
                'success': False,
                'message': 'Username, email, and keystroke features are required'
            }), 400
        
        # Check if user exists, if not create
        user = user_service.find_user_by_name(username)
        if not user:
            print(f"[NEW] Creating new user: {username}")
            
            # Hash password if provided
            if password:
                hashed_password = hash_password(password)
                print(f"[OK] Password hashed for user: {username}")
            else:
                hashed_password = None
                print(f"[WARNING] No password provided for user: {username}")
            
            user = user_service.create_user(username, email, password_hash=hashed_password)
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create user'
                }), 500
        
        user_id = user.get('user_id') or user.get('id')
        
        # Save keystroke profile
        success = user_service.save_keystroke_profile(
            user_id=user_id,
            reg_id=user_id,  # You can generate a separate reg_id if needed
            sample_text=sample_text,
            typing_pattern=keystroke_features
        )
        
        if success:
            print(f"[OK] Saved keystroke profile for {username} (attempt {attempt_number}) to DATABASE")
            return jsonify({
                'success': True,
                'message': f'Sample {attempt_number} registered successfully',
                'user_id': user_id,
                'role': user.get('role', 'user'),
                'attempt': attempt_number
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to save keystroke profile'
            }), 500
            
    except Exception as e:
        print(f"[ERROR] Registration error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500


@app.route('/api/dashboard/user', methods=['POST'])
def dashboard_user():
    """
    POST /api/dashboard/user
    Input JSON: { "user_id": <int> }
    Output JSON: { profile_count, verified (bool), last_login: { login_time, status, method } | null }
    Uses raw SQLite queries only.
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400

        conn = user_service._get_conn()
        try:
            # Profile count
            cur = conn.execute("SELECT COUNT(*) FROM biometric_profile WHERE user_id = ?", (user_id,))
            profile_count = cur.fetchone()[0]

            # Verified flag: at least 3 samples
            verified = bool(profile_count >= 3)

            # Last login details
            cur = conn.execute(
                "SELECT login_time, status, login_method FROM login_session WHERE user_id = ? ORDER BY login_time DESC LIMIT 1",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                last_login = {'login_time': row[0], 'status': row[1], 'method': row[2]}
            else:
                last_login = None

        finally:
            conn.close()

        return jsonify({
            'success': True,
            'user_id': int(user_id),
            'typing_profile': {
                'count': int(profile_count),
                'verified': verified
            },
            'last_login': last_login
        }), 200

    except Exception as e:
        print(f"[ERROR] dashboard_user: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/login-password', methods=['POST'])
def login_password():
    """Password-based login endpoint. Returns role on success."""
    try:
        data = request.get_json() or {}
        username = data.get('username') or data.get('name')
        password = data.get('password')

        if not username or not password:
            return jsonify({'access_granted': False, 'message': 'Username and password required'}), 400

        user = user_service.find_user_by_name(username)
        if not user:
            return jsonify({'access_granted': False, 'message': 'User not found'}), 404

        user_id = user.get('user_id') or user.get('id')

        # Retrieve stored password hash and role from user_registration
        conn = user_service._get_conn()
        try:
            cur = conn.execute("SELECT password, role FROM user_registration WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'access_granted': False, 'message': 'User registration record not found'}), 404
            stored_hash = row[0]
            role = row[1]
        finally:
            conn.close()

        if not stored_hash:
            return jsonify({'access_granted': False, 'message': 'Password not set for user'}), 400

        if verify_password(password, stored_hash):
            user_service.create_login_session(
                user_id=user_id,
                reg_id=user_id,
                login_method='password',
                status='success'
            )
            return jsonify({
                'access_granted': True,
                'username': username,
                'user_id': user_id,
                'role': role,
                'message': 'Login successful'
            }), 200
        else:
            user_service.create_login_session(
                user_id=user_id,
                reg_id=user_id,
                login_method='password',
                status='failed'
            )
            return jsonify({'access_granted': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print(f"[ERROR] login_password: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'access_granted': False, 'message': 'Internal server error during authentication'}), 500


@app.route('/api/login-hybrid', methods=['POST', 'OPTIONS'])
def login_hybrid():
    """
    Hybrid login endpoint with intelligent routing:
    - CSV users (user1, user2, user3) → ML Model (95% accuracy)
    - Database-only users → Statistical comparison (75-85% accuracy)
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        username = data.get('username') or data.get('name')
        keystroke_features_list = data.get('keystroke_features_list', [])
        
        print(f"\n{'='*60}")
        print(f"[AUTH] HYBRID LOGIN ATTEMPT for user: {username}")
        print(f"Number of keystroke samples: {len(keystroke_features_list)}")
        print(f"{'='*60}")
        
        if not username:
            return jsonify({
                'access_granted': False,
                'message': 'Username is required'
            }), 400
        
        if not keystroke_features_list or len(keystroke_features_list) == 0:
            return jsonify({
                'access_granted': False,
                'message': 'Keystroke features are required'
            }), 400
        
        # Step 1: Check if user exists in database
        user = user_service.find_user_by_name(username)
        
        if not user:
            print(f"[ERROR] User '{username}' not found in database")
            return jsonify({
                'access_granted': False,
                'message': 'User not found'
            }), 404
        
        user_id = user.get('user_id') or user.get('id')
        
        # Fetch role from user_registration
        conn = user_service._get_conn()
        try:
            cur = conn.execute("SELECT role FROM user_registration WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'access_granted': False, 'message': 'User registration record not found'}), 404
            role = row[0]
        finally:
            conn.close()
        
        # Step 2: Check if user is in CSV/ML Model
        csv_users = ['user1', 'user2', 'user3']  # Users with 100 samples in CSV
        
        if username in csv_users:
            # HIGH ACCURACY PATH: Use ML Model (95% accuracy)
            print(f"[OK] User '{username}' found in CSV - Using ML MODEL (High Accuracy)")
            
            try:
                # Use the existing auth_service which has ML model logic
                # Pass the first sample for compatibility (or modify auth_service to handle lists)
                auth_result = auth_service.authenticate_user(username, keystroke_features_list)
                
                if auth_result['authenticated']:
                    ml_details = auth_result['details']['ml_prediction']
                    
                    # Record successful login
                    user_service.create_login_session(
                        user_id=user_id,
                        reg_id=user_id,
                        login_method='ml_model',
                        status='success'
                    )
                    
                    return jsonify({
                        'access_granted': True,
                        'username': username,
                        'user_id': user_id,
                        'role': role,
                        'method': 'ML_MODEL',
                        'confidence': float(ml_details['confidence']),
                        'message': 'Login successful (High accuracy - ML Model)',
                        'details': {
                            'predicted_user': str(ml_details['predicted_user']),
                            'confidence': float(ml_details['confidence']),
                            'threshold': float(ml_details['threshold'])
                        }
                    }), 200
                else:
                    # ML model rejected
                    ml_details = auth_result['details']['ml_prediction']
                    
                    # Record failed login
                    user_service.create_login_session(
                        user_id=user_id,
                        reg_id=user_id,
                        login_method='ml_model',
                        status='failed'
                    )
                    
                    return jsonify({
                        'access_granted': False,
                        'username': username,
                        'method': 'ML_MODEL',
                        'message': 'Authentication failed - Typing pattern does not match',
                        'details': {
                            'predicted_user': str(ml_details['predicted_user']),
                            'confidence': float(ml_details['confidence']),
                            'threshold': float(ml_details['threshold'])
                        }
                    }), 401
                    
            except Exception as e:
                print(f"[ERROR] ML Model error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'access_granted': False,
                    'message': f'ML Model authentication failed: {str(e)}'
                }), 500
        
        else:
            # FAST PATH: Use Database Comparison (75-85% accuracy)
            print(f"[OK] User '{username}' NOT in CSV - Using DATABASE COMPARISON (Fast Path)")
            
            try:
                # Use existing auth_service for statistical matching
                auth_result = auth_service.authenticate_user(username, keystroke_features_list)
                
                if auth_result['authenticated']:
                    stat_details = auth_result['details']['statistical_match']
                    
                    # Record successful login
                    user_service.create_login_session(
                        user_id=user_id,
                        reg_id=user_id,
                        login_method='database_comparison',
                        status='success'
                    )
                    
                    return jsonify({
                        'access_granted': True,
                        'username': username,
                        'user_id': user_id,
                        'role': role,
                        'method': 'DATABASE_COMPARISON',
                        'similarity': float(stat_details['score']),
                        'message': 'Login successful (Database profile match)',
                        'details': {
                            'similarity': float(stat_details['score']),
                            'threshold': float(stat_details['threshold'])
                        }
                    }), 200
                else:
                    # Statistical matching failed
                    stat_details = auth_result['details']['statistical_match']
                    
                    # Record failed login
                    user_service.create_login_session(
                        user_id=user_id,
                        reg_id=user_id,
                        login_method='database_comparison',
                        status='failed'
                    )
                    
                    return jsonify({
                        'access_granted': False,
                        'username': username,
                        'method': 'DATABASE_COMPARISON',
                        'message': 'Authentication failed - Typing pattern does not match stored profile',
                        'details': {
                            'similarity': float(stat_details['score']),
                            'threshold': float(stat_details['threshold'])
                        }
                    }), 401
                    
            except Exception as e:
                print(f"[ERROR] Database comparison error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'access_granted': False,
                    'message': f'Database comparison failed: {str(e)}'
                }), 500
            
    except Exception as e:
        print(f"[ERROR] Hybrid login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'access_granted': False,
            'message': 'Internal server error during authentication'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'TypeID Backend is running'
    }), 200


@app.route('/api/dashboard/admin', methods=['GET'])
def dashboard_admin():
    """
    GET /api/dashboard/admin?role=admin
    GET /api/dashboard/admin?role=student&user_id=<id> OR role=teacher&user_id=<id>
    Admin (role=admin): Returns system-wide summary
    Student/Teacher: Returns user-specific summary if user_id provided
    """
    try:
        role = (request.args.get('role') or '').lower()
        user_id = request.args.get('user_id')

        conn = user_service._get_conn()
        try:
            if role == 'admin':
                # Admin: return system-wide summary
                cur = conn.execute("SELECT COUNT(*) FROM user")
                total_users = cur.fetchone()[0]

                cur = conn.execute("SELECT COUNT(*) FROM biometric_profile")
                total_profiles = cur.fetchone()[0]

                cur = conn.execute("SELECT user_id, name, email, created_at FROM user ORDER BY created_at DESC LIMIT 5")
                recent = [dict(row) for row in cur.fetchall()]

                cur = conn.execute(
                    "SELECT bp.user_id, u.name as username, COUNT(*) as profile_count "
                    "FROM biometric_profile bp JOIN user u ON u.user_id = bp.user_id "
                    "GROUP BY bp.user_id ORDER BY profile_count DESC LIMIT 5"
                )
                top = [dict(row) for row in cur.fetchall()]

                # Fetch activity logs from login_session table
                cur = conn.execute(
                    "SELECT login_time, user_id, status, login_method FROM login_session ORDER BY login_time DESC LIMIT 10"
                )
                activity_logs = [dict(row) for row in cur.fetchall()]

                return jsonify({'success': True, 'total_users': total_users, 'total_profiles': total_profiles, 'recent_users': recent, 'top_users': top, 'activity_logs': activity_logs}), 200

            elif role in ['student', 'teacher']:
                # Student/Teacher: return user-specific summary
                if not user_id:
                    return jsonify({'success': False, 'message': 'user_id required for student/teacher role'}), 400

                # Profile count
                cur = conn.execute("SELECT COUNT(*) FROM biometric_profile WHERE user_id = ?", (user_id,))
                profile_count = cur.fetchone()[0]

                # Verified flag: at least 3 samples
                verified = bool(profile_count >= 3)

                # Last login details
                cur = conn.execute(
                    "SELECT login_time, status, login_method FROM login_session WHERE user_id = ? ORDER BY login_time DESC LIMIT 1",
                    (user_id,)
                )
                row = cur.fetchone()
                if row:
                    last_login = {'login_time': row[0], 'status': row[1], 'method': row[2]}
                else:
                    last_login = None

                return jsonify({
                    'success': True,
                    'user_id': int(user_id),
                    'typing_profile': {
                        'count': int(profile_count),
                        'verified': verified
                    },
                    'last_login': last_login
                }), 200

            else:
                return jsonify({'success': False, 'message': 'invalid role'}), 400

        finally:
            conn.close()

    except Exception as e:
        print(f"[ERROR] dashboard_admin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500



def ensure_admin_exists():
    """Ensure a default admin user exists (username: admin, password: admin123)."""
    try:
        admin = user_service.find_user_by_name("admin")
        if not admin:
            print("[INIT] Default admin not found - creating admin user")
            try:
                pwd_hash = hash_password("admin123")
            except Exception:
                # Fallback if hash_password signature changes
                pwd_hash = None

            user = user_service.create_user("admin", "admin@typeid.com", password_hash=pwd_hash)
            if user:
                print("[INIT] Default admin created (username: admin, password: admin123)")
            else:
                print("[WARNING] Failed to create default admin user")
        else:
            print("[INIT] Admin user already exists")
    except Exception as e:
        print(f"[ERROR] ensure_admin_exists: {e}")


if __name__ == '__main__':
    # Confirm admin exists before starting the server
    ensure_admin_exists()
    app.run(host='0.0.0.0', port=5000, debug=True)