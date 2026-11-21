---
name: odoo-mca-timelines
description: >-
  Curate and feed module and code-element timelines into the Odoo MCA
  (Module Composition Analysis) MCP server for a module across Odoo versions.
  Starts from the MCA absent-element list, then finds what each
  model/field/method/data became using OpenUpgrade (apriori.py,
  upgrade_analysis.txt, pre/post-migration scripts), MCA element scans,
  and Odoo git history. Detects module renames/merges/removals and
  creates confirmed timelines for [HIGHLY-CONFIDENT] matches and drafts
  for [LESS-CONFIDENT] ones, with source URLs. Use when asked to populate
  or update MCA timelines, or to analyze what a module or code element
  became between Odoo versions.
compatibility: >-
  Requires the odoo-mca MCP server. Uses OpenUpgrade and an Odoo git
  clone when available.
metadata:
  requires-skills: odoo-knowledge
  requires-mcp: odoo-mca
---

# Curate Odoo MCA timelines

Feed the Odoo MCA with module and code-element timelines: confirmed for
high-confidence matches, drafts for uncertain ones. This skill covers the
curation workflow only; load `odoo-knowledge` for Odoo version and
migration rules.

Evidence order: **MCA scans** (what exists) -> **OpenUpgrade** (explicit
renames and deletions) -> **Odoo/OCA git history and source** (code
confirmation and note URLs).

## When to use

- Populate or update MCA timelines for a module over a version range.
- Analyze what a module, model, field, method, or data record became.
- Audit existing timelines or find the successor of a removed element.

Not for reviewing a normal code change; use `odoo-review` for that.

## Before you start

Confirm or infer: module and repository (`odoo/odoo` or `OCA/<repo>`),
version range, element types, removal policy, and confidence policy.
Default version range: the oldest and newest MCA versions. Default
confidence: `[HIGHLY-CONFIDENT]` matches are confirmed,
`[LESS-CONFIDENT]` matches are drafts; state explicitly when the user asks
for drafts only. Never modify the user's Odoo checkouts.

Check the environment:

- MCA tools resolve: `code_list_absent_elements`,
  `code_search_elements`, `code_get_next_version_element`,
  `code_create_timeline`, `migration_create_timeline`.
- OpenUpgrade branches are readable with `git show` (no checkout switch);
  read `references/evidence-sources.md` for layout and extraction commands.
- An Odoo clone exists; core modules can live under `addons/` or
  `odoo/addons/`.
- For a method pass, read `references/method-matching.md`; the helpers
  need Python 3.9+ and a clone that supports `git archive`.

## Non-negotiable rules

- **Confirm only high-confidence evidence; draft the rest.** Confirm when
  an explicit OpenUpgrade/apriori/migration-script rename, an explicit
  Odoo/OCA rename commit, or identical normalized code/data with a unique
  structural match is documented, and the note carries a `Source:` URL.
  Confirmed timelines are locked; confirmation is a one-way decision.
- **Never confirm a cross-module target before the same-module check.**
  If the source module has an extension of the target element, or the
  source model is an extension, use the same-module element. Confirmed
  mislinks can only be fixed in the MCA UI.
- **Tag every note** with `[HIGHLY-CONFIDENT]` or `[LESS-CONFIDENT]`.
  The note is HTML; end it with
  `<p>Source:</p><ul><li><a href="URL">URL</a></li></ul>` and read it back
  after creation. Do not use Markdown.
- **Cite element-specific sources.** `apriori.py` covers only
  modules/models and `upgrade_analysis.txt` only models/fields/XML
  records. Never cite either for a method; a migration script is valid
  only when it names the method hook. Put the commit/PR first, then
  OpenUpgrade; one strong element-specific source beats several
  transition-level links. Full order and OCA URLs:
  `references/evidence-sources.md`.
- **Filter every search hit by exact name/model.** `code_search_elements`
  is `ilike`; `user_id` also returns `user_ids`.
- **Deduplicate first.** Start from `timeline_state="none"`; page
  `code_list_timelines` and `migration_list_timelines` to `total` before
  creating. Never overwrite a confirmed timeline.
- **Prefer `moved` over `removed`.** Create `removed` only for explicit
  deletions or elements with no successor. Report uncertain
  disappearances instead of flooding the MCA.
- **Do not create timelines for population/reference data.** Report
  country, state, language, currency, chart templates, tax/report
  population lines, and generated asset bundles as datasets. Structural
  XML records that custom modules can override — ACLs/rules
  (`ir.model.access`, `ir.rule`, `ir.access`), menus, actions,
  views/report templates, groups, payment methods/providers, UoM records
  and categories, and demo records — may get per-record timelines when
  element-specific rename/move/deletion evidence exists. For large
  mechanical sets without per-record evidence, report the set instead of
  drafting hundreds of links.
