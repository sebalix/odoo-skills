# Worked examples

Concrete cases from real curation runs. Use them to calibrate decisions,
not as a substitute for the element-specific evidence.

## Module lineage is not model lineage

Confirming the module timeline alone is not enough when model names change.
An absorbed module (`hr_contract`, `base_vat`, `fetchmail`, …) is out of
scope unless requested: the table lists model timelines that can feed the
requested target, not permission to create the module timeline.

| Module | Target | Model timelines still needed |
|---|---|---|
| `coupon` 15.0 | `loyalty` (renamed) | `coupon.coupon` -> `loyalty.card`, `coupon.program` -> `loyalty.program`, `coupon.reward` -> `loyalty.reward`, `coupon.rule` -> `loyalty.rule` |
| `gift_card` 15.0 | `loyalty` (replaced) | `gift.card` -> `loyalty.card` |
| `hr_contract` 18.0 | `hr` (replaced) | `hr.contract` -> `hr.version`, plus field renames |
| `l10n_fr_fec` 17.0 | `l10n_fr_account` (replaced) | `account.fr.fec` is removed; no successor model |
| `sale_product_configurator` 17.0 | `sale` (replaced) | `sale.product.configurator` is removed |

## Module split example

`delivery` 16.0 -> 17.0 is a split, not a rename: `delivery` survives while
stock-related fields, views, and the package wizard move to
`stock_delivery`. Create no module timeline; use per-element `moved` with
`next_module="stock_delivery"`. Extension models such as `stock.picking`
and `stock.move` remain defined in other modules: report them, do not
turn them into removals.

## Data target reconciliation

OpenUpgrade rename lists describe the migration intent; the MCA scan is
the authority for the target identity.

- `payment.payment_acquirer_kanban` / `_list` / `_search`: the script
  names `account_payment`, but the records stayed in `payment`.
- `payment.payment_acquirer_test`: the script names
  `payment_provider_test`, but `payment_test` was renamed `payment_demo`,
  so the actual target is `payment.payment_provider_demo`.
- A full target XML ID that exists in several later versions requires an
  explicit `next_module` in `code_create_timeline`.

## Same-module mislinks to avoid

These were confirmed before the pre-confirm gate was applied; they now
require a UI retarget:

| Source | Confirmed target | Preferred target |
|---|---|---|
| `repair@16.0 repair.line` | `stock/stock.move` | `repair/stock.move` |
| `point_of_sale@17.0 pos.combo` | `product/product.combo` | `point_of_sale/product.combo` |
| `point_of_sale@17.0 pos.combo.line` | `product/product.combo.item` | `point_of_sale/product.combo.item` |
| `point_of_sale@18.0 procurement.group` | `stock/stock.reference` | `point_of_sale/stock.reference` |
| `point_of_sale@18.0 product.packaging` | `product/product.uom` | `point_of_sale/product.uom` |

The source modules all carry the target model as an extension. Run the
gate in `audit-report.md` before `confirm=True`.

## Invalid data moves

The old XML ID still resolved in the target version, so the move was
skipped:

- `l10n_fr.dom-tom`: the analysis listed it as renamed to `base`, but the
  old ID still existed at 19.0.
- `point_of_sale.product_product_consumable`: still present at 18.0.

## MCA data scan gaps

These explicit rename targets were not present in the MCA data scan, so
no timeline was created:

- `website_event.constraint_event_registration_answer_value_check` ->
  `event.*`
- `point_of_sale.constraint_pos_order_line_uuid_unique`,
  `constraint_pos_order_uuid_unique`,
  `constraint_pos_payment_uuid_unique`

## Method extraction to a mixin

Cross-model method moves are drafts unless a commit confirms them:

- `hr_attendance@16.0 hr.employee._compute_presence_icon` ->
  `hr_attendance/hr.employee.base._compute_presence_icon`
- `analytic@17.0 account.analytic.line._compute_auto_account`,
  `_inverse_auto_account`, `_search_auto_account` ->
  `analytic/analytic.plan.fields.mixin`
- `point_of_sale@19.0 pos.session._load_pos_data_relations` ->
  `point_of_sale/pos.load.mixin._load_data_relations`

The scanner can misattribute a candidate module because of class
inheritance. Re-search the exact model/name in the MCA; for example
`_sms_get_number_fields` was reported as `sms/base` while the MCA target
is `sms/mail.thread.phone`.

## Population data sets

Report these as one dataset, no per-record timelines:

- `l10n_fr` 17.0 -> 18.0: 2,813 chart-template/report records moving to
  `l10n_fr_account`.
- country/state/language/currency rows moved from `l10n_*` to `base`.
- chart templates, tax/report population lines.
- large mechanical sets without element-specific evidence (e.g. 360 demo
  `account.analytic.line` records in `hr_timesheet`, 150 in
  `sale_timesheet`).

## Structural data timelines

Per-record timelines are appropriate when there is element-specific
evidence:

- ACLs/rules, including `ir.model.access`/`ir.rule` -> `ir.access`
  conversions, because custom modules override them;
- menus, actions, views/report templates, groups, payment
  methods/providers;
- UoM records and categories (`uom.uom`, `uom.category`): custom modules
  extend them, and the 19.0 UoM refactor renames/removes many of them;
- demo records (real XML IDs, occasionally referenced by custom demo
  modules);
- `noupdate` records with explicit rename/move evidence.

## Apriori key quirk

The 16.0 `merged_modules` contains `"gift_card "` with a trailing space.
Strip keys before lookup, or the `gift_card` -> `loyalty` merge is missed.

## Dry-run decisions (19.0 -> 20.0)

`phone_validation`:

- `phone_validation.access_phone_blacklist_all` is part of the 20.0
  `ir.model.access` -> `ir.access` conversion: create the per-record
  timeline when the mapping is explicit (custom modules may override it).
- `_phone_sanitized_search_index_exists` and
  `_onchange_phone_validation` are removed with no successor: report, no
  method timeline. The scanner labelled the latter `model_removed` even
  though `phone_validation/res.partner` still exists as an extension;
  verify the model in the MCA before trusting that status.

`calendar`:

- `res.users.settings.calendar_default_privacy` ->
  `calendar.calendar.calendar_default_privacy` is an explicit cross-model
  move (commit `c03c3502040d`: “field was moved from user_settings to the
  individual calendars”). Confirmed.
- `res.users.calendar_default_privacy` is the computed proxy over the
  settings field: same target, draft (secondary source).
- `calendar.filters.partner_checked` is removed (commit
  `8b031fa8ba06`); `active` already existed and is not a rename.
- `calendar.event.activity_ids` is still provided by
  `mail.activity.mixin` in 20.0; the calendar element is an extension
  removal, not a field removal.
- `calendar.popover.delete.wizard.delete` -> `requested_action` is not a
  rename (different selection values); report.
- The provider-config fields/methods/ACLs/views are covered by the
  confirmed model removal; create per-record ACL/view timelines only when
  the evidence is element-specific, otherwise report the set.
- The delete-wizard ACL/view/action changes are explicit in commit
  `2a9413ea4def`; per-record timelines may be created for them.
