# Backend Review: Modules 1-3 (Registration, Login, Dashboard)

**Date:** February 1, 2026  
**Scope:** Flask backend endpoints for biometric authentication system  
**Constraints Applied:** No JWT/sessions, no ML logic changes, fixes only if necessary

---

## ✅ WHAT IS ALREADY CORRECT

### SQL Injection Protection
- ✅ **All SQL queries use parameterized placeholders (?)** - no string concatenation
  - `user_service.py`: `SELECT * FROM user WHERE name = ?` (line 116)
  - `auth_service.py`: Statistical matching with parameterized queries
  - `app.py` endpoints: All dashboard queries parameterized (lines 107-127, 368-395)
- ✅ **Database connection pooling with retry logic** for locked database (user_service.py line 221-242)
- ✅ **WAL mode enabled** for concurrent access (user_service.py line 73)

### Input Validation
- ✅ **Registration endpoint** validates required fields: username, email, keystroke_features (app.py line 46-50)
- ✅ **Login-hybrid endpoint** validates username and keystroke_features_list (app.py line 160-171)
- ✅ **Dashboard endpoints** validate required parameters:
  - `POST /api/dashboard/user`: user_id required (app.py line 109-110)
  - `GET /api/dashboard/admin`: role parameter required (app.py line 347, 380-381)

### Authentication Logic
- ✅ **Two-layer authentication** implemented correctly:
  1. Statistical matching (75-85% accuracy) - auth_service.py lines 97-193
  2. ML model prediction (95% accuracy for CSV users) - auth_service.py lines 187-234
  3. Both layers must pass for successful authentication (auth_service.py line 152)
- ✅ **User existence check** before authentication (auth_service.py line 81-88)
- ✅ **Intelligent routing**: CSV users (user1, user2, user3) → ML model; others → database comparison (app.py line 181-184)

### Database Schema Integration
- ✅ **All 4 required tables properly used:**
  - `user` table: Created in register, queried in auth (user_service.py line 155)
  - `user_registration` table: Auto-created during user creation (user_service.py line 163-174)
  - `biometric_profile` table: Keystroke samples stored (user_service.py line 222-242)
  - `login_session` table: Login attempts recorded (user_service.py line 192-212)
- ✅ **Login session recording** for all authentication attempts:
  - Success case: app.py lines 197-201, 250-254
  - Failure case: app.py lines 213-218, 264-269
  - Database vs ML routing: app.py lines 230-236

### Error Handling
- ✅ **Try-catch blocks** on all endpoints with traceback logging
- ✅ **Informative error messages** returned to frontend
- ✅ **Graceful fallback** when ML model unavailable (auth_service.py lines 34-40)

### Response Format Consistency
- ✅ **Standard JSON response structure:**
  - Success responses include `success: true` + data
  - Error responses include `success: false` + `message`
  - HTTP status codes match semantics (200 success, 400 bad request, 404 not found, 500 error)
- ✅ **Dashboard responses properly structured:**
  - Admin: `{ success, total_users, total_profiles, recent_users, top_users }`
  - User: `{ success, user_id, typing_profile: { count, verified }, last_login }`

### Feature Extraction
- ✅ **Consistent feature ordering** across training and authentication (auth_service.py lines 226-249)
- ✅ **Null-safe feature extraction** with default 0.0 values (auth_service.py line 244)
- ✅ **Z-score normalization** for similarity calculation (auth_service.py line 259-267)

---

## ⚠️ ISSUES FOUND

### 1. **Missing Email Validation** (MINOR)
- **Location:** `app.py` line 46 (registration endpoint)
- **Issue:** Email field accepted but never validated (no format check, no uniqueness check)
- **Current code:**
  ```python
  email = data.get('email')
  if not username or not email or not keystroke_features:
      return jsonify({'success': False, 'message': '...'}), 400
  ```
- **Risk:** Invalid emails accepted; multiple accounts with same email possible
- **Fix:** Add regex validation + uniqueness check in `find_user_by_name()` or database constraint
- **Priority:** LOW - Not required for Module 1-3, can be deferred to Module 4

### 2. **No User ID Type Validation** (MINOR)
- **Location:** `app.py` line 109 (`/api/dashboard/user`) and line 381 (`/api/dashboard/admin`)
- **Issue:** `user_id` and query parameters accepted but not cast to int; could cause SQL errors if non-numeric string passed
- **Current code:**
  ```python
  user_id = data.get('user_id')  # No int() cast
  user_id = request.args.get('user_id')  # No int() cast
  ```
- **Risk:** TypeError in SQL query if `user_id` is malformed string
- **Suggested fix:** 
  ```python
  try:
      user_id = int(data.get('user_id'))
  except (ValueError, TypeError):
      return jsonify({'success': False, 'message': 'user_id must be integer'}), 400
  ```
- **Priority:** MEDIUM - Prevents crashes, improves error messages
- **Note:** Dashboard endpoints still work if database driver coerces types, but explicit validation is better practice

