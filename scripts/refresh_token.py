#!/usr/bin/env python3
"""
refresh_token.py

Generate a new Canvas API access token and save it to token files.

Opens the Canvas Settings page in your browser where you can create a new
personal access token, then validates and saves it.

Usage:
    python scripts/refresh_token.py
    python scripts/refresh_token.py --canvas-server https://canvas.uw.edu
    python scripts/refresh_token.py --token-file ~/local/bin/token-canvas.txt
"""

import argparse
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path

import requests


DEFAULT_SERVER = "https://canvas.uw.edu"
TOKEN_FILES = [
    Path("~/local/bin/token-canvas.txt").expanduser(),
    Path("canvas-token.txt"),
]


def validate_token(server: str, token: str) -> tuple[bool, str]:
    """Test the token with a simple API call. Returns (ok, message)."""
    url = f"{server}/api/v1/users/self/profile"
    try:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if resp.status_code == 200:
            name = resp.json().get("name", "unknown")
            return True, f"Authenticated as: {name}"
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.RequestException as e:
        return False, f"Connection error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Generate and save a new Canvas API token")
    parser.add_argument("--canvas-server", default=DEFAULT_SERVER, help=f"Canvas base URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--token-file", action="append", default=None, help="Additional token file path(s) to write")
    args = parser.parse_args()

    server = args.canvas_server.rstrip("/")
    settings_url = f"{server}/profile/settings"

    print(f"Canvas server: {server}")
    print(f"Opening {settings_url} in your browser...")
    print()
    webbrowser.open(settings_url)

    print("In Canvas Settings:")
    print("  1. Scroll to 'Approved Integrations'")
    print("  2. Click '+ New Access Token'")
    print("  3. Purpose: 'CLI grading tools'")
    print("  4. Leave 'Expires' blank for no expiry (or pick a date)")
    print("  5. Click 'Generate Token' and copy the token string")
    print()

    token = input("Paste the new token here: ").strip()

    if not token:
        print("No token entered. Aborting.")
        return 1

    # Validate
    ok, message = validate_token(server, token)
    if not ok:
        print(f"Token validation FAILED: {message}")
        return 1
    print(f"Token valid. {message}")

    # Determine which files to write
    targets = list(TOKEN_FILES)
    if args.token_file:
        for tf in args.token_file:
            targets.append(Path(tf).expanduser())

    # Save to each file
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Back up existing file
        if path.exists():
            backup = path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d')}")
            shutil.copy2(path, backup)
            print(f"  Backed up {path} -> {backup.name}")

        path.write_text(token + "\n")
        path.chmod(0o600)
        print(f"  Saved to {path}")

    print()
    print("Done. Token saved and validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
