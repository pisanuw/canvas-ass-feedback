2026-05-03 [doc] Created BRIEFING.md for project
2026-05-03 [doc] Created /canvas-assignment-feedback global slash command at ~/.claude/commands/
2026-05-03 [note] Added YAML frontmatter to all ~/.claude/commands/*.md for proper slash command recognition
2026-05-03 [note] Canvas group assignment comments require comment[group_comment]=true in API PUT call, otherwise comments post to one member only and are invisible in SpeedGrader
2026-05-03 [code] canvas-upload-feeback.py: added comment[group_comment]=true to fix SpeedGrader visibility for group assignments
2026-05-03 [scope] MDP-Agency feedback uploaded to Canvas for all 11 groups with Claude.AI header, visible in SpeedGrader
2026-05-07 [scope] reinforcement-1 (Parts 1+2, assignment 11417278): graded 15 submissions, uploaded all; filenames need 2 numeric tokens for upload script
2026-05-07 [note] reinforcement-1 upload: files initially named with one numeric token; renamed to add second token from original PDF filename
2026-05-07 [scope] reinforcement-2 (Parts 3+4, assignment 11417717): graded 15 submissions, uploaded all 15 successfully
2026-05-07 [note] reinforcement-2: thursday3 submission contains prompt injection attempt; thursday11 contains AI-generation artifact text; flagged to instructor
2026-05-07 [note] canvas-assignment-feedback skill: graded questions parameter added (e.g., "questions 3 and 4") to scope grading to specific parts
2026-05-08 [doc] Created README.md documenting all scripts, workflow, auth setup, and requirements
2026-05-08 [doc] Created .gitignore excluding submission folders, screenshots, auth-state.json, canvas-token.txt, cookies-* files
2026-05-08 [doc] Redacted Canvas URLs and assignment IDs from AI-log.md before committing
2026-05-08 [note] Repository initialized and pushed to github.com/pisanuw/canvas-ass-feedback
2026-05-08 [scope] Copied scripts from run-student-assignments repo: run_autograder.py, upload_grades.py, config_loader.py, configs/ma.json
2026-05-08 [code] Refactored: extracted shared Canvas helpers into scripts/canvas_api.py (load_token, build_submission_url, canvas_put)
2026-05-08 [code] Created scripts/upload_feedback.py (replaces canvas-upload-feeback.py); uses canvas_api; comment[group_comment] always on
2026-05-08 [code] Moved save-auth.py and sharepoint-ocr.py to scripts-sharepoint/ with snake_case names; deleted old root-level files
2026-05-09 [doc] Rewrote README.md with usage instructions for all 5 contexts: feedback upload, autograder run, grade upload, config pipeline, SharePoint OCR
