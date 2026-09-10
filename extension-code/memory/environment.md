# Extension Development Environment

**Generated:** 2026-09-10 08:51:27

## Project Registry
extension_name: extension-code
uses_ticketing_system: no

## UAC Configuration
See .env for connection parameters. (.env is git-ignored — never committed.)

## Workspace Structure

```
extension-code/
├── .claude/                      # Claude Code settings
├── CLAUDE.md                     # Session-loaded project context
├── src/                          # Extension source code
├── atest/                        # Acceptance test definitions
├── memory/                       # Permanent work item artifacts
│   ├── {work_item_id}/          # Scoped per work item
│   ├── events.jsonl              # Append-only event log
│   └── environment.md            # This file
├── memory-ephemeral/             # Ephemeral working files (not committed)
├── ue-dev-env/                   # Python virtual environment (not committed)
└── .env                          # UAC credentials (not committed)
```

## Virtual Environment
ue-dev-env/ — Python venv; git-ignored; install dependencies before running tests.

```bash
source ue-dev-env/bin/activate
```
