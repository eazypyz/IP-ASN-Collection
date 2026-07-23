#!/usr/bin/env python3
"""
Diagnostic script - Cek kenapa pipeline lama atau hang.
Jalankan ini di GitHub Actions untuk debug.
"""
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def diagnose():
    print("=" * 60)
    print("🔍 IP Assets Scanner Diagnostic")
    print("=" * 60)

    # Check data files
    files = ["asns.json", "prefixes.json", "ips.json", "http_results.json", "screenshot_results.json"]
    for f in files:
        path = DATA_DIR / f
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {f}: {size} bytes")
        else:
            print(f"❌ {f}: NOT FOUND")

    # Check if previous run was too big
    ip_path = DATA_DIR / "ips.json"
    if ip_path.exists():
        import json
        with open(ip_path) as f:
            ips = json.load(f)
        ipv4 = [ip for ip in ips if ip.get("ip_version") == 4]
        print(f"\n📊 IP Stats:")
        print(f"   Total IPs: {len(ips)}")
        print(f"   IPv4: {len(ipv4)}")
        print(f"   IPv6: {len(ips) - len(ipv4)}")
        print(f"   HTTP requests needed: {len(ipv4) * 4} (4 ports each)")
        print(f"   Est. time @ 30 req/s: {len(ipv4) * 4 / 30:.0f}s")
        print(f"   Est. time @ 10 req/s: {len(ipv4) * 4 / 10:.0f}s")

    # Check screenshot count
    ss_dir = DATA_DIR / "screenshots"
    if ss_dir.exists():
        ss_files = list(ss_dir.glob("*.png"))
        print(f"\n📸 Screenshots: {len(ss_files)} files")

    print("\n💡 Tips jika pipeline terlalu lama:")
    print("   1. Kurangi jumlah perusahaan di collector/asn.py")
    print("   2. Kurangi MAX_IPS_TO_SCAN di main.py (default: 200)")
    print("   3. Kurangi MAX_SCREENSHOTS di main.py (default: 20)")
    print("   4. Kurangi MAX_PREFIX_IPS di main.py (default: 128)")
    print("   5. Naikkan CONCURRENT_LIMIT di scanner/http.py")
    print("=" * 60)

if __name__ == "__main__":
    diagnose()
