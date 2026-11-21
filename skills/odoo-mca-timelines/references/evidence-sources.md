# Evidence sources

The MCA scan is the authority for what exists. OpenUpgrade, target-branch
PRs, and Odoo/OCA git provide the element-specific mapping and the URL
cited in the note.

## 1. MCA scans

Use `module_search(name=<module>)` and `module_get_details` to build the
per-version existence map, then `code_list_absent_elements` for the
source-side to-do list.

- `module_list_versions` is a hint only: it can be empty for an existing
  module, stop before the newest version, or return duplicate scans.
- `module_get_details` is the primary authority, but it can return no
  `modules` entry (empty or null) for an existing module (`repair` 20.0).
  It returns one entry per repository; select the requested one.
  Cross-check `module_search` and the code scan before concluding the
  module disappeared.
- Record `last_scanned_commit` for every transition. The source at that
  commit is the reference when the local clone and the MCA disagree.
- Several scans for one version can resolve the absent list against a
  different commit than `module_get_details` returns. If an element is
  absent but exists in the source at `last_scanned_commit`, record a
  scan/identity gap; do not create a removal.
- Use `code_search_elements` to fetch target candidates; verify the source
  element exists in the MCA before creating its timeline.
- Record the first version where the target module is actually scanned.
  `module_list_versions` can omit an intermediate version; a module whose
  target appears later than the source-version successor leaves a scan gap,
  not a missing successor. State that gap in the timeline note.

## 2. OpenUpgrade layout

One branch per Odoo version (`14.0` ... `20.0`). Branch `N` analyzes the
transition `N-1 -> N`.

- A model timeline derived from branch `N` is created at version `N-1`,
  because the source element must exist there. If the source lookup fails,
  shift the timeline back one version and verify.
- Renames can reverse in a later branch (`hr.applicant.skill` ->
  `hr.candidate.skill` -> `hr.applicant.skill`), so always anchor the
  entry to the version where the source element actually exists.

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

The `scripts/<module>` directory may be absent. In the checked-out
repository the 20.0 branch had no `openupgrade_scripts/scripts` directory
at all: only `apriori.py` is available for 19.0 -> 20.0.

## 3. `apriori.py`

`apriori.py` contains `renamed_modules`, `merged_modules`,
`renamed_models`, and `merged_models`.

- **It is cumulative.** An entry on branch `N` may describe a merge that
  happened many versions earlier. Use the module's last existing version,
  not the branch where the entry appears.
- **A merge is not a rename.** `merged_modules` / `merged_models` use
  `timeline_type: "replaced"`. Use `"renamed"` only for a 1:1 rename.
- **Normalize keys.** The 16.0 `merged_modules` contains `"gift_card "`
  with a trailing space; strip whitespace from keys and values.
- **Distinguish Odoo-core from OCA entries.** `l10n_eu_service` ->
  `l10n_eu_oss` is an Odoo-core merge; `l10n_eu_oss` ->
  `l10n_eu_oss_oca` is OCA-only.
- **OCA module absorbed into core.** A `merged_modules` entry such as
  `"mail_preview_base": "mail"` (under `# OCA/social`) means the OCA
  module's functionality was absorbed by a core module. Create a
  `replaced` module timeline with the core module as `new_module`; the
  OCA module itself disappears.

Parse the dictionaries with `ast`:

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

For module timelines, create one entry per source module at its last
existing version, with `new_module` set to the target.

## 4. Analysis files

Read `upgrade_analysis_work.txt` first. Its `# DONE:` and
`# NOTHING TO DO` lines are the maintainers' decisions and often name the
exact mapping (`planned_hours -> allocated_hours`, `user_id -> user_ids`,
`analytic_account_id -> account_id`). The plain
`upgrade_analysis.txt` is the raw diff.

The analysis lists models and fields with `renamed to` / `renamed from`,
`DEL`, `NEW`, and type changes. Explicit `renamed to` lines are high
confidence. `DEL`/`NEW` pairs are candidates for matching, not renames by
themselves.

