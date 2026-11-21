# Matching heuristics

Use these rules to turn the absent-element list into a small number of
high-confidence moves/replacements. The goal is not to match every absent
element: confirm the HIGHLY-CONFIDENT matches and leave the rest as drafts
for human review.

## 1. Start from the absent list

Call `code_list_absent_elements` for the source module/version and page
through it. That is the source side: the elements that do not resolve
automatically in the next version. Start from `timeline_state="none"`;
skip `timeline.state="draft"` (already proposed) and
`timeline.type="removed"` with `timeline.state="confirmed"` (removal).
Record the `counts` from the unfiltered call for the report.

For data, the server only lists records loaded by the module. Classify
the rest before matching:

- `is_override=True`: report an extension removal, not a removal;
- demo (`data_type="demo"`) or noupdate (`noupdate=True`) records:
  allowed when explicit deletion, rename or move evidence exists; these
  are real XML IDs and may be referenced by custom modules;
- structural records (`data_type="data"`, `noupdate=False`,
  `is_override=False`): normal matching;
- population/reference records (country, state, language, currency, chart
  templates, tax/report lines): report the dataset, no per-record
  timelines. UoM records and categories are **not** population data here:
  custom modules extend them, so keep per-record timelines when the
  evidence exists.

For a large module, fetch all data elements once per module/version and
build a full-XML-ID map in memory instead of calling
`code_get_element_details` per record. Use the full XML ID as the key
(`name` in the absent list, `xml_id` in `code_search_elements`), not the
display `name`; map it to `{data_type, noupdate, is_override}`. This makes
it cheap to separate structural records from population data and large
mechanical sets (e.g. the 2,813 `l10n_fr` chart/report records, or the 360
demo analytic lines in `hr_timesheet`). Do not create hundreds of
mechanical links: require element-specific evidence per record.

Then fetch the target candidates once per `(version, module,
element_type)` with `code_search_elements`, scoped to the modules/models
implied by the model rename map and the absent elements. Keep the
results in memory; a module with ~700 fields and ~1000 methods is normal.

The name filter is `ilike`: filter every result by exact identity. For
fields/methods use `hit.name === source.name` and
`hit.model === source.model`; for data use `hit.xml_id` (the full XML ID),
not `hit.name` (the display name). A hit that only shares a prefix
(`user_id` vs `user_ids`) is not a target.

The absent list does not carry `field_type` or `comodel_name`. Fetch them
from the source version with `code_search_elements` or
`code_get_element_details` before grouping fields.

## 2. Target candidates

The absent list replaces the manual `removed = N - N+1` set difference.
Do not compute a global added set: for each absent element, search only
the plausible target scope.

For fields, repeat the search by name **without** the model filter to find
cross-model moves (`project.project.rating_active` ->
`project.task.type.rating_active`); validate the field type and comodel
before using the target. For methods, use
`scripts/method_scan.py --search-all-models`, and `--search-modules` when
the source element is an extension of a model owned by another module.

Call `code_get_next_version_element` first. If `state="available"`, the
link is confirmed and the element can be skipped. If `timeline` has
`state="draft"`, a draft already exists: skip it or review it; do not
create a duplicate. The draft does not make the element resolved. To
inspect a multi-version chain, use `code_get_element_lineage` (set
`to_version`) or `code_get_elements_lineage` for up to 100 elements.

For a module rename/replacement, `code_list_absent_elements` resolves
through the module lineage only when the module timeline is confirmed.
If it is still a draft, use the successor module's elements as the target
set (and do not treat the source module's absent list as a list of
removals).

## 3. Model rename map

Build `old_model -> new_model` from the explicit OpenUpgrade/apriori,
analysis, and migration-script renames for the transition.

Resolve the target model in the **source module** first. If it exists
there, the target is that same-module element; linking to the base model
in another module is wrong. Only fall back to the base module when the
source module has no element for the target model and the source is not
an extension; an extension with no same-module target is an extension
removal or a review. Run the pre-confirm gate in `audit-report.md`; a
non-empty `inherit` makes the same-module rule mandatory for an
extension.

Consequences:

- If the model is renamed and the field/method keeps its name on the
  renamed model, no field/method timeline is needed once the model
  timeline is **confirmed**: the model lineage covers it.
- A renamed model in module `M` targets the target model in `M` when it
  exists, not the base model in another module. An extension makes this
  mandatory.
- If the field/method is renamed or moved to another model, create a
  field/method timeline with `next_name`/`next_model`.
- Skip elements on models that are new or truly removed.
- For data, validate the target model against the map (step 6) and
reconcile the OpenUpgrade target with the MCA scan. The reconciliation
examples and the `next_module` rule are in `evidence-sources.md` and
`mca-tools.md`.

