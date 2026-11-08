# AGENTS.md

Conventions for agents working on this repository — its skills and
knowledge base. (The skills themselves target Odoo projects; this file
targets work on the repository itself.)

## Knowledge base style

- Rules are imperative and short, with a one-line rationale when not
  obvious.
- Topic files open with `Rules for ...` and scope themselves with an
  "everything else follows standard Odoo practice" line pointing at
  `versions/<X>.md`.
- Version-specific rules live only in `references/versions/<X>.md`;
  topic files stay version-agnostic. Patterns shared by same-version
  refactoring and version migration live in topic files (e.g.
  `migration-scripts.md`), not under `migrations/`.
- Wrap lines at ~76 chars, and never break inside a backtick span.
- Cross-references use paths relative to `references/` (e.g. `orm.md`,
  `migrations/common-patterns.md`).

## New reference file checklist

Register a new reference file in all three places:

1. `skills/index.json` — the skill's `files` list
2. `references/index.md` — topic table row
3. `skills/odoo-knowledge/SKILL.md` — routing table row

## Skills

- Skills describe workflows (when and how to apply the knowledge); the
  rules themselves live only in the `odoo-knowledge` references — never
  duplicate a rule in a skill.
- A skill's `description` frontmatter is what triggers its selection:
  keep its task keywords current.
