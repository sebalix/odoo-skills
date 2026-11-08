# Module Structure

Rules for creating and reviewing Odoo modules: layout, manifest, naming,
dependencies, and how to split code across modules.

## Layout

Canonical layout:

```text
my_module/
├── __init__.py              ← imports models/, controllers/, wizards/, report/
├── __manifest__.py
├── hooks.py                 ← {pre,post}_init_hook / uninstall_hook entry points
├── models/                  ← one file per model, named after the model
│   └── res_partner.py
├── views/
│   └── res_partner.xml
├── security/
│   ├── ir.model.access.csv  ← ACLs only
│   └── ir_rule.xml          ← record rules
│   └── res_groups.xml       ← security groups
├── data/                    ← data required on production install
├── demo/                    ← demo data only
├── wizards/                 ← transient models and their views
│   ├── make_action.py
│   └── make_action.xml
├── reports/                 ← report models and QWeb templates
├── controllers/
├── static/                  ← assets only
├── i18n/                    ← .pot + generated .po
└── tests/
```

- One model per file in `models/`, file named after the model
  (`models/account_move.py` for `account.move`).
- No loose `.py` or `.xml` files at module root — the sole exception is
  `hooks.py` (init/uninstall hook entry points, imported from
  `__init__.py`; see `data.md`); everything below the root is
  imported through `__init__.py` or declared in the manifest.
- New Python files carry the project copyright header (author, license).
- `security/ir.model.access.csv` contains ACLs only; record rules live in a
  sibling XML file.
- `data/` vs `demo/`: the module must work fully with `demo/` absent;
  if something breaks without demo data, it belongs in `data/`.
- `static/` holds source assets only; never commit build artifacts.
- `i18n/` files are export artifacts — fix translatable strings at the
  source and re-export; do not hand-edit `.po` files.

## Manifest rules

- Required keys: `name`, `summary`, `version`, `category`, `author`,
  `license`, `depends`, `data`.
- Version format: `<odoo_series>.<serial>` (e.g. `20.0.1.0.0`).
- `license` is mandatory: `AGPL-3` for anything publishable to OCA;
  the appropriate proprietary license otherwise.
- `application: True` only for modules providing their own top menu and
  meant to be installed standalone; pure extensions leave it unset.
- `installable` must never be `False` in a released module.
- Declare every third-party import in `external_dependencies` (`python`,
  `bin`): the module must fail at install time with a clear message, not
  at first use.

## Naming conventions

- Modules: `snake_case`. Private/company modules carry a short prefix
  (`custom_stock`).
- Modules are named after what they extend:
  `custom_sale`, `custom_stock`, `custom_sale_stock`, ...
- View xml_ids: `<model>_view_<type>` (`res_partner_view_form`); actions and
  menus follow the same pattern (`res_partner_action`, `res_partner_menu`).
- When extending another module's view, keep the original id; the view
  *name* may carry the "inherit" term.

## Dependency discipline

- Depend on the smallest set of modules that provides what you actually use.
  Depend on the module that actually defines the objects you extend.
- Follow the std layering direction: workflow modules depend on
  master-data modules, never the reverse (sale, stock, account all
  depend on product).
- Glue code between two optional modules belongs in a separate module
  depending on both, so either can be installed without the other.
- `auto_install: True` is only for glue modules that are meaningless
  unless both dependencies are installed.
- Verify each dependency exists in the target version.

## Multi-module projects

- Split by installable feature (optional functionality = separate module),
  by integration point (each external system = separate connector).
- Modules in the same repo must remain independently installable: a module
  must not import Python from a sibling module it does not depend on.
- Extract early: splitting a module out is cheap at project start and
  expensive once many depend on it.
- Avoid modules depending on multiple big functional Odoo modules
  (e.g. `sale` + `mrp` + `stock` + `hr`...). Features have to be split in
  different modules, with loose coupling (through hooks for instance) making
  them working together.
- Layer custom modules like the standard ones: one feature module per
  area (`custom_sale`, `custom_stock`, `custom_mrp`, ...), one glue
  module per pair of areas (`custom_sale_stock`). A module extending
  `mrp` may depend on the custom stock module — standard `mrp` already
  depends on `stock`.
- A resource belongs to the module of the model it is bound to, not to
  the flow that triggers it: a mail template on `stock.picking` lives in
  the stock module, a template on `project.project` in the project
  module.
- When a resource moves to another module, move it whole — field,
  views, ACLs and test fixtures together; the sender keeps nothing
  half-moved.
- Code never mentions a sibling module it does not depend on — not even
  in comments and docstrings. A hook docstring states the contract and
  the default behavior, and says it can be overridden; it never names
  the overriding module. Cross-references belong in manifest
  descriptions and migration scripts, where they are functional.
- Put security groups in a base module (e.g. `custom_base`) as empty, allowing
  their usage in several submodules.
  Submodules will depend on the base module to complete the groups and set
  them where they should (views, ACLs...).
