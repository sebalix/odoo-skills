# Comments and Docstrings

Rules for what a linter cannot judge: the *usefulness* of a
comment or docstring. Style and formatting are not covered — run the
tools instead.

## Usefulness

- Do not write comments unless the code is not obvious at all: a
  comment must say what the code cannot — intent, rationale,
  non-obvious consequences. Never restate adjacent code, a method
  name, or the docstring above.
- Docstrings document contracts — one for every method whose behavior
  is not obvious: business rules, expected formats, what the caller
  gets. Lists of field names and walkthroughs of the body are not
  contracts.
- No commentary the mechanism already implies: an
  `{pre,post}_init_hook` means the module is not installed, a
  migration script means it is; in migrations, the moved xmlid pairs
  and the script location tell the story — a one-line intent comment
  suffices.

## Refactoring

- When code moves, its comments move with it and keep their wording
  verbatim: no removal, no rewording. Judge only the comments the
  change newly adds.
