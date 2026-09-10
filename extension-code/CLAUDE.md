## Project
For project environment, registry, and UAC configuration, see memory/environment.md.

## Artefact Rules
- memory/{work_item_id}/requirements.md — captured during the requirements phase; do not modify after committing
- memory/events.jsonl — append-only; never edit existing entries

## Phases
- /ue:requirements — capture requirements and open the work item
- /ue:analysis — refine requirements and produce implementation-blueprint.md
- /ue:implementation — generate extension source files
- /ue:testing — validate against UAC

## Output Style Override for Interactive Q&A Steps

When a command explicitly instructs you to present rich context before asking
a question (e.g., Question Type, Context, Rationale, Trade-offs, Resources),
the general brevity guidelines are suspended for that step.
Full context MUST be written as text output to the user before any
AskUserQuestion tool call is made.

## External References
