#!/usr/bin/env python3
"""
Main Orchestrator - Menjalankan seluruh pipeline scanning.
Optimized untuk GitHub Actions dengan timeout handling & progress tracking.
"""
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from collector.asn import collect_asns, save_asns, load_asns
from collector.prefix import collect_prefixes, save_prefixes, load_prefixes
from collector.ip import collect_ips, save_ips, load_ips
from scanner.http import scan_ips, save_http_results, load_http_results
from scanner.fingerprint import fingerprint_services, save_fingerprinted, load_fingerprinted
from screenshot.capture import capture_all, save_screenshot_results, load_screenshot_results
from notifier.discord import (
    send_discord_message,
    send_new_ip_alert,
    send_status_change_alert,
    send_server_change_alert,
    send_new_screenshot_alert,
    send_summary_alert,
)
from storage.github import commit_changes, load_previous_data, compare_data

DATA_DIR = Path(__file__).parent / "data"

# ═══════════════════════════════════════════════════════════════
# KONFIGURASI LIMITS (sesuaikan untuk GitHub Actions)
# ═══════════════════════════════════════════════════════════════
MAX_IPS_TO_SCAN = 50        # Batasi IP yang discan (default: 200)
MAX_SCREENSHOTS = 5         # Batasi screenshot (default: 20)
MAX_PREFIX_IPS = 128         # Max IP per prefix (default: 128)
HTTP_TIMEOUT = 8.0           # Timeout per HTTP request (default: 8s)
SCREENSHOT_TIMEOUT = 12000   # Screenshot timeout ms (default: 12s)


def timeout_handler(signum, frame):
    """Handler untuk SIGALRM timeout."""
    raise TimeoutError("Pipeline exceeded time limit")


