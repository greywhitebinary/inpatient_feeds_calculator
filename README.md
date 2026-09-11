# Adult Inpatient Enteral Nutrition Calculator

[Open ENCalc](https://encalc.feedformflow.ca)

ENCalc is a Streamlit calculation workspace for adult inpatient enteral
nutrition. It brings a clinician-maintained formulary, assessment inputs,
transparent energy equations, EN delivery planning, modular orders, hydration
flushes, and a chart-note aid into one workflow.

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

The calculator does not make patient-specific recommendations. The clinician
selects the goals, formula, rate, modular order, and hydration plan.

## Records and privacy

ENCalc has no accounts, shared workspace, remote patient-record database, or
application-level case storage. A hosted Streamlit app processes the inputs in
its active session so it can calculate and render the page, but it does not
retain them as case records or expose them to the site owner.

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

Run from the repository root, not from `webapp/`. Streamlit reads
`.streamlit/config.toml` relative to the working directory, and that file — which
carries the shared colour palette — lives at the root. Starting from inside
`webapp/` loads no theme, so Streamlit paints its own default red wherever the
stylesheet does not override it.

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

GitHub Actions runs all of the above on any push to `main` and on any pull
request targeting it, and again every Monday — nothing in the repository
changes on a Monday, so that run catches the world changing underneath it. A
push to a topic branch with no pull request open runs nothing, so open one
before relying on the checks.

`scripts/check_css_hooks.py` is the one check a test suite cannot replace.
`webapp/styles.css` reaches into Streamlit's internal `data-testid`
attributes, which carry no stability guarantee, and the tests drive
Streamlit's Python API and never see a stylesheet — so a renamed attribute
breaks the page while every test stays green. The check reads every
`data-testid` the stylesheet depends on and asserts each still exists in the
Streamlit build. It checks no `data-baseweb` attribute, which the stylesheet
also relies on, because those values are short enough to appear somewhere in a
20 MB bundle by coincidence and the check would report a confidence it had not
established. So a renamed `data-baseweb` value would still break the styling
quietly; the script's docstring records that limit deliberately. This is also
why `webapp/requirements.txt` pins `streamlit` to an exact version rather than
to a range.

`.github/workflows/canary.yml` runs the same checks weekly against the
*latest* releases instead of the pinned ones. It never gates a push: a red
canary means "do not upgrade yet", not "main is broken".

## Structure

- `webapp/app.py` is the small Streamlit entry point and page orchestrator.
- `webapp/assessment_ui.py` contains the assessment workflow and its authoritative EN goals.
- `webapp/plan_ui.py` contains the shared EN formula, modular, hydration, and regimen-check workflow.
- `webapp/propofol_ui.py` contains the two-scenario Propofol workflow.
- `webapp/formulary_ui.py` contains the Formulary and modular-library interface.
- `webapp/session_state.py` contains session initialization, legacy-state migration, and widget synchronization.
- `webapp/case_record_ui.py` contains saved-record controls and the footer.
- `webapp/chart_note.py` builds the ADIME chart-note text and renders the editable draft.
- `webapp/copy_block.py` is the chart-note copy control, shared with BTF-Calc — see below.
- `webapp/ui_common.py` and `webapp/constants.py` contain shared presentation helpers and display constants.
- `scripts/check_css_hooks.py` verifies the stylesheet's Streamlit selectors still exist.
- `webapp/calculations.py` contains the inspectable calculation layer.
- `webapp/case_io.py` contains the saved-record workbook contract.
- `webapp/data.py` contains formulary loading, validation, import, and export.
- `formulary_working/` contains the working feed and modular data.
- `formula_sources/SOURCES.md` records the manufacturer documents used to
  review the public formulary data. The documents themselves are kept locally
  under `reference_documents/canada/` and are not needed at application runtime.

Keep patient records, downloaded workbooks, historical working spreadsheets,
screenshots, and other private local material outside this repository. The
repository should remain the single source of truth for the application code,
tests, public assets, and maintained product data.

### Shared with BTF-Calc

This tool has a sibling, the [Blenderized Tube Feeding
Calculator](https://github.com/greywhitebinary/blenderized-tubefeed-calculator).
The two are meant to read as one family, so five things are deliberately kept
identical between the repositories and must be changed in both:

- `webapp/copy_block.py` — the chart-note copy control. Byte-identical to
  BTF-Calc's `app/copy_block.py`, so `diff` between them is the whole sync
  check. Its own docstring explains the formatting constraint that keeps it
  that way, and why it reads no Streamlit theme variables.
- `render_alert()` in `webapp/ui_common.py`, and the `.app-alert` block in
  `webapp/styles.css`.
- The colour tokens in `.streamlit/config.toml`.
- `scripts/check_css_hooks.py`, where only the `STYLESHEET` path differs.
- `.github/workflows/canary.yml`.

## Licence

The application code, its tests, and its documentation are [MIT](LICENSE).
Use it, fork it, adapt it for another region's product data.

The licence includes the standard warranty disclaimer, which matters here: the
software is provided as is, and clinical responsibility stays with the dietitian
using it.

The product data is a separate question. `formulary_working/*.csv` holds values
transcribed from Nestlé Health Science Canada and Abbott Nutrition Canada product
documents, which carry their own terms, so the MIT grant is scoped to the software
and does not extend to that compilation. `formula_sources/SOURCES.md` records which
document each row was reviewed against, and the documents themselves are never
committed here. The dataset is a starting library rather than an approved
institutional formulary — see [Product data and clinical
checks](#product-data-and-clinical-checks) for what to verify before clinical use.

See `configurable_rd_calculation_workspace_v2.md` for the V1 scope and clinical-workflow decisions.

For feedback, open an [issue on GitHub](https://github.com/greywhitebinary/inpatient_feeds_calculator/issues)
or find Hui-Jun Gail Chew on [LinkedIn](https://www.linkedin.com/in/hui-jun-gail-chew/).
