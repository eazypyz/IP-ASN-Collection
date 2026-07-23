#!/usr/bin/env python3
"""
Fingerprint Collector - Mengumpulkan metadata dari hasil HTTP scan.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def fingerprint_services(http_results: list[dict]) -> list[dict]:
    """Menambahkan fingerprinting ke hasil HTTP."""
    fingerprinted = []
    for result in http_results:
        fp = result.copy()

        # Extract technology hints dari headers
        headers = result.get("headers", {})
        tech_stack = []

        server = headers.get("server", "").lower()
        if "nginx" in server:
            tech_stack.append("nginx")
        if "apache" in server:
            tech_stack.append("apache")
        if "cloudflare" in server:
            tech_stack.append("cloudflare")
        if "envoy" in server:
            tech_stack.append("envoy")
        if "caddy" in server:
            tech_stack.append("caddy")
        if "microsoft-iis" in server:
            tech_stack.append("iis")

        x_powered = headers.get("x-powered-by", "").lower()
        if "php" in x_powered:
            tech_stack.append("php")
        if "asp.net" in x_powered:
            tech_stack.append("asp.net")

        fp["tech_stack"] = tech_stack
        fp["fingerprint"] = "|".join(tech_stack) if tech_stack else "unknown"

        fingerprinted.append(fp)

    return fingerprinted


def save_fingerprinted(results: list[dict]):
    """Menyimpan hasil fingerprint ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "fingerprinted.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[FINGERPRINT] Saved {len(results)} result(s) to {path}")


def load_fingerprinted() -> list[dict]:
    """Memuat data fingerprint yang sudah ada."""
    path = DATA_DIR / "fingerprinted.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    import sys
    http_path = DATA_DIR / "http_results.json"
    if not http_path.exists():
        print("[ERROR] http_results.json tidak ditemukan.", file=sys.stderr)
        sys.exit(1)

    with open(http_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    fingerprinted = fingerprint_services(results)
    save_fingerprinted(fingerprinted)