def run_pipeline():
    """Menjalankan pipeline lengkap dengan timeout protection."""
    start_time = time.time()

    print("=" * 60)
    print("🚀 IP Assets Scanner Pipeline")
    print(f"   Limits: {MAX_IPS_TO_SCAN} IPs, {MAX_SCREENSHOTS} screenshots, {MAX_PREFIX_IPS} IPs/prefix")
    print("=" * 60)

    # Setup timeout alarm (100 menit max untuk safety)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(6000)  # 100 menit dalam detik

    try:
        # Step 1: Collect ASN
        print("\n[1/6] Collecting ASNs...")
        step_start = time.time()
        old_asns = load_previous_data("asns.json")
        new_asns = collect_asns()
        save_asns(new_asns)
        asn_diff = compare_data(old_asns, new_asns, "asn")
        print(f"    ⏱ {time.time() - step_start:.1f}s | ASN: +{len(asn_diff['added'])}, -{len(asn_diff['removed'])}")

        if not new_asns:
            print("[WARN] Tidak ada ASN ditemukan, menggunakan data lama...")
            new_asns = old_asns

        # Step 2: Collect Prefixes
        print("\n[2/6] Collecting Prefixes...")
        step_start = time.time()
        old_prefixes = load_previous_data("prefixes.json")
        new_prefixes = collect_prefixes(new_asns)
        save_prefixes(new_prefixes)
        prefix_diff = compare_data(old_prefixes, new_prefixes, "prefix")
        print(f"    ⏱ {time.time() - step_start:.1f}s | Prefix: +{len(prefix_diff['added'])}, -{len(prefix_diff['removed'])}")

        if not new_prefixes:
            print("[WARN] Tidak ada prefix ditemukan, menggunakan data lama...")
            new_prefixes = old_prefixes

        # Step 3: Enumerate IPs
        print("\n[3/6] Enumerating IPs...")
        step_start = time.time()
        new_ips = collect_ips(new_prefixes, max_per_prefix=MAX_PREFIX_IPS)
        save_ips(new_ips)
        print(f"    ⏱ {time.time() - step_start:.1f}s | Total IPs: {len(new_ips)}")

        # Step 4: HTTP Scan (async, dengan batasan)
        print("\n[4/6] Scanning HTTP services...")
        step_start = time.time()
        ipv4_ips = [ip for ip in new_ips if ip.get("ip_version") == 4]
        scan_targets = ipv4_ips[:MAX_IPS_TO_SCAN]
        print(f"    Scanning {len(scan_targets)} IPs (dari {len(ipv4_ips)} total IPv4)...")

        new_http = asyncio.run(scan_ips(scan_targets))
        save_http_results(new_http)
        print(f"    ⏱ {time.time() - step_start:.1f}s | Alive services: {len(new_http)}")

        # Step 5: Fingerprint
        print("\n[5/6] Fingerprinting services...")
        step_start = time.time()
        fingerprinted = fingerprint_services(new_http)
        save_fingerprinted(fingerprinted)
        print(f"    ⏱ {time.time() - step_start:.1f}s | Fingerprinted: {len(fingerprinted)}")

        # Step 6: Screenshot (async, dengan batasan ketat)
        print("\n[6/6] Capturing screenshots...")
        step_start = time.time()
        screenshot_results = asyncio.run(capture_all(new_http, max_screenshots=MAX_SCREENSHOTS))
        save_screenshot_results(screenshot_results)
        print(f"    ⏱ {time.time() - step_start:.1f}s | Screenshots: {len(screenshot_results)}")

        # Compare dengan data lama
        print("\n[COMPARE] Checking for changes...")
        step_start = time.time()
        old_http = load_previous_data("http_results.json")
        old_screenshots = load_previous_data("screenshot_results.json")

        # Build lookup by IP:port
        old_http_map = {f"{r.get('ip')}:{r.get('port')}": r for r in old_http}
        new_http_map = {f"{r.get('ip')}:{r.get('port')}": r for r in new_http}

        changes = {
            "new_ips": [],
            "status_changes": [],
            "server_changes": [],
            "new_screenshots": [],
        }

        for key, new_result in new_http_map.items():
            if key not in old_http_map:
                changes["new_ips"].append(new_result)
            else:
                old_result = old_http_map[key]
                if old_result.get("status_code") != new_result.get("status_code"):
                    changes["status_changes"].append({"old": old_result, "new": new_result})
                if old_result.get("server") != new_result.get("server"):
                    changes["server_changes"].append({"old": old_result, "new": new_result})

        # Check new screenshots
        old_ss_map = {r.get("url"): r for r in old_screenshots}
        for ss in screenshot_results:
            if ss.get("url") not in old_ss_map:
                changes["new_screenshots"].append(ss)

        print(f"    ⏱ {time.time() - step_start:.1f}s | New IPs: {len(changes['new_ips'])}, Status changes: {len(changes['status_changes'])}")

        # Send notifications
        print("\n[NOTIFY] Sending Discord notifications...")
        step_start = time.time()

        for ip in changes["new_ips"]:
            send_new_ip_alert(ip)

        for change in changes["status_changes"]:
            send_status_change_alert(change["old"], change["new"])

        for change in changes["server_changes"]:
            send_server_change_alert(change["old"], change["new"])

        for ss in changes["new_screenshots"]:
            send_new_screenshot_alert(ss)

        # Send summary
        send_summary_alert(
            company="All Companies",
            new_asn=len(asn_diff["added"]),
            new_prefix=len(prefix_diff["added"]),
            new_alive_ip=len(changes["new_ips"]),
            new_screenshots=len(changes["new_screenshots"]),
            changed_status=len(changes["status_changes"]),
        )

        print(f"    ⏱ {time.time() - step_start:.1f}s | Notifications sent")

        # Commit changes
        print("\n[STORAGE] Committing to GitHub...")
        step_start = time.time()
        has_changes = commit_changes("Update IP assets scan results")
        print(f"    ⏱ {time.time() - step_start:.1f}s | Commit done")

        # Disable alarm
        signal.alarm(0)

        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"✅ Pipeline completed in {total_time:.1f}s!")
        print(f"   New IPs: {len(changes['new_ips'])}")
        print(f"   Status Changes: {len(changes['status_changes'])}")
        print(f"   Server Changes: {len(changes['server_changes'])}")
        print(f"   New Screenshots: {len(changes['new_screenshots'])}")
        print("=" * 60)

    except TimeoutError:
        print("\n[ERROR] ⏰ Pipeline exceeded 100 minute limit!", file=sys.stderr)
        print("[INFO] Tips: Kurangi MAX_IPS_TO_SCAN atau MAX_SCREENSHOTS di main.py", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
