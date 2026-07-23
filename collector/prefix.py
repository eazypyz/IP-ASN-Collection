#!/usr/bin/env python3
"""
Prefix Collector - Multi-source prefix discovery dengan retry & graceful fallback.
Sumber: RIPEstat API (primary), bgp.he.net (fallback), bgp.tools (fallback 2).
"""
import json
import re
import sys
import time
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent / "data"

# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════
RIPESTAT_PREFIXES_URL = "https://stat.ripe.net/data/announced-prefixes/data.json"
BGP_HE_NET_URL = "https://bgp.he.net/AS{asn}"
BGP_TOOLS_URL = "https://bgp.tools/as/{asn}"


def fetch_with_retry(client: httpx.Client, url: str, params: dict | None = None,
                     max_retries: int = 3, backoff: float = 2.0) -> httpx.Response | None:
    """Fetch dengan exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            if params:
                resp = client.get(url, params=params, timeout=30.0)
            else:
                resp = client.get(url, timeout=30.0)
            if resp.status_code < 500:  # 4xx = client error, 5xx = retry
                return resp
            # 502/504 = server error, retry
            print(f"      → Retry {attempt + 1}/{max_retries}: HTTP {resp.status_code}")
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            print(f"      → Retry {attempt + 1}/{max_retries}: {type(e).__name__}")

        if attempt < max_retries - 1:
            sleep_time = backoff * (2 ** attempt)
            print(f"      → Waiting {sleep_time}s before retry...")
            time.sleep(sleep_time)
    return None


def fetch_ripestat_prefixes(asn: str | int) -> list[dict]:
    """Ambil prefix dari RIPEstat announced-prefixes API dengan retry."""
    results = []
    try:
        with httpx.Client() as client:
            resp = fetch_with_retry(
                client, RIPESTAT_PREFIXES_URL,
                params={"resource": f"AS{asn}"},
                max_retries=3, backoff=2.0
            )
            if resp is None:
                print(f"      → RIPEstat failed after retries, skipping")
                return results

            if resp.status_code != 200:
                print(f"      → RIPEstat returned HTTP {resp.status_code}")
                return results

            data = resp.json()

            seen = set()
            for p in data.get("data", {}).get("prefixes", []):
                prefix = p.get("prefix", "")
                if prefix and prefix not in seen:
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
                        "timelines": p.get("timelines", []),
                        "parent_asn": str(asn),
                        "source": "ripestat",
                    })

            if results:
                print(f"      → RIPEstat: {len(results)} prefix(es)")
    except Exception as e:
        print(f"[WARN] RIPEstat prefixes error untuk AS{asn}: {e}", file=sys.stderr)
    return results


def fetch_bgp_he_net_prefixes(asn: str | int) -> list[dict]:
    """Scrape prefix dari bgp.he.net sebagai fallback."""
    results = []
    try:
        with httpx.Client(follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; IPAssetsBot/1.0)"}
            resp = fetch_with_retry(
                client, BGP_HE_NET_URL.format(asn=asn),
                max_retries=2, backoff=1.0
            )
            if resp is None or resp.status_code != 200:
                return results

            html = resp.text

            # Pattern for prefix links: href="/net/1.2.3.0/24"
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

            if results:
                print(f"      → bgp.he.net: {len(results)} prefix(es)")
    except Exception as e:
        print(f"[WARN] bgp.he.net scrape error untuk AS{asn}: {e}", file=sys.stderr)
    return results


def fetch_bgp_tools_prefixes(asn: str | int) -> list[dict]:
    """Scrape prefix dari bgp.tools sebagai fallback kedua."""
    results = []
    try:
        with httpx.Client(follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; IPAssetsBot/1.0)"}
            resp = fetch_with_retry(
                client, BGP_TOOLS_URL.format(asn=asn),
                max_retries=2, backoff=1.0
            )
            if resp is None or resp.status_code != 200:
                return results

            html = resp.text

            # bgp.tools uses pattern like: <a href="/prefix/1.2.3.0/24">1.2.3.0/24</a>
            prefix_links = re.findall(r'href="/prefix/([0-9a-fA-F.:]+/[0-9]+)"', html)

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
                        "source": "bgp.tools",
                    })

            if results:
                print(f"      → bgp.tools: {len(results)} prefix(es)")
    except Exception as e:
        print(f"[WARN] bgp.tools scrape error untuk AS{asn}: {e}", file=sys.stderr)
    return results


def collect_prefixes_for_asn(asn: str | int) -> list[dict]:
    """Kumpulkan prefix untuk satu ASN dari semua sumber (dengan fallback chain)."""
    print(f"[PREFIX] Collecting prefixes for AS{asn} ...")

    # Primary: RIPEstat (live BGP data)
    prefixes = fetch_ripestat_prefixes(asn)

    # Fallback 1: bgp.he.net
    if not prefixes:
        print(f"      → RIPEstat kosong, fallback ke bgp.he.net")
        prefixes = fetch_bgp_he_net_prefixes(asn)

    # Fallback 2: bgp.tools
    if not prefixes:
        print(f"      → bgp.he.net kosong, fallback ke bgp.tools")
        prefixes = fetch_bgp_tools_prefixes(asn)

    if not prefixes:
        print(f"      ⚠️ Semua source gagal untuk AS{asn}")
    else:
        print(f"      ✓ Total: {len(prefixes)} prefix(es)")

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
