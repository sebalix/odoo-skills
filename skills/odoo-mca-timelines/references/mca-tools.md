# MCA MCP tools

The `odoo-mca` server exposes the tools listed below. The Code Mode
catalog may show only a subset; use `search` with the query `odoo-mca`
to discover them all.

## Tool contracts and gotchas

- **`module_search` takes `name`, not `query`.** Unknown parameters are
  silently ignored and the call returns an unfiltered first page (default
  `limit` 20); `total` is the whole catalogue (tens of thousands of rows).
  Filter with `name`, `version`, `org`, `repository`, `category`, or
  `author`.
- **`module_list_versions` is a hint, not an index.** It can return an
  empty list for a module that exists, stop before the newest version, or
  return duplicate scans for the same version with different manifest
  values. `module_search` and `module_get_details` are the primary
  authority for existence and for `last_scanned_commit`.
- **`module_get_details` can return no `modules` entry (empty or null)
  for an existing module.** It returned none for `repair` 20.0 while
  `module_search` and `code_search_elements` still found the module. It
  returns one entry per repository hosting the module; select the entry
  for the requested repository. If no entry is returned, cross-check
  `module_search` and the code scan before concluding that the module
  disappeared; treat the mismatch as an MCA scan/identity gap.
- **`code_search_elements` matches names with `ilike`.** `user_id` also
  returns `user_ids`; `stock.quant` also returns
  `stock.quantity.history`. Filter by exact identity: `hit.name ===
  source.name` and `hit.model === source.model` for fields/methods;
  `hit.xml_id` (the full XML ID) for data, not the display `name`.
- **`code_create_timeline` returns `{timeline: {id, state}}`** on success
  and `{error: ...}` otherwise. The id/state are not at the top level.
- **Data `next_name` can be ambiguous across later versions.**
  `code_create_timeline` then fails with “Several data records match …
  Specify `next_module`”; pass `next_module` explicitly even when the full
  XML ID also contains the target module.
- **Run the same-module gate before `confirm=True`.** The detection recipe
  and classification table are in `audit-report.md`. Confirmed
  timelines cannot be retargeted or deleted through the MCP tools.
- **`code_list_timelines` returns the note and, in current builds, a
  `next` target reference.** Use it to deduplicate and to compare the
  intended target, but still call `code_get_next_version_element` to
  verify that a confirmed timeline actually resolves.
  `code_get_element_lineage` follows the full chain; use
  `code_get_element_history` for the timeline-linked steps.
- **The note is sanitized.** A `<br/>- <a href="...">...</a>` bullet list
  can be flattened on creation (anchors stripped, URL hoisted above
  `Source:`). Use `<ul><li><a href="...">...</a></li></ul>` and read the
  note back after creating it. `code_update_timeline` preserves the
  `<ul>` form.
- **`migration_get_module_status` returns an empty `migrations` list for
  standard modules.** The call still returns an object; check
  `migrations`, not the truthiness of the result. That is normal; it is
  not evidence that no migration happened.

## Repositories and modules

| Tool | Purpose |
|---|---|
| `repo_list_versions` | Odoo versions known to the MCA. |
| `repo_list_repositories` | Organizations, repositories, branches. |
| `module_search` | Search modules by name, version, repo, category, author. |
| `module_list_versions` | All versions of a module across versions/repos. |
| `module_get_details` | Manifest, dependencies, SLOC, URLs, scan commit. |
| `module_get_dependencies` | Direct/recursive dependencies or reverse deps. |

`module_search` arguments:

```text
name            module technical name (ilike)
version         Odoo version
org             organization (e.g. "OCA")
repository      "name" or "org/name"
category        module category
author          module author
limit, offset
```

It returns `total` and `modules[]` with `module`, `version`, `org`,
`repository`, `removed`, `installable`, and the manifest summary.

## Migration

| Tool | Purpose |
|---|---|
| `migration_get_module_status` | Status per migration path. |
| `migration_get_data` | Scan data for a source/target pair. |
| `migration_list_timelines` | Module timelines, draft or confirmed. |
| `migration_create_timeline` | Create a module timeline (draft, or confirmed for high confidence). |
| `migration_update_timeline` | Update a draft module timeline, or annotate a confirmed one (note only). |
| `migration_delete_timeline` | Delete a draft module timeline. |

`migration_list_timelines` returns an empty `timelines` list for standard
Odoo modules: it is populated by OCA migration projects, not by the module
index. An empty list does not mean the module never changed. It is not
paginated; `code_list_timelines` is.

