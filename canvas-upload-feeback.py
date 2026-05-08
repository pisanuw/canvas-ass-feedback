#!/usr/bin/env python3
"""Upload markdown feedback files to Canvas submission comments.

Expected filename pattern (supports optional LATE marker):
    LastnameFirstname[_LATE]_UserId_SecondNumericToken_Anything.md

The script extracts the first all-digit underscore-separated token as:
    user_id

By default it uses the second all-digit token as assignment_id. If your course
uses a single assignment for all files, pass --assignment-id to override.

It then uploads the entire markdown file as:
    comment[text_comment]
to:
    PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id



Usage: python3 upload_feedback_to_canvas.py 1902104 --homeworks-dir homeworks --server https://canvas.uw.edu/ --token $CANVAS_TOKEN --assignment-id 11223983
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib import error, parse, request


@dataclass
class FeedbackFile:
    path: Path
    user_id: str
    filename_assignment_id: str


def extract_ids_from_filename(path: Path) -> Optional[FeedbackFile]:
    parts = path.stem.split("_")
    digit_tokens = [part for part in parts if part.isdigit()]
    if len(digit_tokens) < 2:
        return None
    return FeedbackFile(path=path, user_id=digit_tokens[0], filename_assignment_id=digit_tokens[1])


def canvas_put_comment(
    server: str,
    token: str,
    course_id: str,
    assignment_id: str,
    user_id: str,
    comment_text: str,
) -> tuple[bool, str]:
    server = server.rstrip("/")
    endpoint = (
        f"{server}/api/v1/courses/{course_id}/assignments/{assignment_id}"
        f"/submissions/{user_id}"
    )
    payload = parse.urlencode({
        "comment[text_comment]": comment_text,
        "comment[attempt]": "1",
        "comment[group_comment]": "true",
    }).encode("utf-8")

    req = request.Request(
        endpoint,
        data=payload,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
                submission_id = parsed.get("id")
                return True, f"HTTP {resp.status}; submission_id={submission_id}"
            except json.JSONDecodeError:
                return True, f"HTTP {resp.status}; non-JSON response"
    except error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}; {err_body[:600]}"
    except error.URLError as exc:
        return False, f"Connection error: {exc.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload markdown feedback files in homeworks/ to Canvas as submission comments."
    )
    parser.add_argument(
        "course_id",
        nargs="?",
        default="1902104",
        help="Canvas course ID (default: 1902104)",
    )
    parser.add_argument(
        "--homeworks-dir",
        default="homeworks",
        help="Directory containing markdown feedback files (default: homeworks)",
    )
    parser.add_argument(
        "--server",
        default=os.environ.get("CANVAS_SERVER", ""),
        help="Canvas base URL (default: $CANVAS_SERVER)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("CANVAS_TOKEN", ""),
        help="Canvas API token (default: $CANVAS_TOKEN)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be uploaded without making API calls.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Upload at most N files (0 means no limit).",
    )
    parser.add_argument(
        "--assignment-id",
        default="",
        help=(
            "Override assignment ID for all files. Recommended when all feedback files "
            "belong to one assignment."
        ),
    )

    args = parser.parse_args()

    if not args.server:
        print("Error: Canvas server is required. Set $CANVAS_SERVER or pass --server.", file=sys.stderr)
        return 2

    if not args.token and not args.dry_run:
        print("Error: Canvas token is required. Set $CANVAS_TOKEN or pass --token.", file=sys.stderr)
        return 2

    hw_dir = Path(args.homeworks_dir)
    if not hw_dir.exists() or not hw_dir.is_dir():
        print(f"Error: homeworks directory not found: {hw_dir}", file=sys.stderr)
        return 2

    md_files = sorted(hw_dir.glob("*.md"))
    parsed_files: list[FeedbackFile] = []
    skipped: list[Path] = []

    for md in md_files:
        parsed = extract_ids_from_filename(md)
        if parsed is None:
            skipped.append(md)
            continue
        parsed_files.append(parsed)

    if args.limit > 0:
        parsed_files = parsed_files[: args.limit]

    if not parsed_files:
        print("No parsable markdown files found.")
        return 1

    ok_count = 0
    fail_count = 0

    for item in parsed_files:
        text = item.path.read_text(encoding="utf-8", errors="replace")
        assignment_id = args.assignment_id or item.filename_assignment_id
        if args.dry_run:
            print(
                f"DRY RUN: {item.path.name} -> course={args.course_id}, "
                f"assignment={assignment_id}, user={item.user_id}, chars={len(text)}"
            )
            ok_count += 1
            continue

        ok, message = canvas_put_comment(
            server=args.server,
            token=args.token,
            course_id=args.course_id,
            assignment_id=assignment_id,
            user_id=item.user_id,
            comment_text=text,
        )
        status = "OK" if ok else "FAIL"
        if not ok and "HTTP 404" in message and not args.assignment_id:
            message += (
                " (hint: pass --assignment-id <id>; the second numeric token in the "
                "filename may not be the Canvas assignment ID)"
            )
        print(f"{status}: {item.path.name} -> {message}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    if skipped:
        print("\nSkipped files (could not parse user_id and a second numeric token):")
        for p in skipped:
            print(f"- {p.name}")

    print(
        f"\nSummary: success={ok_count}, failed={fail_count}, "
        f"skipped={len(skipped)}, total_seen={len(md_files)}"
    )

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
