# <module>

<!-- Per-module audit report: one file per audited module, written as
     `odoo-audit/<Group>/<module>.md` right after the module audit
     completes. Keep it short — a synthesis, not a full report; the
     global report links it instead of duplicating it. Write "None"
     explicitly in an empty section, never leave it blank. -->

- Origin / upstream:
- Project Odoo version:
- Availability: <!-- 1/0 values from module-inventory.csv for 18.0/19.0/20.0, plus the comment when it adds context -->
- Port starting point: <!-- <version>: <url> and whether it applies, or the last stable branch version if no PR -->
- LOC: <!-- python / xml / js / css from module-inventory.csv -->
- Migration effort: <!-- semantic days to the confirmed target version, matches the CSV; the mechanical sweep is excluded -->
- Path: <!-- where the module was found on disk -->

## Description

<!-- 2-3 lines: what the module does (manifest `summary`/`description`),
     main models, views and dependencies. No judgement here. -->

## Good points

<!-- What is clean, solid or well-designed: patterns worth keeping, test
     coverage, correct security setup, clean layering. -->

## Bad points

<!-- Quality findings that are NOT migration blockers: should-fix and
     nit findings, maintainability issues, convention violations. Start
     each finding bullet with exactly `**Should-fix**` or `**Nit**` (no
     High/Medium/Low labels). One bullet per finding: the rule violated
     and `file:line` evidence. -->

## Blocking points

<!-- Findings that block or weigh on the semantic migration to the
     target Odoo version: removed/renamed models, fields or methods used
     by the local code (source → target model/module), changed
     workflows/state machines, ORM/search/`read_group` semantics,
     serial/lot/quant behaviour, JS/OWL rewrites, REST/API contract
     changes, security issues to fix before porting, data migrations.
     Start each bullet with exactly `**Blocker**` (no High/Medium/Low
     labels). If the target version adds a non-core dependency absent
     from the inventory, list it here; the orchestrator adds the
     `New - required by ...` row. Mechanical view/ORM patterns (`attrs=`,
     `<tree>`, `t-esc`, `groups_id`, `ir.access.csv`, `self._cr`, UoM
     helpers, …) go to the next section, not here. One bullet per
     finding: severity, `file:line` evidence, the version delta
     responsible (odoo-knowledge `versions/<X>.md`,
     `migrations/common-patterns.md`) and the recommended fix. Close
     with one line on the semantic effort and the deltas that drove it,
     consistent with `migration_effort_days` in the inventory CSV. -->

## Mechanical migration notes

<!-- Toolable changes only: attrs=, <tree>, t-esc, groups_id,
     ir.access.csv, self._cr/_uid/_context, UoM/float helpers,
     _sql_constraints, name_get, user_has_groups, hook signatures,
     res.config getters. Give counts and file references, no effort.
     Write "None" explicitly. -->

## Stub variant

For a module skipped because it already tracks upstream (`1` in the
target version column, no exception comment), write only the header
block and replace the Description/Good/Bad/Blocking/Mechanical sections
with:

> Not audited: already available upstream on `<target>` with no local
> modification — tracks upstream, no migration work.

