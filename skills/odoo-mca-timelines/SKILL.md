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

Feed the Odoo MCA (Module Composition Analysis) with module and
code-element timelines: confirmed for high-confidence matches, drafts for
the uncertain ones. The MCA tells migration reviewers what a module,
model, field, method, or data record became in the next Odoo version.
This skill covers the curation workflow only; load `odoo-knowledge` for
Odoo version and migration rules.

The agent works from several evidence sources, in this order:

1. **MCA scans** — the authority for what exists in each version.
2. **OpenUpgrade** — `apriori.py`, `upgrade_analysis.txt`, and the
   pre/post/end migration scripts.
3. **Odoo git history and source** — for code-confirmed renames and the
   commit/file URL placed in the timeline note.

## Hard rules

- **Confirm high-confidence timelines; draft the rest.** Create a
  code-element timeline as **confirmed** (`confirm=True`) when the
  evidence is high confidence — an explicit OpenUpgrade/apriori/migration
  script rename, an explicit Odoo rename commit, or identical normalized
  code/data with a unique structural match — and the note carries a
  `Source:` URL. Create `[LESS-CONFIDENT]` matches as drafts for human
  review. A module rename/replacement may likewise be created as
  confirmed when the evidence is explicit (OpenUpgrade `apriori.py`, a
  migration script, or an Odoo commit): the absent-elements workflow only
  follows confirmed module timelines. When in doubt, leave a draft.
  Confirmed timelines are locked, so confirming is a one-way decision.
  For a merge (several sources -> one target), confirm the primary source
  only and keep secondary sources as drafts unless the evidence documents
  a 1:1 mapping or the source is a thin wrapper/alias fully represented by
  the target. A secondary source is usually only partially represented by
  the target.
- **Tag every note.** The note is HTML: start its visible text with
  `[HIGHLY-CONFIDENT]` or `[LESS-CONFIDENT]`.
- **Use `<ul><li>` for the Source section, and verify it after
  creation.** The MCA sanitizer can flatten a `<br/>- <a>` bullet list on
  creation: anchors are stripped and the URL is hoisted above `Source:`.
  Use `<p>...</p><p>Source:</p><ul><li><a href="URL">URL</a></li></ul>`.
  After creating, read the timeline back and check the tag and at least
  one `<a href>`; rewrite the note with `code_update_timeline` if the
  anchors were lost.
- **Filter every search hit by exact name.** `code_search_elements`
  searches names with `ilike`: `user_id` also returns `user_ids`, and
  `stock.quant` also returns `stock.quantity.history`. A candidate is
  valid only when `hit.name === source.name` and, for fields/methods,
  `hit.model === source.model`. Never resolve a target from the raw result
  list; the same applies to XML IDs.
- **Cite element-specific sources.** End every note with a bulleted
  `Source:` section. Every bullet must document the specific element's
  change, not merely the transition. Put one bullet per link, with the
  full URL as the link text. Order the bullets: Odoo/OCA commit, PR,
  OpenUpgrade work notes, OpenUpgrade migration script, OpenUpgrade
  analysis/apriori, module tree. Put the commit first when available.
  `apriori.py` covers only modules/models and `upgrade_analysis.txt` only
  models/fields/XML records: never cite either for a method, and cite
  them for a field/data/model only when the element name actually appears
  in the file (see the source-relevance check in Step 7). One strong
  element-specific source is better than a commit plus a transition-level
  link. The confidence tag is driven by the OpenUpgrade/explicit evidence,
  not by the presence of a commit. Do not use Markdown.
- **Annotate confirmed timelines, don't retarget them.** A confirmed
  timeline can still receive a note-only update (HTML + source URL); its
  semantic fields and state are locked and it cannot be deleted through
  the MCP tools.
- **Deduplicate first.** `code_list_absent_elements` reports the
  `timeline` of each absent element; start from `timeline_state="none"`.
  Also call `code_list_timelines` (page until `total`) and
  `migration_list_timelines` for a full view. Skip existing timelines;
  never overwrite confirmed timelines. A pre-existing confirmed timeline
  can already have resolved its element, so it may not appear in the
  absent list at all: list timelines before creating anything.
- **Classify methods before matching them.** `apriori.py` and
  `upgrade_analysis.txt` never list methods. Run the method playbook in
  `references/method-matching.md`: classify by model, parse the exact
  scanned commits, compare normalized bodies, then confirm exact/unique
  matches and draft similarity-only ones. Do not infer a method rename
  from a field rename alone.
- **One best candidate.** When several elements could match, create the
  single best match, not every permutation.
- **Do not flood the MCA.** Prefer a `moved` timeline with the target
  over `removed` whenever the target exists. Create `removed` only for
  explicit deletions or elements with no successor; report uncertain
  disappearances instead of creating hundreds of low-confidence
  timelines. Report technical data in bulk rather than as per-record
  removals: asset bundles, ACLs that migrate to a new model (for example
  `ir.model.access` -> `ir.access` in 20.0), access-rights records,
  country/state/language population data moved from `l10n_*` modules into
  `base`, views/actions tied to a removed model, demo records, and records
  without user-facing semantics. For an access-rights migration, create
  the model timeline(s) and report the records in bulk.
