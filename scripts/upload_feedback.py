#!/usr/bin/env python3
"""
upload_feedback.py

Uploads markdown feedback files to Canvas submission comments.
Always sets comment[group_comment]=true (required for group assignments).

Expected filename pattern:
    LastnameFirstname[_LATE]_UserId_SecondNumericToken_Anything.md

The first all-digit underscore-separated token is used as the Canvas user_id.
The second all-digit token is used as assignment_id unless --assignment-id overrides it.

Usage:
    python scripts/upload_feedback.py [options]

Options:
    --config            Path to JSON config file (e.g. configs/ma.json)
    --homeworks-dir     Directory containing markdown feedback files (default: homeworks)
    --course-id         Canvas course ID
    --assignment-id     Override assignment ID for all files
    --canvas-server     Canvas base URL (default: https://canvas.uw.edu)
    --token-file        Path to file containing Canvas API token
                        (default: ~/local/bin/token-canvas.txt)
    --dry-run           Print what would be uploaded without making API calls
    --limit             Upload at most N files (0 = no limit)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from canvas_api import build_submission_url, canvas_put, load_token
from config_loader import apply_config_defaults, load_config


@dataclass
class FeedbackFile:
    path: Path
    user_id: str
    filename_assignment_id: str


def extract_ids_from_filename(path: Path) -> FeedbackFile | None:
    """
    Parse user_id and a secondary numeric token from a Canvas submission filename.
    Returns None if fewer than two numeric tokens are found.
    """
    parts = path.stem.split("_")
    digit_tokens = [part for part in parts if part.isdigit()]
    if len(digit_tokens) < 2:
        return None
    return FeedbackFile(path=path, user_id=digit_tokens[0], filename_assignment_id=digit_tokens[1])


def upload_feedback(
    canvas_server: str,
    course_id: str,
    assignment_id: str,
    user_id: str,
    comment_text: str,
    token: str,
    dry_run: bool,
) -> str:
    """
    Upload a text comment for one student submission.
    Always sends comment[group_comment]=true.

    Returns "success", "dry_run", or "error:<message>".
    """
    url = build_submission_url(canvas_server, course_id, assignment_id, user_id)
    data = {
        "comment[text_comment]": comment_text,
        "comment[attempt]": "1",
        "comment[group_comment]": "true",
    }

    response = canvas_put(url, token, data, dry_run)

    if dry_run:
        return "dry_run"

    if response is None:
        return "error:no_response"

    if response.status_code in (200, 201):
        return "success"

    hint = ""
    if response.status_code == 404 and not assignment_id:
        hint = " (hint: pass --assignment-id; the second numeric token may not be the Canvas assignment ID)"
    return f"error:HTTP_{response.status_code}:{response.text[:200]}{hint}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload markdown feedback files to Canvas as submission comments."
    )
    parser.add_argument("--config", default=None, help="Path to JSON config file (e.g. configs/ma.json)")
    parser.add_argument("--homeworks-dir", default=None, help="Directory containing markdown feedback files")
    parser.add_argument("--course-id", default=None, help="Canvas course ID")
    parser.add_argument("--assignment-id", default=None, help="Override assignment ID for all files")
    parser.add_argument("--canvas-server", default=None, help="Canvas base URL")
    parser.add_argument("--token-file", default=None, help="Path to file containing Canvas API token")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without making API calls")
    parser.add_argument("--limit", type=int, default=0, help="Upload at most N files (0 = no limit)")
    args = parser.parse_args()

    if args.config:
        apply_config_defaults(args, load_config(args.config))

    # Final fallback defaults
    if args.homeworks_dir is None:
        args.homeworks_dir = "homeworks"
    if args.canvas_server is None:
        args.canvas_server = "https://canvas.uw.edu"
    if args.token_file is None:
        args.token_file = "~/local/bin/token-canvas.txt"

    if args.course_id is None:
        print("ERROR: --course-id is required (or set in config file)", file=sys.stderr)
        return 2

    hw_dir = Path(args.homeworks_dir)
    if not hw_dir.is_dir():
        print(f"ERROR: homeworks directory not found: {hw_dir}", file=sys.stderr)
        return 2

    token = load_token(args.token_file) if not args.dry_run else "DRY_RUN_TOKEN"

    md_files = sorted(hw_dir.glob("*.md"))
    parsed_files: list[FeedbackFile] = []
    skipped_parse: list[Path] = []

    for md in md_files:
        parsed = extract_ids_from_filename(md)
        if parsed is None:
            skipped_parse.append(md)
            continue
        parsed_files.append(parsed)

    if args.limit > 0:
        parsed_files = parsed_files[:args.limit]

    if not parsed_files:
        print("No parsable markdown files found.")
        return 1

    print(f"Canvas: {args.canvas_server}/courses/{args.course_id}")
    print(f"Homeworks dir: {hw_dir}  ({len(parsed_files)} files)")
    if args.dry_run:
        print("DRY RUN mode: no changes will be made to Canvas")
    print("-" * 60)

    ok_count = 0
    fail_count = 0

    for item in parsed_files:
        text = item.path.read_text(encoding="utf-8", errors="replace")
        assignment_id = args.assignment_id or item.filename_assignment_id

        print(f"  {item.path.name} -> user={item.user_id} assignment={assignment_id} ...", end=" ", flush=True)

        result = upload_feedback(
            canvas_server=args.canvas_server,
            course_id=args.course_id,
            assignment_id=assignment_id,
            user_id=item.user_id,
            comment_text=text,
            token=token,
            dry_run=args.dry_run,
        )

        print(result)
        if result in ("success", "dry_run"):
            ok_count += 1
        else:
            fail_count += 1

    if skipped_parse:
        print("\nSkipped (could not parse user_id and a second numeric token):")
        for p in skipped_parse:
            print(f"  - {p.name}")

    print("-" * 60)
    print(f"Done. Success: {ok_count}, Failed: {fail_count}, Skipped: {len(skipped_parse)}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
