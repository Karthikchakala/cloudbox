"""
Comprehensive test script for Phase 2: User Creation & Authentication
Tests:
1. Register user 'karthik' and 'venkat' with 'password123'
2. Login with username and with email
3. Token validation via /api/auth/me
4. Rejection of invalid passwords (401)
5. Rejection of duplicate registrations (409)
6. Rejection of invalid/empty fields (400)
7. Unauthorized access to protected routes (401)
"""
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_auth():
    print("==================================================")
    print("PHASE 2: AUTHENTICATION & USER MANAGEMENT TESTS")
    print("==================================================")
    
    users = [
        {"username": "karthik", "email": "karthik@cloudbox.local", "password": "password123"},
        {"username": "venkat", "email": "venkat@cloudbox.local", "password": "password123"}
    ]
    
    tokens = {}
    
    for u in users:
        uname = u["username"]
        email = u["email"]
        pwd = u["password"]
        print(f"\n--- Testing Account: {uname} ({email}) ---")
        
        # 1. Try login first
        r_login = requests.post(f"{BASE_URL}/auth/login", json={"username": uname, "password": pwd})
        if r_login.status_code == 200:
            print(f"[PASS] User '{uname}' logged in successfully using username (HTTP 200).")
            tokens[uname] = r_login.json()["access_token"]
        else:
            # 2. Register
            r_reg = requests.post(f"{BASE_URL}/auth/register", json={"username": uname, "email": email, "password": pwd})
            assert r_reg.status_code in [201, 200], f"Registration failed for {uname}: {r_reg.text}"
            print(f"[PASS] User '{uname}' registered successfully (HTTP {r_reg.status_code}).")
            tokens[uname] = r_reg.json()["access_token"]
            
        # 3. Test login with email
        r_email = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": pwd})
        assert r_email.status_code == 200, f"Email login failed: {r_email.text}"
        print(f"[PASS] User '{uname}' logged in successfully using email (HTTP 200).")
        
        # 4. Test /api/auth/me
        r_me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {tokens[uname]}"})
        assert r_me.status_code == 200, f"Profile lookup failed: {r_me.text}"
        profile = r_me.json()["user"]
        assert profile["username"].lower() == uname.lower(), f"Username mismatch: {profile}"
        print(f"[PASS] Token verified via /api/auth/me -> User ID: {profile['id']}, Email: {profile['email']}")
        
        # 5. Test invalid password rejection
        r_bad_pwd = requests.post(f"{BASE_URL}/auth/login", json={"username": uname, "password": "WrongPassword!999"})
        assert r_bad_pwd.status_code == 401, f"Expected 401 on bad password, got {r_bad_pwd.status_code}"
        print(f"[PASS] Invalid password correctly rejected with HTTP 401.")
        
        # 6. Test duplicate registration rejection
        r_dup = requests.post(f"{BASE_URL}/auth/register", json={"username": uname, "email": email, "password": pwd})
        assert r_dup.status_code == 409, f"Expected 409 on duplicate register, got {r_dup.status_code}"
        print(f"[PASS] Duplicate registration rejected with HTTP 409 ({r_dup.json().get('code')}).")

    print("\n--- Additional Edge Case & Protection Tests ---")
    # Missing fields
    r_empty = requests.post(f"{BASE_URL}/auth/login", json={})
    assert r_empty.status_code == 400
    print("[PASS] Empty login payload rejected with HTTP 400.")
    
    # Invalid email format in registration
    r_bad_email = requests.post(f"{BASE_URL}/auth/register", json={"username": "temp_user_xyz", "email": "invalid-email-format", "password": "password123"})
    assert r_bad_email.status_code == 400
    print("[PASS] Invalid email registration rejected with HTTP 400.")
    
    # Unauthorized access to protected /api/auth/me
    r_unauth = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": "Bearer invalid_token_12345"})
    assert r_unauth.status_code == 401
    print("[PASS] Invalid bearer token rejected with HTTP 401.")

    print("\n>>> ALL PHASE 2 AUTHENTICATION TESTS PASSED (100%) <<<")

if __name__ == "__main__":
    test_auth()