- **Never modify the user's Odoo checkouts.** Use a throwaway clone or a
  writable object cache under `/tmp`.

## Inputs

Confirm or infer before starting:

- **Module** and **repository** (`odoo/odoo` or `OCA/<repo>`).
- **Version range** (default: the oldest and newest MCA versions).
- **Element types** (`model`, `field`, `method`, `data`).
- **Removal policy** — all removals, merges only, or renames only.
- **Confidence policy** — `[HIGHLY-CONFIDENT]` matches are created
  confirmed; `[LESS-CONFIDENT]` matches are created as drafts for human
  review. State the policy explicitly when the user asks for drafts only.

## Environment checks

1. Locate the MCA tools. The Code Mode catalog may be partial; use
   `search` for `odoo-mca`, then confirm the key tools resolve:
   `code_list_absent_elements`, `code_search_elements`,
   `code_get_next_version_element`, `code_create_timeline`,
   `migration_create_timeline`. A tool count alone proves nothing — a
   missing core tool passes any count check.
2. Read `references/mca-tools.md` for signatures and semantics.
3. Locate OpenUpgrade. Check out or read each branch with `git show`
   rather than switching the working tree.
4. Locate an Odoo git clone. A bare or full clone is best; a read-only or
   partial clone can still serve path-limited logs and commit messages.
   Core modules are not always under `addons/`: `base` lives under
   `odoo/addons/base`, and the 20.0 core tree uses `odoo/addons`. The
   method scanner auto-detects both prefixes.
5. Read `references/openupgrade-sources.md` for the repository layout
   and extraction commands.
6. For a method pass, read `references/method-matching.md`. The helpers
   `scripts/method_scan.py` (single transition) and
   `scripts/batch_method_scan.py` (multi-transition driver) need Python
   3.9+ (`ast.unparse`) and a full git clone.

## Source hierarchy

### 1. MCA scans

Use `module_search` (filter by `name`) and `module_get_details` to build
the per-version existence map, then `code_list_absent_elements` for the
source-side to-do list. Treat `module_list_versions` as a hint only: it
can return an empty list for a module that exists and can stop before the
newest version. Several scans for the same version are possible; record
the `last_scanned_commit` from `module_get_details` for every transition.
Use `code_search_elements` to fetch the target candidates. The MCA scan
data is what the timelines will be applied to; verify that the source
element exists in the MCA before creating a timeline for it.

Check the scan commit (`last_scanned_commit`) when the local clone and the
MCA disagree. The source at that commit is the reference.

### 2. OpenUpgrade `apriori.py`

`apriori.py` contains `renamed_modules`, `merged_modules`,
`renamed_models`, and `merged_models`. Two rules matter:

- **It is cumulative.** An entry on branch `N` may describe a merge that
  happened many versions earlier. Determine the effective transition from
  the module's last existing version, not from the branch where the entry
  appears.
- **A merge is not a rename.** Use `timeline_type: "replaced"` with
  `new_module` when the source module was merged into an existing module.
  Use `"renamed"` only for a 1:1 module rename.

For module timelines, create one entry per source module, at its last
existing version, with `new_module` set to the target.

### 3. OpenUpgrade analysis files

Branch `N` analyzes the transition `N-1 -> N`. The relevant files are:

```text
openupgrade_scripts/scripts/<module>/<version>/upgrade_analysis.txt
openupgrade_scripts/scripts/<module>/<version>/upgrade_analysis_work.txt
```

Read `upgrade_analysis_work.txt` first. Its `# DONE:` / `# NOTHING TO DO`
lines are the maintainers' own mapping decisions and often name the exact
field/XML-ID mapping (`planned_hours -> allocated_hours`,
`user_id -> user_ids`, `analytic_account_id -> account_id`). The plain
analysis file is the raw diff; the work file tells you what was decided.

The analysis file lists models and fields with `renamed to` / `renamed
from`, `DEL`, `NEW`, and type changes. Treat explicit `renamed to` lines
as high confidence. Treat `DEL`/`NEW` pairs as candidates for the
matching heuristics, not as renames by themselves.

### 4. OpenUpgrade migration scripts

Pre-migration scripts contain the explicit rename lists:

- `_models_renames`, `_renamed_models`
- `_tables_renames`, `_renamed_tables`
- `_fields_renames`, `_field_renames`, `_renamed_fields`
- `_xmlids_renames`, `_renamed_xmlids`
- `_deleted_xmlids`, `_deleted_xml_records`
- `delete_records_safely_by_xml_id` / `_deleted_records_safely_by_xml_id`
  calls (explicit data deletions, often on `noupdate=True` records)
- column copies such as `_column_copies` / `_columns_copy` (often a
  rename plus a copy)

These are the strongest evidence. Read them before running any
heuristic. A rename listed in a migration script is high confidence even
when the analysis file does not mention it.

### 5. Odoo git history and source