An **OCA timeline** is a module timeline whose source repository is an
OCA repository. An OCA module absorbed into core is recorded as
`replaced` with the core module as `new_module`, even when the module
name disappears (`mail_preview_base` 15.0 -> `mail`, from the 16.0
`apriori.py` `merged_modules` entry). The module status may report
`moved_to_standard` for this case, or `replaced` with `replaced_by` once
the timeline exists; before the timeline it can still say `migrate`, so
use `apriori.py` as the authority.

`migration_create_timeline` arguments:

```text
module          source module
version         source version
new_module      target module (renames/replacements)
timeline_type   "renamed" | "replaced"
note            HTML; tag first; <p>Source:</p><ul><li><a href="URL">URL</a></li></ul>
confirm         create as confirmed (high confidence; Source URL required)
repository      disambiguate when several repos host the module
```

A module timeline supports renames and replacements only: a module with no
successor has no module timeline. The successor is the module named by
`apriori.py` or the rename/merge evidence, even when it is a core module
with a different name.

`starting_version` is derived by the server (the next available Odoo
version after the source module branch). The target module may be first
scanned later than `starting_version`; record that MCA scan gap in the
note instead of treating it as an invalid mapping.

## Code elements

| Tool | Purpose |
|---|---|
| `code_search_elements` | Search models, fields, methods, data. |
| `code_get_element_details` | Full code, JSON, XML for one element. |
| `code_get_next_version_element` | Next version, via confirmed timelines. |
| `code_get_element_history` | Timeline-linked version chain of an element. |
| `code_get_element_lineage` | Full lineage to `to_version` (default: latest), jumping gaps. |
| `code_get_elements_lineage` | Batch lineage for 1-100 elements. |
| `code_list_absent_elements` | Elements absent from the next version (source to-do list). |
| `code_list_timelines` | Code timelines, draft or confirmed. |
| `code_create_timeline` | Create a code timeline (confirmed for high confidence, draft otherwise). |
| `code_update_timeline` | Update a draft code timeline, or annotate a confirmed one (note only). |
| `code_delete_timeline` | Delete a draft code timeline. |

`code_get_element_lineage` arguments:

```text
to_version      target Odoo version (default: latest known)
```

`code_get_elements_lineage` additionally takes `elements` (1-100 element
identities) and a shared `to_version`. It returns `results[]`; each result
carries the input `element`, its `lineage` (same shape as above) and a
per-element `error`.

`code_create_timeline` arguments:

```text
element_type    "model" | "field" | "method" | "data"
version         source version
module          source technical module
model           source model for fields/methods; omit for models and data
name            name, or full XML ID for data
timeline_type   "moved" (rename, replacement, cross-module/model move) | "removed"
next_name       target name/XML ID; omit for a pure move or for removed
next_module     target module; omit if unchanged
next_model      target model for fields/methods; omit if unchanged
note            HTML; tag first; <p>Source:</p><ul><li><a href="URL">URL</a></li></ul>
confirm         create as confirmed for a HIGHLY-CONFIDENT match
                (Source URL required in note); false keeps a draft for a
                LESS-CONFIDENT match
repository      disambiguate when several repos host the module
```

For data, a full `next_name` infers the target module only when the XML ID
is unambiguous across later versions; pass `next_module` otherwise. A
target module named by OpenUpgrade must still be checked against the MCA
scan (the record may have stayed in the source module, or a module rename
may have changed the local XML ID).

`code_create_timeline` returns `{timeline: {id, state, ...}}` on success
and `{error: ...}` otherwise. The id and state are not at the top level.
A draft can later be confirmed with
`code_update_timeline(confirm=True)` once its note carries a source URL.

`code_list_absent_elements` arguments:

```text
module          source module
version         source version
element_type    optional filter
model           optional model filter
data_type       optional data filter: "data" | "demo"
noupdate        optional data filter: true | false
is_override     optional data filter: true | false
timeline_state  optional filter: "none" | "draft" | "confirmed"
timeline_type   optional filter: "moved" | "removed"
repository      disambiguate when several repos host the module
limit           page size (default 50)
offset          pagination offset
```

Data elements are always restricted to records loaded by the module
(`loaded=True`); unloaded records never appear in the list. Setting any
data filter restricts the search to data elements.

It returns `total`, `next_version`, `counts`, and `elements`.

- `total` is the number of elements matching all filters, including the
  timeline filters, before pagination.
