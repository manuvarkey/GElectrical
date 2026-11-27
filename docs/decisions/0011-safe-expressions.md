# 0011. Safe expression evaluation replaces `eval`, Mako and pickle

- Status: Accepted (owner 2026-11-26)
- Date: 2026-11-26
- Related: [audit §12](../migration/existing-application-audit.md#12-defects-and-weaknesses) (D1–D3, D10)

## Context

Protection-curve definitions (stored in databases **and inside project
files**), rules-check expressions, numeric field entry and database references
are evaluated with Python `eval()`. Copy/paste uses pickle through the system
clipboard. Symbol labels use Mako templates. Once files arrive from untrusted
sources or MCP clients edit projects, these paths allow arbitrary code
execution.

## Decision

- Implement `gelectrical/core/expressions.py`, a bounded AST evaluator with an
  explicit whitelist: numeric literals, lists, names from a supplied namespace,
  attribute access on whitelisted wrapper objects (`f`, `d`, `e.f`, `e.r`, `ss`,
  `sr`), arithmetic, comparisons, boolean operators, conditional expressions
  and calls to whitelisted functions. No dunder names, imports, lambdas,
  comprehensions or arbitrary calls. Limits on length, depth and evaluation cost.
- Rules-check expressions (code-defined) use the same evaluator so behaviour is
  uniform.
- Numeric entry uses the numeric subset (inspired by GEstimator's
  `NumericExpression`).
- Database tuple references use `ast.literal_eval` or a migrated column.
- Clipboard uses a versioned JSON payload validated by Python.
- Symbol labels are produced by Python formatting functions, not Mako.

## Alternatives considered

- *`asteval` or `simpleeval` libraries*: possible, but their default feature
  sets are broader than needed and attribute access rules differ; a small local
  evaluator is auditable. Re-evaluate if the local evaluator grows.
- *Keep eval with restricted globals*: not a security boundary.

## Consequences

Some unusual expressions in user projects might be rejected; they are reported
with element and field, never executed or silently replaced.

## Verification

Every bundled expression parses; curve and rules baselines unchanged; malicious
project and clipboard samples are rejected; CI static check forbids `eval`,
`exec` and `pickle.loads` in engine and backend code.

## Implementation (M3, 2026-11-27)

*Current* on branch `feat/m3-safe-expressions`.

- `gelectrical/core/expressions.py`: tree-walking evaluator over a validated
  AST, no project imports. A `Policy` lists the callable functions, the types
  whose attributes may be read (each with a resolver function) and the types
  whose methods may be called. Validation failures and limit violations raise
  `ExpressionNotAllowed`; evaluation failures (unknown field, division by
  zero) raise its base class `ExpressionError`. Limits: 2000 characters,
  400 AST nodes, depth 40, integer powers up to 100 000 bits, sequence
  repetition up to 10 000 items; text formatting (`'%g' % x`) only with a
  literal format string.
- Policies: `FIELD_POLICY` (`core/fields.py`: `f.code`/`d.code` read field
  values of a `FieldDict`) for protection curves; `RULES_POLICY`
  (`model/rulescheck.py`: also `Element` instance variables, the six curve
  geometries of `ProtectionModel` and its methods `contains`, `get_current`,
  `get_time`); `LABEL_POLICY` (`symbols/formatter.py`: names only);
  `NUMERIC_POLICY` (numbers, arithmetic, `abs`, `min`, `max`, `round`,
  `sqrt`) for field entry and spreadsheet formulas.
- Protection curves keep the previous error handling: a curve item whose
  value fails to evaluate is logged and skipped as before, but an
  `ExpressionNotAllowed` is never skipped. Loading a project raises
  `ExpressionNotAllowed` naming element, reference and stage; the GTK window
  shows "Project could not be opened: unsupported expression - ...".
- Curve function names stored as text (`'IEC'`, `'point'`) are looked up in
  the function table instead of being evaluated. Names containing `.`
  (`'IEC_S_INV_3.0'`, `'IEC_S_INV_1.3'`) raised `SyntaxError` under `eval`
  and now resolve; no bundled database or test project uses them.
- Labels: `${...}` fields of `text_model` are parsed by
  `parse_template` and rendered by `format_template` (`str` of the value, as
  Mako). Mako is removed from `pixi.toml`, `requirements.txt`, `setup.py` and
  the Flatpak manifest.
- Database references: `core/database.py` `parse_data_reference` uses
  `ast.literal_eval` and rejects absolute paths, drive letters and `..`.
- Clipboard: `model/clipboard.py`, payload
  `{"format": "gelectrical-elements", "version": 1, "elements": [...],
  "assemblies": {...}}` with the stored element models; validated, then built
  with `DrawingModel.new_element_from_model` (the code path of project
  loading). The floating preview is built from the stored models; the inserted
  elements are copies made by `get_element_copy` as before.
- Reports (D10): Jinja2 autoescape for `.html` templates; generated tables
  and embedded images are passed as `Markup`; WeasyPrint uses a URL fetcher
  that only resolves `data:` URLs and the generated `report.css`.
- Verification: `tests/engine/test_expressions.py` (language, limits,
  rejected constructs, numeric entry, templates, every curve expression of the
  bundled databases and the 17 baseline projects compared with Python `eval`
  as oracle), `tests/engine/test_security.py` (static check over
  `gelectrical/`, `tools/`, `modern/` and the launcher; database references;
  rule expressions; malicious projects; clipboard; report escaping and URL
  fetcher). Evidence in the [validation log](../migration/validation.md).
