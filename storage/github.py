#!/usr/bin/env python3
"""
GitHub Storage - Menyimpan dan membandingkan data di repository.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def run_git_command(args: list[str]) -> str:
    """Menjalankan perintah git."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        print(f"[GIT] Error: {result.stderr}", file=sys.stderr)
    return result.stdout.strip()


def commit_changes(message: str = "Update scan results"):
    """Commit perubahan data ke GitHub."""
    run_git_command(["config", "--global", "user.email", "action@github.com"])
    run_git_command(["config", "--global", "user.name", "GitHub Action"])

    run_git_command(["add", "data/"])

    # Cek apakah ada perubahan
    status = run_git_command(["status", "--porcelain"])
    if not status:
        print("[GIT] No changes to commit.")
        return False

    run_git_command(["commit", "-m", message])

    # Push jika ada remote
    remotes = run_git_command(["remote"])
    if remotes:
        run_git_command(["push"])
        print("[GIT] Changes pushed to GitHub.")
    else:
        print("[GIT] No remote configured, skipping push.")

    return True


def load_previous_data(filename: str) -> list[dict]:
    """Memuat data dari commit sebelumnya menggunakan git show."""
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:data/{filename}"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


def compare_data(old: list[dict], new: list[dict], key_field: str) -> dict:
    """Membandingkan data lama dan baru."""
    old_keys = {item.get(key_field) for item in old}
    new_keys = {item.get(key_field) for item in new}

    added = [item for item in new if item.get(key_field) not in old_keys]
    removed = [item for item in old if item.get(key_field) not in new_keys]

    return {
        "added": added,
        "removed": removed,
        "total_old": len(old),
        "total_new": len(new),
    }


if __name__ == "__main__":
    commit_changes("Test commit from storage module")