Use git for:

- explicit rename commits (`[REN]`, `[REF] ... rename`, `[MOV]`);
- field/method renames that are not in OpenUpgrade;
- the `Source:` URL.

Prefer `git log -- <path>` and `git log --grep` on a full clone. A
partial clone may need a writable object directory; see
`references/openupgrade-sources.md`.

Verify file paths before citing them, at the scanned commit, not at branch
HEAD: `addons/<module>/models/...`, `addons/<module>/wizard/...`,
`addons/<module>/security/...`, `addons/<module>/data/...`. Model files are
not always named after the model (in 16.0 `project.task` lives in
`addons/project/models/project.py`). Prefer the scan commit SHA over the
branch name in blob URLs.

### 6. Newest branch without OpenUpgrade scripts

The newest OpenUpgrade branch may have no `scripts/<module>` directory.
Do not skip the transition; use git as the primary evidence source:

```bash
git -C <odoo> log --oneline --reverse -S "<old_field>" <source>..<target> \
  -- addons/<module>/models addons/<module>/wizard
git -C <odoo> log --oneline <source>..<target> -- addons/<module> \
  | grep -iE '\[(REN|REF|MOV|REM)\]|rename|remove'
```

Filter out `[I18N]` commits and translation files. A confirmed move or
removal needs an explicit commit (`[REF]`, `[MOV]`, `[REM]`, or a commit
message that names the element) or an element-specific target source file
when the body/XML is identical and unique.

## Large-module playbook

For a module with hundreds or thousands of absent elements (`base`,
`mail`, `hr`), use this order instead of working element type by element
type:

1. Create the model timelines first (apriori/analysis). Model lineage
   resolves same-name fields and methods on the renamed models.
2. Re-list the absent fields and methods; many disappear without new
   timelines. Record the new snapshot.
3. Map explicit field renames from migration scripts (`_fields_renames`,
   `_renamed_fields`, column renames, `_inherits` delegation).
4. Map data renames/deletions from `_xmlids_renames` / `_deleted_xmlids` /
   `_deleted_xml_records`.
5. Run the method body scan only on the remaining methods.
6. Report the bulk data sets (access rights, population data, technical
   records) instead of creating per-record removals. Fetch all data
   elements once per module/version and build a
   `name -> {data_type, noupdate, is_override}` map; this separates the
   structural records from the bulk demo/noupdate/override sets without a
   per-record details call.

This keeps the method scan small and avoids `model_removed` noise.

## Workflow

### Step 1 — build the module map

1. `module_search` with `name=<module>` (not `query`) to confirm
   existence and the repositories hosting it.
2. `module_get_details` for each version in scope. It is the primary
   authority for existence and for `last_scanned_commit`. If it returns
   `null`, do not conclude the module disappeared: cross-check
   `module_search` and any
   `code_search_elements` hit for that version. A module can be absent from
   `module_get_details` while both the module index and the code scan still
   contain it (observed for `repair` 20.0); record that as an MCA
   scan/identity gap.
3. Record: version, repository, manifest version, `last_scanned_commit`,
   existence. Cross-check `module_list_versions` only as a hint: it can be
   empty for an existing module, stop before the newest version, and
   return duplicate scans for one version.
4. If the module disappears, find the effective last version and the
   successor module.
5. Check `migration_get_module_status` for existing hints
   (`renamed_to`, `replaced_by`, `moved_to_standard`). An empty list is
   normal for standard modules; it is not evidence that nothing changed.
6. Check `migration_list_timelines` and page `code_list_timelines` for
   existing drafts or confirmed entries. Pre-existing confirmed timelines
   may already have resolved elements and therefore be invisible in
   `code_list_absent_elements`.

### Step 2 — create module timelines

Create one timeline per source module. Use `confirm=True` only when the
rename/replacement is explicit in OpenUpgrade/apriori, a migration script,
or a commit, and the note carries a `Source:` URL: a confirmed module
timeline immediately activates the module lineage used by
`code_list_absent_elements`. Otherwise leave it as a draft and handle the
module rename manually until a reviewer confirms it.

```text
migration_create_timeline(
  module=<source module>,
  version=<last existing version>,
  new_module=<target module>,
  timeline_type="replaced" | "renamed",
  note=(
    '<p>[HIGHLY-CONFIDENT] ...</p><p>Source:</p><ul>'
    '<li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>'
    '<li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>'
    '</ul>'
  ),
  confirm=<true only for high-confidence renames/replacements>,
  repository=<repo>
)
```

A module timeline supports renames and replacements only. A module that
truly disappears (no successor) has no module timeline: report it and
analyze its elements as removed.

A **module split** is not a module rename. When the source module still
exists and a new module receives part of its elements — for example
`delivery` → `stock_delivery` in 17.0 — create **no module timeline**.
Create per-element `moved` timelines with `next_module`, and report
extension models that remain defined in other modules (`stock.picking`,
`stock.move`, …) instead of turning them into removals.

