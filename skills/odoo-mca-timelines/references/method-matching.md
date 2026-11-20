# Method matching

Methods are the one element type with no OpenUpgrade evidence:
`apriori.py` and `upgrade_analysis.txt` never list them, and the
pre/post-migration scripts only mention a method when a migration hook
happens to be named after it. Run a separate method pass; do not infer
method renames from field renames.

The pass is deliberately conservative. On a typical large module only a
small percentage of absent methods are renames; most disappear with a
model, a wizard or a feature. Classify first, compare second, create last.

## Inputs

- The module, repository and transition (`source` -> `target`).
- The exact **scan commits** from `module_get_details`
  (`last_scanned_commit`), not branch HEAD.
- The absent-method list from `code_list_absent_elements`
  (`element_type="method"`, `timeline_state="none"`), as JSON: a list of
  `{model, name}` or the tool's `{elements: [...]}` payload.
- Optionally a model map for confirmed model moves:
  `{"old.model": {"next_module": "target_module", "next_model": "new.model"}}`.
  The map is keyed by model name and applies to the module being scanned.

## Exporting absent methods for the helper scripts

The helper scripts need one JSON file per transition. When the MCA server
is remote, its MCP HTTP endpoint can be called directly with `tools/call`
and the `structuredContent.elements` payload saved as
`{"elements": [...]}`. This makes a multi-transition batch practical:

```text
POST <MCA_URL>
Authorization: Bearer <TOKEN>
Content-Type: application/json

{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{"name":"code_list_absent_elements",
           "arguments":{"module":"payment","version":"15.0",
                        "repository":"odoo/odoo",
                        "element_type":"method","limit":1000}}}
```

Skip transitions where the module does not exist in the target version
(module rename/merge); the module timeline covers those. Keep the exact
`last_scanned_commit` when available, but branch names still work for
`git archive` when the local clone lacks the scan commit.

`batch_method_scan.py` writes one `<module>_<source>_<target>.json` per
transition plus a `batch_summary.json` that contains only the per-transition
`out` path and status counts. The candidates are in the per-transition
files, not in `batch_summary.json`.

## Step 1 — classify by model

For each absent method, resolve its model in the target version:

| Model situation | Action |
|---|---|
| Model removed, no successor | report (`model_removed`); no method timeline |
| Model moved by a **confirmed** model timeline | target model is the timeline target; same-name methods are already covered; only name-changed methods are candidates |
| Model exists under the same name | candidate for comparison |
| The module no longer defines the model, but the model exists in another module | report `extension_model_removed`; do not create a method removal |
| Model exists only as an extension in another module | report an extension removal, no method removal |

A method can also move to **another model** in the same module or to a
**base module** that owns the model. The scanner only compares the same
model by default; run it with `--search-all-models` to see cross-model
candidates and `--search-modules` to include the base module. Treat a
cross-model/cross-module match as a draft unless an explicit commit
confirms it.

Model extraction is a common case: a new mixin receives methods from the
old model (`mail.alias.mixin` -> `mail.alias.mixin.optional`,
`mail.thread` -> `mail.track.mixin`). Set `next_model` to the new mixin and
cite the extraction commit.

Use `code_get_next_version_element(element_type="model", ...)` and
`code_search_elements` for this. Do not compare against a model that no
longer exists.

Run the method pass on the **remaining** methods after the model timelines
are confirmed: model lineage already resolves same-name methods on
renamed/moved models. Scanning before that produces a large
`model_removed` bucket that is really covered by the model migration.

When the source model is renamed or merged, resolve the target model in
the source module first. If it exists there, use it; only fall back to the
base model when the source module has no target element. A non-empty
`inherit` (`code_get_element_details`) makes this mandatory for an
extension. The same rule applies to the method's `next_model` in a
timeline.

## Step 2 — parse the exact scanned trees

Extract the module at the scanned commit:

```bash
git -C <odoo> archive <scan_commit> addons/<module> |
  tar -x -C /tmp/mca-trees/<module>/<version>
```

Parse each Python file with `ast`:

- walk top-level `ClassDef` nodes;
- read `_name` and `_inherit` to map the class to one or more models;
- collect `FunctionDef`/`AsyncFunctionDef` at class level;
- record file, line and the function AST.

Branch HEAD can contain later changes; it will produce false matches and
false misses.

## Step 3 — normalize and compare

For each method:

1. Deep-copy the function node and set its name to `<NAME>`.
2. Serialize with `ast.unparse` so formatting and comments are folded.
3. Collapse trailing whitespace.
4. Compare against every target method on the same target model with
   `difflib.SequenceMatcher`.
5. Keep the best candidate by body ratio, then by name ratio.

A method can be defined in several classes/files (inheritance). Compare
all source definitions and take the best pair; do not stop at the first
one.

## Step 4 — classify

