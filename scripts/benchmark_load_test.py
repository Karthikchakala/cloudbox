#!/usr/bin/env python3
"""
CloudBox Performance Benchmark & Load Testing Utility
Measures latency (median, p95, p99), throughput (RPS), and error rates under concurrency.
"""

import os
import sys
import time
import uuid
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.getenv("TARGET_URL", "http://localhost:5000")

def benchmark_endpoint(name: str, fn, iterations: int = 50, concurrency: int = 5) -> dict:
    latencies = []
    errors = 0
    start_all = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fn) for _ in range(iterations)]
        for f in as_completed(futures):
            try:
                latency_ms, success = f.result()
                if success:
                    latencies.append(latency_ms)
                else:
                    errors += 1
            except Exception:
                errors += 1

    total_time = time.time() - start_all
    rps = round(len(latencies) / total_time, 2) if total_time > 0 else 0.0

    if latencies:
        latencies.sort()
        median_lat = round(statistics.median(latencies), 2)
        p95_lat = round(latencies[int(len(latencies) * 0.95)], 2)
        min_lat = round(min(latencies), 2)
        max_lat = round(max(latencies), 2)
    else:
        median_lat = p95_lat = min_lat = max_lat = 0.0

    return {
        "operation": name,
        "total_requests": iterations,
        "concurrency": concurrency,
        "successful": len(latencies),
        "errors": errors,
        "throughput_rps": rps,
        "median_ms": median_lat,
        "p95_ms": p95_lat,
        "min_ms": min_lat,
        "max_ms": max_lat,
    }

def run_benchmarks():
    print("==========================================================")
    print("  CLOUDBOX PERFORMANCE BENCHMARK & LOAD TEST SUITE")
    print(f"  Target: {BASE_URL}")
    print("==========================================================")

    # Setup synthetic user
    synth_user = f"bench_{uuid.uuid4().hex[:8]}"
    synth_email = f"{synth_user}@cloudbox.bench"
    synth_pass = "BenchmarkPassword123!"

    print(f"[*] Registering benchmark user: {synth_email}...")
    reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": synth_user,
        "email": synth_email,
        "password": synth_pass
    })

    if reg_resp.status_code != 201:
        print(f"[-] Registration failed: {reg_resp.text}")
        return

    auth_token = reg_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Upload initial files for listing & download benchmarks
    print("[*] Seeding benchmark files...")
    file_ids = []
    for i in range(5):
        up_resp = requests.post(
            f"{BASE_URL}/api/files",
            headers=headers,
            files={"file": (f"test_doc_{i}.txt", f"Sample text content for file number {i} " * 50)}
        )
        if up_resp.status_code == 201:
            file_ids.append(up_resp.json()["file"]["id"])

    # Define test functions
    def test_login():
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": synth_email, "password": synth_pass})
        return (time.time() - t0) * 1000, r.status_code == 200

    def test_list_files_cached():
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/files?page=1&per_page=20", headers=headers)
        return (time.time() - t0) * 1000, r.status_code == 200

    def test_analytics_overview():
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/analytics/overview", headers=headers)
        return (time.time() - t0) * 1000, r.status_code == 200

    def test_file_download():
        if not file_ids:
            return 0.0, False
        target_id = file_ids[0]
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/files/{target_id}/download", headers=headers)
        return (time.time() - t0) * 1000, r.status_code == 200

    def test_chunked_upload_flow():
        t0 = time.time()
        init_r = requests.post(
            f"{BASE_URL}/api/uploads/initiate",
            headers=headers,
            json={"filename": "bench_chunk.dat", "file_size": 1024 * 1024, "chunk_size": 512 * 1024, "total_chunks": 2}
        )
        if init_r.status_code != 201:
            return (time.time() - t0) * 1000, False

        up_id = init_r.json()["upload_id"]
        c1_r = requests.put(f"{BASE_URL}/api/uploads/{up_id}/chunks/1", headers=headers, data=b"X" * (512 * 1024))
        c2_r = requests.put(f"{BASE_URL}/api/uploads/{up_id}/chunks/2", headers=headers, data=b"Y" * (512 * 1024))
        comp_r = requests.post(f"{BASE_URL}/api/uploads/{up_id}/complete", headers=headers)
        return (time.time() - t0) * 1000, comp_r.status_code == 201

    results = []
    print("\n[*] Benchmarking 1: Login & Argon2 Verification (50 reqs, c=5)...")
    results.append(benchmark_endpoint("Authentication (Login)", test_login, iterations=30, concurrency=5))

    print("[*] Benchmarking 2: Redis-Cached File Listing (100 reqs, c=10)...")
    results.append(benchmark_endpoint("Cached File Listing", test_list_files_cached, iterations=100, concurrency=10))

    print("[*] Benchmarking 3: Storage Analytics Overview (50 reqs, c=5)...")
    results.append(benchmark_endpoint("Analytics Overview", test_analytics_overview, iterations=50, concurrency=5))

    print("[*] Benchmarking 4: MinIO File Download Streaming (50 reqs, c=5)...")
    results.append(benchmark_endpoint("File Download Streaming", test_file_download, iterations=50, concurrency=5))

    print("[*] Benchmarking 5: Resumable Chunked Upload Flow (10 reqs, c=2)...")
    results.append(benchmark_endpoint("Chunked Upload Assembly", test_chunked_upload_flow, iterations=10, concurrency=2))

    print("\n==========================================================================================")
    print("                               BENCHMARK RESULTS MATRIX")
    print("==========================================================================================")
    print(f"{'Operation':<26} | {'Reqs':<6} | {'Throughput (RPS)':<18} | {'Median':<10} | {'p95 Latency':<12}")
    print("-" * 86)
    for r in results:
        print(f"{r['operation']:<26} | {r['total_requests']:<6} | {r['throughput_rps']:>14.1f} rps | {r['median_ms']:>8.2f}ms | {r['p95_ms']:>10.2f}ms")
    print("==========================================================================================")

if __name__ == "__main__":
    run_benchmarks()