An **absorbed module** (`hr_contract`, `base_vat`, `fetchmail`, …) is not
the requested module: its module timeline is out of scope unless asked
for. Key model and field timelines can still be created when they feed
the requested target module (`hr_contract:hr.contract` -> `hr:hr.version`
feeds `hr`), citing the apriori merge.

A confirmed module timeline only resolves **same-name** elements in the
successor module. Renamed or merged models still need their own timelines:
`coupon` -> `loyalty` required `coupon.coupon` -> `loyalty.card`,
`coupon.program` -> `loyalty.program`, etc., and `gift_card` -> `loyalty`
required `gift.card` -> `loyalty.card`. After confirming a module
timeline, re-list the absent models and map every renamed/merged model
before moving to fields and methods.

### Step 3 — list the absent elements

Use `code_list_absent_elements` for each module/version in scope. It is
the primary to-do list: the elements whose next version state is `absent`,
with their current `timeline`.

Start with one unfiltered call per module/version to snapshot the
distribution: `total`, `next_version`, and `counts` (uncovered, draft,
removed, moved). `total` is after any timeline filter; `counts` is the
distribution before it. Confirmed `moved` timelines remove elements from
the list, so `total` shrinks as you work: keep the initial snapshot for
the report. `counts.moved` is **not** a progress metric: moved elements
leave the absent list entirely, so it normally stays at 0 even after many
confirmed moves. Use the drop in `total` (and the confirmed timeline
count) instead.

Then build the worklist:

- `timeline_state="none"` for elements to analyze;
- data structural records: `element_type="data"`, `data_type="data"`,
  `noupdate=False`, `is_override=False`, `timeline_state="none"`;
- data reporting: `data_type="demo"`, `is_override=True`, or
  `noupdate=True` (no timeline filter if you also want to see drafts and
  confirmed removals);
- review: `timeline_state="draft"`; removals: `timeline_type="removed"`.

```text
code_list_absent_elements(
  module=<source module>,
  version=<source version>,
  element_type=<optional>,
  model=<optional>,
  data_type=<optional "data" | "demo">,
  noupdate=<optional true | false>,
  is_override=<optional true | false>,
  timeline_state=<optional "none" | "draft" | "confirmed">,
  timeline_type=<optional "moved" | "removed">,
  repository=<repo>,
  limit=500,
  offset=0,
)
```

Page until `offset + len(elements) >= total`; record `total`, `counts` and
`next_version`. Data elements are always limited to records loaded by the
module; unloaded records are excluded by the server.

Caveats:

- The state is resolved through **confirmed** module/code timelines. If
  the module itself was renamed/replaced and its timeline is still a
  draft, the source module's elements may all be reported as absent. In
  that case use the module map and the successor module's elements as
  the target set; do not create per-element removals. Confirming the
  module timeline (Step 2) avoids this.
- `next_version` is the next global Odoo version, not necessarily the
  next available version of the module (version gaps). Resolve the
  target with `code_get_next_version_element`/`code_search_elements` on
  the actual target version.
- The list only contains `absent` elements. `unknown` means the next
  version or the repository branch is not scanned yet: check
  `module_get_details`/`last_scanned_commit` before concluding.
- A module with no successor has no module timeline: its absent elements
  are removal candidates, subject to the removal policy.
- A confirmed `moved` timeline removes the element from the list; a
  confirmed `removed` remains listed with `timeline.type="removed"`; a
  draft remains listed with `timeline.state="draft"`. A remaining entry is
  not a failed creation.
- Confirmed **model** timelines also resolve same-name fields and methods.
  `total` can therefore shrink by more than the number of timelines you
  created; report the model-lineage contribution separately.
- If an element is reported absent but exists in the target source at
  `last_scanned_commit`, do not create a removal. Record it as an MCA
  scan/identity gap and verify the source before concluding.

### Step 4 — resolve the absent elements

For each absent element:

1. Call `code_get_next_version_element` with the source identity.
   - `state="available"`: a confirmed link already exists; skip it.
   - `timeline` has `state="draft"`: a draft already exists; skip it, or
     review/update the draft instead of creating a duplicate. The draft
     does not change `state` or `next`.
2. Before matching, apply the data and extension classification:
   - `data_type="demo"`: report only, never draft;
   - `is_override=True`: the record overrides another module's record;
     report an extension removal, do not create `removed`;
   - `noupdate=True`: existing databases keep the record; report it
     unless explicit deletion, rename or move evidence exists;
   - structural records (`data_type="data"`, `noupdate=False`,
     `is_override=False`): analyze and map or remove;
   - model with non-empty `next_defined_in`: the model still exists in
     another module; report an extension removal, do not create
     `removed`.
3. Build the model rename map from OpenUpgrade/apriori for the
   transition.
4. Fetch the target candidates in the target version/module/model with
   `code_search_elements`, scoped to the modules/models implied by the
   map and the source element, with a high limit. Cache the results per
   `(version, module, element_type)`; do not re-query per element. Filter
   the hits by exact name/model (the name search is `ilike`). For fields
   and methods, also search by name without the model filter to detect
   cross-model moves (`project.project.rating_*` ->
   `project.task.type.rating_*`); use `code_get_element_details` to confirm
   the field type/comodel.
