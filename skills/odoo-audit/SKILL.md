---
name: odoo-audit
description: Perform a systematic audit of an Odoo project or module set — architecture, security, data model, performance, and upgrade readiness. Use when asked to audit, assess, or run a health check on an Odoo codebase. For reviewing a single change or PR, use the odoo-review skill instead.
compatibility: Requires the odoo-knowledge skill. Uses subagents when available (up to 4 in parallel); falls back to sequential inline audits otherwise. Uses the odoo-mca MCP server read-only when available.
metadata:
  requires-skills: odoo-knowledge
  optional-mcp: odoo-mca
  max-concurrency: "4"
  recommended-subagent: odoo-auditor
---

## Workflow

1. **Inventory**: ask the user for an existing module list (CSV or any
   tabular export) with availability and LOC stats if they have one, then
   complete it following `references/module-inventory.md` (origin and
   upstream detection, module discovery in the directory tree, LOC
   counting, availability resolution, migration effort). When the
   `odoo-mca` MCP server is available, use `references/mca.md` for the
   data it covers; keep the local and GitHub fallbacks for the rest.
   Produce `odoo-audit/module-inventory.csv`, formatted like
   `references/inventory-template.csv`: compact one-line rows, `1`/`0`
   availability per version, the last open (or closed-unmerged) migration
   PR for a version not yet available in `pr` (formatted
   `<version>: <url>`), and an exception-only `comment` (no `installed`,
   no availability restatement, no effort rationale). Record what is
   custom vs. OCA/standard. Confirm the target version with the user; if
   the latest stable is blocked by dependencies, assess the highest
   viable version and record the staged path. After the inventory, run
   the new-dependency scan (see `references/module-inventory.md`):
   compare each target-version manifest with the installed set and add
   new non-core dependencies with `New - required by module X`.
2. Load the `odoo-knowledge` skill — its routing table maps audit areas
   to reference files; the per-module task points each subagent at them
   (see `references/subagent-task.md`). Fallback only (no subagent
   capability, see step 3): read each area reference once before the
   loop.
3. **Per-module audits through subagents**: create the deliverable tree
   (`odoo-audit/` with the `OCA/`, `Others/`, `Specific/` folders) and
   prepare the work list from the CSV, in CSV order:

   - `odoo-core` and `odoo-enterprise` modules are skipped — standard
     code, local modifications are flagged in the CSV `comment`
     instead; no file is written for them.
   - Modules with a `1` in the target-version column and no exception
     comment are not audited — no migration work, they track upstream
     (especially most OCA modules, usually already ported); write their
     stub report yourself following
     `references/module-report-template.md` and move on.
   - Installed modules on disk with a `0` (custom, to migrate, or
     removed/replaced with a successor) are audited — they have port,
     removal or replacement work.
   - Modules marked `not installed` in the CSV are inventoried but not
     audited.
   - Rows with `New - required by ...` are dependency rows, not installed
     modules; no report is written unless the dependency is project-owned
     and on disk.
   - Modules with a `1` but an exception comment (local modifications,
     PR, `renamed to` or `replaced by`) are audited — they have merge,
     rename or replacement work.

   Then spawn one subagent per audited module using the **`odoo-auditor`**
   agent profile if configured in the environment (falling back to a default
   general-purpose subagent with a fast/mid-tier model if not defined), each
   running the task template `references/subagent-task.md` filled with the
   module's Context, including its `pr` starting point — at most **4 running
   concurrently**: launch a new one as each finishes, never two on the same
   module. Each subagent writes
   its own module report `odoo-audit/<Group>/<module>.md` (`OCA` for
   origin `oca`, `Others` for `third-party`, `Specific` for `custom`)
   and returns a short summary. Fallback without subagent capability:
   audit the modules inline, one at a time, following the same task
   template.
4. **Consolidation**: apply each returned summary yourself — update the
   CSV rows (semantic effort, PR, corrections); subagents never touch
   the CSV. Keep the effort rationale in the module report; do not copy it
   into the CSV `comment`. Compare the returned notable patterns to spot
   cross-cutting findings (the same pattern in several modules) for the
   global report; keep the mechanical sweep as a global total, separate
   from the per-module semantic days.
5. **Report**: produce the global report `odoo-audit/README.md` following
   `references/report-template.md` — it aggregates the module reports
   instead of duplicating them. Produce the optional `dependencies.md`
   following `references/dependencies.md` when the project has installed
   external modules or new target-version dependencies.

## Optional MCA

When the `odoo-mca` MCP server is available, read `references/mca.md`
and use it read-only. It speeds up the inventory (availability,
dependency LOC, upstream details) and grounds the model-level upgrade
analysis. It is optional: every step keeps a fallback, and the audit
never creates or updates MCA timelines. Keep the deliverables
tool-agnostic — do not mention the MCA in the reports.

## Deliverables

All deliverables live under `odoo-audit/` in the audited project:

```text
odoo-audit/
├── README.md              global report + index of the module reports
├── module-inventory.csv   one row per module, built at step 1
├── dependencies.md        optional external/new dependency readiness
├── OCA/                   one <module>.md per `oca` module
├── Others/                one <module>.md per `third-party` module
└── Specific/              one <module>.md per `custom` module
```

- `module-inventory.csv` — one row per module, sorted by origin then
  upstream, with LOC stats, `1`/`0` availability, the last open (or
  closed-unmerged) migration PR for a version not yet available,
  exception-only comments and semantic migration effort. Flat CSV,
  imports directly into Google Sheets; built at step 1.
- Module reports — one short markdown file per module (step 3): written
  by the module's subagent, or a stub by the orchestrator for modules
  tracking upstream.
- The global report — markdown following `references/report-template.md`,
  imports into Google Docs; summarizes the inventory and the module
  reports instead of duplicating them.
- `dependencies.md` — optional; installed external modules and new
  target-version dependencies, with availability, PRs and the port gate.
  External/new dependency rows do not get module reports.

## Before delivery

- CSV header exactly matches `references/inventory-template.csv`; no
  `summary` column.
- Version columns contain only `0`/`1`; `pr` cells are
  `<version>: <url>` or empty.
- `comment` is exception-only; new dependencies start with
  `New - required by`.
- Every installed project module has a report; external/new dependency
  rows do not.
- `dependencies.md` availability/PR values match the CSV.
- README counts, findings table and links are valid; no placeholders.
- No merged PR or PR for an already-available version appears in `pr`.

## Coverage rules

- Do not skip an area or a module because it "looks fine" — assess each
  one explicitly, even if only to record "no findings".
- Prefer evidence (file paths, line numbers) over generalities.
- Distinguish findings in custom code from findings in unmodified
  OCA/standard modules; the latter usually call for an upstream fix or an
  override, not a local patch.
- Keep new target-version dependencies in the CSV with the
  `New - required by ...` marker; they are dependency rows, not module
  reports unless project-owned and on disk.