## 5. Migration scripts

Pre-migration scripts contain the strongest explicit evidence:

- `_models_renames`, `_renamed_models`
- `_tables_renames`, `_renamed_tables`
- `_fields_renames`, `_field_renames`, `_renamed_fields`
- `_xmlids_renames`, `_renamed_xmlids`
- `_deleted_xmlids`, `_deleted_xml_records`
- `delete_records_safely_by_xml_id` /
  `_deleted_records_safely_by_xml_id`
- `_column_copies`, `_columns_copy`

Extract the definitions with:

```bash
branch=19.0; module=stock
git -C <openupgrade> grep -nE \
  'rename_fields|rename_columns|rename_models|rename_tables|rename_xmlids' \
  "$branch" -- "openupgrade_scripts/scripts/$module"
git -C <openupgrade> show \
  "$branch:openupgrade_scripts/scripts/$module/<version>/pre-migration.py" |
  grep -nE '^_[a-z_]*(renames|renamed|deleted|column_copies|columns_copy) =' \
  -A 40
```

`_deleted_xmlids` / `_deleted_xml_records` are explicit deletion evidence:
a `noupdate=True` record listed there may be created as a confirmed
removal.

Use the exact target XML ID written in `_xmlids_renames`; do not derive it
from the source local ID. A module split can drop a suffix, e.g.
`delivery.sale_order_portal_content_inherit_sale_stock_inherit_website_sale_delivery`
-> `stock_delivery.sale_order_portal_content_inherit_sale_stock_inherit_website_sale`.

The rename list is migration intent, not necessarily the final MCA target.
Reconcile it with the scan: a record can stay in the source module
(`payment.payment_acquirer_kanban` -> `payment.payment_provider_kanban`,
not `account_payment`), and a module rename in the same transition changes
the local ID (`payment_test` -> `payment_demo`, so
`payment_acquirer_test` -> `payment.payment_provider_demo`).

## 6. Git history and source

Use git for explicit rename commits (`[REN]`, `[REF] ... rename`,
`[MOV]`), field/method renames not in OpenUpgrade, and the `Source:` URL.

```bash
git -C <odoo> log --oneline <source>..<target> -- addons/<module> \
  | grep -iE '\[(REN|REF|MOV|REM)\]|rename|remove'
git -C <odoo> log --oneline --reverse -S "<old_field>" <source>..<target> \
  -- addons/<module>/models addons/<module>/wizard
```

Filter out `[I18N]` commits and translation files. A confirmed move or
removal needs an explicit commit, or an element-specific target source
file when the normalized body/XML is identical and unique.

Verify file paths at the scanned commit, not branch HEAD. Model files are
not always named after the model (in 16.0 `project.task` lives in
`addons/project/models/project.py`). Prefer the scan commit SHA over the
branch name in blob URLs.

### Closed target-branch PRs

For OCA module renames/replacements, search closed/merged PRs on the
target branch before falling back to a draft:

```text
https://github.com/OCA/<repo>/pulls?q=is:pr+is:closed+<module>
```

For core modules, use the `odoo/odoo` commit history and PRs. Also search
the old module name and, when the module moved repositories, the target
repository. Read the PR title, body and comments. Phrases such
as "X was Y", "renamed to", "replaced by", "moved to", "no longer needed",
or "full functionality is now in Z" are module-level evidence when they
name both sides.

A PR on the target branch is strong evidence; a PR on an older branch is
context only. Cite the PR first in the note's `Source:` list, then the
commit or OpenUpgrade entry. A closed (not merged) PR is still valid when
its comments explicitly explain the rename/replacement, for example a
module moved to another repository or its functionality was absorbed
elsewhere. If the GitHub API rate-limits, the HTML PR search page is
enough.

### Newest branch without scripts

The 20.0 branch may have no `scripts/<module>` at all. Do not skip the
transition; use git and the target source. `apriori.py` plus the MCA diff
are the starting point.

