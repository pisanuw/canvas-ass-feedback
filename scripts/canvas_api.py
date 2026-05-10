"""
canvas_api.py

Shared Canvas REST API helpers used by upload_grades.py and upload_feedback.py.
"""

import sys
from pathlib import Path

import requests


def load_token(token_file: str) -> str:
    """Read and return the Canvas API token, stripping whitespace."""
    path = Path(token_file).expanduser()
    if not path.exists():
        print(f"ERROR: Token file not found: {path}")
        sys.exit(1)
    return path.read_text().strip()


def build_submission_url(server: str, course_id: str, assignment_id: str, user_id: str) -> str:
    """Build the Canvas API URL for a student submission."""
    server = server.rstrip("/")
    return (
        f"{server}/api/v1/courses/{course_id}"
        f"/assignments/{assignment_id}/submissions/{user_id}"
    )


def get_submission_attempt(url: str, token: str) -> int | None:
    """Fetch the current attempt number for a submission. Returns None on error."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("attempt")
    except requests.RequestException:
        pass
    return None


def canvas_put(url: str, token: str, data: dict, dry_run: bool) -> requests.Response | None:
    """
    Send a PUT request to the Canvas API.
    Returns the Response on success, or None on error.
    In dry_run mode, prints the request and returns None.
    """
    if dry_run:
        print(f"    [DRY RUN] PUT {url}")
        print(f"    [DRY RUN] data={data}")
        return None

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.put(url, headers=headers, data=data, timeout=30)
    return response