- `counts` gives the current distribution over `uncovered`, `draft`,
  `removed` and defensive `moved`. It is computed from the timeline objects
  before the timeline filters, so it still shows the full distribution when
  a timeline filter is used. Confirmed `moved` elements leave the absent
  list, so `counts.moved` normally stays at 0; do not use it as a progress
  metric. Measure progress with the drop in `total`.
- Each element carries `element_type`, `module`, `version`, `model`, `name`
  (full XML ID for data), `org`, `repository`, and `timeline`:
  - `timeline=null`: no timeline, to analyze;
  - `timeline.state="draft"`: a draft timeline exists, pending
    review;
  - `timeline.type="removed"` with `timeline.state="confirmed"`: a
    confirmed removal, intentionally still listed.
  - `timeline` also carries `id` and `target` (the target element for a
    move, confirmed or proposed).
- Data elements also carry `data_type` (`data` / `demo`), `noupdate`,
  `is_override`, and `overridden_xml_id`.
- Model elements carry `next_defined_in`, the modules defining the same
  model in the next version.

`code_list_timelines` arguments:

```text
module          optional source module
version         optional source version
element_type    optional filter
state           optional filter: "draft" | "confirmed"
timeline_type   optional filter: "moved" | "removed"
repository      optional repository
limit           page size (default 50)
offset          pagination offset
```

It returns `total` and `timelines`; page with `limit`/`offset` until
`offset + len(timelines) >= total`. The list exposes the source identity,
`element_type`, `timeline_type`, `state`, `note`, and (in current builds)
a `next` target reference. Still verify the target with
`code_get_next_version_element` rather than relying on the list alone:
only a confirmed timeline actually resolves, and a draft reports its
target without changing the element state. For a chain, use
`code_get_element_history` or `code_get_element_lineage`.

For data timelines, `model` is the record model (e.g. `ir.ui.view`) and
`name` is the **full XML ID** (e.g. `project.assets_backend`). Do not pass
the concatenated display form as the element identity.

In `code_search_elements`, a data element has two identifiers:
`name` is the **display name** (it may equal the local XML ID for
views/actions, but for records such as access rules it is a human label
like `Administrators can access all User Settings.`) and `xml_id` is the
**full** XML ID (`product.report_simple_label2x7`). Build lookup indexes
from `xml_id`, never from `name`, when comparing against a timeline.

## Element identity

| Type | Identity |
|---|---|
| `model` | model name (`stock.move`) |
| `field` | `model` + field name (`stock.move.product_uom`) |
| `method` | `model` + method name (`stock.move._action_assign`) |
| `data` | full XML ID (`stock.access_stock_lot_user`) |

## Semantics to remember

- `code_search_elements` accepts a high `limit`; 2000–3000 returns the
  full set for a module. Use it once per version and type, then work in
  memory. For data elements, the `name` filter matches the display name,
  the local XML ID and the full XML ID. The name filter is `ilike`: always
  filter by exact identity (name/model for code elements, `xml_id` for
  data). The returned `name` is the display name; compare data identities
  with `xml_id`.
- **The MCA note is sanitized.** Use
  `<p>...</p><p>Source:</p><ul><li><a href="URL">URL</a></li></ul>`.
  The tool schema text suggests `<br/>Source:<br/>- <a>...`, but a
  `<br/>- <a>` list can be flattened on creation (anchors stripped, URL
  moved above `Source:`), so read the note back after creating a timeline
  and rewrite it with `code_update_timeline` if needed.
- `code_get_element_details` returns the details under `element`:
  `fields[]`/`methods[]`/`inherit` for a model, `code` for
  fields/methods, and `data_json`/`data_xml` for data. For data, it also
  reports `data_type`, `noupdate`, `loaded`, `is_override`, and
  `overridden_xml_id`. A model's `fields[]`/`methods[]` cover that
  module's model element, so call it per `(module, model)` rather than
  assuming it aggregates every extension.
- `code_list_absent_elements` is the primary source-side inventory. It
  resolves through confirmed module/code timelines: a draft module
  timeline does not move the source elements to the successor module. It
  returns only elements absent from the next version; elements whose next
  version is not scanned are excluded (use
  `code_get_next_version_element`'s `state="unknown"` to detect that
  case). Its `next_version` is the next global Odoo version, not
  necessarily the module's next available version.
- Start from `timeline_state="none"`. A confirmed `moved` timeline
  removes the element from the list; a confirmed `removed` stays listed
  with `timeline.type="removed"`; a draft stays listed with
  `timeline.state="draft"`. Use `timeline_state="draft"` to
  review proposals and `timeline_type="removed"` to report confirmed
  removals.