- **Classify methods separately.** OpenUpgrade never lists methods. Do not
  infer a method rename from a field rename.
- **One best candidate.** When several elements could match, create the
  single best one.

## Workflow

### Step 1 — build the module map

Use `module_search(name=<module>)` and `module_get_details` for each
version. `module_get_details` is the primary authority for existence and
`last_scanned_commit`, but it can return `null` for an existing module:
cross-check `module_search` and any `code_search_elements` hit before
concluding it disappeared.

Treat `module_list_versions` as a hint only. Record version, repository,
manifest version, scan commit, and existence. Check
`migration_get_module_status` for hints and list existing module/code
timelines.

### Step 2 — create module timelines

Create one timeline per source module at its last existing version:
`migration_create_timeline(module=..., version=..., new_module=...,
timeline_type=..., note=..., confirm=..., repository=...)`. Use
`confirm=True` only for an explicit rename/replacement with a `Source:`
URL. A module with no successor has no module timeline: report it.

- 1:1 rename -> `renamed`.
- Merge into an existing module -> `replaced`.
- Module split (source survives) -> no module timeline; per-element
  `moved` with `next_module`.

An absorbed module (`hr_contract`, `base_vat`, `fetchmail`, …) is out of
scope unless requested: its module timeline is not created during an
unrelated run, but key model/field timelines can still feed the requested
target.

A confirmed module timeline resolves **same-name** elements only. Renamed
models still need their own timelines (`coupon` -> `loyalty` required
`coupon.coupon` -> `loyalty.card`; `gift_card` -> `loyalty` required
`gift.card` -> `loyalty.card`). Re-list absent models after confirming a
module timeline.

### Step 3 — snapshot the absent list

Call `code_list_absent_elements` once per module/version and record
`total`, `next_version`, and `counts`. Page to `total`; data elements are
limited to records loaded by the module.

Worklists:

- `timeline_state="none"` for analysis;
- structural data records: `element_type="data"`, `data_type="data"`,
  `noupdate=False`, `is_override=False` (excluding the population/reference
  records below);
- data that may get per-record timelines with element-specific evidence:
  `data_type="demo"` and `noupdate=True` (ACLs, rules, menus, actions,
  views/report templates, groups, payment records, UoM records and
  categories, demo records);
- report an extension removal: `is_override=True`;
- report as a dataset, no per-record timelines: population/reference
  records (country, state, language, currency, chart templates, tax/report
  lines) and large mechanical sets without element-specific evidence;
- review: `timeline_state="draft"`; removals: `timeline_type="removed"`.

`counts.moved` normally stays 0: moved elements leave the absent list.
Measure progress with the drop in `total`. `next_version` is global;
resolve the actual target with `code_get_next_version_element` /
`code_search_elements`.

### Step 4 — resolve the absent elements

1. Call `code_get_next_version_element` first. `state="available"` means
   skip; a draft means review it instead of creating a duplicate.
2. Classify before matching: demo and `noupdate=True` records may be
   matched when explicit deletion/rename/move evidence exists (they are
   real XML IDs that custom modules can reference); override -> report an
   extension removal; population/reference data -> report the dataset;
   model with non-empty `next_defined_in` -> report an extension removal.
   For large mechanical sets without per-record evidence, report the set.
3. Build the model rename map from apriori, analysis, and migration
   scripts.
4. Fetch target candidates once per `(version, module, element_type)`.
   Filter by exact name/model. For fields/methods also search by name
   without the model filter to catch cross-model moves.
5. For data moved across modules, reconcile the OpenUpgrade target with
   the actual MCA scan. A script can name a different module than the scan,
   or a module rename can change the local XML ID. See
   `references/evidence-sources.md`.
6. For methods, run `references/method-matching.md` after model lineage is
   applied, and pass the confirmed model map to the scanner.

### Step 5 — match candidates

- Fields: group by `(model, field_type, comodel_name)`.
- Methods: group by `(model)`; compare normalized bodies and use the
  signature only as a tie-breaker.
- Data: group by `(model, data_type)`.
- Pick the best candidate only, ranking by code/data similarity then name.
- If a model was renamed and the field/method keeps its name, model
  lineage covers it: no extra timeline.
- If the field/method name or target model changes, use
  `next_name`/`next_model`.

Detailed grouping, normalization, and false positives:
`references/matching-heuristics.md` and
`references/method-matching.md`.

### Step 6 — assign confidence

High confidence:

- explicit OpenUpgrade/apriori/migration-script rename;
- explicit Odoo/OCA rename commit;
- identical normalized code/data, unique structural match, meaningful
  name relation;
