# Canvas Assignment Feedback

Tools for grading student submissions and uploading feedback to Canvas SpeedGrader as inline comments.

## Scripts

### canvas-upload-feeback.py

Uploads `*_feedback.md` files as submission comments via the Canvas REST API.

```
python3 canvas-upload-feeback.py <course_id> \
  --homeworks-dir <submissions_folder> \
  --server https://canvas.uw.edu \
  --token <token> \
  --assignment-id <assignment_id>
```

Feedback files must be named with at least two underscore-separated numeric tokens, matching the Canvas submission filename convention, e.g.:

```
reinforcementthursday1_4469428_149726581_feedback.md
```

The first numeric token is treated as the Canvas user ID.

Uses `comment[group_comment]=true` so comments appear in SpeedGrader for group assignments.

### save-auth.py

Opens a browser window for manual login to SharePoint, then saves the full session (cookies + storage) to `auth-state.json` for use by `sharepoint-ocr.py`.

```
python3 save-auth.py <sharepoint_url>
```

### sharepoint-ocr.py

Extracts text from a SharePoint Word Online document by scrolling through it with Playwright and running Tesseract OCR on each screenshot.

```
python3 sharepoint-ocr.py <url> [--out output.txt]
```

Reads auth state from `auth-state.json` (created by `save-auth.py`). Falls back to `cookies-fedauth.txt` / `cookies-rtfa.txt` if `auth-state.json` is absent.

Outputs:
- `screenshots/page_NNN.png` (one per page)
- `<output.txt>` (concatenated OCR text, default: `document-text.txt`)

## Workflow

The `/canvas-assignment-feedback` Claude Code skill automates the full grading workflow:

1. Read the assignment PDF to understand questions and rubric
2. Create `<submissions_folder>/sample-solution.md` as a reference
3. Grade each student PDF and write a `*_feedback.md` file
4. Upload all feedback files to Canvas via `canvas-upload-feeback.py`
5. Report score distribution and flag any skipped or failed uploads

Invoke with:

```
/canvas-assignment-feedback
```

Provide: Canvas assignment URL, which questions to grade, submissions folder, and assignment PDF path.

## Auth Setup

1. Put your Canvas API token in `canvas-token.txt` (one line, no trailing whitespace).
2. For SharePoint access, run `save-auth.py` once to create `auth-state.json`.

## Requirements

```
pip install playwright pytesseract pillow
playwright install chromium
```

Tesseract must be installed separately (e.g., `brew install tesseract` on macOS).
