# Module Inventory Report

Build the module inventory CSV — one row per module in the audited project,
grouped by origin and upstream repository. The file is a flat CSV that
imports directly into Google Sheets; grouping is expressed by the sort
order and the `origin` / `upstream` columns (pivotable in the spreadsheet).

## Input: ask the user first

Before computing anything, ask the user for an existing module list (CSV or
any tabular export: previous audit, Odoo instance export, asset register)
containing any of: module list, availability per version, LOC stats.

- Provided → digest it: keep its LOC numbers as-is and convert its
  availability statuses to `1`/`0` (`1` = available and installable,
  `0` = not); move only the non-obvious details to `comment` (see
  Comment policy).
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

- The inventory covers the installed module set (the user's list or an
  instance export). A module found on disk but not installed is added
  only when it is a candidate for the migration; mark it `not installed`
  in `comment` and do not write a module report for it. Otherwise leave
  it out and mention it in the global report's scope.
- In the list but not found on disk (typically an OCA/third-party
  dependency) → keep the row; it gets no module report. Its LOC comes
  from the upstream scan when the `odoo-mca` MCP server is available
  (see `mca.md`). Do not add `not found on disk` to `comment` for an
  external dependency — the `origin` column already says the module is
  not project code; note it only when a project-owned module is missing.
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
| `loc_python`, `loc_xml`, `loc_js`, `loc_css` | lines of code per language (counting rules below) |
| `<X.0>` ×3 | one column per version for the last 3 stable Odoo versions at audit time (e.g. `18.0`, `19.0`, `20.0`): `1` when the module is available and installable in that version, `0` otherwise (encoding in Availability resolution) |
| `pr` | `<target version>: <url>` of the last open/unmerged migration PR whose target version is still above the highest available version; empty when none or when the target version is already available (see Migration PR) |
| `comment` | empty by default; exception-only notes — see Comment policy |
| `migration_effort_days` | semantic migration effort to the confirmed target version; the global mechanical sweep is not included (rubric below) |

### Comment policy

`comment` is empty by default: the `origin`/`upstream` columns and the
version columns already carry most of the information. Use it only for
facts that the `1`/`0` columns cannot express:

- `not installed` — a module found on disk but absent from the installed
  set (no module report is written for it).
- `local modifications; PR <url>` — an upstream version exists (column
  `1`) but cannot be tracked as-is; this URL is the merge/review PR,
  distinct from the migration PR in `pr`.
- `renamed to <module>` — the successor drives the 1/0 columns; name it.
- `removed` / `replaced by <module>` — a `0` with a known alternative;
  keep it short.
- `New - required by module X` — a non-core dependency introduced by a
  target-version manifest. Use `New - required by modules X, Y` for
  several requirers, and append `; unknown` / `; renamed to Y` /
  `; replaced by Y` only when needed. This supersedes `not installed`
  for that row.
- `unknown` — the availability could not be determined (unscanned
  repository or branch); `0` is not evidence of absence.
- `bundled <origin> module, backported/renamed` — provenance for a
  vendored module.
- `vendored code inflates LOC` or `LOC unavailable` — only when it
  explains the numbers.

Do not write `installed`, `custom`, `to migrate`, an availability
sentence, the mechanical-pattern exclusion, the effort rationale or a
duplicate of the migration PR URL in `comment`; a distinct
local-modification/review PR may be named there. Those facts live in the
columns, the module report's Blocking points and the global report.
`installable: False` on a target branch is a normal sign that the module
has not been migrated: encode it as `0` and leave `comment` empty. Keep
`comment` tool-agnostic: never name the MCA or its tools; cite the
upstream module, version and URL instead.

### New dependencies introduced by target versions

A target-version manifest can add dependencies that are not installed in
the project. They can add migration work and must not be forgotten.

- For each audited module with a target manifest (external module or a
  renamed successor), compare the target `depends` with the installed set
  and the inventory.
- Add every new **non-core** dependency as a row: origin/upstream, LOC,
  1/0 availability, PR, `comment` = `New - required by module X`, and
  `migration_effort_days` = 0 for an external upstream port (estimate it
  only if the project owns the port). It gets no module report unless it
  is project-owned and on disk.
- Recurse into the newly added dependencies' target manifests; stop when
  no new non-core module remains. Do not re-list the existing installed
  dependency tree.
- Skip new standard Odoo dependencies unless the user explicitly asks to
  include them; they need no port.
- When the target manifest is only on a migration PR, use the PR's
  manifest (diff/API) as the target source.
- If several modules require the same new dependency, merge them into
  `New - required by modules X, Y`.

### Migration PR (`pr`)

Record `<target version>: <url>` of the **last open (or
closed-unmerged) migration PR whose target version is still above the
highest available version** for the module. A PR for 19.0 is valid when
19.0 and 20.0 are not yet available. A merged PR means its target
version is already in the stable branch: do not put it in `pr`; start
from that stable version instead. This is the starting point for the
port: use the PR when present, otherwise the last stable branch version
available.

- Consider only target versions above the highest `1` in the version
  columns. Example: a module available on 18.0 but not 19.0/20.0 can
  carry a 19.0 or 20.0 PR; a module available on 20.0 carries none.
