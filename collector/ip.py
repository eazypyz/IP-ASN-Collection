#!/usr/bin/env python3
"""
IP Enumerator - Mengekstrak IP individual dari prefix.
"""
import ipaddress
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def enumerate_ips_from_prefix(prefix: str, max_hosts: int = 256) -> list[str]:
    """Mengekstrak IP dari prefix CIDR."""
    try:
        network = ipaddress.ip_network(prefix, strict=False)
        if network.version == 6:
            # Untuk IPv6, hanya ambil beberapa sample
            hosts = list(network.hosts())[:max_hosts]
        else:
            # Untuk IPv4, batasi jumlah host
            hosts = list(network.hosts())[:max_hosts]
        return [str(h) for h in hosts]
    except ValueError:
        return []


def collect_ips(prefixes: list[dict], max_per_prefix: int = 256) -> list[dict]:
    """Mengumpulkan semua IP dari daftar prefix."""
    all_ips = []
    for p in prefixes:
        prefix = p["prefix"]
        print(f"[IP] Enumerating IPs from {prefix} ...")
        ips = enumerate_ips_from_prefix(prefix, max_per_prefix)
        for ip in ips:
            all_ips.append({
                "ip": ip,
                "prefix": prefix,
                "ip_version": p["ip_version"],
                "parent_asn": p["parent_asn"],
            })
        print(f"[IP] Found {len(ips)} IP(s) from {prefix}")
    return all_ips


def save_ips(ips: list[dict]):
    """Menyimpan hasil IP ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "ips.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ips, f, indent=2, ensure_ascii=False)
    print(f"[IP] Saved {len(ips)} IP(s) to {path}")


def load_ips() -> list[dict]:
    """Memuat data IP yang sudah ada."""
    path = DATA_DIR / "ips.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    import sys
    prefix_path = DATA_DIR / "prefixes.json"
    if not prefix_path.exists():
        print("[ERROR] prefixes.json tidak ditemukan. Jalankan prefix.py dulu.", file=sys.stderr)
        sys.exit(1)

    with open(prefix_path, "r", encoding="utf-8") as f:
        prefixes = json.load(f)

    ips = collect_ips(prefixes)
    save_ips(ips)
