# odoo-mca for audits

Optional read-only use of the `odoo-mca` MCP server during an audit.
When the server or its tools are unavailable, skip this file and use the
fallbacks in `module-inventory.md`.

## Probe and coverage

- Discover the tools with `search` (query `odoo-mca`): the Code Mode
  catalog may expose only a subset.
- Call `repo_list_versions` once. If it fails, stop using the MCA for
  the run.
- Call `repo_list_repositories` and keep the scanned organizations,
  repositories and branches.
- Coverage is bounded by those scans:
  - absence from a scanned branch is evidence of absence at the scan
    commit;
  - absence from an unscanned repository or branch is `unknown` (CSV
    `0` plus an `unknown` comment), not evidence: fall back to GitHub;
  - `specific: true` marks project-specific scans; check whether the
    audited project's own repository is covered.
- `last_scanned_commit` is the scanned commit. A difference with the
  audited checkout explains a LOC or availability gap; it is not a
  finding by itself.

## Inventory

Use the MCA for the columns it covers; compute the rest locally as
described in `module-inventory.md`.

### Module identity, manifest and dependencies

`module_get_details(module, version)` returns one entry per repository
hosting the module. Match the entry to the module's upstream repository
and branch; the others are forks, backports or historical moves.

- `title` / `summary`: use only in the module report description when the
  local manifest has no summary; the inventory CSV has no summary
  column.
- `depends` / `external_dependencies`: cross-check for the dependency
  analysis; the local manifest stays authoritative.
- `is_standard` / `is_enterprise` / `is_community` / `specific`:
  corroborate `origin`; never override an explicit local git remote.
- `url`: upstream module URL for the report evidence.
- `pr_url`: upstream migration PR, when present.
- `versions` is the manifest-version history, not the Odoo version list.

### Availability

Search by exact technical name and filter by the upstream repository:

```text
module_search(name=<module>, version=<V>, repository=<org/repo>)
```

- `name` is `ilike`: keep only `module == <module>`. A same-named
  module in another repository (e.g. an OCA backport of a removed core
  module) is not the audited module.
- `custom` modules are `0` on every target version; a scan of the
  project repository only documents the project version. Leave
  `comment` empty.
- Present with `removed: false` and `installable: true` in the scanned
  branch → `1`. A present branch with `installable: False` is not
  migrated → `0`, comment empty (the flag is normal). With local
  modifications or divergence → `1` plus `local modifications; PR <url>`
  in `comment` (the `To review` case).
- Present with `removed: true` → `0` for the old technical name; add
  `removed` or the confirmed successor (`renamed to <module>` /
  `replaced by <module>`) to `comment`. For a confirmed rename, the
  version columns follow the successor (see below).
- Absent, branch scanned:
  - confirmed rename → set `1` in each version where the successor
    exists and is installable, `0` elsewhere; keep `renamed to <module>`
    in `comment`. The old technical name is not scanned under the old
    name, so the successor drives the version columns;
  - confirmed replacement → `0` + `replaced by <module>` (the old module
    is gone; the replacement's availability is separate);
  - standard module → `0` + `removed`; name a maintained OCA backport in
    `comment` as an alternative;
  - addon without successor → `0`; leave `comment` empty.
- Branch not scanned → `0` + `unknown`; use the GitHub fallback before
  concluding.
- For an absent module, `migration_get_module_status` refines the
  reason: `migrate`/`port_commits` → `0` (comment empty unless a PR is
  worth citing); `review_migration` → `0` + the `pr_url`;
  `fully_ported` → `1`. These statuses are sparse and may skip versions
  (e.g. 14.0 → 18.0): existence/installability in the target branch is
  the primary source.
- `migration_list_timelines(module=<module>, version=<source V>, state="confirmed")`
  lists module renames/replacements; `starting_version` is the version
  where the successor applies. For a confirmed rename, follow the
  successor's existence/installability in each target version; the old
  technical name ends at `starting_version`. Existence in the target
  branch wins over a stale timeline.
- `moved_to_oca` / `moved_to_generic`: record the new upstream in
  `comment` (`renamed to`/`replaced by` only when the old technical name
  is gone). `moved_to_standard`: `0` + `replaced by <standard module>` in
  `comment` (or `removed` when none).
- Standard modules return `[]` from both migration tools: a missing
  standard module is `0` + `removed`, not "no migration".

### Migration PR

`module_get_details(...).pr_url` and the `pr_url` of each
`migration_get_module_status` path are the first source. Query every
version/path and keep the highest target version that is **not yet
available** and has a URL — a 19.0 PR when 19.0/20.0 are not available,
for example. A merged PR means the version is already in the stable
branch: leave `pr` empty and start from that branch version instead. If
the MCA has no URL, search the module's current upstream repository (and
any repository it moved to) for `[MIG] <module>`, `[PORT] <module>` or
`[FW] <module>`; prefer open over closed-unmerged, never merged. Record
`<target version>: <url>` in `pr`; leave it empty when none.