- Prefer an open PR; use a closed-unmerged PR only when no open one
  exists. Never use a merged PR.
- Search the module's current upstream repository and any repository it
  moved to: modules can move between OCA repositories between versions.
- Use the MCA `pr_url` fields when available (`module_get_details`,
  `migration_get_module_status`); otherwise search the upstream
  repository's PRs for `[MIG] <module>`, `[PORT] <module>` or
  `[FW] <module>`.
- Write the cell as `<target version>: <url>`, for example
  `19.0: https://github.com/OCA/manufacture/pull/1830`. The version is
  the PR's target/base branch, not the project version.
- Leave the cell empty when no such PR exists; do not use `-`.
- For a `To review` module already available on the target, `pr` is
  empty unless a migration PR exists; the local merge/review PR belongs
  in `comment`.
- For a renamed module, search the successor's PRs as well; use the
  successor PR when the successor is not yet available.
- Do not repeat the migration PR URL in `comment`; a distinct
  local-modification/review PR may be named there.

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
  `mca.md`). Do not expand the inventory with the existing transitive
  dependencies; only add **new** dependencies introduced by target
  versions (see New dependencies). When the module is not in the MCA
  either, leave LOC empty and note it in `comment`.
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
repository (e.g. an OCA backport of a removed core module): the column
is `0` for the core module, with the backport as an alternative in
`comment`.

The version columns (`18.0`, `19.0`, `20.0`, ...) cover the last 3 stable
Odoo versions at audit time and record whether the module is available
and installable in each — not necessarily the version the project uses.

### Availability encoding (1/0)

`1` means the module is present **and installable** in the scanned
branch; `0` means absent or not migrated. The status names below are
analysis vocabulary used to decide the value and the comment, not CSV
values.

| Analysis status | CSV | Comment |
|-----------------|-----|---------|
| `Available` | 1 | empty |
| `To review` | 1, or 0 if only a PR exists | `local modifications; PR <url>` / `PR <url>` |
| `To migrate` | 0 | empty (custom module or dependency without successor) |
| `Removed` | 0 | `removed` or a short alternative |
| `Replaced` | 0 | `replaced by <module>` |
| `Renamed` | 1 where the successor exists, 0 elsewhere | `renamed to <module>` |
| `Unknown` | 0 | `unknown` |

A module present with `installable: False` is not migrated: CSV `0`,
comment empty.

## Migration effort rubric (to the confirmed target version)

Estimate in days, rounded to the closest 0.5:

1. Base by LOC (python + xml + js + css): under 500 → 0.5d; 500–2 000 → 1d;
   2 000–5 000 → 2.5d; above 5 000 → 5d.
2. Version distance: multiply the base by `1 + 0.3 × jumps`, one jump per
   version between the project's version and the confirmed target version
   (e.g. 17.0 → 20.0: base × 1.9). If the latest stable is blocked and
   the audit assesses the highest viable version, compute the effort to
   that version and record the next step in the global report; do not
   silently use the latest stable.
3. Semantic breaking deltas: scan the module against the odoo-knowledge
   `versions/<X>.md` files for every crossed version; add 0.5–1d per major
   break found. Count only breaks that require a design or behavioural
   change: removed or renamed models/fields/methods the module uses,
   changed workflow/state machines, ORM/search/`read_group` semantics,
   serial/lot/quant behaviour, JS/OWL rewrites, REST/API contract changes,
   security fixes and data migrations. An upstream model rename, move or
   removal that the local code uses is such a break (see `mca.md`). Cap
   the penalty at +5d.
4. Mechanical sweep (global, not per module): patterns a codemod or an
   automated migration handles — `attrs=` → direct attributes, `<tree>` →
   `<list>`, `t-esc`/`t-raw` → `t-out`, `groups_id` → `group_ids`,
   `ir.model.access.csv` → `ir.access.csv`, `self._cr`/`_uid`/`_context` →
   `self.env.*`, UoM/float helpers, `_sql_constraints`, `name_get`,
   `user_has_groups`, hook signatures, `res.config` getters — are
   estimated once for the whole codebase (tooling + review) and recorded
   in the global report. They do not change `migration_effort_days`; list
   their counts in the module report's Mechanical migration notes.
5. Upstream discount: when the target column is `1` and `comment` has no
   local-modification note, the effort is "track upstream": 0.5d. When
   the target column is `1` but `comment` flags local modifications/PR,
   estimate the merge/review. When the target column is `0` and
   `comment` names a successor/alternative or a PR, estimate the
   migration/merge; `renamed to <module>` is a light dependency switch.
   Modules with local modifications and `custom` modules get the full
   estimate.
6. Record the rationale in the module report's Blocking points (which
   deltas drove the number); do not copy it into the CSV `comment`.

## Feeding the markdown reports

Per-origin totals for the global report (module counts, LOC, days) come
from this CSV; the global report references it instead of duplicating
per-module rows. Each module report header (`1`/`0` availability and
comment, PR, LOC, effort, path) is written from its CSV row — when the
module audit revises a value, update the CSV row too so the two stay in
sync.
Modules with `1` in the target column and no exception comment get a
stub report only — no migration work, they track upstream (the rubric's
upstream discount).