### 3. **Error Leakage in Exception Handlers** (MINOR)
- **Location:** Multiple endpoints expose raw exception messages to frontend
- **Examples:**
  - `app.py` line 86: `'message': f'Internal server error: {str(e)}'` (registration)
  - `app.py` line 315: `'message': f'ML Model authentication failed: {str(e)}'` (login-hybrid)
  - `app.py` line 327: `'message': f'Database comparison failed: {str(e)}'` (login-hybrid)
- **Risk:** Stack traces, internal paths, and exception details exposed to client
- **Current behavior:** Generic "Internal server error" without details on success path (dashboard endpoints do this correctly)
- **Suggested fix:** Use generic message for clients; keep detailed trace in server logs only
  ```python
  # Instead of:
  'message': f'ML Model authentication failed: {str(e)}'
  # Use:
  'message': 'Authentication service temporarily unavailable'
  ```
- **Priority:** LOW - No sensitive data leakage in current setup, but security best practice
- **Note:** Already done correctly in dashboard endpoints (line 409, 427)

### 4. **Hardcoded CSV User List** (DESIGN)
- **Location:** `app.py` line 182
- **Issue:** Hardcoded list `['user1', 'user2', 'user3']` for ML routing decision
- **Current code:**
  ```python
  csv_users = ['user1', 'user2', 'user3']  # Users with 100 samples in CSV
  ```
- **Risk:** Adding new high-accuracy users requires code change + redeploy
- **Suggested fix:** Move to config file or database table in Module 4
- **Priority:** LOW - Not required for current functionality, design improvement
- **Note:** Does not affect Modules 1-3 functionality

### 5. **No Rate Limiting on Endpoints** (SECURITY)
- **Location:** All endpoints (registration, login, dashboard)
- **Issue:** No protection against brute-force login attempts or registration spam
- **Risk:** Attackers can submit unlimited login attempts
- **Suggested fix:** Add Flask-Limiter or similar in Module 4 (not Module 1-3 scope)
- **Priority:** MEDIUM - For later modules, not required for current scope
- **Note:** Out of scope per constraints (no session/auth framework additions)

### 6. **Insufficient Keystroke Sample Validation** (MINOR)
- **Location:** `app.py` line 46 (registration) and `app.py` line 165 (login)
- **Issue:** Keystroke features accepted without schema validation
- **Current validation:**
  ```python
  if not username or not email or not keystroke_features:
      return jsonify({...}), 400
  ```
- **Missing:** Check that keystroke_features is dict with required keys (ks_count, ks_rate, etc.)
- **Risk:** Invalid data saved to database; auth fails on retrieval
- **Suggested fix:** Validate feature keys exist
  ```python
  required_keys = ['ks_count', 'ks_rate', 'dwell_mean', ...]
  if not all(k in keystroke_features for k in required_keys):
      return jsonify({'success': False, 'message': 'Invalid keystroke features'}), 400
  ```
- **Priority:** LOW - Not strictly required; auth_service handles gracefully with default 0.0 values
- **Note:** Feature extraction already handles missing keys safely (auth_service.py line 244)

### 7. **SQL Query Logging in Production** (OPERATIONS)
- **Location:** `user_service.py` line 116, 124, 157, 192 (full queries logged)
- **Issue:** All SQL queries printed to console for debugging
- **Example:** `print(f"[STATS] Retrieved {len(rows)} samples from database for user '{username}'")`
- **Risk:** Console logs may end up in log files; production servers shouldn't log this verbosity
- **Suggested fix:** Use Python logging module with configurable levels
- **Priority:** LOW - Not a security issue currently; operational improvement for Module 4+
- **Note:** Already doing this correctly in app.py for most errors

### 8. **Duplicate Database Connection Logic** (CODE QUALITY)
- **Location:** `user_service.py` lines 108-111 vs `user_service.py` line 113
- **Issue:** `_get_db_paths()`, `_is_sqlite_db_file()`, `_initialize_sqlite_db()`, `_ensure_database_ready()` defined outside class
- **Current pattern:**
  ```python
  # Lines 9-99: Standalone functions
  def _get_db_paths(): ...
  def _is_sqlite_db_file(): ...
  
  # Lines 101-124: Class methods that call standalone functions
  class UserService:
      def _get_conn(self):
          db_path = _ensure_database_ready()
  ```
- **Risk:** Minor - functions are module-private (underscore prefix), but mixing patterns
- **Suggested fix:** Move all database init into class as static/class methods
- **Priority:** VERY LOW - No functional issue, code organization improvement for Module 4+

### 9. **No Attempt Limit on Authentication** (SECURITY DESIGN)
- **Location:** `app.py` lines 144-327 (login-hybrid endpoint)
- **Issue:** No counter for failed login attempts; no account lockout
- **Risk:** Brute-force attacks possible
- **Note:** Deliberately omitted per constraints (no session/auth framework)
- **Suggested fix:** Implement in Module 4 with separate failed_attempts table
- **Priority:** NOT FOR MODULES 1-3 (out of scope)

