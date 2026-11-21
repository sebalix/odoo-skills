# Odoo Project Audit Report

<!-- Fill every section; write "No findings" explicitly when an area is clean. -->

## 1. Executive summary

- Project / scope audited:
- Odoo version(s):
- Audit date:
- Overall assessment: <!-- one paragraph: health, main risks, top priorities -->
- Headline numbers: X blockers, Y should-fix, Z nits; N modules
  (M custom), E person-days for the semantic migration to the latest
  stable, plus G person-days for the global mechanical sweep.

## 2. Scope & inventory

- Modules audited (custom vs. OCA/standard):
- Out of scope:
- Not audited, tracking upstream: <!-- count of modules with a `1` in
  the target version column and no exception comment; see their stub
  reports -->
- Detailed inventory: `odoo-audit/module-inventory.csv` — one compact
  row per module (origin, upstream, LOC, 1/0 availability, last open
  (or closed-unmerged) migration PR for a version not yet available,
  exception-only comment, migration effort).
- Module reports: one file per module under `odoo-audit/`
  (`OCA/`, `Others/`, `Specific/`, by origin) — full report for audited
  modules, stub for modules tracking upstream. Link them here and in
  the findings summary instead of duplicating their content.
- External / new dependencies: `odoo-audit/dependencies.md` when the
  project is split across repositories; installed external modules and
  new target-version dependencies, with PRs and the port gate.

### Inventory summary

<!-- One row per origin, totals from module-inventory.csv. -->

| Origin | Modules | Python LOC | Total LOC | Est. semantic days |
|--------|---------|-----------|-----------|---------------------|
| odoo-core | | | | |
| odoo-enterprise | | | | |
| oca | | | | |
| third-party | | | | |
| custom | | | | |
| **Total** | | | | |

## 3. Findings summary

<!-- One row per module, linking its report; per-finding detail lives in
     the module reports. Rows linking a stub (module tracking upstream)
     carry — in the severity columns. -->

| Module | Report | Blockers | Should-fix | Nits | Migration effort |
|--------|--------|----------|------------|------|------------------|

## 4. Cross-cutting findings per area

<!-- Findings that affect several modules, grouped by area — per-module
     detail lives in the module reports. Write "No findings" explicitly
     when an area is clean. -->

### 4.1 Module structure & dependencies
### 4.2 Models & ORM
### 4.3 Security
### 4.4 Views
### 4.5 Data files
### 4.6 Performance
### 4.7 Tests
### 4.8 Tooling coverage

<!-- For each finding: description, evidence (file:line), impacted
     modules, impact, recommended fix. -->

## 5. Upgrade readiness

- Target version assessed:
- Version deltas affecting this codebase:
- Estimated semantic migration effort: per-module days in
  `odoo-audit/module-inventory.csv`; summarize the main cost drivers
  (modules, deltas) and the total here.
- Mechanical migration workstream: <!-- G days, separate from the
  per-module semantic days; list the main patterns and counts -->
- Port starting points: the `pr` column in the inventory contains the
  last open (or closed-unmerged) migration PR for a version not yet
  available, formatted `<target version>: <url>` (e.g.
  `19.0: https://...`); empty when the target version is already
  available. Start from the PR when present, otherwise from the last
  stable branch version available.
- Dependency gate: installed external readiness (18/19/20) plus new
  target-version dependencies; list the blockers and link
  `dependencies.md`. New dependencies are rows with
  `New - required by ...`.
- Staged path: <!-- if the latest stable is blocked, target -> ... ->
  latest, with the dependency gate at each step -->

## 6. Prioritized action plan

1. <!-- blockers first, with suggested owner and effort -->
