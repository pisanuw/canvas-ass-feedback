# Canvas Assignment Feedback

Tools for grading student submissions, running autograders, and uploading feedback and grades to Canvas.

## Repository Structure

```
scripts/
  canvas_api.py         # Shared Canvas REST API helpers (token, PUT, URL builder)
  upload_feedback.py    # Upload markdown feedback files as Canvas comments
  upload_grades.py      # Upload numeric scores from autograder results JSON
  run_autograder.py     # Run per-student Python autograder, parse scores, save JSON
  config_loader.py      # Merge JSON config with argparse CLI defaults
scripts-sharepoint/
  save_auth.py          # Playwright browser login to save SharePoint session
  sharepoint_ocr.py     # Playwright + Tesseract OCR for SharePoint Word docs
configs/
  ma.json               # Example config for Multiagent assignment
```

## Usage

### 1. Upload markdown feedback to Canvas (manual grading workflow)

Grade student PDFs by hand (or with the `/canvas-assignment-feedback` skill), then upload the resulting `*_feedback.md` files as SpeedGrader comments.

```bash
python scripts/upload_feedback.py \
  --homeworks-dir reinforcement-2 \
  --course-id 1902104 \
  --assignment-id 11417717 \
  --canvas-server https://canvas.uw.edu \
  --token-file ~/local/bin/token-canvas.txt
```

Or use a config file:

```bash
python scripts/upload_feedback.py --config configs/ma.json --homeworks-dir reinforcement-2
```

Feedback filenames must contain at least two underscore-separated numeric tokens (Canvas submission format):

```
reinforcementthursday1_4469428_149726581_feedback.md
                       ^^^^^^^                        <- Canvas user ID
                                ^^^^^^^^^             <- second numeric token (or use --assignment-id)
```

Add `--dry-run` to preview without uploading. Add `--limit 3` to upload only the first 3 files.

### 2. Run an autograder on student Python submissions

Copy each student's `.py` file into a framework directory, run `autograder.py`, parse the `Total: X/Y` score, and save results to JSON.

```bash
python scripts/run_autograder.py \
  --assignments-dir assignments/ma \
  --framework-dir frameworks/multiagent \
  --results-file results/ma_results.json \
  --timeout 60
```

Or with a config file:

```bash
python scripts/run_autograder.py --config configs/ma.json
```

Options:
- `--student <name>`: run for one student only (debugging)
- `--force`: re-run even if already graded
- `--timeout <seconds>`: per-student time limit (default: 60)

Supports resume: students already recorded in the results JSON are skipped.

### 3. Upload autograder scores to Canvas gradebook

Read the results JSON produced by `run_autograder.py` and upload each student's numeric grade. Attaches autograder output as a comment when score < max.

```bash
python scripts/upload_grades.py \
  --results-file results/ma_results.json \
  --course-id 1902104 \
  --assignment-id 11224139 \
  --canvas-server https://canvas.uw.edu \
  --token-file ~/local/bin/token-canvas.txt
```

Or with a config file:

```bash
python scripts/upload_grades.py --config configs/ma.json
```

Options:
- `--dry-run`: preview without uploading
- `--force`: re-upload even if already marked success
- `--student <name>`: upload for one student only

### 4. Full autograder pipeline (config file)

Create a JSON config in `configs/` for your assignment:

```json
{
  "assignment": {
    "name": "Multiagent",
    "assignments_dir": "assignments/ma",
    "framework_dir": "frameworks/multiagent",
    "results_file": "results/ma_results.json",
    "timeout": 60
  },
  "canvas": {
    "server": "https://canvas.uw.edu",
    "course_id": "1902104",
    "assignment_id": "11224139",
    "token_file": "~/local/bin/token-canvas.txt"
  }
}
```

Then run both steps:

```bash
python scripts/run_autograder.py --config configs/ma.json
python scripts/upload_grades.py --config configs/ma.json
```

CLI arguments override config values, which override hardcoded defaults.

### 5. SharePoint document extraction

Save a browser session (one-time login):

```bash
python scripts-sharepoint/save_auth.py <sharepoint_url>
```

Extract text via OCR:

```bash
python scripts-sharepoint/sharepoint_ocr.py <url> --out output.txt
```

Outputs `screenshots/page_NNN.png` and the concatenated OCR text.

## Claude Code Skills

### /canvas-assignment-feedback

Automates the manual grading workflow:

1. Read the assignment PDF to understand questions and rubric
2. Create a sample solution as reference
3. Grade each student PDF and write a `*_feedback.md` file
4. Upload all feedback to Canvas via `upload_feedback.py`
5. Report score distribution and flag skipped/failed uploads

### /run-autograder

Orchestrates the autograder pipeline (run + upload).

## Auth Setup

1. Put your Canvas API token in `canvas-token.txt` or `~/local/bin/token-canvas.txt` (one line, no trailing whitespace).
2. For SharePoint access, run `scripts-sharepoint/save_auth.py` once to create `auth-state.json`.

## Requirements

Canvas scripts:

```
pip install requests
```

SharePoint scripts:

```
pip install playwright pytesseract pillow
playwright install chromium
```

Tesseract must be installed separately (e.g., `brew install tesseract` on macOS).