| Status | Rule | Action |
|---|---|---|
| `exact` | body ratio >= 0.999, unique target, **and** a meaningful name relation or explicit commit | `[HIGHLY-CONFIDENT]`, create confirmed |
| `exact_unrelated_name` | body ratio >= 0.999 but name ratio below the threshold | report/review; confirm only with a commit |
| `target_exists_in_source` | the candidate name already exists in the source version | review; confirm only with a commit that documents the semantic replacement |
| `similar` | body ratio >= 0.92 | `[LESS-CONFIDENT]`, create draft |
| `weak` | body ratio >= 0.80 | report only |
| `no_match` | below 0.80 | report only (removed/refactored) |
| `model_removed` | target module no longer defines the model and the source owned it | report only |
| `extension_model_removed` | target module no longer defines the model, but the source definitions are `_inherit` extensions | report the extension removal |
| `same_name_exists` | target method with the same name exists | MCA scan/identity gap; do not create |
| `ambiguous` | several target names share a >= 0.999 body | report; inspect manually |
| `no_candidate` | target model has no methods at all | report only |
| `source_not_parsed` | source definition not found by the parser | report and inspect manually |

`exact` is not enough on its own: see the false-positive guards below.
For `similar`, require a unique best candidate (no other target within
0.02 of the best body ratio) and a meaningful name relation; otherwise
report instead of drafting.

## Step 5 — false-positive guards

Reject candidates even at ratio 1.0 when:

- the body is a trivial one-liner (`return True`, `return False`, `pass`);
- the body is a parallel implementation for another field or model —
  e.g. `_can_edit_name` vs `_can_edit_country`;
- it is a template hook that differs only by the template model —
  e.g. `_get_account_group` vs `_get_account_tax_group`;
- it is a generic CRUD method (`create`, `write`, `unlink`, `name_get`,
  `search_read`, …) without an explicit rename commit;
- the body matches but the semantics changed — e.g.
  `_should_force_price_unit` (`return False`) vs `_get_aml_value`
  (`return self.value`);
- the target method is not present in the MCA target scan;
- the target name already exists as a sibling in the source version **and
  no commit documents the replacement** — e.g. `_inverse_is_favorite` vs
  `toggle_favorite`, where `toggle_favorite` already existed;
- the body is identical but the name is unrelated and no commit confirms
  the rename (`exact_unrelated_name`).

A one-line method that is a clear field-following rename
(`_compute_currency` -> `_compute_currency_id`) is still valid; judge the
name and the field history, not only the length.

## Step 6 — mine explicit renames

The body comparison cannot find renames whose implementation changed
substantially. Search commit messages and diffs:

```bash
git -C <odoo> log --oneline <source>..<target> -- addons/<module> |
  grep -iE '\[(REN|MOV)\]|rename' |
  grep -iE 'method|function|helper|compute|onchange|hook'

git -C <odoo> log --reverse --format='%h %s' -S '<old_method>' \
  <source>..<target> -- addons/<module>/models addons/<module>/wizard
```

`git log -S` also matches translation files and calls; restrict the path
to `models`/`wizard`, filter `[I18N]`, and inspect the diff for a removed
`def old` and an added `def new`. A commit that renames a wizard method is
evidence even when the body changed.

Do not cite `apriori.py` or `upgrade_analysis.txt` for a method. Cite the
commit, or the target-branch source file when the body is identical and
unique.

## Step 7 — target check and creation

Before `code_create_timeline`:

1. Search the target method in the MCA with `code_search_elements` on the
   actual target version/module/model. Filter the hit by exact name and
   model. The scanner's `candidate_module`/`target_module` is **not**
   authoritative: class inheritance can attribute a method to `base` or to
   another module (e.g. `_sms_get_number_fields` reported as `sms/base`
   while the MCA target is `sms/mail.thread.phone`, and
   `_phone_get_country_field` reported as `base/mail.thread` while the MCA
   target is `phone_validation/mail.thread.phone`). Use the module/model
   that actually defines the target in the MCA.
2. If it is absent, report "target not in MCA scan" and skip.
3. Create a `moved` timeline with `next_name` (and `next_model` when the
   method moved to another model).
4. Use `confirm=True` only for `exact` + unique + non-trivial **and** a
   meaningful name relation or an explicit commit; keep `similar` matches
   as drafts. An `exact_unrelated_name` result is report-only unless a
   commit confirms it. A `target_exists_in_source` result is confirmable
   when the note cites a commit that documents the source's retirement.
5. For a cross-model move, set `next_model`; for a cross-module move, set
   `next_module`. The model lineage alone is not enough when the method
   name changed.

## Helper script

`scripts/method_scan.py` implements steps 1–4:

```bash
python3 scripts/method_scan.py \
  --repo /path/to/odoo \
  --module account \
  --source-version 15.0 \
  --target-version 16.0 \
  --source-commit <scan_sha> \
  --target-commit <scan_sha> \
  --absent-methods /tmp/absent_methods.json \
  --out /tmp/method_candidates.json
```