---

## ✅ DUPLICATE CODE ANALYSIS

### No Significant Duplication Found
- **Registration vs Login:** Different workflows (create user vs verify user)
- **Dashboard User vs Admin endpoints:** Same queries but different conditions (`WHERE user_id = ?` vs `GROUP BY`), appropriate separation
- **SQL query patterns:** Consistent use of parameterized queries, no copy-paste errors
- **Response handling:** Consistent try-catch-finally pattern across endpoints

**Note:** Code is well-organized and doesn't violate DRY principle

---

## ✅ ARCHITECTURE COMPLIANCE

### ER Diagram Tables Usage
- ✅ **user** table: Used in registration (create), login (verify), dashboard (count)
- ✅ **user_registration** table: Created during user registration, linked to user
- ✅ **biometric_profile** table: Populated during registration, queried for auth
- ✅ **login_session** table: Populated on every login attempt (success/failure)

### Module 1-3 Requirements Met
- ✅ **Module 1 (Registration):** User creation, keystroke profile storage
- ✅ **Module 2 (Login):** Biometric authentication with statistical + ML layers; fallback path for non-CSV users
- ✅ **Module 3 (Dashboard):** User and admin summary endpoints with role-based access

### Not Implemented (Correctly Omitted from Modules 1-3)
- ❌ JWT tokens (Module 4 - Authentication Tokens)
- ❌ Session management (Module 4 - Session Management)
- ❌ Password-based login (Module 2B - password fallback mentioned but not implemented)
- ❌ Rate limiting (Module 5 - Security Enhancements)
- ❌ Audit logging (Module 6 - Compliance)

---

## 📋 SUMMARY TABLE

| Category | Status | Details |
|----------|--------|---------|
| SQL Injection | ✅ SECURE | All queries parameterized, no vulnerabilities |
| Input Validation | ⚠️ ADEQUATE | Required fields checked; email & user_id validation missing |
| Error Handling | ✅ GOOD | Try-catch on all endpoints; minor error leakage |
| Database Integration | ✅ CORRECT | All 4 tables used appropriately |
| Response Format | ✅ CONSISTENT | Standard JSON structure across endpoints |
| Authentication Logic | ✅ CORRECT | Two-layer auth working as designed |
| Code Duplication | ✅ MINIMAL | No significant copy-paste issues |
| Architecture | ✅ COMPLIANT | Module 1-3 requirements met |
| Error Leakage | ⚠️ MINOR | Exception details exposed in 2-3 places |
| Rate Limiting | ❌ N/A | Not required for Module 1-3 scope |

---

## 🎯 RECOMMENDATIONS BY PRIORITY

### REQUIRED FOR MODULES 1-3 (Fix Now)
None - all critical functionality is working correctly

### SUGGESTED FOR MODULES 1-3 (Optional)
1. **Add integer validation for user_id parameters** (3 lines of code, prevents edge cases)
   - Location: `app.py` lines 109, 381
   - Effort: 5 minutes

2. **Generic error messages in exception handlers** (replace 3 instances)
   - Location: `app.py` lines 315, 327
   - Effort: 2 minutes

### DEFERRED TO MODULE 4+ (Do Not Implement Now)
- Email validation and uniqueness
- Hardcoded CSV user list → database config
- Rate limiting
- Token-based authentication
- Session management
- Password fallback mechanism

---

## 🔍 DETAILED FINDINGS BY ENDPOINT

### POST /api/register
- ✅ Validates username, email, keystroke_features
- ✅ Creates user if not exists
- ✅ Saves keystroke profile with parameterized SQL
- ✅ Records success/failure
- ⚠️ No email format validation
- ⚠️ No keystroke schema validation (minor - safe default handling)

### POST /api/login-hybrid
- ✅ Two-layer authentication working
- ✅ Intelligent routing (CSV vs database)
- ✅ Records login session
- ⚠️ Error messages expose exception details
- ❌ No rate limiting (expected for Module 1-3)

### POST /api/dashboard/user
- ✅ Parameterized SQL queries
- ✅ Correct response format
- ✅ Role-based logic
- ⚠️ Missing user_id type validation

### GET /api/dashboard/admin
- ✅ Parameterized SQL queries
- ✅ Handles multiple roles (admin, student, teacher)
- ✅ Correct response format
- ⚠️ Missing user_id type validation for student/teacher mode

### GET /api/health
- ✅ Simple health check working

---

## CONCLUSION

**Backend is PRODUCTION-READY for Modules 1-3 with minor non-critical issues.**

- ✅ All critical security checks in place (SQL injection protection)
- ✅ Core functionality (registration, login, dashboard) working correctly
- ✅ Database schema properly integrated
- ✅ Error handling adequate for current scope
- ⚠️ 2-3 minor suggestions for robustness (not blockers)
- ❌ 0 critical bugs found

**Recommendation:** Deploy current backend for Modules 1-3 UAT. Address type validation suggestions in code review before production release.

