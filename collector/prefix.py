#!/usr/bin/env python3
"""
Prefix Collector - Mengumpulkan prefix IP dari ASN.
"""
import json
import sys
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent / "data"
PREFIX_API = "https://api.bgpview.io/asn/{asn}/prefixes"


def fetch_prefixes_for_asn(asn: str | int) -> list[dict]:
    """Mengambil prefix IPv4/IPv6 untuk sebuah ASN."""
    url = PREFIX_API.format(asn=asn)
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

            prefixes = []
            for p in data.get("data", {}).get("ipv4_prefixes", []):
                prefixes.append({
                    "prefix": p["prefix"],
                    "ip_version": 4,
                    "name": p.get("name", ""),
                    "description": p.get("description", ""),
                    "country_code": p.get("country_code", ""),
                    "parent_asn": str(asn),
                })
            for p in data.get("data", {}).get("ipv6_prefixes", []):
                prefixes.append({
                    "prefix": p["prefix"],
                    "ip_version": 6,
                    "name": p.get("name", ""),
                    "description": p.get("description", ""),
                    "country_code": p.get("country_code", ""),
                    "parent_asn": str(asn),
                })
            return prefixes
    except Exception as e:
        print(f"[ERROR] Gagal fetch prefix untuk ASN {asn}: {e}", file=sys.stderr)
        return []


def collect_prefixes(asns: list[dict]) -> list[dict]:
    """Mengumpulkan semua prefix dari daftar ASN."""
    all_prefixes = []
    for asn_info in asns:
        asn = asn_info["asn"]
        print(f"[PREFIX] Collecting prefixes for AS{asn} ...")
        prefixes = fetch_prefixes_for_asn(asn)
        all_prefixes.extend(prefixes)
        print(f"[PREFIX] Found {len(prefixes)} prefix(es) for AS{asn}")
    return all_prefixes


def save_prefixes(prefixes: list[dict]):
    """Menyimpan hasil prefix ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "prefixes.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prefixes, f, indent=2, ensure_ascii=False)
    print(f"[PREFIX] Saved {len(prefixes)} prefix(es) to {path}")


def load_prefixes() -> list[dict]:
    """Memuat data prefix yang sudah ada."""
    path = DATA_DIR / "prefixes.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    # Load ASN data
    asn_path = DATA_DIR / "asns.json"
    if not asn_path.exists():
        print("[ERROR] asns.json tidak ditemukan. Jalankan asn.py dulu.", file=sys.stderr)
        sys.exit(1)

    with open(asn_path, "r", encoding="utf-8") as f:
        asns = json.load(f)

    prefixes = collect_prefixes(asns)
    save_prefixes(prefixes)
