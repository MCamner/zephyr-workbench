---
name: terminal-ui-polisher
description: Use when improving Zephyr Workbench CLI help, command output, validation messages, prompts, interactive add/init flows, or terminal UX.
---

# Terminal UI Polisher

Improve Zephyr Workbench's command-line experience while keeping it quiet, readable, and script-friendly.

## CLI Surfaces

- `zephyr/cli.py` for command routing, help, and output shape
- `zephyr/_prompts.py` for interactive prompting helpers
- `zephyr/add.py` for interactive model editing
- `zephyr/init_wizard.py` for model creation flows
- `zephyr/validation.py` for error and warning messages
- `zephyr/analyzer.py` for summary output
- `tests/test_cli.py`, `tests/test_add.py`, and `tests/test_init_wizard.py`

## Principles

- Keep output scannable in plain terminals.
- Preserve predictable exit codes, especially `validate` and `diff`.
- Make errors actionable: include field names, object names, and likely fix.
- Keep machine-readable modes such as `summary --json` stable.
- Avoid noisy decoration that makes copied output harder to use.
- Interactive prompts should offer clear defaults and safe cancellation.

## Review Checklist

- Command names and flags are discoverable from help.
- Validation output separates errors from warnings.
- Generated file paths are printed when output is written.
- Empty states explain what to do next.
- Long YAML field names do not create awkward wrapping.
- Scripts and CI can still parse or tolerate output changes.

## Verification

```bash
python -m zephyr.cli help
python -m zephyr.cli validate examples/secure-workplace.yaml
python -m zephyr.cli summary examples/secure-workplace.yaml
python -m zephyr.cli summary examples/secure-workplace.yaml --json
python -m zephyr.cli diff examples/secure-workplace.yaml examples/identity-flow.yaml
pytest -q tests/test_cli.py tests/test_add.py tests/test_init_wizard.py
```

## Output

When reviewing CLI UX, lead with the highest-impact problems, then give exact copy or code-level changes. When editing, keep tests close to the changed command.
