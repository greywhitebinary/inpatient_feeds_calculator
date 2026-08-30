# Adult Inpatient Enteral Nutrition Calculator

A standalone Streamlit calculation workspace for adult inpatient enteral
nutrition. It supports an RD-maintained formulary, transparent assessment
equations, EN-plan comparison, modular orders, water-flush planning, and a
read-only chart-note aid.

The tool is not an autonomous clinical decision system. Clinicians must verify
current product data, apply local policy, and use independent clinical judgment.

## Local case records

The application has no account system, shared workspace, remote patient-record
database, or application-level case storage. It does not include a code path
that saves or exposes entered case data to the site owner. A remotely hosted
Streamlit app still processes inputs on its active application server so that
the Python calculation can run; it does not retain them as case records. An RD
can download an EN case record workbook to an approved local location and
upload that same workbook later to restore the assessment, plan inputs, and
the formulary snapshot used for the plan.

Set the `CALCULATOR_WEBSITE_URL` environment variable to the public calculator
URL when the application is deployed. Newly downloaded records will then show
that address as a clickable link. When the setting is absent or points to a
local address, the workbook displays `To be added after deployment` instead.

The patient / record label is part of the downloaded workbook. It must follow
local privacy policy. The exported workbook is a local clinical file, so its
storage and transfer remain the clinician's and institution's responsibility.

For a strict requirement that entered inputs never leave the clinician's device,
the calculator must run locally or be rebuilt as a browser-only application.

## Run locally

```sh
cd webapp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

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
