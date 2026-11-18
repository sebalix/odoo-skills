# Timeline audit: inherited elements and same-module targets

Run this audit after creating timelines, and whenever a model rename or
merge touches an extension model. It catches timelines that point to the
base definition in another module while the source module still has its
own extension of the target model.

## Checklist

1. Page `code_list_timelines` to `total`. For every confirmed `moved`
   timeline, run `code_get_next_version_element` and require
   `state="available"` with the expected target.
2. Run the same-module target detection below for every cross-module
   timeline.
3. Re-search the target version for every source name/XML ID and flag
   `invalid_move` (data) or `same_name_continuation`
   (model/field/method).
4. Re-read every note: tag, exact-name source relevance, a `<ul>` Source
   list, and working URLs.
5. Record the audit result in the report (`id | state | source | current
   target | corrected target | reason`).

## Why

MCA model elements are per module. `stock:stock.reference` and
`mrp:stock.reference` are different elements:

- `stock:stock.reference` is the base model (`inherit: []`);
- `mrp:stock.reference` is the MRP extension (`inherit: ["stock.reference"]`).

When `procurement.group` in `mrp` is renamed to `stock.reference`, the
element must follow `mrp:stock.reference`, not the base
`stock:stock.reference`. This applies to base models and extensions, and
to fields and methods on them: if the target exists in the source module,
prefer it. A non-empty `inherit` makes it mandatory for an extension.

## Detection

1. Page all timelines until `total`:

   ```text
   code_list_timelines(limit=500, offset=0)
   ```

2. Keep the cross-module ones:

   ```text
   timeline.next != null and timeline.next.module != timeline.module
   ```

3. For each, search the target element in the **source module** at
   `next.version`, and require an **exact** name match:
   - model: `name == next.name`;
   - field/method: `model == next.model and name == next.name`.

   `code_search_elements` uses `ilike`, so filter the results yourself;
   `stock.quant` also returns `stock.quantity.history`.

4. If there is no same-module target, the base target is correct: skip it.

5. Fetch model details for the source model and for the same-module target
   model:

   ```text
   code_get_element_details(element_type="model",
                            version=<source>, module=<source module>,
                            name=<source model>)
   code_get_element_details(element_type="model",
                            version=<next.version>, module=<source module>,
                            name=<next.model or next.name>)
   ```

6. Classify:

   | Source `inherit` | Same-module target `inherit` | Classification |
   |---|---|---|
   | non-empty | non-empty | **inherited same-module target**: mandatory fix |
   | empty | non-empty | **base-source same-module target**: review; the policy prefers the same module |
   | unknown | any | review: source details unavailable |
   | any | empty | base target: usually correct |

   A source model with `inherit: ["stock.scrap"]` is an extension. A base
   model has `inherit: []`. In both the clear inherited and the base-source
   cases, the same-module target is the preferred link when it exists.

## Source still exists

A moved timeline is only valid when the source is really absent from the
target version. For every timeline, search the target version for the
**source** name/XML ID. For data, index `code_search_elements` results by
`xml_id` (the full XML ID); its `name` field is only the local XML ID,
while timelines store the full XML ID.

- model/field/method: same module, source model, source name;
- data: same module, source local XML ID.

If the source still exists, distinguish:

- **data**: the old XML ID is usually a duplicate and the move is invalid
  (`invalid_move`). A confirmed one must be deleted in the MCA UI (the MCP
  tools cannot delete a confirmed timeline). This catches records that
  OpenUpgrade renames in the database while the source XML record is still
  present in the target branch.
- **model/field/method**: the name may have been reintroduced with new
  semantics (`same_name_continuation`). An explicit OpenUpgrade rename can
  still justify a move to a differently named element — e.g.
  `stock.move.location_dest_id -> location_final_id`, where
  `location_dest_id` also exists in 18 with new semantics. Review before
  deleting.

## Fix

- **Draft timeline:** update it with
  `code_update_timeline(..., next_module="<source module>", confirm=True)`
  and rewrite the note to say which extension it targets. Preserve the
  source URL.
- **Confirmed timeline:** the MCP tools cannot retarget it. It must be
  fixed in the MCA UI, as for `procurement.group`. A note-only update is
  still possible.

## Worked example

| Source | Wrong target | Correct target |
|---|---|---|
| `mrp:procurement.group` 18.0 | `stock:stock.reference` | `mrp:stock.reference` |
| `mrp:stock.scrap` 19.0 | `stock:stock.move` | `mrp:stock.move` |
| `mrp:stock.production.lot` 15.0 | `stock:stock.lot` | `mrp:stock.lot` |
| `account:account.analytic.default` 15.0 | `analytic:account.analytic.distribution.model` | `account:account.analytic.distribution.model` |
| `mrp:mrp.document` 17.0 | `product:product.document` | `mrp:product.document` |
| `stock_account:stock_account.stock.valuation.report` 19.0 | `account:account.stock.valuation.report` | `stock_account:account.stock.valuation.report` |

The first three are inherited-extension cases. The last three are
base-source cases where the source module still carries the relevant
same-module element.

## False positives

- A **base** source model moved to another module while an extension stays
  behind. Example: `mrp.document` (base in `mrp`) merged into
  `product.document`. The same-module policy still prefers
  `mrp:product.document` when that extension carries the MRP behavior;
  keep the base target only when the source module's element is unrelated.
- A report model or an element whose source details are not scanned:
  classify as `unknown_source`, not as a mislink.
- A same-module element with the same name but a different model (ilike
  prefix): reject it with the exact-name check.

## Reporting

Add a **same-module target audit** section to the final report:

```text
id | state | source | current target | corrected target | reason
```

Count the clear mislinks separately from the review-only base-source
cases. If a timeline is confirmed, mark it "UI fix required".
