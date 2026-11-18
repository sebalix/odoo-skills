# MCA MCP tools

The `odoo-mca` server exposes the tools listed below. The Code Mode
catalog may show only a subset; use `search` with the query `odoo-mca`
to discover them all.

## Tool contracts and gotchas

- **`module_search` takes `name`, not `query`.** Unknown parameters are
  silently ignored and the call returns the whole catalogue (tens of
  thousands of rows). Filter with `name`, `version`, `org`, `repository`,
  `category`, or `author`.
- **`module_list_versions` is a hint, not an index.** It can return an
  empty list for a module that exists, stop before the newest version, or
  return duplicate scans for the same version with different manifest
  values. `module_search` and `module_get_details` are the authority for
  existence and for `last_scanned_commit`.
- **`code_search_elements` matches names with `ilike`.** `user_id` also
  returns `user_ids`; `stock.quant` also returns
  `stock.quantity.history`. Always filter hits with
  `hit.name === source.name` and, for fields/methods,
  `hit.model === source.model`.
- **`code_create_timeline` returns `{timeline: {id, state}}`** on success
  and `{error: ...}` otherwise. The id/state are not at the top level.
- **`code_list_timelines` returns the note but not the resolved target
  fields.** It is enough to audit notes; use
  `code_get_next_version_element` or `code_get_element_history` to verify
  what a timeline actually resolves to.
- **The note is sanitized.** A `<br/>- <a href="...">...</a>` bullet list
  can be flattened on creation (anchors stripped, URL hoisted above
  `Source:`). Use `<ul><li><a href="...">...</a></li></ul>` and read the
  note back after creating it. `code_update_timeline` preserves the
  `<ul>` form.
- **`migration_get_module_status` returns `[]` for standard modules.**
  That is normal; it is not evidence that no migration happened.

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

`migration_list_timelines` returns `[]` for standard Odoo modules: it is
populated by OCA migration projects, not by the module index. An empty
list does not mean the module never changed.

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
successor has no module timeline.

`starting_version` is derived by the server (the next available Odoo
version after the source module branch).

## Code elements

| Tool | Purpose |
|---|---|
| `code_search_elements` | Search models, fields, methods, data. |
| `code_get_element_details` | Full code, JSON, XML for one element. |
| `code_get_next_version_element` | Next version, via confirmed timelines. |
| `code_get_element_history` | Timeline-linked version chain of an element. |
| `code_get_element_lineage` | Full version lineage, jumping missing versions and scans. |
| `code_get_elements_lineage` | Batch version lineage for several elements. |
| `code_list_absent_elements` | Elements absent from the next version (source to-do list). |
| `code_list_timelines` | Code timelines, draft or confirmed. |
| `code_create_timeline` | Create a code timeline (confirmed for high confidence, draft otherwise). |
| `code_update_timeline` | Update a draft code timeline, or annotate a confirmed one (note only). |
| `code_delete_timeline` | Delete a draft code timeline. |

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
  a timeline filter is used.
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
`element_type`, `timeline_type`, `state`, and `note`; it does **not**
expose the resolved `next_name`/`next_module`/`next_model`. Verify the
target with `code_get_next_version_element` (or
`code_get_element_history`) rather than reading it from this list.

For data timelines, `model` is the record model (e.g. `ir.ui.view`) and
`name` is the **full XML ID** (e.g. `project.assets_backend`). Do not pass
the concatenated display form as the element identity.

In `code_search_elements`, a data element has two identifiers:
`name` is the **local** XML ID (`report_simple_label2x7`) and `xml_id` is
the **full** XML ID (`product.report_simple_label2x7`). Build lookup
indexes from `xml_id`, not `name`, when comparing against a timeline.

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
  apply an exact-name (and exact-model) filter to the result.
- **The MCA note is sanitized.** Use
  `<p>...</p><p>Source:</p><ul><li><a href="URL">URL</a></li></ul>`.
  A `<br/>- <a>` list can be flattened on creation (anchors stripped, URL
  moved above `Source:`), so read the note back after creating a timeline
  and rewrite it with `code_update_timeline` if needed.
- `code_get_element_details` returns `code` for fields/methods and
  `data_json`/`data_xml` for data. Use it for similarity checks. For data,
  it also reports `data_type`, `noupdate`, `loaded`, `is_override`, and
  `overridden_xml_id`.
- `code_list_absent_elements` is the primary source-side inventory. It
  resolves through confirmed module/code timelines: a draft module
  timeline does not move the source elements to the successor module. It
  only returns `absent` states (`unknown` means the next version or
  repository branch is not scanned), and its `next_version` is the next
  global Odoo version, not necessarily the module's next available
  version.