5. Match with the heuristics (Step 5).
6. For data that moved to another module without a model rename (menus,
   access rights), use the full XML ID plus the OpenUpgrade
   `_renamed_xmlids`/git evidence to locate the target module; create a
   `moved` timeline with `next_module` (or the full `next_name`). Reconcile
   the OpenUpgrade target with the actual MCA scan before creating: a script
   may name `account_payment` while the record stayed in `payment`
   (`payment_acquirer_kanban`/`_list`/`_search`), and a module renamed in
   the same transition changes the local XML ID
   (`payment_test` -> `payment_demo`, so `payment_acquirer_test` targets
   `payment.payment_provider_demo`, not `payment_provider_test`).
7. Create a `moved` timeline when a target exists; create `removed`
   only when there is no successor (see the removal policy).
8. For methods, apply the method playbook before any body comparison:
   methods on a removed model are report-only; methods on a model with a
   confirmed model timeline are covered when the name is unchanged; only
   the remaining methods are candidates.
9. Verify every target with `code_search_elements` in the actual target
   version/module/model before creating a timeline. A target that exists
   only in the source tree is a scan gap, not a valid link: report it.

### Step 5 — match candidates

Read `references/matching-heuristics.md` for the full matching method. In short:

- Fields: group by `(model, field_type, comodel_name)`.
- Methods: read `references/method-matching.md`; group by `(model)`,
  compare normalized bodies (method name replaced), and use the signature
  only as a tie-breaker.
- Data: group by `(model, data_type)`.
- Pick the best candidate only, ranking by code/data similarity and then
  name similarity.
- Fetch `code_get_element_details` for both sides and compare normalized
  code or JSON.
- For data, validate that the target record's model matches the model
  rename map. Reject different-model matches.
- If the model was renamed and the field/method keeps its name on the
  renamed model, the model lineage covers it: no field/method timeline.
  Create a field/method timeline only when its name or target model
  changes; use `next_name`/`next_model`.
- **Same-module target for renamed models.** Before linking a model to
  another module, search the target model in the source module at the
  target version. If it exists, use that element (omit `next_module` or
  set it to the source module). Only link to the base module when the
  source module has no element for the target model. A non-empty `inherit`
  is a strong signal that the source element is an extension and must
  follow the same-module extension. Apply the same rule to fields and
  methods on inherited models, and run the pre-confirm gate in Step 7
  before setting `confirm=True`.

### Step 6 — assign confidence

High confidence when any of these is true:

- explicit OpenUpgrade/apriori/migration-script rename;
- explicit Odoo rename commit;
- normalized code or data is identical, the structural match is unique,
  and the name relation is meaningful or a commit confirms it;
- a data record follows an explicit model rename and its group,
  permissions, or target model is unchanged.

Less confidence when:

- code similarity is high but not identical (fields >= 0.85, methods
  >= 0.92, data JSON >= 0.90);
- the name changed semantically (`quantity_done` -> `quantity`);
- several candidates share the same structure;
- the view XML similarity is low;
- a cross-model field rename uses `next_model` (and a model timeline,
  when one is declared).

For methods, reject rather than draft a candidate when the normalized body
is a trivial one-liner (`return True/False`, `pass`), a parallel
implementation for another field, a template hook differing only by model,
or a generic CRUD method without an explicit rename commit.

For a merge (several sources -> one target), the target often represents
only part of a secondary source: confirm the primary source and keep the
secondary sources as drafts unless the evidence documents a 1:1 mapping
or the source is a thin wrapper/alias fully represented by the target.
An exact normalized body with an unrelated name is report-only unless a
commit confirms the rename. A candidate that already exists as a sibling
in the source version is advisory: confirm it when an explicit commit
documents that the source was retired in favor of that target; otherwise
report it.

Tag accordingly, explain the uncertainty in the note, and create the
timeline confirmed for `[HIGHLY-CONFIDENT]` (with a `Source:` URL) or as
a draft for `[LESS-CONFIDENT]`.

### Step 7 — create code-element timelines

Use `code_create_timeline`, with `confirm=True` for a
`[HIGHLY-CONFIDENT]` match and the default draft for a
`[LESS-CONFIDENT]` one:

```text
code_create_timeline(
  element_type="model" | "field" | "method" | "data",
  version=<source version>,
  module=<source module>,
  model=<source model for fields/methods, omit for models/data>,
  name=<name or XML ID>,
  timeline_type="moved" | "removed",
  next_name=<target name or XML ID; omit for a pure move or for removed>,
  next_module=<target module; omit if unchanged>,
  next_model=<target model for fields/methods; omit if unchanged>,
  note=(
    '<p>[HIGHLY-CONFIDENT] ...</p><p>Source:</p><ul>'
    '<li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>'
    '<li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>'
    '</ul>'
  ),
  confirm=<true for HIGHLY-CONFIDENT, false for LESS-CONFIDENT>,
  repository=<repo>
)
```

