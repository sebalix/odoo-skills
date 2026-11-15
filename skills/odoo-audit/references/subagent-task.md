# Per-Module Audit Task

Self-contained task handed to one subagent per module: the subagent runs
in its own context, so this template must be enough for it to work. The
orchestrator fills the Context block, spawns the subagent, and collects
only the Result — orchestration rules (order, at most 4 subagents in
parallel, who writes what) live in the skill workflow.

## Context (filled by the orchestrator)

- Module: `<name>`
- Path: `<module directory found by the inventory>`
- Report to write: `odoo-audit/<Group>/<module>.md`
- Origin / upstream:
- Project Odoo version:
- Target Odoo version: <next version to assess the migration against>
- Availability: <statuses from the inventory CSV>
- LOC: <python / xml / js / css from the inventory CSV>
- Skill locations: odoo-audit `<path>`, odoo-knowledge `<path>`

## Task

1. Read the module report template
   `<odoo-audit>/references/module-report-template.md` — the report
   follows it; the `<Group>` folder is given in the Context.
2. Read the odoo-knowledge references for every area below, plus the
   target version file (`versions/<target>.md`),
   `migrations/common-patterns.md` and `migration-scripts.md`:

   - Module structure & dependencies — `module-structure.md`
   - Models & ORM — `orm.md`
   - Views (xml, qweb) — `views.md`
   - Security — `security.md`
   - Data files — `data.md`
   - Tests — `testing.md`

3. Audit the module area by area: sweep its code for the patterns each
   reference flags and judge every hit against its rules — a hit is not
   a finding by itself; the rules say what makes it one. The audit is
   complete when every area has been swept and every hit judged. Skip
   style issues a linter would catch.
4. Assess the upgrade readiness: check the module against the target
   version's breaks, and confirm or correct the effort from the Context
   following the migration effort rubric in
   `<odoo-audit>/references/module-inventory.md`.
5. Write the report to the path given in the Context: findings with
   severity (blocker / should-fix / nit) and `file:line` evidence; the
   effort estimate and its drivers close the Blocking points, consistent
   with the CSV values above.

## Result (return this, and only this)

- Counts: X blockers, Y should-fix, Z nits.
- Effort: N d to the target version — drivers in one line.
- Top blockers: up to 3, one line each (`file:line` + issue).
- Notable patterns: findings likely shared with other modules (e.g.
  `attrs=` in views, a `read_group` override), one line each.
- CSV corrections: any Context value the audit contradicts (effort,
  availability, LOC) with the corrected value.

## Constraints

- Write only the report file named in the Context — never the CSV, the
  global report, another module's file, or the audited code itself.
- Keep the final answer to the Result section: the orchestrator merges
  one per module into the CSV and the global report.
