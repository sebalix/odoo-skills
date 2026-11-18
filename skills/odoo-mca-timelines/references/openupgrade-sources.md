# OpenUpgrade sources

OpenUpgrade is the OCA migration toolkit. It has one branch per Odoo
version (`14.0` … `20.0`). Each branch contains the migration knowledge
for the transition into that version.

## Layout

```text
openupgrade_scripts/
├── apriori.py
└── scripts/
    └── <module>/
        └── <version>/
            ├── upgrade_analysis.txt
            ├── upgrade_analysis_work.txt
            ├── pre-migration.py
            ├── post-migration.py
            └── end-migration.py
```

The `scripts/<module>` directory may be absent on the newest branch.
`apriori.py` is always present.

## Branch semantics

- Branch `N` analyzes `N-1 -> N`. The 16.0 analysis covers 15.0 -> 16.0.
- `apriori.py` is cumulative. An entry on 20.0 can describe a merge that
  happened in 15.0. Use `module_list_versions` to find the module's last
  existing version; that is the effective transition.
- `renamed_modules` / `renamed_models` are 1:1 renames.
- `merged_modules` / `merged_models` are merges into an existing module.
  Use `timeline_type: "replaced"`.

## Read the work notes first

`upgrade_analysis_work.txt` is the maintainers' decision log. Its
`# DONE:` and `# NOTHING TO DO` lines often state the exact mapping that
the raw `upgrade_analysis.txt` only implies:

```text
# DONE: rename planned_hours -> allocated_hours
# DONE: pre-migration: rename field
# DONE: pre-migration: renamed field (analytic_account_id -> account_id)
# DONE: post-migration: renamed columns user_id -> user_ids
```

Read it before the plain analysis file and before running any heuristic.
A `# DONE:` line that names the source and target is explicit evidence,
even when the analysis file says only `DEL`/`NEW`.

## Exact scan commits

The MCA scans a specific commit, not the branch tip. For code or method
comparison, extract the module tree at `last_scanned_commit`:

```bash
git -C <odoo> archive <scan_commit> addons/<module> | tar -x -C /tmp/mca-trees/<module>/<version>
```

Use that tree as the source of truth. Branch HEAD can contain later
changes and produce false matches or misses.

## Extract apriori

```bash
git -C <openupgrade> show <branch>:openupgrade_scripts/apriori.py
```

Parse the dictionaries with Python `ast`:

```python
import ast, subprocess

src = subprocess.check_output(
    ["git", "-C", repo, "show", f"{branch}:openupgrade_scripts/apriori.py"]
).decode()
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in {
            "renamed_modules", "merged_modules",
            "renamed_models", "merged_models",
        }:
            print(node.targets[0].id, ast.literal_eval(node.value))
```

## Extract explicit renames

```bash
branch=19.0
module=stock
git -C <openupgrade> grep -nE \
  'rename_fields|rename_columns|rename_models|rename_tables|rename_xmlids' \
  "$branch" -- "openupgrade_scripts/scripts/$module"
```

Read the variable definitions:

```bash
git -C <openupgrade> show \
  "$branch:openupgrade_scripts/scripts/stock/19.0.1.1/pre-migration.py" |
  grep -nE \
  '^_[a-z_]*(renames|renamed|deleted|column_copies|columns_copy) =' \
  -A 40
```

Typical variables:

- `_models_renames`, `_renamed_models`
- `_tables_renames`, `_renamed_tables`
- `_fields_renames`, `_field_renames`, `_renamed_fields`
- `_xmlids_renames`, `_renamed_xmlids`
- `_deleted_xmlids`, `_deleted_xml_records`
- `delete_records_safely_by_xml_id` /
  `_deleted_records_safely_by_xml_id` calls (explicit data deletion, often
  on `noupdate=True` records)
- `_column_copies`, `_columns_copy`

`_deleted_xmlids` / `_deleted_xml_records` are explicit deletion
evidence: a `noupdate=True` record listed there may be created as a
confirmed removal. Use the target XML ID
exactly as written in `_xmlids_renames`; do not derive it from the source
local ID. A module split can drop a suffix, e.g.
`delivery.sale_order_portal_content_inherit_sale_stock_inherit_website_sale_delivery`
→
`stock_delivery.sale_order_portal_content_inherit_sale_stock_inherit_website_sale`.

## Module splits

`renamed_models` / `merged_models` give the **base** target. Before using
it, check whether the source module still has an extension of the target
model; if so, the same-module element is the correct target (see
`timeline-audit.md`).

A source module that still exists while a new module receives part of its
elements is a **split**, not a rename. Do not create a module timeline.
Create per-element `moved` timelines with `next_module` (and
`next_model`/`next_name` when needed), and report extension models that
remain defined in other modules. `delivery` → `stock_delivery` in 17.0 is
the reference example: `delivery` survives, while stock-related fields,
views and the package wizard move to `stock_delivery`.

## Newest branch without scripts

The newest branch may have no `scripts/<module>` directory. Do not skip
the transition; use git as the primary evidence source:

```bash
git -C <odoo> log --oneline --reverse -S "<old_field>" <source>..<target> \
  -- addons/<module>/models addons/<module>/wizard
git -C <odoo> log --oneline <source>..<target> -- addons/<module> \
  | grep -iE '\[(REN|REF|MOV|REM)\]|rename|remove'
```

