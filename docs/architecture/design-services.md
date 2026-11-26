# Design services (future capability)

Status: **proposed framework only**. No design calculation is implemented or
specified in Phase 1, and none may be implemented during the migration
milestones. Navigation: [index](../README.md) · [backend](backend.md) ·
[MCP](mcp.md) · [roadmap](../roadmap.md).

GElectrical currently *analyses* a network that the user draws. Future work
extends it to *design*: sizing, selection, schedules and generation. This page
defines the shape such modules must take so that each new module does not need
a bespoke GUI, a separate MCP tool or its own persistence.

## 1. Anticipated modules

Load estimation and demand calculation; cable and conductor sizing; circuit
breaker selection; transformer and generator sizing; protection coordination
assistance; distribution board and circuit schedules; earthing system design;
automatic schematic generation; design alternatives and comparison; bill of
quantities; compliance checking; AI-assisted design through MCP.

## 2. Design service contract

A design service is a Python class registered in
`gelectrical/design/registry.py` (proposed) with:

| Part | Content |
| --- | --- |
| `id`, `title`, `version` | Stable identifier and version of the method |
| `inputs` | Typed input definitions: name, type, unit, default, bounds, choices, help text, source binding (element field, project setting, library item or user value) |
| `constraints` | Declarative checks over inputs (ranges, dependencies) evaluated in Python |
| `assumptions` | Explicit list with defaults, editable where the method allows |
| `standards` | References (standard, edition, clause) used by the method |
| `run(inputs, context)` | Pure calculation returning a `DesignResult` |
| `apply(result, selection)` | Optional: converts accepted results into a list of service commands (field updates, inserted elements) executed in one transaction |

`DesignResult` contains: computed values with units, pass/fail checks with
margins, intermediate steps for reports, warnings, the assumptions actually
used and alternatives where applicable.

Rules:

- Calculations reuse engine functions (for example `LTCableIEC` derating tables
  and pandapower results). A service never duplicates an element calculation.
- `run` has no side effects. Only `apply` changes the project, through
  commands, so undo, revisions, events and MCP review work unchanged.
- Results are reproducible from stored inputs and the method version; stored
  design records (if persisted) use an additive `.gepro` member with a
  migration plan ([project format](project-format.md)).

## 3. Schema-driven presentation

The frontend renders any design service with generic EngineeringUI components:

- `EuiPropertyInspector` / form layout from `inputs` (groups, units, choices,
  help, validation messages returned by Python).
- `EuiDataGrid` for tabular inputs and results (circuit schedules, BOQ).
- `EuiChart` components for curves.
- A generic *workflow* container: steps (inputs → assumptions → run → review →
  apply), with a diff preview of the commands `apply` would execute (service
  preview transaction).

Presentation metadata (grouping, ordering, widget hints, labels) lives in a
separate optional `presentation` block, never inside the engineering rules.

Candidate schema format: JSON Schema (draft 2020-12) generated from Python type
definitions, with GElectrical extensions for units and bindings. The existing
element field dicts already behave like a schema; the element catalogue in
[backend](backend.md#8-data-contracts-summary) should use the same generator so
element properties and design inputs share one form renderer.

## 4. MCP exposure

- `run_design` takes a service `id`, inputs and `preview` flag and returns the
  `DesignResult` with assumptions and standards.
- `apply` happens through the same tool with `apply: true` (write mode only),
  executing commands in one transaction.
- Discovery uses `describe_design_services` content inside an existing read
  tool to keep the tool count small; engineering guidance lives in skills.

## 5. Prerequisites before the first design module

1. Migration parity milestone signed off ([plan](../migration/implementation-plan.md)).
2. Typed result records and stable element identity in services.
3. Unit handling helper (`gelectrical/core/units.py`) agreed and tested.
4. One pilot service (proposed: cable sizing check, because the engine already
   contains IEC derating data) specified in its own design document with a
   worked example and independent verification data.
