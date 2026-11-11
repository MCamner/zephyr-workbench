# Architecture reliability implementation plan

## Goal
Close the verified review gaps while preserving existing YAML and CLI workflows.

## Owner repo
zephyr-workbench

## Secondary repos
None. Record verified lessons through mq-mcp after validation.

## Architecture boundary
Zephyr owns models, analysis, rendering, runtime contracts and browser drafts.
External OCR is optional; no remote model service is introduced.

## Non-goals
Deployment, publishing, repository settings and an unrestricted vision engine.

## Approval gates
- File writes: authorized by the user.
- Commit/push/merge: not part of this implementation request.
- Deletions or production changes: excluded.

## Tasks
1. Complete Python/browser diffs, serialization and history counts.
2. Add explicit risk references with validation, loading, search and explanations.
3. Fix image runtime import and add bounded local box/connector recognition.
4. Detect stale/missing memory sources and compare typed graph topology.
5. Complete tool safety contracts and document errors and write effects.
6. Persist browser drafts, show storage errors and verify reload recovery.
7. Update README, roadmap, schema, changelog, repository skills and lessons.

## Test gates
`python3 -m pytest -q`, focused regression tests, generated JS idempotence,
Node browser-core tests, browser reload smoke check, model validation, skill validation.
Each bug gets a failing regression before implementation.

## Rollback
Review `git diff`; revert only the individual implementation hunks if required.
No migration rewrites existing model files or memory indexes automatically.

## Completion evidence
All seven tasks are implemented and verified. See
`docs/reviews/2026-11-11-reliability.md` for the final test results, smoke checks,
updated skills, and explicit product limits. No release or remote Git mutation was performed.
