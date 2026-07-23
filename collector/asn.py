#!/usr/bin/env python3
"""
ASN Collector - Mengumpulkan ASN berdasarkan daftar perusahaan.
"""
import json
import os
import sys
from pathlib import Path

import httpx

# Daftar perusahaan yang akan dipantau
COMPANIES = [
    {"name": "Example Corp", "domain": "example.com"},
    {"name": "Tech Solutions", "domain": "techsolutions.io"},
]

# API endpoint untuk ASN lookup
ASN_LOOKUP_URL = "https://api.bgpview.io/search"
DATA_DIR = Path(__file__).parent.parent / "data"


def fetch_asn_for_company(company_name: str, domain: str) -> list[dict]:
    """Mencari ASN untuk sebuah perusahaan menggunakan BGPView API."""
    results = []
    queries = [company_name, domain]

    with httpx.Client(timeout=30.0) as client:
        for query in queries:
            try:
                resp = client.get(ASN_LOOKUP_URL, params={"query_terms": query})
                resp.raise_for_status()
                data = resp.json()

                for asn in data.get("data", {}).get("asns", []):
                    results.append({
                        "asn": asn["asn"],
                        "name": asn.get("name", ""),
                        "description": asn.get("description", ""),
                        "country_code": asn.get("country_code", ""),
                        "source_query": query,
                        "company": company_name,
                    })
            except Exception as e:
                print(f"[ERROR] Gagal fetch ASN untuk '{query}': {e}", file=sys.stderr)

    # Deduplicate by ASN number
    seen = set()
    unique = []
    for r in results:
        if r["asn"] not in seen:
            seen.add(r["asn"])
            unique.append(r)
    return unique


def collect_asns() -> list[dict]:
    """Mengumpulkan semua ASN untuk semua perusahaan."""
    all_asns = []
    for company in COMPANIES:
        print(f"[ASN] Collecting for {company['name']} ...")
        asns = fetch_asn_for_company(company["name"], company["domain"])
        all_asns.extend(asns)
        print(f"[ASN] Found {len(asns)} ASN(s) for {company['name']}")
    return all_asns


def save_asns(asns: list[dict]):
    """Menyimpan hasil ASN ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "asns.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asns, f, indent=2, ensure_ascii=False)
    print(f"[ASN] Saved {len(asns)} ASN(s) to {path}")


def load_asns() -> list[dict]:
    """Memuat data ASN yang sudah ada."""
    path = DATA_DIR / "asns.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    asns = collect_asns()
    save_asns(asns)
