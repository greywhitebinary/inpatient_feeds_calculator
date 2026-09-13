# Adult Inpatient Enteral Nutrition Calculator

[Open ENCalc](https://encalc.feedformflow.ca)

ENCalc helps you plan a new tube feed or review one already running for an
adult inpatient. Enter assessment goals and a feeding regimen, then review
its energy, protein, water and electrolyte provision alongside modulars,
oral supplements, IV fluids and propofol.

It is designed for dietitians and teams supporting adult inpatient enteral
nutrition. It supports, but does not replace, clinical judgement.

## Clinical workflow

1. **Formulary.** Build My Formulary from the included feeds and modulars, or
   import a local workbook. Product values remain editable because local labels
   and institutional formulary choices can differ.
2. **Assessment.** Enter available measurements and clinical inputs. Review the
   equations and worked ranges, then enter the energy, protein, and water goals
   that will drive the plan.
3. **Enteral nutrition.** Choose a delivery schedule, compare formulas, set or
   adjust a rate, add modulars, set hydration flushes, and review the daily
   intake and the EN regimen check. A feed that is already running can be
   entered here without an assessment: nothing is calculated backwards from a
   goal, so the page reports what the order delivers and leaves the goal
   columns out until goals are entered.
4. **EN + Propofol.** The same steps for a patient on propofol, given as a
   single rate or as rates that change through the day. Propofol's energy comes
   off the target first, so the feed is sized to make up the remainder.

Suggested feed rates are calculated from clinician-selected goals, products
and other inputs. The clinician chooses the final rate, modular order and
hydration plan. When a manually entered feed rate is preserved, changes to
the goals update the suggestion; “Use suggested rate” applies it explicitly.

## Records and privacy

ENCalc has no accounts, shared workspace, remote patient-record database, or
application-level case storage. A hosted Streamlit app processes the inputs in
its active session so it can calculate and render the page, but it does not
retain them as case records. The app has no interface for the site owner
to browse patient records.

Download an EN case-record workbook to an approved local location and upload
the same workbook later to restore the assessment, plan inputs, and formulary
snapshot used for that plan. The patient or record label is part of the
workbook, so its storage and transfer must follow local privacy policy.

If policy requires inputs never to leave the clinician's device, run the
calculator locally or use a browser-only implementation instead.

## Product data and clinical checks

Formula and modular values come from manufacturers’ Canadian product
information. Verify them against current local product labels and institutional
formularies before clinical use.

The application shows its calculations and intermediate values so that the
clinician can review the effect of the selected inputs. It does not replace
local policy, clinical assessment, or professional advice for an individual’s
care.

## Run locally

```sh
git clone https://github.com/greywhitebinary/inpatient_feeds_calculator.git
cd inpatient_feeds_calculator
python3 -m venv webapp/.venv
webapp/.venv/bin/pip install -r webapp/requirements.txt
webapp/.venv/bin/streamlit run webapp/app.py
```

Run from the repository root so Streamlit loads the shared theme from
`.streamlit/config.toml`.

The local app opens at `http://localhost:8501` unless you set another port.

To work on the code rather than just run it, install `requirements-dev.txt`
from the repository root instead — it pulls in the runtime dependencies plus
`pytest`, `black` and `ruff`, which is what CI runs.

```sh
webapp/.venv/bin/pip install -r requirements-dev.txt
```

## Deployment configuration

Set `CALCULATOR_WEBSITE_URL` to the public calculator URL when deploying. New
record workbooks then include that address as a clickable link. When the value
is absent or points to a local address, the workbook shows `To be added after
deployment` instead.

## Tests

From the repository root:

```sh
webapp/.venv/bin/python -m pytest webapp/tests/ -q
webapp/.venv/bin/python scripts/check_css_hooks.py
webapp/.venv/bin/ruff check . && webapp/.venv/bin/black --check .
```

The test suite covers the calculation layer, formulary validation, saved-record
round trips, and key Streamlit workflows. Each test file puts `webapp/` on
`sys.path` itself, so they run from the root with no configuration.

GitHub Actions runs these checks on pushes to `main`, pull requests targeting
`main`, and weekly. For stylesheet checks, dependency upgrades, and the weekly
canary, see [UI compatibility checks](docs/CALCULATION_FLOW.md#ui-compatibility-checks).

## Documentation map

For everyday code maintenance, start with
[Calculation and record flow](docs/CALCULATION_FLOW.md). It is the single guide
to current workflow decisions, architecture, repair history, and known issues.
[AGENTS.md](AGENTS.md) supplies working instructions for coding agents; this
README supplies setup, testing, and deployment information.

| When you need more detail | Read |
| --- | --- |
| Change product values or interpret missing data, units, or conflicting sources | [Data conventions](formula_sources/DATA_CONVENTIONS.md) |
| Find the cited manufacturer documents | [Source register](formula_sources/SOURCES.md) |
| Review manufacturer websites or hand source-review work to another project | [Reviewer methods](formula_sources/REVIEWING_MANUFACTURER_SOURCES.md); source-choice rules link back to Data conventions |
| Inspect earlier checks, decisions, and data questions | [Dated verification backlog](formula_sources/VERIFICATION_BACKLOG.md), [ONS verification](formula_sources/ONS_VERIFICATION.md), and [micronutrient verification](formula_sources/MICRONUTRIENT_VERIFICATION.md) |
| Inspect the recorded flavour comparisons | [Abbott survey](formula_sources/ONS_FLAVOUR_SURVEY.md) and [Nestlé survey](formula_sources/ONS_FLAVOUR_SURVEY_NESTLE.md) |
| Understand original design reasoning | [Historical working notes](configurable_rd_calculation_workspace_v2.md) |
| Identify the public datasets and their intended use | [Working data README](formulary_working/README.md) |

The dated records preserve evidence and may describe states superseded by later
work. Their paths and headings stay available for old links. Update the current
guide or applicable data convention rather than copying the same decisions into
a new handoff. `docs/MAINTENANCE_HANDOFF.md` is now a forwarding page.

## Structure

The app's entry point is `webapp/app.py`. Calculation functions, screen
components, saved-record handling and source data are documented in the
[calculation and maintenance guide](docs/CALCULATION_FLOW.md#application-file-map).
Keep patient records and other private local material outside this repository.

### Shared with BTF-Calc

ENCalc and the [Blenderized Tube Feeding Calculator](https://btfcalc.feedformflow.ca)
share presentation components. See [Shared with BTF-Calc](docs/CALCULATION_FLOW.md#shared-with-btf-calc)
in the maintenance guide before changing those components.

## Licence

The application’s original code, tests and documentation are licensed under
[MIT](LICENSE).

Product names identify the products used in calculations. Nutrient values are
factual information transcribed from the sources listed in the source register.
No exclusive rights are claimed over those individual facts, and inclusion
does not imply manufacturer endorsement.

See the [source register](formula_sources/SOURCES.md#licence-and-attribution) for provenance
and supporting guidance.

For feedback, open an [issue on GitHub](https://github.com/greywhitebinary/inpatient_feeds_calculator/issues)
or find Hui-Jun Gail Chew on [LinkedIn](https://www.linkedin.com/in/hui-jun-gail-chew/).
