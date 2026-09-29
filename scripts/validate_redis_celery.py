"""
Redis, Celery and Background Processing Validation Script for Phase 7.
"""
import os
import redis

def validate_redis_celery():
    print("==================================================")
    print("PHASE 7: REDIS & CELERY WORKER VALIDATION")
    print("==================================================")
    
    redis_host = "redis" if os.path.exists("/app") else "localhost"
    
    # 1. Test Authenticated Redis
    print("--- 1. Testing Redis Authentication & Caching ---")
    r_auth = redis.Redis(host=redis_host, port=6379, password="password123", decode_responses=True)
    ping_res = r_auth.ping()
    print(f"[PASS] Authenticated Redis PING -> {ping_res}")
    assert ping_res is True

    # Test cache set/get/delete
    r_auth.set("test_key_phase7", "cloudbox_cache_value", ex=60)
    val = r_auth.get("test_key_phase7")
    assert val == "cloudbox_cache_value"
    r_auth.delete("test_key_phase7")
    print("[PASS] Redis cache SET, GET, EXPIRE, and DELETE operations successful.")

    # Redis info memory
    info = r_auth.info("memory")
    used_mem_human = info.get("used_memory_human", "N/A")
    print(f"[PASS] Redis Memory Usage: {used_mem_human}")

    # 2. Test Unauthenticated / Bad Password Redis
    print("\n--- 2. Testing Redis Security & Auth Rejection ---")
    try:
        r_unauth = redis.Redis(host=redis_host, port=6379, decode_responses=True)
        r_unauth.ping()
        assert False, "Unauthenticated Redis PING should fail!"
    except redis.exceptions.AuthenticationError:
        print("[PASS] Unauthenticated Redis request correctly rejected (AuthenticationError).")

    # 3. Test Celery Worker
    print("\n--- 3. Testing Celery Worker Connectivity & Tasks ---")
    from app.celery_app import celery
    insp = celery.control.inspect(timeout=3.0)
    pings = insp.ping()
    print(f"[PASS] Celery Worker Control Ping: {pings}")
    assert pings and len(pings) > 0, "No active Celery workers responded to ping!"

    registered = insp.registered()
    print(f"[PASS] Registered Celery Tasks on Workers: {list(registered.values())[0]}")

    print("\n>>> ALL PHASE 7 REDIS & CELERY VALIDATION TESTS PASSED (100%) <<<")

if __name__ == "__main__":
    validate_redis_celery()