### Delegated models (`_inherits`)

A field can move to the model named in the target model's `_inherits`
(e.g. `hr.employee` inherits `hr.version` in 19.0). The field keeps its
name but lives on the delegated model:

- Read `inherits` (the model's `_inherits`) from the target model
  details.
- For an absent field on the delegating model, search the delegated model
  first and prefer the **stored** field there over a related same-name
  field on the delegating model.
- For an obsolete abstract model (`hr.employee.base`), map its fields to
  the concrete model/version that carries them.
- Compare field type and comodel before creating the move.
- Cite the analysis `_inherits` line; the target field alone is not
  evidence of the delegation.

## 4. Group candidates

Pick the best candidate only.

| Type | Structural group |
|---|---|
| field | `(model, field_type, comodel_name)` |
| method | `(model)`; use `(model, signature)` only as a tie-breaker |
| data | `(model, data_type)` |

Rank by normalized code/data similarity, then by name similarity. Do not
create every pair in a group.

Grouping keys come from the element summaries: `code_get_element_details`
on a **model** returns its `fields[]` (`name`, `field_type`) and
`methods[]` (`name`, `signature`), so one call per model element (module +
model) builds that module's candidate inventory; reserve per-element
details for the final comparison (step 5).

## 5. Normalize and compare

Fetch `code_get_element_details` for the source and the best candidate.

Field code:

- replace the field name with `<NAME>`;
- collapse whitespace;
- compare the resulting strings.

Method code:

- parse the exact `last_scanned_commit` trees, not branch HEAD;
- use `ast.unparse` on the function node and replace the method name with
  `<NAME>` (comments are folded, docstrings remain);
- collapse whitespace;
- compare the resulting strings;
- classify as `exact` (identical, unique target), `similar` (>= 0.92),
  `weak` (>= 0.80) or `no_match`; see `method-matching.md` and
  `scripts/method_scan.py`.

Data JSON:

- parse `data_json`;
- delete `id`, `name`, `file_path`, and `xml_id`;
- compare the remaining JSON.

A field definition includes the field name, so replace it before
comparing. A method body may call itself, so replace all occurrences of
the method name.

## 6. Validate data models

Extract the target model from the data JSON:

| Record model | Target model field |
|---|---|
| `ir.model.access` | `data.model_id` (`model_stock_package`) |
| `ir.rule` | `data.model_id` |
| `ir.access` (20.0+) | `data.model_id` |
| `ir.ui.view` | `data.model` |
| `ir.actions.report` | `data.model` |
| `ir.actions.act_window` | `data.res_model` |

Normalize `model_<name>` to `<name>` with underscores replaced by dots.

Then:

- if the source target model is in the model rename map, the target
  record's model must equal the mapped model;
- otherwise, the source and target target models must be equal.

Reject the pair when they differ. This filters access rights that were
reassigned to a different model.

A source data record with `is_override=True` is an override of another
module's record, not a removal candidate. Report the extension removal
rather than matching it against a new record.

## 7. Confidence thresholds

| Evidence | Tag | State |
|---|---|---|
| explicit OpenUpgrade/commit rename | `[HIGHLY-CONFIDENT]` | confirmed |
| identical normalized code/data, unique match, meaningful name relation | `[HIGHLY-CONFIDENT]` | confirmed |
| data follows an explicit model rename | `[HIGHLY-CONFIDENT]` | confirmed |
| secondary source of a merge (partial target) | `[LESS-CONFIDENT]` | draft |
| fields: code similarity >= 0.85 | `[LESS-CONFIDENT]` | draft |
| methods: code similarity >= 0.92 | `[LESS-CONFIDENT]` | draft |
| data: JSON similarity >= 0.90 | `[LESS-CONFIDENT]` | draft |
| exact body but unrelated name, no commit | report only | none |
| candidate name already exists in the source version | `[HIGHLY-CONFIDENT]` with a semantic commit, otherwise report | confirmed only with a commit |
| low view XML similarity | `[LESS-CONFIDENT]` or report only | draft |

For methods, a trivial one-liner (`return True/False`, `pass`), a parallel
implementation for another field, or a template hook differing only by
model is not a match even at similarity 1.0. Reject it instead of drafting.

A merge (several sources -> one target) does not make every source a 1:1
rename. Confirm the primary source; keep the other sources as drafts
unless the source is a thin wrapper/alias fully represented by the target.
An exact body with an unrelated name is usually a false positive: confirm
it only with an explicit commit. A candidate whose name already exists as
a sibling in the source version is advisory: confirm it when a commit
documents the semantic replacement; otherwise report it.

Create the timeline with `confirm=True` for a `[HIGHLY-CONFIDENT]` match
and as a draft for a `[LESS-CONFIDENT]` one. A source must document the
element itself, not just the transition: never cite `apriori.py` or
`upgrade_analysis.txt` on a method timeline (see `evidence-sources.md`).
In the HTML note, explain the score or the reason,
then use a bulleted `Source:` section with one full URL per bullet:

```html
<p>[HIGHLY-CONFIDENT] ...</p><p>Source:</p><ul>
  <li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>
  <li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>
</ul>
```

Use the `<ul><li>` form: the MCA sanitizer can flatten a `<br/>- <a>`
list on creation. Read the note back after creating the timeline.

When no commit is found, keep the element-specific OpenUpgrade link for a
model/field/data; for a method cite the target-branch source file. The tag
is not downgraded.

## 8. Common false positives

- Same type and comodel but different semantics: two booleans, two
  selection fields, a source/destination pair (`location_id` vs
  `location_dest_id`) — unless an explicit migration script confirms the
  rename.
- Multiple target candidates in the same structural group: pick the best
  by code similarity, not the first by name.
- Access rights consolidated into fewer records: several `moved`
  timelines to the same target. A true split (one source -> several
  targets) is a primary target + note, not a single rename.
- A data record reassigned to a different model without explicit evidence:
  reject.
- A data record whose old XML ID still resolves in the target version:
  reject the move. This caught `l10n_fr.dom-tom` and
  `point_of_sale.product_product_consumable`.
- A data target module taken from the OpenUpgrade list but not from the
  scan: reconcile it before creating. The record may have stayed in the
  source module, or moved to a module whose local XML IDs changed.
- An element reported absent but present in the source at
  `last_scanned_commit` (model, field, method, or data): record an MCA
  scan/identity gap; do not create a removal.
- A merge into an existing module: use `replaced`, not `renamed`.
- A method body identical to another method that implements a different
  field or model (parallel implementation), e.g. `_can_edit_name` vs
  `_can_edit_country`.
- A trivial method body (`return True`, `return False`, `pass`) matching
  another trivial method.
- A template hook that differs only by the template model.
- A target that already exists as a sibling in the source version **and no
  commit documents the replacement**: the body coincidence is not a rename
  (e.g. `_inverse_is_favorite` vs `toggle_favorite`, where
  `toggle_favorite` already existed).
- A secondary source of a merge where the target only represents part of
  it: do not confirm it as a 1:1 rename.

## 9. Removal policy

Create `removed` timelines for:

- explicit deletions in `_deleted_xmlids` / `_deleted_xml_records` or via
  `delete_records_safely_by_xml_id`;
- a structural data record with an explicit `DEL` line in
  `upgrade_analysis.txt` and no successor;
- models/elements that truly disappear and have no successor, including
  transient models when the removal is explicit (commit, analysis `DEL`,
  or deletion list); the model lineage covers their fields and methods.

Do not create `removed` for:

- a model with non-empty `next_defined_in` (it still exists in another
  module, typically `base`): report an extension removal or a cross-module
  move, not a removal;
- a data record with `is_override=True` (it overrides another module's
  record);
- a demo record without an explicit `DEL`/deletion-list entry; demo
  records may get a removal timeline when the removal is explicit;
- a `noupdate=True` record without explicit deletion, rename or move
  evidence: existing databases keep it;
- a method unless its model or feature is explicitly removed and it has no
  successor: report method disappearances in bulk, do not draft hundreds
  of removals;
- generated technical data in bulk (asset bundles, tracking records);
- country/state/language/currency population data moved from `l10n_*`
  modules into `base`: the source module is the `l10n_*` module, so do not
  create base timelines for those records;
- population/reference rows such as chart templates and tax/report lines;
- a large mechanical set without element-specific evidence: report the
  set; ACLs/rules, menus, actions, views/report templates, groups, payment
  records, UoM records and categories, and demo records may get per-record
  timelines when the evidence is element-specific.

For a merge with a known target, create one `moved` timeline per source
pointing to the same target; a merge is not a removal. For a module merge,
the module timeline uses `replaced`. A thin wrapper/alias fully
represented by the target may remain confirmed even when the target
already existed.

Do not create `removed` for every disappeared field, method, or data
record. Report them as a list of uncertain removals instead.

## 10. Deduplicate

The absent list reports a `timeline` per element: skip `timeline.state`
`draft`/`confirmed` entries and work from `timeline=null`. Still call the
list tools for a full view (chains, confirmed timelines):

```text
code_list_timelines(module=..., state="draft" | "confirmed",
                    timeline_type="moved" | "removed",
                    limit=50, offset=0)
migration_list_timelines(module=..., state="draft" | "confirmed")
```

`code_list_timelines` is paginated (default 50): page until `total` is
reached before concluding an element is not already covered. Skip
existing timelines. Never delete or modify a confirmed timeline.
