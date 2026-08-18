# directives/

This folder contains **SOP-style Markdown directives** — the instructions layer of the DOE system.

## What goes here

Each `.md` file describes **one task or workflow**:
- **Goal** — what needs to happen
- **Inputs** — what data / parameters are required
- **Execution** — which script(s) in `execution/` to run, in what order
- **Outputs** — what the script produces and where it goes
- **Edge cases & learnings** — constraints discovered over time

## Rules

1. Write directives in **plain language**, as if briefing a competent teammate.
2. Directives are **living documents** — update them when you discover new constraints.
3. Do **not** create, overwrite, or delete directives unless explicitly instructed by the user.
4. Use the template in `_template.md` as a starting point for new directives.