- a data record follows an explicit model rename and its group/permissions
  are unchanged.

Less confidence: code similarity only (fields >= 0.85, methods >= 0.92,
data JSON >= 0.90), semantic name change, several candidates, low view XML
similarity, or a cross-model field/method move without a commit.

Reject trivial methods, generic CRUD without a commit, parallel
implementations for another field/model, and exact bodies with unrelated
names. For a merge, confirm the primary source only; keep secondary
sources as drafts unless they are thin wrappers fully represented by the
target.

### Step 7 — create timelines

```text
code_create_timeline(
  element_type="model" | "field" | "method" | "data",
  version=<source version>,
  module=<source module>,
  model=<source model for fields/methods>,
  name=<name or full XML ID for data>,
  timeline_type="moved" | "removed",
  next_name=<target name/XML ID; omit for a pure move or removed>,
  next_module=<target module; omit if unchanged>,
  next_model=<target model for fields/methods; omit if unchanged>,
  note='<p>[TAG] ...</p><p>Source:</p><ul>...</ul>',
  confirm=<true only for HIGHLY-CONFIDENT>,
  repository=<repo>
)
```

Before creating:

- Verify the target exists in the MCA at the actual target
  version/module/model. A target found only in the source tree is a scan
  gap: report it.
- Verify the source is still absent. If the old XML ID still exists, the
  data move is invalid; if a model/field/method name was reintroduced,
  review before linking.
- **Run the same-module gate.** Search the target element in the source
  module at the target version and fetch the source model details. If the
  source `inherit` is non-empty, or a same-module target exists, link to
  the same-module element. Do this before `confirm=True`. See
  `references/audit-report.md`.

Note format:

```html
<p>[HIGHLY-CONFIDENT] ...</p><p>Source:</p>
<ul>
  <li><a href="COMMIT_OR_FILE_URL">COMMIT_OR_FILE_URL</a></li>
</ul>
```

For data, use the exact full XML ID from `_xmlids_renames` or the
migration script. When the same full XML ID exists in several later
versions, pass `next_module` explicitly. `moved` covers renames,
semantic replacements, and cross-module/model moves; `removed` only when
there is no successor.

A confirmed timeline can later receive a **note-only** update. Pass only
`note` plus the source identity and repository; including
`timeline_type`, `next_name`, `next_module`, or `next_model` is rejected.

### Step 8 — audit

Run `references/audit-report.md` before reporting:

- every confirmed move resolves with `code_get_next_version_element`;
- cross-module targets pass the same-module check;
- no old source name/XML ID still exists in the target;
- every note has the tag, a `<ul>` Source section, and working URLs.

### Step 9 — report

Use the report checklist in `references/audit-report.md` §5. At minimum:
per-transition totals, created timelines with id/type/state, method
classification counts, audit findings, and reported/uncertain items.

## Large-module playbook

For `base`, `mail`, `hr`, or a module with hundreds/thousands of absent
elements:

1. Create model timelines first; model lineage resolves same-name fields
   and methods.
2. Re-list absent fields/methods and record the new snapshot.
3. Map explicit field renames from migration scripts, `_inherits`, and
   column renames.
4. Map data renames/deletions from `_xmlids_renames` / `_deleted_xmlids`.
5. Run the method body scan only on the remaining methods.
6. Fetch all data elements once and build a `name -> {data_type,
   noupdate, is_override}` map. Create per-record timelines for structural
   records with element-specific evidence; report population/reference
   data and large mechanical sets as datasets.

## Timeline type

| Situation | Type |
|---|---|
| 1:1 module rename | `renamed` |
| Module merged into an existing module | `replaced` |
| Module split (source survives) | no module timeline; `moved` + `next_module` |
| Module deleted with no successor | no module timeline; report |
| Model/field/method/data renamed or replaced | `moved` |
| Element moved to another module/model | `moved` + `next_module`/`next_model` |
| Element deleted | `removed` |
| Several sources merged into one target | one `moved` per source |
| One source split into several targets | primary target + note |

## Reference map

| Need | Read |
|---|---|
| Tool signatures, gotchas, note format | `references/mca-tools.md` |
| OpenUpgrade/git evidence, source URLs, clone tips | `references/evidence-sources.md` |
| Field/data/model matching, thresholds, population data | `references/matching-heuristics.md` |
| Method scanner, AST rules, false positives | `references/method-matching.md` |
| Same-module gate, audit, report template | `references/audit-report.md` |
| Worked examples from real runs | `references/examples.md` |
| AST scanners | `scripts/method_scan.py`, `scripts/batch_method_scan.py` |