- Data elements are always restricted to loaded records. Classify them
  with the filters and output fields:
  - `is_override=True`: an override of another module's record, report
    an extension removal;
  - demo (`data_type="demo"`) or noupdate (`noupdate=True`): may be
    matched when explicit deletion, rename or move evidence exists;
  - structural records (`data_type="data"`, `noupdate=False`,
    `is_override=False`): normal matching;
  - population/reference records (country, state, language, currency,
    chart templates, tax/report lines): report the dataset;
  - UoM records/categories are structural: keep per-record timelines when
    the evidence exists.
- For model elements, a non-empty `next_defined_in` means the model still
  exists in another module (typically `base`). If the source element is
  an extension (`inherit` non-empty), report an extension removal, not a
  model removal. If the source owns the model (`inherit: []`), treat it
  as a cross-module model move and verify the target module.
- `code_get_element_details` on a model returns `inherit` and `inherits`.
  A non-empty `inherit` means this module element is an extension; see the
  pre-confirm gate in `audit-report.md` before targeting another module.
  `inherits` lists the delegated models.
- `code_get_next_version_element` and `code_search_elements` resolve the
  actual target; use them on the target version rather than assuming
  `next_version`.
- `code_get_next_version_element` follows confirmed timelines only:
  `state="available"` means resolved, `state="absent"` with `next=null`
  means no confirmed link, and `state="unknown"` means the next
  version/branch is not scanned. Its `timeline` reports the linked
  timeline; a draft timeline has `timeline.state="draft"` and
  `timeline.target`, but `next` remains null. Use it to deduplicate or
  review, never as a confirmed link.
- `code_get_element_lineage` walks the full chain to a target version
  (`to_version`, default latest known). It follows same-name
  continuations, confirmed timelines and module/model lineage, and jumps
  versions missing from the MCA. Version jumps are gaps, not removals. It
  returns `start`, `target_version` and `steps[]`, each step with an
  element and its outgoing timeline. Use it to report an element's
  evolution; use `code_get_elements_lineage` to batch 1-100 elements.
- Drafts are not applied to the analysis. Only confirmed timelines are
  followed by `code_get_next_version_element`, the migration analysis,
  and the absent list's timeline state.
- `code_list_timelines` is paginated (default 50 rows). Page to `total`
  before deduplicating; use `state`, `timeline_type` and `element_type`
  to narrow the listing. `migration_list_timelines` returns all matching
  module timelines and has no `total`/pagination.
- `confirm=True` requires a Source URL and is one-way. Confirm only
  high-confidence evidence; keep LESS-CONFIDENT matches as drafts.
  Confirmed timelines can only be note-annotated.
- Before creating, verify the target and the source in the MCA (see SKILL
  Step 7). `code_create_timeline` does not enforce source absence.
- `code_create_timeline` accepts `next_module`/`next_model`; use `moved`
  when the target exists, `removed` only when it does not.
- `repository` is required when several repositories host the source
  module. Cross-repository targets are rejected unless they are reached
  through a confirmed module rename/replacement timeline.

## Update or annotate timelines

Both update tools accept the source identity plus the fields to change.
Pass only `note` to annotate a draft, or a confirmed timeline (note-only;
HTML + Source URL required) without touching the rename. On a confirmed
timeline, pass **only** `note`, the source identity and `repository`:
including `timeline_type`, `next_name`, `next_module` or `next_model` —
even with the existing value — is rejected with “only its note can be
updated”. A draft timeline can be confirmed with `confirm=True` once the
note carries a Source URL. Once confirmed, semantic fields cannot be
modified. For code elements, confirm HIGHLY-CONFIDENT matches and keep
LESS-CONFIDENT matches as drafts for human review.

```text
code_update_timeline(element_type=..., version=..., module=...,
                     model=..., name=..., repository=...,
                     next_module=..., next_model=...,
                     note=(
                       '<p><existing note></p><p>Source:</p><ul>'
                       '<li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>'
                       '<li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>'
                       '</ul>'
                     ))

migration_update_timeline(module=..., version=..., repository=...,
                          note=(
                            '<p><existing note></p><p>Source:</p><ul>'
                            '<li><a href="<ODOO_COMMIT_URL>"><ODOO_COMMIT_URL></a></li>'
                            '<li><a href="<OPENUPGRADE_URL>"><OPENUPGRADE_URL></a></li>'
                            '</ul>'
                          ))
```

Deduplicate the `Source:` suffix: check the current note first.
