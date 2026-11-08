---
name: odoo-audit
description: Perform a systematic audit of an Odoo project or module set — architecture, security, data model, performance, and upgrade readiness. Use when asked to audit, assess, or run a health check on an Odoo codebase. For reviewing a single change or PR, use the odoo-review skill instead.
---

## Workflow

1. **Inventory**: ask the user for an existing module list (CSV or any
   tabular export) with availability and LOC stats if they have one, then
   complete it following `references/module-inventory.md` (origin and
   upstream detection, LOC counting, availability resolution, migration
   effort). Produce `module-inventory.csv`, formatted like
   `references/inventory-template.csv`. Record what is
   custom vs. OCA/standard.
2. Load the `odoo-knowledge` skill — its routing table maps each area below
   to its reference file.
3. **Per-area assessment**: for each area below, read the matching
   odoo-knowledge reference *before* assessing, then sweep the codebase for
   the patterns the file flags and judge every hit against its rules — a hit
   is not a finding by itself; the rules say what makes it one. The
   assessment of an area is complete when every pattern has been swept and
   every hit judged. Record findings with severity (blocker / should-fix /
   nit) and `file:line` evidence:

   - Module structure & dependencies
   - Models & ORM
   - Views (xml, qweb)
   - Security
   - Data files
   - Tests

4. **Upgrade readiness**: assess against the odoo-knowledge version
   reference for the next Odoo version, its module checks
   (`migrations/common-patterns.md`) and `migration-scripts.md`.
5. **Report**: produce the markdown audit report following
   `references/report-template.md` and deliver it together with
   `module-inventory.csv` (see Deliverables).

## Deliverables

- `module-inventory.csv` — one row per module, sorted by origin then
  upstream, with LOC stats, availability and migration effort. Flat CSV,
  imports directly into Google Sheets; built at step 1.
- The audit report — markdown following `references/report-template.md`,
  imports into Google Docs; summarizes the inventory instead of
  duplicating it.

## Coverage rules

- Do not skip an area because it "looks fine" — assess each one explicitly,
  even if only to record "no findings".
- Prefer evidence (file paths, line numbers) over generalities.
- Distinguish findings in custom code from findings in unmodified
  OCA/standard modules; the latter usually call for an upstream fix or an
  override, not a local patch.
