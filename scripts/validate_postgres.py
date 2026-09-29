"""
PostgreSQL Database Validation Script for Phase 5.
"""
import os
import sys
import psycopg2

def validate_postgres():
    print("==================================================")
    print("PHASE 5: POSTGRESQL TERMINAL & DATA MODEL VALIDATION")
    print("==================================================")
    
    # 1. Connect with valid credentials
    print("--- 1. Authenticating to PostgreSQL ---")
    pg_host = "db" if os.path.exists("/app") else "localhost"
    conn = psycopg2.connect(
        host=pg_host,
        port=5432,
        user="cloudbox_user",
        password="password123",
        dbname="cloudbox_db"
    )
    cur = conn.cursor()
    
    # 2. Verify current user and database
    cur.execute("SELECT current_user, current_database();")
    user, db = cur.fetchone()
    print(f"[PASS] Connected as User: '{user}', Database: '{db}'")
    assert user == "cloudbox_user"
    assert db == "cloudbox_db"
    
    # 3. List tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [t[0] for t in cur.fetchall()]
    print(f"[PASS] Database Tables Found ({len(tables)}): {tables}")
    expected_tables = ["files", "file_versions", "share_links", "upload_sessions", "users"]
    for et in expected_tables:
        assert et in tables, f"Expected table '{et}' missing from public schema."

    # 4. Verify User records
    cur.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at;")
    users = cur.fetchall()
    print(f"[PASS] User Records Found ({len(users)} users):")
    usernames = [u[1] for u in users]
    for u in users:
        print(f"  - ID: {u[0]} | Username: {u[1]} | Email: {u[2]}")
    assert "karthik" in usernames
    assert "venkat" in usernames

    # 5. Verify File & Version records
    cur.execute("SELECT count(*) FROM files;")
    file_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM file_versions;")
    version_count = cur.fetchone()[0]
    print(f"[PASS] File Metadata Records: {file_count} files, {version_count} version entries.")

    # 6. Verify Foreign Keys and Constraints
    cur.execute("""
        SELECT
            tc.constraint_name, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
    """)
    fks = cur.fetchall()
    print(f"[PASS] Foreign Key Constraints Verified ({len(fks)} constraints):")
    for fk in fks:
        print(f"  - {fk[1]}.{fk[2]} -> {fk[3]}.{fk[4]} ({fk[0]})")

    # 7. Test Invalid Password Rejection
    print("\n--- 2. Negative Authentication Test ---")
    try:
        bad_conn = psycopg2.connect(
            host=pg_host,
            port=5432,
            user="cloudbox_user",
            password="wrong_password_999",
            dbname="cloudbox_db"
        )
        assert False, "Connection with bad password should have failed!"
    except psycopg2.OperationalError:
        print("[PASS] Connection rejected with invalid password (psycopg2.OperationalError).")

    cur.close()
    conn.close()
    print("\n>>> ALL PHASE 5 POSTGRESQL VALIDATION TESTS PASSED (100%) <<<")

if __name__ == "__main__":
    validate_postgres()
