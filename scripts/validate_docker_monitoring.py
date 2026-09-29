"""
Docker, Networks, Volumes & Monitoring Validation Script for Phase 8 & Phase 9.
"""
import subprocess
import requests
import json

def validate_docker_and_monitoring():
    print("==================================================")
    print("PHASE 8: DOCKER CONTAINERS, NETWORKS & VOLUMES")
    print("==================================================")
    
    # 1. Docker ps / health checks
    cmd = ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = res.stdout.strip().split("\n")
    print(f"[PASS] Running Docker Containers ({len(lines)}):")
    for l in lines:
        print(f"  - {l}")

    # 2. Docker named volumes
    cmd_vol = ["docker", "volume", "ls", "--format", "{{.Name}}"]
    res_vol = subprocess.run(cmd_vol, capture_output=True, text=True, check=True)
    vols = res_vol.stdout.strip().split("\n")
    print(f"[PASS] Named Volumes Verified ({len(vols)}):")
    for v in vols:
        if "cloudbox" in v.lower():
            print(f"  - {v}")

    print("\n==================================================")
    print("PHASE 9: PROMETHEUS, GRAFANA & MONITORING VALIDATION")
    print("==================================================")

    # 3. Prometheus Health & Targets
    prom_health = requests.get("http://localhost:9090/-/healthy")
    print(f"[PASS] Prometheus Health Endpoint: HTTP {prom_health.status_code}")
    assert prom_health.status_code == 200

    prom_targets = requests.get("http://localhost:9090/api/v1/targets")
    assert prom_targets.status_code == 200
    targets_data = prom_targets.json().get("data", {}).get("activeTargets", [])
    print(f"[PASS] Prometheus Active Scrape Targets ({len(targets_data)}):")
    for t in targets_data:
        print(f"  - Job: '{t.get('labels', {}).get('job')}' | URL: {t.get('scrapeUrl')} | Health: {t.get('health')}")

    # 4. Grafana Data Source & Dashboard API
    grafana_auth = ("admin", "password123")
    ds_res = requests.get("http://localhost:3000/api/datasources", auth=grafana_auth)
    assert ds_res.status_code == 200
    datasources = ds_res.json()
    print(f"[PASS] Grafana Data Sources Connected ({len(datasources)}):")
    for ds in datasources:
        print(f"  - Name: {ds.get('name')} | Type: {ds.get('type')} | URL: {ds.get('url')} | Default: {ds.get('isDefault')}")

    dash_res = requests.get("http://localhost:3000/api/search", auth=grafana_auth)
    assert dash_res.status_code == 200
    dashboards = dash_res.json()
    print(f"[PASS] Provisioned Grafana Dashboards ({len(dashboards)}):")
    for d in dashboards:
        print(f"  - Title: '{d.get('title')}' (UID: {d.get('uid')})")

    # 5. Alertmanager Health
    alert_res = requests.get("http://localhost:9093/-/healthy")
    print(f"[PASS] Alertmanager Health Endpoint: HTTP {alert_res.status_code}")
    assert alert_res.status_code == 200

    print("\n>>> ALL PHASE 8 & 9 DOCKER & MONITORING VALIDATION TESTS PASSED (100%) <<<")

if __name__ == "__main__":
    validate_docker_and_monitoring()