- Filter out `[I18N]` commits and translation files; `git log -S` also
  matches `.po` files and calls.
- A confirmed move or removal needs an explicit commit (`[REF]`, `[MOV]`,
  `[REM]`, or a commit message that names the element).
- When no commit exists, cite the target source file only if the
  normalized body/XML is identical and the match is unique.
- Verify the file path at the scanned commit before citing it: model files
  are not always named after the model. In 16.0, `project.task` lives in
  `addons/project/models/project.py`, not `project_task.py`.
- Prefer the scan commit SHA over the branch name in blob URLs.

## Source URLs

```text
https://github.com/OCA/OpenUpgrade/blob/<branch>/openupgrade_scripts/apriori.py
https://github.com/OCA/OpenUpgrade/blob/<branch>/openupgrade_scripts/scripts/<module>/<version>/<file>
```

Examples from the `stock` analysis:

- 16.0 pre-migration `_fields_renames`:
  `stock.move.line.product_qty -> reserved_qty`,
  `stock.move.line.product_uom_qty -> reserved_uom_qty`,
  `stock.rule.location_id -> location_dest_id`,
  `stock.picking.move_lines -> move_ids`.
- 17.0 pre-migration `_field_renames`:
  `stock.move.quantity_done -> quantity`.
- 18.0 pre-migration `_field_renames`:
  `stock.move.location_dest_id -> location_final_id`,
  `stock.warehouse.orderpoint.qty_to_order -> qty_to_order_manual`.
- 19.0 pre-migration `_renamed_fields`:
  `stock.reference.stock_move_ids -> move_ids`,
  `stock.move.line.package_level_id -> package_history_id`,
  `stock.picking.package_level_ids -> package_history_ids`,
  `stock.route.packaging_selectable -> package_type_selectable`.
- 19.0 `_renamed_xmlids`: `stock.seq_quant_package -> stock.seq_package`.
- 19.0 `_deleted_xmlids`: `stock.stock_quant_package_comp_rule`,
  `stock.sequence_proc_group`,
  `stock.constraint_stock_warehouse_orderpoint_qty_multiple_check`.
- 20.0 `merged_models`: `stock.scrap -> stock.move`.

## Source relevance

An OpenUpgrade link is evidence only when the cited file documents the
element itself.

| Element | Valid OpenUpgrade evidence |
|---|---|
| module | `apriori.py` `renamed_modules` / `merged_modules` |
| model | `apriori.py` `renamed_models` / `merged_models`, analysis `obsolete model`, migration script |
| field | analysis line (`renamed to`, `DEL`, `NEW`, type change), field renames in a migration script |
| data | analysis `DEL`/`NEW`/`renamed` XML record line, `_renamed_xmlids` / `_deleted_xmlids` / `_deleted_xml_records`, `delete_records_safely_by_xml_id` |
| method | none: `apriori.py` and `upgrade_analysis.txt` do not list methods; use the Odoo/OCA commit or the target-branch source file. Run the method playbook in `method-matching.md`. |

`upgrade_analysis.txt` never lists methods and `apriori.py` never lists
fields, methods, or data records. Do not cite them as method evidence.

For a data removal, quote the exact `DEL ...` line or the XML ID from
`_deleted_xml_records` in the note. Citing the whole analysis file is
transition context, not element-specific evidence. A `# DONE:` line in
`upgrade_analysis_work.txt` that names the source and target is valid
element-specific evidence.

Verify before citing:

```bash
git -C <openupgrade> show <branch>:<file> | grep -nF "<name>"
```

If the element name is absent, the link is transition context, not
evidence: drop it.

## Git and source URLs

```text
https://github.com/odoo/odoo/blob/<branch>/addons/<module>/<path>
https://github.com/odoo/odoo/commit/<sha>
```

## Timeline note source line

Use a bulleted `Source:` section; put one full URL per bullet. Use a
`<ul><li>` list: the MCA sanitizer can flatten a `<br/>- <a>` list on
creation (anchors stripped, URL hoisted above `Source:`).

```html
<p>[HIGHLY-CONFIDENT] ...</p><p>Source:</p><ul>
  <li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>
  <li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>
</ul>
```

- The Odoo commit/PR is the code change and comes first.
- The OpenUpgrade script documents the migration convention and comes
  second.
- The OpenUpgrade bullet is valid only when the file mentions the element
  (see Source relevance above). For a method, cite the commit or the
  target-branch source file, never the analysis/apriori.
- Use the full URL as the link text; do not add labels.
- If no commit is found, keep the OpenUpgrade link only. The
  `[HIGHLY-CONFIDENT]` tag is driven by the OpenUpgrade/explicit evidence
  and is not downgraded by a missing commit.
- For OCA modules, use the OCA repository commit instead of an Odoo
  commit.

Check the MCA `last_scanned_commit` before trusting a local clone; the
clone may be older or newer than the scan. The source at the scanned
commit is the reference.

## Read-only or partial clones

A `blob:none` or `tree:0` clone on a read-only mount cannot lazily fetch
missing objects. Use one of these:

- a full bare clone in a writable directory;
- a writable copy of the partial bare clone with
  `objects/info/alternates` removed;
- `GIT_OBJECT_DIRECTORY=<writable>` plus
  `GIT_ALTERNATE_OBJECT_DIRECTORIES=<clone>/objects` for tree-only work.

Never modify the user's read-only clones.
