# <module>

<!-- Per-module audit report: one file per audited module, written as
     `odoo-audit/<Group>/<module>.md` right after the module audit
     completes. Keep it short — a synthesis, not a full report; the
     global report links it instead of duplicating it. Write "None"
     explicitly in an empty section, never leave it blank. -->

- Origin / upstream:
- Project Odoo version:
- Availability: <!-- statuses from module-inventory.csv, last 3 versions -->
- LOC: <!-- python / xml / js / css from module-inventory.csv -->
- Migration effort: <!-- days to the latest stable, matches the CSV -->
- Path: <!-- where the module was found on disk -->

## Description

<!-- 2-3 lines: what the module does (manifest `summary`/`description`),
     main models, views and dependencies. No judgement here. -->

## Good points

<!-- What is clean, solid or well-designed: patterns worth keeping, test
     coverage, correct security setup, clean layering. -->

## Bad points

<!-- Quality findings that are NOT migration blockers: should-fix and
     nit findings, maintainability issues, convention violations. One
     bullet per finding: the rule violated and `file:line` evidence. -->

## Blocking points

<!-- Findings that block or weigh on the migration to the latest stable
     Odoo version: blockers, breaking-pattern hits (e.g. `attrs=`,
     `<tree>` tags, `read_group` overrides, removed APIs), upstream
     model renames/moves/removals used by the local code (source →
     target model/module), security issues to fix before porting. One
     bullet per finding: severity, `file:line` evidence, the version
     delta responsible (odoo-knowledge `versions/<X>.md`,
     `migrations/common-patterns.md`) and the recommended fix. Close
     with one line on the effort and the deltas that drove it,
     consistent with `migration_effort_days` in the inventory CSV. -->

## Stub variant

For a module skipped because it already tracks upstream (`Available` on
the target version, no local modification), write only the header block
and replace the four sections with:

> Not audited: already available upstream on `<target>` with no local
> modification — tracks upstream, no migration work.

