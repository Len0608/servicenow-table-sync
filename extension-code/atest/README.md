# Acceptance Tests (`atest/`)

Robot Framework integration tests for this Universal Extension. Tests create real UAC entities (credentials, scripts, tasks), launch tasks against a live UAC instance, and assert on the results.

## Prerequisites

Before running anything, source the project's `.env`:

```bash
source .env
```

This sets `UIP_URL`/`UIP_USERID`/`UIP_PASSWORD` (UAC connection), plus `UE_CLAUDE_CODE_UAC_LIBRARY_PATH` and `PYTHONPATH`, which point at the shared `UACLibrary` Robot Framework keyword library (lives outside this project, alongside the installed Stonebranch Universal Extension AI Builder — see `__init__.robot`'s `Library` line). If `.env` is missing these two variables, re-run `ue-init`'s environment setup step, or add them manually and update `UE_CLAUDE_CODE_UAC_LIBRARY_PATH` if the plugin is installed somewhere else.

## Running the tests

**Dry-run** (structural check only — no UAC task is launched, catches broken imports/keywords/syntax):

```bash
robot --dryrun --outputdir memory-ephemeral/test-results atest/
```

**Full run** (stops at the first failure):

```bash
robot -X --outputdir memory-ephemeral/test-results --skip status:sunset --skip status:design_gap --skip status:max_fix_attempts --skip status:manual_intervention --skip status:dep_failed atest/
```

Run both from the extension's project root, not from inside `atest/`. Do **not** prefix either command with `python -m` — that was the old convention when `uac/` lived inside this project; the library is now resolved via `UE_CLAUDE_CODE_UAC_LIBRARY_PATH`/`PYTHONPATH`, so bare `robot` is enough.

This excludes every test with a terminal or cascade-failed status tag, but leaves `status:passed` tests in — so a manual full run always re-verifies previously-passing tests too. Tests start with no tag (meaning "not yet run"). The testing phase writes tags as runs complete: `status:passed` (orchestrator, after each run); `status:dep_failed` (debugger, cascaded from a terminal ancestor); and four terminal outcomes that are never re-run unless explicitly cleared — `status:sunset` (retired by a later feature), `status:design_gap` (needs a design change), `status:max_fix_attempts` (stuck after two fix attempts), `status:manual_intervention` (blocked on something external).

At the start of each testing session, the phase clears session-scoped tags (`status:passed`, `status:dep_failed`, `status:max_fix_attempts`, `status:manual_intervention`) so all tests re-run fresh. The two permanent tags (`status:sunset`, `status:design_gap`) are never cleared.

## Layout

```
atest/
├── __init__.robot          # Suite setup/teardown: verifies deployment, creates/deletes UAC entities
├── common.resource         # Shared variables (${AGENT}) and library import, used by every suite
├── test_environment.md     # Agent host paths, required env vars, external service config
├── data/                   # Script source files referenced by __init__.robot (.sql, .sh, .py, ...)
│   └── schemas/             # JSON Schema files for Extension Output validation, one per work item
└── {M}__{work_item_id}.robot    # Per-work-item test suite
```

Results (`output.xml`, `log.html`, `report.html`) are written to `memory-ephemeral/test-results/` and are never committed.
