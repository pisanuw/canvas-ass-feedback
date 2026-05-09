#!/usr/bin/env python3
"""
run_autograder.py

Copies each student submission into the framework directory, runs the autograder,
parses the score, and writes results to a JSON file.

Supports resume: students already recorded in the results file are skipped.

Usage:
    python scripts/run_autograder.py [options]

Options:
    --assignments-dir   Directory containing student submission files (default: assignments/ma)
    --framework-dir     Directory containing autograder framework (default: frameworks/multiagent)
    --results-file      Path to JSON results file (default: results/ma_results.json)
    --timeout           Seconds before killing autograder per student (default: 60)
    --student           Only run for a single student name (optional, for debugging)
    --force             Re-run even if student already has a result
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config_loader import apply_config_defaults, load_config


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

def parse_submission_filename(filename: str) -> dict | None:
    """
    Parse a Canvas submission filename into components.

    Expected formats:
        name_CANVASID_SUBMISSIONID_originalname.py
        name_LATE_CANVASID_SUBMISSIONID_originalname.py
        name_LATE_CANVASID_SUBMISSIONID_originalname-1.py  (resubmission)

    Returns a dict with keys: student_name, canvas_user_id, submission_id, is_late
    Returns None if the filename does not match.
    """
    stem = Path(filename).stem  # strip .py
    # Remove trailing resubmission suffix like -1, -2
    stem = re.sub(r"-\d+$", "", stem)
    parts = stem.split("_")

    if len(parts) < 4:
        return None

    if parts[1].upper() == "LATE":
        if len(parts) < 5:
            return None
        return {
            "student_name": parts[0],
            "is_late": True,
            "canvas_user_id": parts[2],
            "submission_id": parts[3],
        }
    else:
        return {
            "student_name": parts[0],
            "is_late": False,
            "canvas_user_id": parts[1],
            "submission_id": parts[2],
        }


def collect_submissions(assignments_dir: Path) -> list[dict]:
    """
    Return a list of parsed submission dicts for all .py files in assignments_dir.
    Each dict also includes the 'filepath' key.
    Skips files that cannot be parsed.
    """
    submissions = []
    for f in sorted(assignments_dir.iterdir()):
        if f.suffix != ".py":
            continue
        info = parse_submission_filename(f.name)
        if info is None:
            print(f"  [WARN] Could not parse filename, skipping: {f.name}")
            continue
        info["filepath"] = str(f)
        info["filename"] = f.name
        submissions.append(info)
    return submissions


# ---------------------------------------------------------------------------
# Autograder execution
# ---------------------------------------------------------------------------

SCORE_PATTERN = re.compile(r"Total:\s*(\d+)/(\d+)", re.IGNORECASE)


def parse_score(output: str) -> tuple[int | None, int | None]:
    """Extract (earned, total) from autograder output. Returns (None, None) if not found."""
    match = SCORE_PATTERN.search(output)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def run_autograder(student: dict, framework_dir: Path, timeout: int) -> dict:
    """
    Copy student file into framework_dir, run autograder, parse result.

    Returns a result dict with keys:
        student_name, canvas_user_id, is_late, filename,
        score, max_score, output, status, graded_at
    where status is one of: "graded", "timeout", "error"
    """
    target = framework_dir / "multiAgents.py"

    # Copy submission into framework
    shutil.copy2(student["filepath"], target)

    output = ""
    status = "error"
    score = None
    max_score = None

    try:
        result = subprocess.run(
            [sys.executable, "autograder.py"],
            cwd=str(framework_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        score, max_score = parse_score(output)
        if score is not None:
            status = "graded"
        else:
            status = "error"
            print(f"    [WARN] Could not find 'Total:' in output for {student['student_name']}")
    except subprocess.TimeoutExpired:
        status = "timeout"
        output = f"[TIMEOUT after {timeout}s]"
        print(f"    [TIMEOUT] {student['student_name']} exceeded {timeout}s")
    except Exception as e:
        status = "error"
        output = f"[ERROR] {e}"
        print(f"    [ERROR] {student['student_name']}: {e}")
    finally:
        # Always clean up
        if target.exists():
            target.unlink()

    return {
        "student_name": student["student_name"],
        "canvas_user_id": student["canvas_user_id"],
        "is_late": student["is_late"],
        "filename": student["filename"],
        "score": score,
        "max_score": max_score,
        "output": output,
        "status": status,
        "graded_at": datetime.now().isoformat(),
        "upload_status": None,
    }


# ---------------------------------------------------------------------------
# Results file I/O
# ---------------------------------------------------------------------------

def load_results(results_file: Path) -> dict:
    """Load existing results JSON, or return empty structure."""
    if results_file.exists():
        with open(results_file) as f:
            return json.load(f)
    return {"students": {}}


def save_results(results: dict, results_file: Path) -> None:
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run autograder for all student submissions")
    parser.add_argument("--config", default=None, help="Path to JSON config file (e.g. configs/ma.json)")
    parser.add_argument("--assignments-dir", default=None, help="Folder with student .py files")
    parser.add_argument("--framework-dir", default=None, help="Folder with autograder.py")
    parser.add_argument("--results-file", default=None, help="JSON file to store results")
    parser.add_argument("--timeout", type=int, default=None, help="Seconds per student before timeout")
    parser.add_argument("--student", default=None, help="Only run for this student name (debugging)")
    parser.add_argument("--force", action="store_true", help="Re-run even if student already has a result")
    args = parser.parse_args()

    if args.config:
        apply_config_defaults(args, load_config(args.config))

    # Final fallback defaults (if no config and no CLI arg)
    if args.assignments_dir is None:
        args.assignments_dir = "assignments/ma"
    if args.framework_dir is None:
        args.framework_dir = "frameworks/multiagent"
    if args.results_file is None:
        args.results_file = "results/ma_results.json"
    if args.timeout is None:
        args.timeout = 60

    assignments_dir = Path(args.assignments_dir)
    framework_dir = Path(args.framework_dir)
    results_file = Path(args.results_file)

    # Validate paths
    if not assignments_dir.is_dir():
        print(f"ERROR: assignments dir not found: {assignments_dir}")
        sys.exit(1)
    if not framework_dir.is_dir():
        print(f"ERROR: framework dir not found: {framework_dir}")
        sys.exit(1)
    if not (framework_dir / "autograder.py").exists():
        print(f"ERROR: autograder.py not found in {framework_dir}")
        sys.exit(1)

    submissions = collect_submissions(assignments_dir)
    if args.student:
        submissions = [s for s in submissions if s["student_name"] == args.student]
        if not submissions:
            print(f"ERROR: No submission found for student '{args.student}'")
            sys.exit(1)

    results = load_results(results_file)
    students = results["students"]

    total = len(submissions)
    skipped = 0
    ran = 0
    errors = 0

    print(f"Found {total} submissions in {assignments_dir}")
    print(f"Results file: {results_file}")
    print(f"Timeout: {args.timeout}s per student")
    print("-" * 60)

    for i, student in enumerate(submissions, 1):
        name = student["student_name"]
        key = student["canvas_user_id"]  # use Canvas ID as unique key

        if not args.force and key in students and students[key].get("status") in ("graded", "timeout"):
            score = students[key].get("score")
            max_s = students[key].get("max_score")
            print(f"[{i}/{total}] SKIP {name} (already {students[key]['status']}: {score}/{max_s})")
            skipped += 1
            continue

        print(f"[{i}/{total}] Running {name} ({student['filename']}) ...", end=" ", flush=True)
        result = run_autograder(student, framework_dir, args.timeout)
        students[key] = result

        if result["status"] == "graded":
            print(f"{result['score']}/{result['max_score']}")
            ran += 1
        elif result["status"] == "timeout":
            print("TIMEOUT")
            errors += 1
        else:
            print("ERROR")
            errors += 1

        # Save after every student so a crash doesn't lose progress
        save_results(results, results_file)

    print("-" * 60)
    print(f"Done. Ran: {ran}, Skipped: {skipped}, Errors/Timeouts: {errors}")
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main()
