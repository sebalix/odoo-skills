# Module Inventory Report

Build the module inventory CSV — one row per module in the audited project,
grouped by origin and upstream repository. The file is a flat CSV that
imports directly into Google Sheets; grouping is expressed by the sort
order and the `origin` / `upstream` columns (pivotable in the spreadsheet).

## Input: ask the user first

Before computing anything, ask the user for an existing module list (CSV or
any tabular export: previous audit, Odoo instance export, asset register)
containing any of: module list, availability per version, LOC stats.

- Provided → digest it: keep its availability and LOC numbers as-is and only
  fill in the missing columns.
- Missing or partial → compute the missing values following the rules below.

Whatever the source, the output CSV doubles as the input file for the next
audit: when availability had to be resolved online, the result is in the
file, and the next audit digests it instead of re-querying.

## Module discovery

Locate the modules in the current directory tree — the audit audits the
code found on disk:

```bash
find . -name '__manifest__.py' \
  -not -path '*/.git/*' -not -path '*/node_modules/*'
```

Each hit's parent directory is a module. Reconcile the hits with the
user's list before computing anything:

- Found on disk but not in the list → add a row and determine its origin
  like any other module.
- In the list but not found on disk (typically a dependency) → keep the
  row, note `not found on disk` in `comment`; it gets no module report.
  Its LOC comes from the upstream scan when the `odoo-mca` MCP server
  is available (see `mca.md`).
- Several copies of the same technical name → ask the user which copy is
  authoritative before auditing.

## Output format

One file, `odoo-audit/module-inventory.csv`, rows sorted by origin (in
the order `odoo-core`, `odoo-enterprise`, `oca`, `third-party`,
`custom`), then upstream, then technical name. See
`inventory-template.csv` for the exact header and example rows.

| Column | Content |
|--------|---------|
| `origin` | `odoo-core`, `odoo-enterprise`, `oca`, `third-party`, `custom` |
| `upstream` | normalized git remote: `odoo/odoo`, `odoo/enterprise`, `OCA/server-tools`, `vendor/foo`; `-` for custom modules |
| `technical_name` | manifest directory name |
| `summary` | one line: manifest `summary` attribute, or generated from the main models/views when missing |
| `loc_python`, `loc_xml`, `loc_js`, `loc_css` | lines of code per language (counting rules below) |
| `<X.0>` ×3 | one column per version for the last 3 stable Odoo versions at audit time (e.g. `18.0`, `19.0`, `20.0`): status of the module in that version (vocabulary in Availability resolution) |
| `comment` | free text: local modifications, replacement plans, evidence for the effort estimate, successor/new technical name for `Replaced` / `Renamed` statuses, PR URL for `To review` |
| `migration_effort_days` | estimated days to migrate to the latest stable Odoo (rubric below) |

Keep `comment` tool-agnostic: do not name the MCA or its tools; cite
the upstream module, version and URL instead.

## Origin & upstream detection

Determine `origin` and `upstream` in this order:

1. Git remote of the repository containing the module: `odoo/odoo` →
   `odoo-core`, `odoo/enterprise` → `odoo-enterprise`, `OCA/<repo>` → `oca`,
   any other remote → `third-party`. Modules in a repo without a remote, or
   in the project's own repo → `custom`.
2. Manifest metadata fallback: `Odoo Community Association (OCA)` in
   authors → `oca`; OPL license → `odoo-enterprise`; Odoo S.A. + LGPL →
   `odoo-core`.
3. Project conventions: ask the user which directories/repositories hold
   the custom modules.

When the origin is ambiguous, ask the user instead of guessing. A forked or
locally modified OCA/standard module keeps its origin; record the
modification in `comment` — it usually blocks upstream tracking and raises
migration effort.

When the `odoo-mca` MCP server is available, corroborate the remote
with `module_get_details` (`repository`, `is_standard`,
`is_enterprise`, `is_community`, `url`). Do not override an explicit
local remote: a fork stays `third-party`; record the canonical upstream
in `comment`.

## LOC counting

- Count LOC from the module directory on disk, always.
- When a row has no module directory on disk (typically a dependency),
  take the LOC from the upstream scan through the `odoo-mca` MCP server
  when available: `module_get_details` returns `sloc_python`,
  `sloc_xml`, `sloc_js` and `sloc_css` for the scanned version (see
  `mca.md`). Do not expand the inventory with transitive dependencies.
  When the module is not in the MCA either, leave LOC empty and note it
  in `comment`.
