---
name: odoo-audit
description: Perform a systematic audit of an Odoo project or module set — architecture, security, data model, performance, and upgrade readiness. Use when asked to audit, assess, or run a health check on an Odoo codebase. For reviewing a single change or PR, use the odoo-review skill instead.
---

## Workflow

1. **Inventory**: ask the user for an existing module list (CSV or any
   tabular export) with availability and LOC stats if they have one, then
   complete it following `references/module-inventory.md` (origin and
   upstream detection, module discovery in the directory tree, LOC
   counting, availability resolution, migration effort). Produce
   `odoo-audit/module-inventory.csv`, formatted like
   `references/inventory-template.csv`. Record what is custom vs.
   OCA/standard.
2. Load the `odoo-knowledge` skill — its routing table maps audit areas
   to reference files; the per-module task points each subagent at them
   (see `references/subagent-task.md`). Fallback only (no subagent
   capability, see step 3): read each area reference once before the
   loop.
3. **Per-module audits through subagents**: prepare the work list from
   the CSV, in CSV order:

   - `odoo-core` and `odoo-enterprise` modules are skipped — standard
     code, local modifications are flagged in the CSV `comment`
     instead; no file is written for them.
   - Modules already `Available` on the target version without local
     modification are not audited — no migration work, they track
     upstream (especially most OCA modules, usually already ported);
     write their stub report yourself following
     `references/module-report-template.md` and move on.
   - Modules `To review` (available upstream but locally modified) are
     audited — they have merge work.

   Then spawn one subagent per audited module, each running the task
   template `references/subagent-task.md` filled with the module's
   Context — at most **4 running concurrently**: launch a new one as
   each finishes, never two on the same module. Each subagent writes
   its own module report `odoo-audit/<Group>/<module>.md` (`OCA` for
   origin `oca`, `Others` for `third-party`, `Specific` for `custom`)
   and returns a short summary. Fallback without subagent capability:
   audit the modules inline, one at a time, following the same task
   template.
4. **Consolidation**: apply each returned summary yourself — update the
   CSV rows (effort, corrections); subagents never touch the CSV.
   Compare the returned notable patterns to spot cross-cutting findings
   (the same pattern in several modules) for the global report.
5. **Report**: produce the global report `odoo-audit/README.md` following
   `references/report-template.md` — it aggregates the module reports
   instead of duplicating them.

## Deliverables

All deliverables live under `odoo-audit/` in the audited project:

```text
odoo-audit/
├── README.md              global report + index of the module reports
├── module-inventory.csv   one row per module, built at step 1
├── OCA/                   one <module>.md per `oca` module
├── Others/                one <module>.md per `third-party` module
└── Specific/              one <module>.md per `custom` module
```

- `module-inventory.csv` — one row per module, sorted by origin then
  upstream, with LOC stats, availability and migration effort. Flat CSV,
  imports directly into Google Sheets; built at step 1.
- Module reports — one short markdown file per module (step 3): written
  by the module's subagent, or a stub by the orchestrator for modules
  tracking upstream.
- The global report — markdown following `references/report-template.md`,
  imports into Google Docs; summarizes the inventory and the module
  reports instead of duplicating them.

## Coverage rules

- Do not skip an area or a module because it "looks fine" — assess each
  one explicitly, even if only to record "no findings".
- Prefer evidence (file paths, line numbers) over generalities.
- Distinguish findings in custom code from findings in unmodified
  OCA/standard modules; the latter usually call for an upstream fix or an
  override, not a local patch.
