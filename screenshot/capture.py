#!/usr/bin/env python3
"""
Screenshot Service - Mengambil screenshot dari IP yang aktif.
Optimized untuk GitHub Actions dengan strict timeout.
"""
import asyncio
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.parent / "data"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
CONCURRENT_LIMIT = 3        # Dikurangi dari 5 untuk stabilitas
TIMEOUT = 10000             # Dikurangi dari 15s ke 10s


def sanitize_filename(url: str) -> str:
    """Membuat nama file yang aman dari URL."""
    safe = url.replace("://", "_").replace("/", "_").replace(":", "_")
    return safe[:100]


async def capture_screenshot(url: str, page) -> str | None:
    """Mengambil screenshot dari sebuah URL."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
        # Wait a bit more for images
        await asyncio.sleep(1)
        filename = sanitize_filename(url) + ".png"
        filepath = SCREENSHOT_DIR / filename
        await page.screenshot(path=str(filepath), full_page=False)
        return str(filepath.relative_to(DATA_DIR))
    except Exception as e:
        print(f"    [SCREENSHOT] Failed for {url}: {e}")
        return None


async def capture_all(http_results: list[dict], max_screenshots: int = 20) -> list[dict]:
    """Mengambil screenshot untuk semua URL yang aktif."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter hanya status 200-399
    targets = [r for r in http_results if 200 <= r.get("status_code", 0) < 400]
    targets = targets[:max_screenshots]

    if not targets:
        print("    [SCREENSHOT] No valid targets found")
        return []

    print(f"    [SCREENSHOT] Capturing {len(targets)} screenshots (max: {max_screenshots})")

    results_with_screenshots = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

        async def process_target(target, index):
            async with semaphore:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                url = target["url"]
                print(f"    [SCREENSHOT] [{index+1}/{len(targets)}] {url}")
                screenshot_path = await capture_screenshot(url, page)
                await context.close()

                result = target.copy()
                result["screenshot"] = screenshot_path
                return result

        tasks = [process_target(t, i) for i, t in enumerate(targets)]
        results = await asyncio.gather(*tasks)
        results_with_screenshots = [r for r in results if r.get("screenshot")]

        await browser.close()

    print(f"    [SCREENSHOT] Success: {len(results_with_screenshots)}/{len(targets)}")
    return results_with_screenshots


def save_screenshot_results(results: list[dict]):
    """Menyimpan hasil screenshot ke file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "screenshot_results.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[SCREENSHOT] Saved {len(results)} screenshot result(s) to {path}")


def load_screenshot_results() -> list[dict]:
    """Memuat data screenshot yang sudah ada."""
    path = DATA_DIR / "screenshot_results.json"
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

    screenshot_results = asyncio.run(capture_all(results))
    save_screenshot_results(screenshot_results)