Before creating, verify the target exists in the MCA with
`code_search_elements` on the actual target version/module/model. If it is
absent from the scan, report "target not in MCA scan" instead of creating
an unresolvable timeline. Also verify the **source is still absent** in
the target version: search the target for the same source name or XML ID.
If it still exists, distinguish the cases: a data XML ID that still exists
is usually a duplicate and the move is invalid; a model/field/method name
may have been reintroduced with new semantics, so an explicit OpenUpgrade
rename can still justify the move. Review before deleting.
`code_create_timeline` does not enforce this. For a model rename/merge,
resolve the target module first: when the target model
exists in the source module, prefer that element over the base model in
another module; a non-empty `inherit` makes it mandatory for an extension
(see Step 5).

**Same-module target gate — run it before `confirm=True`.** Search the
target element in the source module at the target version and fetch the
source model details. If the source `inherit` is non-empty, or a
same-module target exists, link to the same-module element
(`next_module=<source module>`). Confirmation is irreversible through the
MCP tools: a confirmed timeline cannot be retargeted or deleted, only
annotated. Do not rely on the Step 8 audit to catch this; at that point the
only fix is the MCA UI. The same gate applies to methods extracted to a
mixin in the source module.

The note is HTML. Use a `<ul>` list for the `Source:` section; the MCA
sanitizer preserves it, while a `<br/>- <a>` list can be flattened on
creation:

```html
<p>[HIGHLY-CONFIDENT] ...</p><p>Source:</p>
<ul>
  <li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>
  <li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>
</ul>
```

`code_create_timeline` returns `{timeline: {id, state}}` on success and
`{error: ...}` otherwise. After creating, fetch the timeline with
`code_list_timelines` and check that the note still contains the tag and
at least one `<a href>`. If the sanitizer flattened the list, rewrite the
note with `code_update_timeline` using the `<ul><li>` form.

When no commit is found, keep the OpenUpgrade link only. Confirmed
timelines can later be annotated with a note-only update (HTML + source
URL); their semantic fields remain locked. Pass only `note` (plus the
source identity and repository) on a confirmed timeline: including
`timeline_type`, `next_name`, `next_module` or `next_model` — even with
the existing value — is rejected with “only its note can be updated”.

#### Source relevance check

An OpenUpgrade link is valid only if it documents the element itself:

- `apriori.py` lists only `renamed_modules`/`merged_modules` and
  `renamed_models`/`merged_models`. It never lists fields, methods, or
  data records.
- `upgrade_analysis.txt` lists models, fields, and XML records only. It
  never lists methods.
- A pre/post/end migration script is valid only when it mentions the
  element (field name, XML ID, model, or method hook).

Extract the element identity and grep the cited file:

```bash
git -C <openupgrade> show <branch>:<file> | grep -nF "<name>"
```

For a field, require the source **model and field** on the same analysis
line (`module / model / field`). A field name that only appears under a
different model is not element evidence. For data, require the full XML
ID; for a model, the exact model name.

For a method, skip the OpenUpgrade analysis/apriori entirely and cite the
Odoo/OCA commit or the target-branch source file. If the grep finds
nothing, drop the link instead of keeping it as transition context.

`moved` covers a rename, a semantic replacement (e.g. a `Char` field
turned into a `Many2one` while keeping the same semantics), and a move to
another module/model. Set `next_module` and/or `next_model` for a
cross-module or cross-model move; `next_name` can be omitted when the
element keeps its name/XML ID. The target must exist in the next scanned
version (the next available version of the target module if a version is
missing).

For data, `name` and `next_name` accept full XML IDs
(`stock.access_stock_lot_user`); a full `next_name` can infer the target
module when unambiguous. When the same full XML ID exists in several later
versions, `code_create_timeline` fails with “Several data records match …
Specify `next_module`”; pass `next_module` explicitly. Local IDs work when
`module`/`next_module` disambiguates. Use the **exact** target XML ID from
`_xmlids_renames` or the migration script; do not derive it from the source
local ID. A module split can drop a suffix, e.g.
`delivery.sale_order_portal_content_inherit_sale_stock_inherit_website_sale_delivery`
→ `stock_delivery.sale_order_portal_content_inherit_sale_stock_inherit_website_sale`.

Before creating a `removed` timeline, re-check the false-removal guards:
model `next_defined_in` non-empty, data `is_override=True`,
`data_type="demo"`, and `noupdate=True` without explicit deletion
evidence. Report those instead of drafting a removal. Transient models are
not a blocker: create `removed`/`moved` timelines when the evidence is
explicit; the model lineage covers their fields and methods.

A merge (several sources -> one target) is represented by one `moved`
timeline per source, all pointing to the same target. A true split (one
source -> several targets) still has only one target in the schema:
record the primary target and name the other targets in the note.

### Step 8 — audit the timelines

Run `references/timeline-audit.md` before reporting. Treat the same-module
checks as a confirmation gate, not just a post-creation audit: a confirmed
mislink can only be noted, not retargeted or deleted through the MCP tools.

