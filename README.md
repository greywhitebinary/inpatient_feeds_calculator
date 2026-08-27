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

- `webapp/calculations.py` contains the inspectable calculation layer.
- `webapp/app.py` contains the Streamlit interface.
- `formulary_working/` contains the working feed and modular data.
- `formula_sources/` contains the manufacturer-guide source PDFs.

See `configurable_rd_calculation_workspace_v2.md` for the V1 scope and clinical-workflow decisions.
