# odoo-skills

Consolidated best practices for Odoo development, structured for consumption by
AI coding agents (OpenCode skills, agent context, reviews, audits).

Design principles:

- **Single source of truth**: all knowledge lives in the `odoo-knowledge`
  skill (`skills/odoo-knowledge/references/`). The task skills delegate to it;
  they never duplicate rules.
- **Skills = workflows**: task skills describe *when and how* to apply
  knowledge for a specific task. Knowledge itself lives only in
  `odoo-knowledge`.
- **Versioned knowledge**: version-specific rules live in
  `skills/odoo-knowledge/references/versions/`. Common-to-all-versions rules
  live in the topic files.

## Layout

```text
skills/
├── index.json              HTTP catalog manifest
├── odoo-knowledge/         Shared knowledge base — router + references
│   └── references/         Topic files, migrations/, versions/
├── odoo-review/            Everyday code/PR review workflow
├── odoo-review-oca-migration/  OCA migration/port PR review workflow
├── odoo-audit/             Project audit workflow + report templates
└── odoo-migrate/           Migration knowledge companion
```

## Configuration

### OpenCode

Add to `~/.config/opencode/opencode.json` (or the project `opencode.jsonc`):

```jsonc
{
  "$schema": "https://opencode/config.json",
  "skills": ["~/path/to/odoo-skills/skills"]
}
```

Adjust the path to wherever this repo lives. Every discovered config's
`skills` array entries are combined, so this can be added alongside existing
entries.

### Optional: `odoo-auditor` subagent profile

The `odoo-audit` skill runs one subagent per module (up to 4 in parallel).
For a dedicated profile, copy `agents/odoo-auditor.md` to
`.opencode/agents/odoo-auditor.md` (project) or
`~/.config/opencode/agents/odoo-auditor.md` (global, OpenCode V2). The
skill picks it up automatically when present and falls back to a
general-purpose subagent otherwise.

### Frontmatter metadata

The `compatibility` and `metadata` fields in each skill's frontmatter are
advisory: OpenCode accepts them but does not interpret them, and other
coding agents ignore unknown fields. The skill bodies remain the source of
truth for behavior.

### Ensuring the knowledge base is always loaded

Skill activation is model-driven. To guarantee `odoo-knowledge` is loaded for
every Odoo task, add this rule to the `AGENTS.md` of each project where you
develop on Odoo:

```md
## Odoo development

Any task that touches Odoo code (models, fields, views, manifests, security
files, data files, tests, migrations) must start by loading the `odoo-knowledge`
skill and reading the reference file for each area involved.
```

### Local Odoo sources (optional)

It is recommended to have the Odoo versions you work with cloned somewhere on
your workstation, one branch per directory, e.g.:

```text
~/dev/odoo/
├── odoo-17/
├── odoo-18/
├── odoo-19/
└── odoo-20/
```

This lets the agent browse the actual Odoo source code (ORM internals, field
semantics, addons code) directly instead of fetching it from the web, and
compare the same file between versions. This is especially valuable for
migration tasks, where having both the source and target versions locally
allows direct comparison of the code.

Declare the clones in your global agent configuration (e.g. in
`~/.config/opencode/AGENTS.md` for OpenCode) so that every session knows
they exist, adjusting the path to wherever you cloned them:

```md
## Odoo sources

Read-only clones of Odoo (odoo/odoo) are available under `~/dev/odoo/`, one
directory per version (e.g. `odoo-17` = branch 17.0). When a task requires
reading Odoo core source, read it from the clone of the relevant version
instead of fetching from the web. These clones are read-only: never modify
or commit in them.
```

## Maintenance rules

1. Every rule is written once, in `skills/odoo-knowledge/references/`. If a
   skill needs it, the skill delegates to `odoo-knowledge`.
2. Version-specific rules go in `references/versions/<X>.md`, never inline in
   topic files.
3. When a practice is learned (review finding, migration surprise, bug
   post-mortem), propose to record it in the matching reference file.
