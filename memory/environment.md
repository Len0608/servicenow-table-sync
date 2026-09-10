# ServiceNow Table Sync Extension — Development Environment

**Generated:** 2026-09-10

## Project Overview

- **Extension Name**: servicenow-table-sync
- **Purpose**: Read Universal Controller (UAC) data via REST APIs and synchronize to ServiceNow customer/account tables and Decision Tables
- **Working Directory**: /tmp/servicenow-table-sync
- **Source Code Directory**: /tmp/servicenow-table-sync/extension-code

## Build Platform

The extension build system (`extension-code/setup.py`) enforces platform-specific constraints:

- **On Linux build machines**: Uses `--only-binary=:all: --platform=manylinux_2_17_x86_64` to enforce Linux-compatible binary wheels
- **On Windows build machines**: Installs Windows-specific wheels without platform constraint
- **Single build produces platform-specific output**: A Linux build produces a Linux-only archive; a Windows build produces a Windows-only archive
- **For cross-platform support**: Use only pure-Python modules (no C extensions)

**Target Platform Compatibility**: Not explicitly stated in initial requirements — **OPEN DECISION POINT** (see Question 1 in requirements-QnA.md)

## Python Version

- **Target Runtime**: Python 3.11
- **Build Environment**: Python 3.11 virtual environment (`extension-code/ue-dev-env/`)

## Key Directories

```
/tmp/servicenow-table-sync/
├── extension-code/           # Extension source and build artifacts
│   ├── src/                  # Extension source code
│   ├── atest/                # Acceptance tests (Robot Framework)
│   ├── setup.py              # Build and dependency installer
│   ├── requirements.txt       # Python dependencies (to be populated)
│   └── ue-dev-env/           # Python venv (git-ignored)
├── memory/
│   ├── initial-1/
│   │   ├── requirements.md   # Initial functional requirements (from user)
│   │   └── requirements-QnA.md # Clarifying questions and answers (THIS FILE GENERATED)
│   └── environment.md         # This file
└── openapi.json              # UAC 8.0.0.0 API schema snapshot (reference)
```

## UAC Controller Reference

- **UAC Version**: 8.0.0.0 (from provided openapi.json snapshot)
- **API Endpoints**: Documented in openapi.json; covers agents, calendars, scripts, tasks, business services
- **Important**: Verify against live Controller's `/resources/openapi.json` before deployment

## ServiceNow Reference

- **Release**: Not specified — OPEN DECISION POINT (see Question 3 in requirements-QnA.md)
- **Key APIs**: Table API (/api/now/table/{tableName}), Decision Table API (may require Scripted REST adapter)
- **Target Tables**: Existing customer/account and Decision Tables (instance-specific; to be discovered)

## Next Phase

Requirements analysis complete. Ready for refinement phase:
1. Review `memory/initial-1/requirements-QnA.md`
2. Answer all 20 clarifying questions
3. Populate `requirements-QnA.md` User's Answer fields
4. Proceed to analysis phase for implementation blueprint
