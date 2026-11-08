# Views

Rules for writing and inheriting XML views (form, list, search)
and qweb templates. Everything else (widget usage, view architecture
patterns, template organization) follows standard Odoo practice: check
core modules and `versions/<X>.md` when unsure.

## XPath / inheritance

- Never match elements on translatable content (element text,
  translatable attribute values): archs are translated per language,
  so a match that holds in English breaks in every other language at
  render time — and English-only test databases hide it. Match on
  structural or non-translatable attributes, e.g.
  `t[contains(t[@t-set='url']/@t-value, '/my/tasks')]`,
  rather than matching the text of `t[t[@t-set='title'] = 'Tasks']`.