- Start from `timeline_state="none"`. A confirmed `moved` timeline
  removes the element from the list; a confirmed `removed` stays listed
  with `timeline.type="removed"`; a draft stays listed with
  `timeline.state="draft"`. Use `timeline_state="draft"` to
  review proposals and `timeline_type="removed"` to report confirmed
  removals.
- Data elements are always restricted to loaded records. Classify them
  with the filters and output fields:
  - `data_type="demo"`: report only;
  - `is_override=True`: an override of another module's record, report
    an extension removal;
  - `noupdate=True`: existing databases keep the record; report it
    unless explicit deletion, rename or move evidence exists;
  - structural records: `data_type="data"`, `noupdate=False`,
    `is_override=False`.
- For model elements, a non-empty `next_defined_in` means the model still
  exists in another module (typically `base`): report an extension
  removal, not a model removal.
- `code_get_element_details` on a model returns `inherit`. A non-empty
  `inherit` means this module element is an extension. When a model is
  renamed, target the same module's element of the new model when it
  exists, not the base model in another module; a non-empty `inherit`
  makes this mandatory. `references/timeline-audit.md` has the detection
  recipe.
- `code_get_next_version_element` and `code_search_elements` resolve the
  actual target; use them on the target version rather than assuming
  `next_version`.
- `code_get_next_version_element` follows confirmed timelines only:
  `state="absent"` and `next=null` mean no confirmed link. Its `timeline`
  reports the linked timeline; a draft timeline has
  `timeline.state="draft"` and `timeline.target`, but `next`
  remains null. Use it to deduplicate or review, never as a confirmed
  link.
- `code_get_element_lineage` walks the full chain to a target version. It
  follows same-name continuations, confirmed timelines and module/model
  lineage, and jumps versions missing from the MCA. Version jumps are
  gaps, not removals. Use it to report an element's evolution; use
  `code_get_elements_lineage` to batch several elements.
- Drafts are not applied to the analysis. Only confirmed timelines are
  followed by `code_get_next_version_element`, the migration analysis,
  and the absent list's timeline state.
- `code_list_timelines` is paginated (default 50 rows). Page to `total`
  before deduplicating; use `state`, `timeline_type` and `element_type`
  to narrow the listing.
- Every create/update tool accepts `confirm=True` with a Source URL.
  Confirm a high-confidence module rename/replacement when the evidence
  is explicit: it activates the module lineage used by
  `code_list_absent_elements`. Confirm a code timeline when the match is
  HIGHLY-CONFIDENT (explicit OpenUpgrade/commit evidence, or identical
  normalized code/data with a unique structural match); keep
  LESS-CONFIDENT matches as drafts for human review.
- Confirmed timelines can have their note updated through the MCP tools
  (note-only, HTML, Source URL required). Their semantic fields cannot be
  modified and they cannot be deleted. Create a module timeline confirmed
  only when the evidence is explicit; create a code timeline confirmed
  only for a HIGHLY-CONFIDENT match.
- The MCA only checks that a note carries a source URL; it does not check
  that the URL documents the element. Source relevance is the agent's
  responsibility: see the source relevance check in `SKILL.md`.
- `code_create_timeline` accepts `next_module`/`next_model` for a
  cross-module or cross-model move. The target is still stored as a record
  reference; `code_list_timelines` and `code_get_element_history` expose
  the target module/model. Do not use `removed` when the target exists.
- Before creating a timeline, verify the target with
  `code_search_elements` on the actual target version/module/model. A
  target that exists only in the source tree is a scan gap: report it and
  skip the creation. This is mandatory for methods, whose evidence is the
  target source/commit.
- Also verify the **source is absent** from the target version by searching
  the target for the source name/XML ID. `code_create_timeline` does not
  enforce this: a source that still exists produces an invalid move. A
  confirmed invalid timeline must be deleted in the MCA UI.
- A pre-existing confirmed timeline may already have resolved its element
  and therefore be invisible in `code_list_absent_elements`. Page
  `code_list_timelines` to `total` before creating anything.
- A merge (several sources -> one target) uses one `moved` timeline per
  source, all with the same target. A true split (one source -> several
  targets) keeps one primary target and explains the others in the note.
- `repository` is required when several repositories host the source
  module. Cross-repository targets are rejected.

- **Duplicate scans and access rights.** Several scans can exist for one
  version; take the scan commit from `module_get_details`. When the target
  replaces `ir.model.access` with `ir.access` (20.0), treat the access
  records as one model migration and report them; do not map each old XML
  ID to a guessed new one.

## Update or annotate timelines

Both update tools accept the source identity plus the fields to change.
Pass only `note` to annotate a draft, or a confirmed timeline (note-only;
HTML + Source URL required) without touching the rename. A draft timeline
can be confirmed with `confirm=True` once the note carries a Source URL.
Once confirmed, semantic fields cannot be modified. For code elements,
confirm HIGHLY-CONFIDENT matches and keep LESS-CONFIDENT matches as
drafts for human review.

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
