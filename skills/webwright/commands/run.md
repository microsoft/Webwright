---
description: Run a one-shot web task using the Webwright skill (no parameterization).
argument-hint: <natural-language web task>
---

Use the `webwright` skill (`SKILL.md`) to perform the following web task
in **default one-shot mode**:

$ARGUMENTS

Follow the standard Webwright workflow:

1. Pick a `WORKSPACE_DIR` and write `plan.md` with a numbered list of
   critical points.
2. Explore with scratch Playwright scripts; use `Read` on PNGs to
   inspect UI state.
3. Author and run an instrumented `final_script.py` inside a fresh
   `final_runs/run_<id>/` (viewport 1280×1800, headless local Chromium,
   no `full_page=True`).
4. Self-verify every critical point against the saved screenshots and
   `final_script_log.txt`. Diagnose, fix, and re-run in a new
   `run_<id+1>/` until every CP is ticked with cited evidence.
5. Report the final datum (price, code, winner, …) verbatim.

Refer to `reference/playwright_patterns.md` and `reference/workflow.md`
for details. Do **not** use CLI tool mode for this task.
