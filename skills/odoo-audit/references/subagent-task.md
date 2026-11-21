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
- Availability: <`1`/`0` values for 18.0/19.0/20.0 from the inventory
  CSV, plus the comment if it adds context>
- PR: <last open (or closed-unmerged) migration PR for a version not
  yet available, formatted `<version>: <url>`, or empty>
- LOC: <python / xml / js / css from the inventory CSV>
- MCA coverage: <"check at runtime", or the upstream URL and scanned
  source/target versions>
- Skill locations: odoo-audit `<path>`, odoo-knowledge `<path>`

## Task

1. Read the module report template
   `<odoo-audit>/references/module-report-template.md` — the report
   follows it; the `<Group>` folder is given in the Context.
2. Read the odoo-knowledge references for every area below — all
   under `<odoo-knowledge>/references/` — plus the target version
   file (`versions/<target>.md`) and every intermediate
   `versions/*.md` between the project and target versions, then
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
   style issues a linter would catch. Separate **mechanical/toolable**
   changes (`attrs=`, `<tree>`, `t-esc`, `groups_id`, `ir.access.csv`,
   `self._cr`/`_uid`/`_context`, UoM/float helpers, `_sql_constraints`,
   `name_get`, `user_has_groups`, hook signatures, `res.config` getters)
   from **semantic** breaks: record the former with counts in the
   report's Mechanical migration notes, and do not count them in the
   effort.
4. Assess the upgrade readiness: check the module against the target
   version's breaks, and confirm or correct the semantic effort from the
   Context following the migration effort rubric in
   `<odoo-audit>/references/module-inventory.md`. If a PR is provided,
   fetch/read it and use it as the starting point: check whether it
   applies cleanly to the target, note review comments/CI, and state
   whether the audit recommends starting from it or from the last stable
   branch version. Compare the target-version `depends` with the
   inventory and report any new non-core dependency; the orchestrator
   adds the `New - required by ...` row. The mechanical sweep is global
   and already excluded from the per-module effort. When the `odoo-mca`
   tools are available and cover the module, follow
   `<odoo-audit>/references/mca.md` for model-level evidence only:
   confirmed model renames/moves and model removals for each crossed
   version, reported only where the local code references or extends the
   model. Do not query fields, methods or data records. If the module is
   not covered, keep the local assessment and skip only the MCA evidence.
5. Create the report's parent directory if it does not exist, then
   write the report to the path given in the Context: findings with
   `file:line` evidence and exact labels — `**Blocker**`,
   `**Should-fix**`, `**Nit**` (no High/Medium/Low); the semantic effort
   estimate and its drivers close the Blocking points, consistent with
   the CSV values above, and the Mechanical migration notes section
   lists the toolable patterns without effort.

## Result (return this, and only this)

- Counts: X blockers, Y should-fix, Z nits.
- Effort: N d semantic to the target version — drivers in one line;
  mechanical sweep excluded.
- Port starting point: PR `<version>: <url>` and whether it applies
  cleanly, or the last stable branch version if no PR.
- New dependencies: non-core target-version dependencies absent from the
  inventory, with their requirer; or None.
- Top blockers: up to 3, one line each (`file:line` + issue).
- Notable patterns: findings likely shared with other modules (e.g.
  a `read_group` override, a legacy JS patch, the same ACL pattern), one
  line each.
- CSV corrections: any Context value the audit contradicts (effort,
  availability, PR, LOC) with the corrected value.

## Constraints

- Write only the report file named in the Context — never the CSV, the
  global report, another module's file, or the audited code itself.
- Use the MCA read-only: never create, update or delete timelines.
- Keep the report tool-agnostic: never name the MCA, its tools or the
  audit skill's MCA reference; cite the upstream module, model, version
  and source URL instead.
- Keep the final answer to the Result section: the orchestrator merges
  one per module into the CSV and the global report.