1. Fetch every created or changed timeline and verify a confirmed move
   resolves with `code_get_next_version_element`.
2. For cross-module/cross-model targets, check `inherit` and
   `next_defined_in`; prefer the same-module extension when it exists.
3. Re-search the target version for every source name/XML ID and flag
   `invalid_move` (data) or `same_name_continuation`
   (model/field/method). A method target that already exists in the source
   version is advisory: confirm it only with a commit that documents the
   semantic replacement.
4. Re-read every note: tag, exact-name source relevance, `<ul>` Source
   section, and working URLs.

### Step 9 — report

Return a compact report:

- per-transition counts: initial `total`/`counts` snapshot, created,
  resolved by model lineage, current uncovered/draft/removed. `moved` is
  normally 0 because moved elements leave the list; report the drop in
  `total` as the resolved-by-moves figure instead;
- created timelines: id, transition, element, type, state
  (confirmed/draft), confidence;
- method classification: exact/similar/weak/no_match/model_removed/
  extension_model_removed counts; list `exact_unrelated_name`,
  `target_exists_in_source`, and other rejected false positives
  separately;
- same-module target audit: cross-module timelines where the source module
  has an extension of the target element, with the corrected target;
- source-still-exists audit: invalid data moves whose old XML ID still
  exists, and same-name continuations that need review;
- source audit: any note whose cited OpenUpgrade file does not contain the
  element (especially methods), with the corrected note;
- skipped: already existing;
- reported, not drafted: demo / noupdate / model extension / data override;
- uncertain: candidate, why it was not created;
- tool limitations hit (e.g. one source -> several targets,
  cross-repository targets);
- data-quality gaps found in the MCA scans.

## Timeline type

| Situation | `timeline_type` |
|---|---|
| 1:1 module rename | `renamed` |
| Module merged into an existing module | `replaced` |
| Module split (source survives, new module receives elements) | no module timeline; per-element `moved` with `next_module` |
| Model/field/method/data renamed or replaced (e.g. type change) | `moved` |
| Module deleted with no successor | no module timeline; report it |
| Model/field/method/data deleted | `removed` |
| Model/data moved to another module | `moved` with `next_module` |
| Field/method moved to another model | `moved` with `next_model` |
| Several sources merged into one target | one `moved` per source, same target |
| One source split into several targets | `moved` to the primary target + note |

Cross-module and cross-model targets are actual record references: the
target module/model are derived from the target element, so they are
visible in `code_list_timelines`/`code_get_element_history`. Do not fall
back to `removed` when the target exists: `removed` loses the link for the
migration analysis.

## Pitfalls

- **Cumulative apriori.** Do not trust the branch where an entry appears;
  use the module's last existing version.
- **Analysis branch `N` = `N-1 -> N`.** Do not shift the transition.
- **Newest branch may lack scripts.** The 20.0 OpenUpgrade branch may not
  have `scripts/<module>` yet; use `apriori.py` plus the MCA diff and git
  (see Source hierarchy 6).
- **`module_list_versions` is not an index.** It can be empty for an
  existing module, stop before the newest version, or return duplicate
  scans for one version. Use `module_search`/`module_get_details` and
  record the scan commit.
- **`module_get_details` can return `null` for an existing module.** This
  was observed for `repair` 20.0 while `module_search` and the code scan
  contained it. Cross-check both before treating the module as removed;
  record the discrepancy as an MCA scan/identity gap.
- **Duplicate scans.** Several scans per version can resolve the absent
  list against a different commit than `module_get_details` returns. If an
  element is reported absent but exists in the source at
  `last_scanned_commit`, record a scan/identity gap; do not create a
  removal.
- **`ilike` search.** `code_search_elements` matches substrings. Filter
  every hit by exact name/model before using it.
- **Pre-existing target.** A method whose target already exists in the
  source version is not automatically a false positive: an explicit
  semantic commit can show that the source was retired in favor of that
  target. Confirm with that commit; otherwise report it. The
  `target_exists_in_source` scanner status is advisory.
- **Note sanitizer.** `<br/>- <a>` bullets can be flattened on creation;
  use `<ul><li>` and read the note back after creating it.
- **Confirmed timelines are locked.** A confirmed timeline can only receive
  a note-only update. Pass only `note` plus the source identity and
  repository; including `timeline_type`, `next_name`, `next_module` or
  `next_model` — even unchanged — is rejected. A wrong confirmed target
  must be fixed in the MCA UI.
- **Source still exists in the target scan.** Re-search the old name/XML ID
  before creating a move. Two concrete traps: `l10n_fr.dom-tom` was listed
  as renamed to `base` but the old ID still resolved at 19.0, and
  `point_of_sale.product_product_consumable` still existed at 18.0. In
  both cases the move is invalid; report it instead of creating it.
- **MCA scan gaps.** A model or method can be missing from the MCA scan
  while still being present in the source at the scanned commit. Verify
  against the source before creating a removal. The reverse also happens:
  an element listed absent may exist in the target source (e.g.
  `account.move.statement_id` in 16.0) — report the gap, do not remove it.
