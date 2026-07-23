#!/usr/bin/env python3
"""
HTTP Scanner - Memindai IP untuk mendeteksi layanan HTTP/HTTPS.
"""
import asyncio
import json
import ssl
import sys
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent / "data"
CONCURRENT_LIMIT = 50
TIMEOUT = 10.0
PORTS = [80, 443, 8080, 8443]


async def scan_single_ip(ip: str, port: int, client: httpx.AsyncClient) -> dict | None:
    """Memindai satu IP:port."""
    protocol = "https" if port in (443, 8443) else "http"
    url = f"{protocol}://{ip}:{port}"

    try:
        resp = await client.get(url, follow_redirects=True, timeout=TIMEOUT)

        result = {
            "ip": ip,
            "port": port,
            "protocol": protocol,
            "url": str(resp.url),
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "server": resp.headers.get("server", ""),
            "title": "",
            "content_length": len(resp.content),
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Extract title
        content = resp.text
        if "<title>" in content.lower():
            try:
                start = content.lower().index("<title>") + 7
                end = content.lower().index("</title>")
                result["title"] = content[start:end].strip()[:200]
            except ValueError:
                pass

        return result
    except Exception:
        return None


async def scan_ips(ips: list[dict], limit: int = 500) -> list[dict]:
    """Memindai daftar IP untuk layanan HTTP/HTTPS."""
    # Batasi jumlah IP yang dipindai
    ips = ips[:limit]

    results = []
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

    # Buat client dengan SSL verification disabled untuk IP scanning
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    transport = httpx.AsyncHTTPTransport(verify=ssl_context)

    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
        tasks = []
        for ip_info in ips:
            ip = ip_info["ip"]
            for port in PORTS:
                async def task(ip=ip, port=port):
                    async with semaphore:
                        return await scan_single_ip(ip, port, client)
                tasks.append(task())

        print(f"[HTTP] Scanning {len(ips)} IPs x {len(PORTS)} ports = {len(tasks)} requests ...")

        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            if result and result.get("status_code"):
                results.append(result)
            if (i + 1) % 100 == 0:
                print(f"[HTTP] Progress: {i + 1}/{len(tasks)}")

    return results


def save_http_results(results: list[dict]):
    """Menyimpan hasil scan HTTP ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "http_results.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[HTTP] Saved {len(results)} alive result(s) to {path}")


def load_http_results() -> list[dict]:
    """Memuat hasil scan HTTP yang sudah ada."""
    path = DATA_DIR / "http_results.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    ip_path = DATA_DIR / "ips.json"
    if not ip_path.exists():
        print("[ERROR] ips.json tidak ditemukan. Jalankan ip.py dulu.", file=sys.stderr)
        sys.exit(1)

    with open(ip_path, "r", encoding="utf-8") as f:
        ips = json.load(f)

    # Filter hanya IPv4 untuk scanning
    ipv4_ips = [ip for ip in ips if ip.get("ip_version") == 4]

    results = asyncio.run(scan_ips(ipv4_ips))
    save_http_results(results)
