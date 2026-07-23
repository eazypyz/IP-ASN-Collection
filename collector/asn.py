#!/usr/bin/env python3
"""
ASN Collector - Multi-source ASN discovery dengan fallback.
Sumber: PeeringDB API, RIPEstat API, HackerTarget API, WHOIS RDAP.
"""
import json
import os
import sys
from pathlib import Path

import httpx

# ═══════════════════════════════════════════════════════════════
# DAFTAR PERUSAHAAN YANG AKAN DIPANTAU
# ═══════════════════════════════════════════════════════════════
COMPANIES = [
    {"name": "amazon", "domain": "amazon.com"},
    {"name": "paypal", "domain": "paypal"},
]

DATA_DIR = Path(__file__).parent.parent / "data"

# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════
PEERINGDB_SEARCH_URL = "https://www.peeringdb.com/api/net"
PEERINGDB_ORG_URL = "https://www.peeringdb.com/api/org"
RIPESTAT_SEARCH_URL = "https://stat.ripe.net/data/searchcomplete/data.json"
RIPESTAT_AS_OVERVIEW = "https://stat.ripe.net/data/as-overview/data.json"
HACKERTARGET_ASN_URL = "https://api.hackertarget.com/aslookup/"


def fetch_peeringdb_by_name(name: str) -> list[dict]:
    """Cari ASN di PeeringDB berdasarkan nama perusahaan."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            # Search by name partial match
            resp = client.get(
                PEERINGDB_SEARCH_URL,
                params={"name__contains": name, "limit": 50}
            )
            resp.raise_for_status()
            data = resp.json()

            for net in data.get("data", []):
                asn = net.get("asn")
                if asn:
                    results.append({
                        "asn": str(asn),
                        "name": net.get("name", ""),
                        "long_name": net.get("name_long", ""),
                        "description": "",
                        "info_type": net.get("info_type", ""),
                        "info_scope": net.get("info_scope", ""),
                        "website": net.get("website", ""),
                        "source": "peeringdb",
                        "source_query": name,
                        "company": name,
                    })
    except Exception as e:
        print(f"[WARN] PeeringDB name search gagal untuk '{name}': {e}", file=sys.stderr)
    return results


def fetch_peeringdb_by_domain(domain: str) -> list[dict]:
    """Cari ASN di PeeringDB berdasarkan domain."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            # Try website match
            resp = client.get(
                PEERINGDB_SEARCH_URL,
                params={"website__contains": domain.replace("www.", ""), "limit": 50}
            )
            resp.raise_for_status()
            data = resp.json()

            for net in data.get("data", []):
                asn = net.get("asn")
                if asn:
                    results.append({
                        "asn": str(asn),
                        "name": net.get("name", ""),
                        "long_name": net.get("name_long", ""),
                        "description": "",
                        "info_type": net.get("info_type", ""),
                        "info_scope": net.get("info_scope", ""),
                        "website": net.get("website", ""),
                        "source": "peeringdb",
                        "source_query": domain,
                        "company": domain,
                    })
    except Exception as e:
        print(f"[WARN] PeeringDB domain search gagal untuk '{domain}': {e}", file=sys.stderr)
    return results


def fetch_ripestat_search(query: str) -> list[dict]:
    """Cari ASN di RIPEstat searchcomplete."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(RIPESTAT_SEARCH_URL, params={"query_string": query})
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("data", {}).get("results", []):
                if item.get("type") == "autnum":
                    asn = item.get("key", "").replace("AS", "")
                    if asn.isdigit():
                        results.append({
                            "asn": asn,
                            "name": item.get("description", ""),
                            "long_name": "",
                            "description": item.get("description", ""),
                            "info_type": "",
                            "info_scope": "",
                            "website": "",
                            "source": "ripestat",
                            "source_query": query,
                            "company": query,
                        })
    except Exception as e:
        print(f"[WARN] RIPEstat search gagal untuk '{query}': {e}", file=sys.stderr)
    return results


def fetch_hackertarget_by_ip(domain: str) -> list[dict]:
    """Gunakan HackerTarget untuk resolve domain → ASN."""
    results = []
    try:
        # Resolve domain ke IP dulu
        import socket
        try:
            ip = socket.gethostbyname(domain)
        except socket.gaierror:
            return results

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(HACKERTARGET_ASN_URL, params={"q": ip})
            resp.raise_for_status()
            text = resp.text.strip()

            # Format: "ip","asn","prefix","org"
            if text and not text.startswith("error"):
                parts = [p.strip('"') for p in text.split(",")]
                if len(parts) >= 2:
                    asn = parts[1]
                    if asn.isdigit():
                        results.append({
                            "asn": asn,
                            "name": parts[3] if len(parts) > 3 else "",
                            "long_name": "",
                            "description": parts[3] if len(parts) > 3 else "",
                            "info_type": "",
                            "info_scope": "",
                            "website": domain,
                            "source": "hackertarget",
                            "source_query": domain,
                            "company": domain,
                        })
    except Exception as e:
        print(f"[WARN] HackerTarget gagal untuk '{domain}': {e}", file=sys.stderr)
    return results


def fetch_ripestat_as_overview(asn: str) -> dict:
    """Ambil detail ASN dari RIPEstat AS Overview."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(RIPESTAT_AS_OVERVIEW, params={"resource": f"AS{asn}"})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {})
    except Exception as e:
        print(f"[WARN] RIPEstat AS overview gagal untuk AS{asn}: {e}", file=sys.stderr)
        return {}


def collect_asns_for_company(company: dict) -> list[dict]:
    """Kumpulkan ASN untuk satu perusahaan dari semua sumber."""
    name = company["name"]
    domain = company["domain"]

    print(f"[ASN] Collecting for {name} ...")
    all_results = []

    # Source 1: PeeringDB by name
    print(f"      → PeeringDB (name: {name})")
    all_results.extend(fetch_peeringdb_by_name(name))

    # Source 2: PeeringDB by domain
    print(f"      → PeeringDB (domain: {domain})")
    all_results.extend(fetch_peeringdb_by_domain(domain))

    # Source 3: RIPEstat search
    print(f"      → RIPEstat (query: {name})")
    all_results.extend(fetch_ripestat_search(name))
    print(f"      → RIPEstat (query: {domain})")
    all_results.extend(fetch_ripestat_search(domain))

    # Source 4: HackerTarget (domain → IP → ASN)
    print(f"      → HackerTarget (domain: {domain})")
    all_results.extend(fetch_hackertarget_by_ip(domain))

    # Deduplicate by ASN
    seen = set()
    unique = []
    for r in all_results:
        asn = r.get("asn")
        if asn and asn not in seen:
            seen.add(asn)
            # Enrich dengan RIPEstat overview
            overview = fetch_ripestat_as_overview(asn)
            if overview.get("holder"):
                r["name"] = r["name"] or overview["holder"]
            if overview.get("announced") is not None:
                r["announced"] = overview["announced"]
            unique.append(r)

    print(f"      ✓ Found {len(unique)} unique ASN(s)")
    return unique


def collect_asns() -> list[dict]:
    """Mengumpulkan semua ASN untuk semua perusahaan."""
    all_asns = []
    for company in COMPANIES:
        asns = collect_asns_for_company(company)
        all_asns.extend(asns)
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