- **Targets must exist in the MCA scan.** A target found only in the source
  tree cannot be linked; `code_create_timeline` rejects it. Report
  "target not in MCA scan" and skip.
- **Module splits are not renames.** When the source module survives and a
  new module receives elements, create no module timeline; use per-element
  `moved` with `next_module`.
- **Exact target XML IDs.** Copy the target from `_xmlids_renames` or the
  migration script; a module split may drop a suffix. Reconcile it with
  the actual MCA scan: OpenUpgrade can name a different target module than
  the scan (`payment_acquirer_kanban` stayed in `payment`, not
  `account_payment`) or a local ID changed by a module rename in the same
  transition (`payment_acquirer_test` -> `payment_provider_demo`).
- **Renamed models follow the same module.** When the target model exists
  in the source module, link to it, not to the base model in another
  module. A non-empty `inherit` makes this mandatory for extensions. See
  `references/timeline-audit.md`.
- **Draft timelines are inert for the analysis.**
  `code_get_next_version_element` and the migration analysis only follow
  confirmed timelines. A draft does not resolve the element
  (`state="absent"`, `next=null`), but `code_get_next_version_element`
  reports its target in `timeline.target`: use it to deduplicate or
  review, not as a confirmed link. `[LESS-CONFIDENT]` code-element
  timelines stay drafts for human review; `[HIGHLY-CONFIDENT]` ones are
  created confirmed.
- **Absent-list lifecycle.** A confirmed `moved` timeline removes the
  element from the absent list; a confirmed `removed` remains listed with
  `timeline.type="removed"`; a draft remains listed with
  `timeline.state="draft"`. A remaining entry is not a failed creation.
- **`counts.moved` is not a progress metric.** Moved elements disappear
  from the absent list, so `counts.moved` normally stays at 0 even after
  many confirmed moves. Measure progress with the drop in `total`.
- **Module lineage is not model lineage.** A confirmed module rename/
  replacement resolves same-name models only. Renamed models still need
  their own timelines (e.g. `coupon` -> `loyalty` required
  `coupon.coupon` -> `loyalty.card`; `gift_card` -> `loyalty` required
  `gift.card` -> `loyalty.card`).
- **Timeline lists are paginated.** `code_list_timelines` defaults to 50
  rows. Page with `limit`/`offset` until `total` before deduplicating.
- **Extension removals are not element removals.** A model with non-empty
  `next_defined_in` and a data record with `is_override=True` still exist
  in another module; report them, do not create `removed` timelines.
- **Absent list vs draft module timelines.**
  `code_list_absent_elements` resolves through confirmed timelines only.
  If a module rename/replacement is still a draft, the source module's
  elements may all appear absent: use the module map and the successor
  module's elements, or confirm the module timeline first.
- **`next_version` is global.** It is the next Odoo version, not
  necessarily the next available version of the module. With a version
  gap, resolve the target with
  `code_get_next_version_element`/`code_search_elements` on the actual
  target version. An empty or partial absent list may mean the next
  version is not scanned (`unknown`); check the scan commit before
  concluding.
- **Access rights split or consolidated.** A consolidation (several
  sources -> one target) is represented by several `moved` timelines to
  the same target. A true split (one source -> several targets) is not
  representable: use one primary target and explain the others in the
  note.
- **Bulk access-rights migrations.** When the target replaces
  `ir.model.access` with `ir.access` (20.0), the XML IDs are reorganised
  and consolidated. Report the migration; do not create speculative
  per-record moves.
- **Transient models and wizards.** Create `removed`/`moved` timelines for
  transient models when the evidence is explicit (commit, analysis `DEL`,
  or deletion list). The model lineage covers its fields and methods; do
  not create per-element removals for them.
- **Technical data removals.** Asset bundles, ACLs, and demo or tracking
  records are reported in bulk; create per-record removals only for
  structural records that a migration script must handle.
- **Cross-model field renames.** Set `next_model` to the target model; the
  link no longer depends on a confirmed model timeline (keep the model
  timeline for the model's own history).
- **Repository ambiguity.** Pass `repository` when several repositories
  host the source module. Cross-repository targets are rejected: the
  target module must be in the same repository, or reached through a
  module rename/replacement timeline.

## References

- `references/mca-tools.md` — MCA tools, signatures, semantics.
- `references/openupgrade-sources.md` — branch layout, file names,
  extraction commands, URL patterns.
- `references/matching-heuristics.md` — grouping, normalization,
  confidence thresholds, false positives.
- `references/method-matching.md` — method classification, AST
  normalization, false positives, helper-script usage.
- `references/timeline-audit.md` — pre-confirmation and post-creation
  audit for same-module inherited targets and other cross-module mislinks.
- `scripts/method_scan.py` — AST method scanner/comparator for an
  absent-method list; supports cross-model (`--search-all-models`),
  cross-module (`--search-modules`), and name-relation guards.
- `scripts/batch_method_scan.py` — multi-transition driver for
  `method_scan.py`.
