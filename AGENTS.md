# Collaboration Guidance

## Read before changing the calculator

Read [the calculation and maintenance guide](docs/CALCULATION_FLOW.md) before
changing planning, state, totals, or charting. It records the confirmed workflow,
architecture, validation, and remaining issues. The user's current request
determines the scope of work. Preserve the existing starting/checking workflow;
internal cleanup does not itself justify a UI change.

Update that guide when these decisions change rather than creating another
handoff or status document. Product-data changes also require
[the data conventions](formula_sources/DATA_CONVENTIONS.md); use the README's
[documentation map](README.md#documentation-map) to find supporting evidence.

## Read before changing the public website

Read [the Feed. Form. Flow. website guide](docs/SITE_GUIDE.md) before changing
anything in `docs/index.html`, `docs/home.css`, `docs/encalc/`,
`docs/btfcalc/`, `docs/site.css` or the Pages workflow. It records the intended
visual identity, the different roles of the editorial homepage and product
pages, copy guardrails, visual history, theme status, deployment and DNS.

Preserve the existing ENCalc and BTFCalc copy and screenshots unless the
current task supplies a specific reason to change them. Do not use the homepage
mockup as the product-page layout. Do not reintroduce RSS or automatic Substack
article updates without an explicit decision about their reliability and
maintenance.

Update the website guide when a settled design, content, domain or deployment
decision changes. The user's current request still determines the scope of
work; the guide supplies context rather than independent permission to redesign
the pages.

## Cost-aware delegation

When a task can be divided into independent, bounded subtasks, delegate routine
work to a lower-cost model when doing so will not reduce the quality of the
delivered product. Suitable work includes file discovery, straightforward data
inspection, mechanical transformations with explicit acceptance criteria, and
focused test or documentation checks.

Use a stronger model for architectural decisions, ambiguous requirements,
clinical or other safety-sensitive content, complex debugging, security review,
and final integration when those tasks require substantial judgment. Do not
delegate merely to reduce cost if the task depends on nuanced interpretation or
if verifying the result would cost more than completing it directly.

For each delegated task, provide the relevant context, exact scope, expected
output, constraints, and verification criteria. Prefer the least expensive
model that can reliably meet those criteria. Review every delegated result
against the acceptance criteria, run proportionate validation, and retain
ownership of the final product decision.

Avoid creating agents for tiny tasks that can be completed more efficiently in
the current turn, or for work that would contend with another agent editing the
same files.

## Writing

Avoid asyndetic parataxis in explanatory prose.

Do not default to rhythmic strings of parallel noun phrases, fragments, or
slogan-like contrasts such as “Three models, two datasets, one winner,” “No
setup. No delays.,” or “Not X. Not Y. Just Z.”

Prefer complete sentences that preserve logical relationships between facts.
Use verbs, clauses, conjunctions, and prepositions to show what was done, how,
under what conditions, why, and how it was evaluated.

Do not remove connective language merely to make prose shorter or punchier.
Use parallelism only when it serves a deliberate rhetorical purpose.

## Local source documents and private data

`reference_documents/` contains local-only manufacturer documents arranged by
country. It is ignored by Git and must never be added, committed, or pushed.
When updating public formulary CSVs, read the relevant local document, report
each changed value with its document and page, and update the row-level source
and verification metadata. See `formula_sources/SOURCES.md` for the public
source register.

`local_data/` is also ignored by Git. It may contain private alternative data
sets, which must not be used by, copied into, or assumed to be available to the
public deployment without the owner's explicit direction.