GitHub fallback:

```bash
gh search prs --repo <org/repo> --limit 50 \
  --json title,url,state,updatedAt --match title "[MIG] <module>"
```

Search the current repository and every repository the module moved to.
Derive the target from the title (`[19.0]`, `Migration to 19.0`) or, when
absent, from the PR base branch. For a renamed module, search the
successor name as well.

### New dependencies

Compare `module_get_details(module, target).depends` with the installed
set. For a renamed module use the successor's target manifest. Add new
non-core dependencies recursively; skip new standard Odoo modules unless
the user asks to include them. If the target manifest is only on a PR,
read its `__manifest__.py` from the PR diff/head branch. For a module not
in the MCA, fall back to GitHub and mark it `unknown`. Record the row
with `New - required by module X`.

### LOC

- Module directory on disk: count locally, always.
- Module not on disk (typically a dependency row): take
  `sloc_python` / `sloc_xml` / `sloc_js` / `sloc_css` from
  `module_get_details` for the project version, matching the upstream
  repository. Do not expand the inventory with the existing transitive
  dependencies; only add new target-version dependencies (see New
  dependencies).
- Not in the MCA either: leave LOC empty and add `LOC unavailable` to
  `comment`.

## Model granularity for upgrade readiness

The MCA use stops at models: never query fields, methods or data
records. The local code sweep remains authoritative for the models the
module uses; the MCA tells what happened to them upstream.

### Models that stay, move or disappear

`code_list_absent_elements` hides confirmed moves — it lists only what
still needs analysis. Query the timelines as well.

For each crossed source version `V`, when both `V` and `V+1` are
scanned for the module's repository (otherwise the module is not ported
and the availability status already carries the signal):

1. Confirmed renames and moves:
   `code_list_timelines(module=<module>, version=V, element_type="model", state="confirmed", timeline_type="moved")`.
   For each source model the local code defines, extends or references,
   resolve the target with
   `code_get_next_version_element(element_type="model", version=V, module=<module>, name=<model>)`.
   `state="available"` and `next` give the new module and model; use
   `code_get_element_history` for the full chain when several versions
   are crossed. Report the old → new identity and the local
   `file:line` to migrate.
2. Removals and uncovered absences:
   `code_list_absent_elements(module=<module>, version=V, element_type="model")`.
   - confirmed `removed` → removed;
   - `timeline.state="draft"` → proposed, not applied; report only as
     unconfirmed;
   - `timeline=null` → uncovered absence;
   - non-empty `next_defined_in` → the model still exists elsewhere;
     the module's extension is gone, not the model.
3. Module renames and replacements:
   `migration_list_timelines(module=<module>, version=V, state="confirmed")`.
   A module replacement does not automatically move its models:
   `code_get_next_version_element` does not follow module timelines for
   model elements. Verify each model in the successor module with
   `code_search_elements(element_type="model", version=V+1, module=<new_module>, name=<model>)`;
   report a move only when the model exists there.

A model from a dependency follows the same recipe: resolve its source
module with
`code_search_elements(element_type="model", version=<project>, name=<model>)`
(exact name), then query the code and module timelines on that module.

### Reporting

- Report a model change only when the local code references or extends
  the model; cite local `file:line`.
- Report the source and target model/module and the version; the
  timeline note's source URL (OpenUpgrade, commit) is valid evidence.
- Do not report generic upstream removals with no local impact.
- Model changes used by the local code are breaking deltas for the
  effort rubric; they do not change the rubric's formula.
- Keep the reports and the CSV tool-agnostic: never name the MCA, its
  tools or this reference. Cite the upstream module, model, version and
  URL instead.

## Read-only

The audit never calls `code_create_timeline`, `code_update_timeline`,
`code_delete_timeline`, `migration_create_timeline`,
`migration_update_timeline` or `migration_delete_timeline`. Timeline
curation belongs to the `odoo-mca-timelines` skill.

## Gotchas

- `module_search.name` is `ilike`: filter hits on the exact technical
  name. It is paginated (default 20): set a high `limit` and page to
  `total` before filtering.
- `module_list_versions` is a hint, not an index: it can stop early or
  return duplicate scans. `module_search` / `module_get_details` are
  the authority.
- Several scans can exist for one version: use `module_get_details`
  and its `last_scanned_commit`; match the repository and branch.
- `code_list_absent_elements` checks only the next global version:
  repeat for every crossed version.
- Only confirmed timelines resolve moves; drafts are not applied.
- `code_list_timelines` may not expose the resolved target in every
  case: confirm it with `code_get_next_version_element`.
- `repository` disambiguates when several repositories host a module.
- The MCA is a static scan, not a linter: it does not judge security,
  performance or code quality.