Core modules are not always under `addons/`: `base` lives under
`odoo/addons/base`, and the 20.0 core tree uses `odoo/addons`. The script
auto-detects both prefixes. For a large module such as `base` or `mail`,
run the scanner per transition or in the background; each transition
writes its own JSON, and the tree cache can grow to hundreds of MB
(use a dedicated `--cache-dir`).

Optional:

- `--model-map /tmp/models.json` for confirmed model moves;
- `--commits /tmp/commits.json` for target modules whose scan commit
  differs from the branch name (`{"module": {"version": "sha"}}`);
- `--min-ratio 0.92` (default) and `--include-weak`;
- `--cache-dir /tmp/mca-method-cache` to reuse parsed trees;
- `--github-repo odoo/odoo` and `--target-ref` to emit source URLs;
- `--search-all-models` to also compare against other models in the
  target module (cross-model moves such as
  `project.task.action_create_invoice` ->
  `project.project.action_create_invoice`);
- `--search-modules stock_account,account` to also search base modules
  for an extension method;
- `--min-name-ratio 0.5` to flag exact bodies with unrelated names as
  `exact_unrelated_name` instead of `exact`;
- `--flag-target-existing-in-source` (formerly
  `--reject-target-existing-in-source`) to report a candidate that already
  exists as a sibling in the source version as `target_exists_in_source`.
  The status is advisory: confirm it only with a commit that documents the
  semantic replacement.

`scripts/batch_method_scan.py` runs the scanner for several transitions in
one go. It reads a JSON config:

```json
{
  "repo": "/path/to/odoo",
  "scan_commits": {"project": {"14.0": "<sha>", "15.0": "<sha>"}},
  "transitions": [
    {"module": "project", "source": "14.0", "target": "15.0",
     "absent": "/tmp/absent_methods/project_14.0.json"}
  ],
  "out_dir": "/tmp/method_candidates"
}
```

```bash
python3 scripts/batch_method_scan.py --config /tmp/method_batch.json
```

The script outputs `exact`, `exact_unrelated_name`,
`target_exists_in_source`, `similar`, `weak`, `no_match`,
`model_removed`, `extension_model_removed`, `same_name_exists`,
`ambiguous`, `no_candidate` and `source_not_parsed` records with the
source/target file, line, body ratio, signature ratio and name ratio. The summary always counts every status;
`weak` and `no_match` records are only written with `--include-weak` and
`--include-no-match`.

## Expected yield

On four standard modules across 14.0–20.0, 1,252 uncovered methods yielded
17 exact and 25 similar matches. The rest were removals or refactors. This
is normal: a method pass is a precision tool, not a completeness tool.
Report the classification counts and the rejected false positives so a
reviewer can see why the remaining methods were not drafted.

A second run on `project`, `sale_project`, `sale_mrp` and `purchase_mrp`
(14.0–20.0) scanned 259 methods. Without the guards it produced 3 exact,
13 similar, 14 on removed or extension models, 14 weak, and 215 no-match.
The exact set contained a false positive (`_inverse_is_favorite` ->
`toggle_favorite`, where the target already existed in the source). With
`--search-all-models --min-name-ratio 0.5
--flag-target-existing-in-source` the same run produced 2 exact, 14
similar, 1 `target_exists_in_source`, 6 `model_removed`, 8
`extension_model_removed`, 16 weak, and 212 no-match. The cross-model
search found one additional real move
(`project.project._compute_rating_request_deadline` ->
`project.task.type._compute_rating_request_deadline`), and the guard
surfaced the false exact match.

`target_exists_in_source` is advisory. Six confirmed method moves to
pre-existing targets were reviewed and accepted because their commits
document the semantic replacement; the guard remains useful for the case
without such a commit.

A third run on `base` and `mail` (14.0–20.0) scanned 1,094 methods: 30
exact, 47 similar, 2 ambiguous, 59 weak, 734 no-match, 113
`model_removed`, 9 `extension_model_removed`, and 100
`source_not_parsed`. After the model timelines, 32 commit-backed method
timelines were created; the remaining exact/similar candidates were left
as a review queue because they lacked an explicit commit or were
cross-model parallel implementations. The `base` run also needs the
`odoo/addons` prefix handling described above.

A 23-module run (14.0–20.0, 90 executable transitions) classified 1,212
absent methods: 17 exact, 33 similar, 1 `exact_unrelated_name`, 1
`target_exists_in_source`, 3 ambiguous, 98
`extension_model_removed`, 170 `model_removed`, 836 no-match, and 53
weak. It produced 25 method timelines (7 confirmed, 18 drafts). Most of
the remaining exact/similar hits were same-name scan gaps, generic CRUD
methods, ambiguous multi-candidates, or cross-model mixin extractions
that needed review.
