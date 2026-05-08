# Briefing

- Purpose: Automate grading and Canvas feedback upload for CSS 382 assignments
- Current scope: Grade student PDF submissions, generate plain-text feedback files, upload as inline SpeedGrader comments via Canvas REST API
- Key decisions:
  - Feedback files are plain text (no markdown symbols) to avoid PDF download prompt
  - Canvas API requires comment[group_comment]=true for group assignments; without it comments are invisible in SpeedGrader
  - Upload script: canvas-upload-feeback.py; token in canvas-token.txt
  - Feedback header must read "Claude.AI" (not "Canvas.AI")
- Non-goals: Automated student grade submission (scores are informational in comments only, not posted to gradebook)
- Repository: github.com/pisanuw/canvas-ass-feedback (submissions, auth files, and secrets are gitignored)