- For a module on disk, use the `odoo-addons-parser` package (PyPI) —
  it analyzes module folders statically, without an Odoo runtime, and
  counts **code** lines per language (pygount-based: comments and blank
  lines are excluded):

```python
from odoo_addons_parser import ModuleParser

code = ModuleParser("/path/to/module", scan_models=False, scan_data=False).code
# {'Python': 541, 'XML': 21, 'JavaScript': 0, 'CSS': 0}
```

  Map `Python` → `loc_python`, `XML` → `loc_xml`, `JavaScript` →
  `loc_js`, `CSS` → `loc_css`. `RepositoryParser` scans a whole addons
  repository in one pass.
- Caveat: the parser walks the whole module folder, so vendored code
  (`static/lib/`, ...) is included in the counts. When a module vendors
  large libraries, note it in `comment` and do not treat the inflated LOC
  as maintained code in the effort rubric.
- Fallback when the package cannot be installed: count per extension
  (`.py`, `.xml`, `.js`, `.css`/`.scss` → css), excluding `static/lib/`
  and `node_modules/`, per module:

```bash
find <module> -name '*.py' -not -path '*/static/lib/*' -not -path '*/node_modules/*' -print0 | xargs -0 cat | wc -l
```

(repeat per extension). If the user-provided input already contains LOC,
keep those numbers.

## Availability resolution

Priority:

1. User-provided input file (see above).
2. The `odoo-mca` MCP server when available (see `mca.md`): scanned
   repositories and branches, module existence per version, migration
   statuses, renames/replacements and PR URLs.
3. Any other API or MCP resource available in the audit environment.
4. GitHub API, last resort: core/enterprise — check `addons/<name>` in
   odoo/odoo and odoo/enterprise for the recent stable branches; OCA —
   check the relevant `OCA/<repo>` repositories; third-party — check the
   upstream remote's branches.

An MCA absence is meaningful only for a repository and branch listed by
`repo_list_repositories`; for an unscanned one, fall back to the next
source. Never infer availability from a same-named module in another
repository (e.g. an OCA backport of a removed core module): the status
is `Removed` for the core module, with the backport as an alternative in
`comment`.

The version columns (`18.0`, `19.0`, `20.0`, ...) cover the last 3 stable
Odoo versions at audit time and record the status of the module in each —
not necessarily the version the project uses.

### Status vocabulary

| Status | Meaning |
|--------|---------|
| `Available` | the module exists upstream in that version |
| `To migrate` | no upstream version exists in that version — the module must be ported (always the case for `custom` modules) |
| `To review` | an upstream version exists but cannot be tracked as-is (local modifications to merge, breaking changes to review) — set the upstream PR URL in `comment` |
| `Removed` | Odoo standard module removed from the distribution in that version |
| `Replaced` | replaced by another module — successor technical name in `comment` |
| `Renamed` | renamed upstream — new technical name in `comment` |
| `Unknown` | could not be determined from any source |

## Migration effort rubric (to latest stable)

Estimate in days, rounded to the closest 0.5:

1. Base by LOC (python + xml + js + css): under 500 → 0.5d; 500–2 000 → 1d;
   2 000–5 000 → 2.5d; above 5 000 → 5d.
2. Version distance: multiply the base by `1 + 0.3 × jumps`, one jump per
   version between the project's version and the latest stable (e.g. 17.0 →
   20.0: base × 1.9).
3. Breaking deltas: scan the module against the odoo-knowledge
   `versions/<X>.md` files for every crossed version; add 0.5–1d per major
   break found (e.g. a `read_group` override, `attrs=` views, `<tree>` tags,
   `odoo.osv.expression` usage). An upstream model rename, move or removal
   that the local code uses is such a break (see `mca.md`). Cap the
   penalty at +5d.
4. Upstream discount: when the target-version status is `Available` and
   the module has no local modification, the effort is "track upstream":
   0.5d. `To review` → estimate the merge/review against the upstream PR
   (URL in `comment`). `Removed` or `Replaced` → estimate the migration toward the
   successor named in `comment` (or its removal). `Renamed` → a light
   dependency switch. Modules with local modifications and `custom`
   modules get the full estimate.
5. Record the rationale in `comment` (which deltas drove the number).

## Feeding the markdown reports

Per-origin totals for the global report (module counts, LOC, days) come
from this CSV; the global report references it instead of duplicating
per-module rows. Each module report header (availability, LOC, effort,
path) is written from its CSV row — when the module audit revises a
value, update the CSV row too so the two stay in sync. Modules
`Available` on the target version without local modification get a stub
report only — no migration work, they track upstream (the rubric's
upstream discount).
