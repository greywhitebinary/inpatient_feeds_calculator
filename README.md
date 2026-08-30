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
3. **EN plan.** Choose a delivery schedule, compare formulas, set or adjust a
   rate, add modulars, plan hydration flushes, and review the daily intake and
   EN plan check.
4. **Propofol.** When needed, compare lower- and higher-propofol scenarios
   without overwriting the standard EN plan.

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
cd webapp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

The local app opens at `http://localhost:8501` unless you set another port.

## Deployment configuration

Set `CALCULATOR_WEBSITE_URL` to the public calculator URL when deploying. New
record workbooks then include that address as a clickable link. When the value
is absent or points to a local address, the workbook shows `To be added after
deployment` instead.

## Tests

From `webapp/`, run:

```sh
.venv/bin/python -m unittest discover -s tests -q
```

The test suite covers the calculation layer, formulary validation, saved-record
round trips, and key Streamlit workflows.

## Structure

- `webapp/app.py` is the small Streamlit entry point and page orchestrator.
- `webapp/assessment_ui.py` contains the assessment workflow and its authoritative EN goals.
- `webapp/plan_ui.py` contains the shared EN formula, modular, hydration, and plan-check workflow.
- `webapp/propofol_ui.py` contains the two-scenario Propofol workflow.
- `webapp/formulary_ui.py` contains the Formulary and modular-library interface.
- `webapp/session_state.py` contains session initialization, legacy-state migration, and widget synchronization.
- `webapp/case_record_ui.py` contains saved-record controls and the footer.
- `webapp/ui_common.py` and `webapp/constants.py` contain shared presentation helpers and display constants.
- `webapp/calculations.py` contains the inspectable calculation layer.
- `webapp/case_io.py` contains the saved-record workbook contract.
- `webapp/data.py` contains formulary loading, validation, import, and export.
- `formulary_working/` contains the working feed and modular data.
- `formula_sources/` contains the manufacturer-guide source PDFs.

Keep patient records, downloaded workbooks, historical working spreadsheets,
screenshots, and other private local material outside this repository. The
repository should remain the single source of truth for the application code,
tests, public assets, and maintained product data.

See `configurable_rd_calculation_workspace_v2.md` for the V1 scope and clinical-workflow decisions.

For feedback, open an [issue on GitHub](https://github.com/greywhitebinary/inpatient_feeds_calculator/issues)
or find Hui-Jun Gail Chew on [LinkedIn](https://www.linkedin.com/in/hui-jun-gail-chew/).
