#!/usr/bin/env python3
"""
Discord Notifier - Mengirim notifikasi perubahan ke Discord.
"""
import json
import os
import sys
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent / "data"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def send_discord_message(content: str, embeds: list[dict] | None = None):
    """Mengirim pesan ke Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("[DISCORD] DISCORD_WEBHOOK_URL tidak diatur, skip notifikasi.")
        return

    payload = {"content": content}
    if embeds:
        payload["embeds"] = embeds

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(DISCORD_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
        print("[DISCORD] Message sent successfully.")
    except Exception as e:
        print(f"[DISCORD] Failed to send message: {e}", file=sys.stderr)


def send_new_ip_alert(result: dict, company: str = "Unknown"):
    """Mengirim alert untuk IP baru yang terdeteksi."""
    embed = {
        "title": "📡 New IP Detected",
        "color": 0x00FF00,
        "fields": [
            {"name": "Company", "value": company, "inline": True},
            {"name": "IP", "value": result.get("ip", "N/A"), "inline": True},
            {"name": "Status", "value": str(result.get("status_code", "N/A")), "inline": True},
            {"name": "Server", "value": result.get("server", "N/A") or "N/A", "inline": True},
            {"name": "Title", "value": result.get("title", "N/A") or "N/A", "inline": False},
            {"name": "HTTPS", "value": "Yes" if result.get("protocol") == "https" else "No", "inline": True},
        ],
    }
    send_discord_message("", embeds=[embed])


def send_status_change_alert(old: dict, new: dict, company: str = "Unknown"):
    """Mengirim alert untuk perubahan status."""
    embed = {
        "title": "🔄 Status Changed",
        "color": 0xFFA500,
        "fields": [
            {"name": "Company", "value": company, "inline": True},
            {"name": "IP", "value": new.get("ip", "N/A"), "inline": True},
            {"name": "Old Status", "value": str(old.get("status_code", "N/A")), "inline": True},
            {"name": "New Status", "value": str(new.get("status_code", "N/A")), "inline": True},
            {"name": "Old Server", "value": old.get("server", "N/A") or "N/A", "inline": True},
            {"name": "New Server", "value": new.get("server", "N/A") or "N/A", "inline": True},
        ],
    }
    send_discord_message("", embeds=[embed])


def send_server_change_alert(old: dict, new: dict, company: str = "Unknown"):
    """Mengirim alert untuk perubahan server."""
    embed = {
        "title": "🔧 Server Changed",
        "color": 0x3498DB,
        "fields": [
            {"name": "Company", "value": company, "inline": True},
            {"name": "IP", "value": new.get("ip", "N/A"), "inline": True},
            {"name": "Old Server", "value": old.get("server", "N/A") or "N/A", "inline": True},
            {"name": "New Server", "value": new.get("server", "N/A") or "N/A", "inline": True},
        ],
    }
    send_discord_message("", embeds=[embed])


def send_new_screenshot_alert(result: dict, company: str = "Unknown"):
    """Mengirim alert untuk screenshot baru."""
    embed = {
        "title": "📸 New Screenshot",
        "color": 0x9B59B6,
        "fields": [
            {"name": "Company", "value": company, "inline": True},
            {"name": "IP", "value": result.get("ip", "N/A"), "inline": True},
            {"name": "URL", "value": result.get("url", "N/A"), "inline": False},
            {"name": "Title", "value": result.get("title", "N/A") or "N/A", "inline": False},
        ],
    }
    send_discord_message("", embeds=[embed])


def send_summary_alert(
    company: str,
    new_asn: int = 0,
    new_prefix: int = 0,
    new_alive_ip: int = 0,
    new_screenshots: int = 0,
    changed_status: int = 0,
):
    """Mengirim ringkasan harian."""
    embed = {
        "title": "📊 Daily Scan Summary",
        "color": 0x2ECC71,
        "fields": [
            {"name": "Company", "value": company, "inline": True},
            {"name": "New ASN", "value": str(new_asn), "inline": True},
            {"name": "New Prefix", "value": str(new_prefix), "inline": True},
            {"name": "New Alive IP", "value": str(new_alive_ip), "inline": True},
            {"name": "Screenshots", "value": str(new_screenshots), "inline": True},
            {"name": "Changed Status", "value": str(changed_status), "inline": True},
        ],
    }
    send_discord_message("", embeds=[embed])


if __name__ == "__main__":
    # Test
    send_discord_message("🚀 IP Assets Scanner is running!")
