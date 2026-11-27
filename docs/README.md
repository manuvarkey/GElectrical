# GElectrical developer documentation

Start here for development work. The user manual (Sphinx/MyST, published on
Read the Docs) lives in the same folder as `index.rst`, `introduction.md`,
`installation.md`, `getting_started.md`, `features.md`, `how_to.md`,
`troubleshooting.md` and `faq.md`; developer documents below are excluded from
the Sphinx build in `conf.py`.

Every page states whether it describes the **current implementation** (GTK3
application) or the **proposed architecture** (Tauri + Vue + headless Python).

## Reading order for coding agents

1. [AGENTS.md](../AGENTS.md): mandatory rules and task routing.
2. [ARCHITECTURE.md](../ARCHITECTURE.md): layers, ownership, repository structure.
3. [Development guidelines](development-guidelines.md) and [testing](testing.md).
4. The contract for the layer you are changing (table below).
5. For migration work: the milestone in the
   [implementation plan](migration/implementation-plan.md), the
   [feature inventory](migration/feature-inventory.md) and the
   [risk register](migration/risks-and-decisions.md).

## Find guidance by task

| Task | Read |
| --- | --- |
| Understand how the current app works | [Existing application audit](migration/existing-application-audit.md) |
| Change calculations, elements, connectivity, pandapower mapping | [Backend](architecture/backend.md), [regression baseline](migration/regression-baseline.md) |
| Change `.gepro` load/save or add stored data | [Project format](architecture/project-format.md), [ADR 0008](decisions/0008-project-format-compatibility.md) |
| Add or change a service command, undo, revisions, analysis jobs | [Backend protocol and services](architecture/backend-protocol.md) (current), [backend](architecture/backend.md), [ADR 0019](decisions/0019-service-layer-implementation.md), [ADR 0009](decisions/0009-undo-transactions.md), [ADR 0003](decisions/0003-backend-transport.md) |
| Build Vue views, composables, backend client | [Frontend](architecture/frontend.md), [UI guidelines](ui-guidelines.md) |
| Build or change reusable components | [EngineeringUI](architecture/engineering-ui.md), [package rules](../packages/engineering-ui/AGENTS.md) |
| Work on the schematic editor or symbols | [Schematic editor](architecture/schematic-editor.md), [ADR 0004](decisions/0004-canonical-schematic-model.md), [ADR 0005](decisions/0005-schematic-library.md) |
| Work on charts, protection or load-profile editors | [Graphing](architecture/graphing.md) |
| Add MCP tools, skills or permissions | [MCP](architecture/mcp.md), [ADR 0007](decisions/0007-mcp-server.md) |
| Package, release, sidecar lifecycle | [Packaging](architecture/packaging.md), [ADR 0010](decisions/0010-python-environment-and-sidecar.md), [ADR 0016](decisions/0016-weasyprint-windows-executable.md) |
| Change Python or pandapower versions | [ADR 0015](decisions/0015-python-and-pandapower-versions.md), [plan M1b](migration/implementation-plan.md#m1b--python-and-pandapower-upgrade) |
| Plan a future design module | [Design services](architecture/design-services.md), [roadmap](roadmap.md) |
| Replace `eval`, clipboard pickle or Mako | [ADR 0011](decisions/0011-safe-expressions.md) |
| Check licence compatibility | [Licence inventory](migration/risks-and-decisions.md#4-licence-inventory-target-stack), [ADR 0013](decisions/0013-licensing.md) |
| Verify a change or record evidence | [Testing](testing.md), [validation log](migration/validation.md) |

## Document map

```text
AGENTS.md, ARCHITECTURE.md
docs/
├── README.md                     this index
├── development-guidelines.md     how to work in each layer
├── ui-guidelines.md              interaction and visual rules (proposed)
├── testing.md                    current and planned checks
├── roadmap.md                    milestone status and post-parity work
├── architecture/                 target contracts (proposed until implemented)
│   ├── backend.md  backend-protocol.md  frontend.md  engineering-ui.md  project-format.md
│   ├── schematic-editor.md  graphing.md  design-services.md  mcp.md  packaging.md
├── migration/                    audit, inventory, plan, baseline, risks, validation log
├── decisions/                    architecture decision records
└── (user manual: index.rst and *.md at this level, Sphinx)
packages/engineering-ui/README.md, AGENTS.md
```

## Document ownership

| Kind | Purpose | Update when |
| --- | --- | --- |
| `AGENTS.md` files | Mandatory rules and routing | The owner approves a rule change |
| `ARCHITECTURE.md`, `architecture/` | Current/proposed boundaries and contracts | Behaviour or ownership changes; mark sections *current* once implemented |
| Guides (development, UI, testing) | How to extend and verify | The workflow changes |
| `migration/` | Audit, parity tracking, plan, evidence | Status changes with evidence; validation log is append-only |
| `decisions/` | Why a decision was made | New decision or supersession; never delete |
| `roadmap.md` | Remaining work | Milestone status changes |

Keep one canonical description of each contract and link to it instead of
copying. When code and a contract disagree, investigate, report the mismatch
and update the contract with the behaviour change.
