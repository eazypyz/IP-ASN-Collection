#!/usr/bin/env python3
"""
Prefix Collector - Multi-source prefix discovery.
Sumber: RIPEstat API, PeeringDB API, BGP.HE.NET scraping (fallback).
"""
import json
import re
import sys
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent / "data"

# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════
RIPESTAT_PREFIXES_URL = "https://stat.ripe.net/data/announced-prefixes/data.json"
RIPESTAT_ROUTING_STATUS = "https://stat.ripe.net/data/routing-status/data.json"
PEERINGDB_NET_URL = "https://www.peeringdb.com/api/net"
BGP_HE_NET_URL = "https://bgp.he.net/AS{asn}"


def fetch_ripestat_prefixes(asn: str | int) -> list[dict]:
    """Ambil prefix dari RIPEstat announced-prefixes API."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(RIPESTAT_PREFIXES_URL, params={
                "resource": f"AS{asn}",
                "starttime": "",
                "endtime": "",
            })
            resp.raise_for_status()
            data = resp.json()

            seen = set()
            for p in data.get("data", {}).get("prefixes", []):
                prefix = p.get("prefix", "")
                if prefix and prefix not in seen:
                    seen.add(prefix)
                    # Determine IP version
                    try:
                        import ipaddress
                        network = ipaddress.ip_network(prefix, strict=False)
                        ip_version = network.version
                    except ValueError:
                        ip_version = 4 if "." in prefix else 6

                    results.append({
                        "prefix": prefix,
                        "ip_version": ip_version,
                        "timelines": p.get("timelines", []),
                        "parent_asn": str(asn),
                        "source": "ripestat",
                    })
    except Exception as e:
        print(f"[WARN] RIPEstat prefixes gagal untuk AS{asn}: {e}", file=sys.stderr)
    return results


def fetch_ripestat_routing_status(asn: str | int) -> dict:
    """Ambil routing status dari RIPEstat untuk validasi."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(RIPESTAT_ROUTING_STATUS, params={"resource": f"AS{asn}"})
            resp.raise_for_status()
            return resp.json().get("data", {})
    except Exception as e:
        print(f"[WARN] RIPEstat routing status gagal untuk AS{asn}: {e}", file=sys.stderr)
        return {}


def fetch_peeringdb_prefixes(asn: str | int) -> list[dict]:
    """Ambil prefix dari PeeringDB (prefix guidance, bukan live BGP)."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(PEERINGDB_NET_URL, params={"asn": asn})
            resp.raise_for_status()
            data = resp.json()

            for net in data.get("data", []):
                # PeeringDB tidak selalu punya prefix list detail
                # Tapi kita bisa ambil info_prefixes4 dan info_prefixes6
                info4 = net.get("info_prefixes4", 0)
                info6 = net.get("info_prefixes6", 0)
                # Ini hanya jumlah, bukan list prefix
                # Jadi kita skip untuk prefix collector
                pass
    except Exception as e:
        print(f"[WARN] PeeringDB prefixes gagal untuk AS{asn}: {e}", file=sys.stderr)
    return results


def fetch_bgp_he_net_prefixes(asn: str | int) -> list[dict]:
    """Scrape prefix dari bgp.he.net sebagai fallback."""
    results = []
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; IPAssetsBot/1.0)"}
            resp = client.get(BGP_HE_NET_URL.format(asn=asn), headers=headers)
            resp.raise_for_status()
            html = resp.text

            # Extract IPv4 prefixes
            ipv4_pattern = r'<a href="/net/([^"]+)">[^<]*</a>'
            # Look for prefix table patterns
            # bgp.he.net uses specific HTML structure
            # Try to find prefixes in the page

            # Pattern for prefix links in the table
            prefix_links = re.findall(r'href="/net/([0-9a-fA-F.:]+/[0-9]+)"', html)

            seen = set()
            for prefix in prefix_links:
                if prefix not in seen:
                    seen.add(prefix)
                    try:
                        import ipaddress
                        network = ipaddress.ip_network(prefix, strict=False)
                        ip_version = network.version
                    except ValueError:
                        ip_version = 4 if "." in prefix else 6

                    results.append({
                        "prefix": prefix,
                        "ip_version": ip_version,
                        "parent_asn": str(asn),
                        "source": "bgp.he.net",
                    })
    except Exception as e:
        print(f"[WARN] bgp.he.net scrape gagal untuk AS{asn}: {e}", file=sys.stderr)
    return results


def collect_prefixes_for_asn(asn: str | int) -> list[dict]:
    """Kumpulkan prefix untuk satu ASN dari semua sumber."""
    print(f"[PREFIX] Collecting prefixes for AS{asn} ...")

    # Primary: RIPEstat (live BGP data)
    prefixes = fetch_ripestat_prefixes(asn)

    # Fallback: bgp.he.net jika RIPEstat kosong
    if not prefixes:
        print(f"      → RIPEstat kosong, fallback ke bgp.he.net")
        prefixes = fetch_bgp_he_net_prefixes(asn)

    # Validate dengan routing status
    routing_status = fetch_ripestat_routing_status(asn)
    if routing_status:
        print(f"      → Routing status: {routing_status.get('state', 'unknown')}")

    print(f"      ✓ Found {len(prefixes)} prefix(es)")
    return prefixes


def collect_prefixes(asns: list[dict]) -> list[dict]:
    """Mengumpulkan semua prefix dari daftar ASN."""
    all_prefixes = []
    for asn_info in asns:
        asn = asn_info.get("asn")
        if asn:
            prefixes = collect_prefixes_for_asn(asn)
            all_prefixes.extend(prefixes)
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
    import sys
    asn_path = DATA_DIR / "asns.json"
    if not asn_path.exists():
        print("[ERROR] asns.json tidak ditemukan. Jalankan asn.py dulu.", file=sys.stderr)
        sys.exit(1)

    with open(asn_path, "r", encoding="utf-8") as f:
        asns = json.load(f)

    prefixes = collect_prefixes(asns)
    save_prefixes(prefixes)
