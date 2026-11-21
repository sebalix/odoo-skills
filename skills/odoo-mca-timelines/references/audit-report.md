# Audit and report

Run the same-module check **before creating any cross-module timeline**,
then run the full audit before reporting. Confirmation is one-way: the MCP
tools cannot retarget or delete a confirmed timeline, only annotate its
note.

## 1. Pre-confirm same-module gate

For every model rename/merge and every cross-module or cross-model target:

1. Search the target element in the **source module** at the target
   version. Filter by exact name/model (`code_search_elements` is `ilike`).
2. Fetch the source model details with `code_get_element_details` and read
   `inherit`.
3. Classify:

| Source `inherit` | Same-module target `inherit` | Action |
|---|---|---|
| non-empty | non-empty | **mandatory**: use the same-module target |
| empty | non-empty | preferred: use the same-module target |
| unknown | any | review before confirming |
| any | empty | base target is usually correct |

4. If the source module has a same-module element, use it. Omit
   `next_module` when it is unchanged (the source module); setting it
   explicitly to the source module is equivalent. Set `next_model` when
   the model changed, and `confirm=True` only after this check.

A source model with `inherit: ["stock.scrap"]` is an extension; a base
model has `inherit: []`. Do not rely on the post-creation audit to catch
this: a confirmed mislink needs the MCA UI.

### Target resolution for renames and splits

Use the source model's ownership and the target module layout, not the
apriori entry alone:

| Situation | Target |
|---|---|
| Source model owns the model (`inherit: []`) and it is renamed | the target model, possibly in a new module |
| Source is an extension and the source module still has the target | the same-module extension (`hr:mail.channel` -> `hr:discuss.channel`) |
| Source module is merged into a target module | the target module (`hr_contract:hr.contract` -> `hr:hr.version`) |
| Model is extracted to a new module | the new module (`mail:mail.tracking.value` -> `mail_tracking:...`; `purchase_requisition:purchase.order.group` -> `purchase_alternative:...`) |

Classification cautions:

- `unknown_source` (source details unavailable) is not a mislink: review.
- A base source model moved to another module while an extension stays
  behind still prefers the same-module extension (`mrp.document` ->
  `product.document`, target `mrp:product.document`).
- Reject a same-name hit on a different model (`ilike` prefix); require
  the exact model and name.

## 2. Audit checklist

1. Page `code_list_timelines` to `total`. For every confirmed `moved`
   timeline, run `code_get_next_version_element` and require
   `state="available"` with the expected target.
2. Run the same-module gate for every cross-module timeline.
3. Re-search the target version for every source name/XML ID:
   - data: same module, old XML ID still present -> `invalid_move`;
   - model/field/method: same name reintroduced -> `same_name_continuation`.
4. Re-read every note: tag, exact-name source relevance, `<ul>` Source
   section, working URLs.
5. Record `id | state | source | current target | corrected target |
   reason`.

## 3. Source still exists

A moved timeline is valid only when the source is really absent from the
target version.

- **Data:** an old XML ID that still exists is usually a duplicate. A
  confirmed invalid move must be deleted in the MCA UI. Concrete traps:
  `l10n_fr.dom-tom` (listed as renamed to `base`, but the old ID still
  resolved at 19.0) and `point_of_sale.product_product_consumable`
  (still present at 18.0). Do not create these moves.
- **Model/field/method:** the name may have been reintroduced with new
  semantics. An explicit OpenUpgrade rename can still justify a move to a
  differently named element; review before deleting.
- A method target that already exists in the source version is advisory:
  confirm only with a commit documenting the replacement.
- If an explicit rename list mentions a data record absent from the MCA
  data scan, report “not in MCA scan” instead of creating it. This
  happened for `website_event.constraint_event_registration_answer_value_check`
  and the three `point_of_sale` constraint XML IDs.

## 4. Fix

- **Draft code timeline:** update it with
  `code_update_timeline(..., next_module=<source module>, confirm=True)`
  (or omit `next_module` when unchanged) and rewrite the note. Preserve
  the source URL.
- **Draft module timeline:** use `migration_update_timeline(...)`.
- **Confirmed timeline:** retarget only in the MCA UI. A note-only update
  is still possible; pass only `note` plus the source identity and
  repository, never `timeline_type` or target fields.
- Mark confirmed mislinks as “UI fix required” in the report.

## 5. Report

Return a compact report:

- per-transition initial `total`/`counts`, created, resolved by lineage,
  current uncovered/draft/removed. `moved` is normally 0 because moved
  elements leave the list; report the drop in `total` as the
  resolved-by-moves figure.
- created timelines: id, transition, element, type, state, confidence.
- method classification counts; list `exact_unrelated_name`,
  `target_exists_in_source`, ambiguous and other rejected false positives
  separately.
- same-module audit: `id | state | source | current target | corrected
  target | reason`; mark confirmed mislinks “UI fix required”.
- source-still-exists audit: invalid data moves and same-name
  continuations.
- source audit: notes whose cited OpenUpgrade file does not contain the
  element, with the corrected note.
- skipped already-existing; reported population/reference datasets and
  override/extension removals; uncertain candidates and why they were not
  created.
- population/reference datasets reported rather than drafted.
- tool limitations and MCA data-quality gaps.

## 6. Population data reporting

Report as one dataset, not per record:

- country/state/language/currency population data moved from `l10n_*` to
  `base`;
- chart templates, tax/report population lines;
- asset bundles and generated technical records;
- large mechanical sets without element-specific evidence (e.g. hundreds
  of demo lines or generated views).

Structural XML records that custom modules can override may get per-record
timelines when element-specific evidence exists: ACLs/rules
(`ir.model.access`, `ir.rule`, `ir.access`), menus, actions, views/report
templates, groups, payment methods/providers, UoM records and categories,
and demo records. Create the model/module timeline first, then the
per-record links.

## Worked examples

See `examples.md` for the confirmed mislinks from real runs,
module-lineage cases, data-target reconciliation, invalid data moves, and
method extract/target examples.