## 7. Source relevance

An OpenUpgrade link is evidence only when the cited file documents the
element itself.

| Element | Valid evidence |
|---|---|
| module | `apriori.py` `renamed_modules` / `merged_modules`; closed/merged target-branch PR naming the old and new module |
| model | `apriori.py` `renamed_models` / `merged_models`, analysis `obsolete model`, migration script |
| field | analysis line (`renamed to`, `DEL`, `NEW`, type change), field renames in a migration script |
| data | analysis `DEL`/`NEW`/`renamed` XML line, `_renamed_xmlids` / `_deleted_xmlids` / `_deleted_xml_records`, `delete_records_safely_by_xml_id` |
| method | migration script only when it names the method hook; otherwise the Odoo/OCA commit or target-branch source file |

For a module, an `apriori.py` entry or an explicit target-branch PR/commit
is module-level evidence. When an OCA module is absorbed into core, add the
OCA PR/commit that closed it and the `odoo/odoo` commit/source that
provides the replacement; there is no same-name core module to point at.

For a field, require the source **model and field** on the same analysis
line. For data, require the full XML ID; for a model, the exact model
name. For data, quote the exact `DEL ...` line or the XML ID from
`_deleted_xml_records` in the note: citing the whole analysis file is
transition context, not element-specific evidence. A `# DONE:` line in
`upgrade_analysis_work.txt` that names the source and target is valid
element-specific evidence.

For a method, skip `apriori.py` and `upgrade_analysis.txt`; a
pre/post/end migration script is valid only when it names the method hook.
Otherwise cite the Odoo/OCA commit or the target-branch source file.

Verify before citing:

```bash
git -C <openupgrade> show <branch>:<file> | grep -nF "<name>"
```

If the element name is absent, the link is transition context, not
evidence: drop it.

## 8. URLs and extraction

```text
https://github.com/OCA/OpenUpgrade/blob/<branch>/openupgrade_scripts/apriori.py
https://github.com/OCA/OpenUpgrade/blob/<branch>/openupgrade_scripts/scripts/<module>/<version>/<file>
https://github.com/odoo/odoo/blob/<branch>/addons/<module>/<path>
https://github.com/odoo/odoo/blob/<branch>/odoo/addons/<module>/<path>
https://github.com/odoo/odoo/commit/<sha>
https://github.com/OCA/<repo>/blob/<branch>/<path>
https://github.com/OCA/<repo>/commit/<sha>
https://github.com/OCA/<repo>/pull/<number>
```

In the note, order bullets: target-branch PR/commit, OpenUpgrade work note,
migration script, analysis/apriori, module tree. Use the full URL as link
text; no labels. For an OCA module renamed or merged within OCA, use the
OCA repository PR/commit rather than an `odoo/odoo` commit. For an OCA
module absorbed into core, cite the `apriori.py` `merged_modules` entry,
the OCA PR/commit that closed the module, and the `odoo/odoo`
commit/source that provides the replacement.

Extract a module tree at a commit:

```bash
git -C <odoo> archive <scan_commit> addons/<module> |
  tar -x -C /tmp/mca-trees/<module>/<version>
```

Core modules are not always under `addons/`: `base` is under
`odoo/addons/base`, and the 20.0 tree can use `odoo/addons`. The method
scanner auto-detects both prefixes.

## 9. Read-only or partial clones

A `blob:none` or `tree:0` clone on a read-only mount cannot lazily fetch
missing objects. Use a full bare clone, a writable copy with
`objects/info/alternates` removed, or `GIT_OBJECT_DIRECTORY` plus
`GIT_ALTERNATE_OBJECT_DIRECTORIES`.

Before discarding a read-only or partial clone, test `git archive`:

```bash
git -C <odoo> archive <branch> addons/<module> | tar -t | head
```

A clone that fails `git log -S --all` because lazy objects are missing can
still serve `git archive` for its branch tips. The method scanner only
needs `archive`/`cat-file`.

Never modify the user's read-only clones.
