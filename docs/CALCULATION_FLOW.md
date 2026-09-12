# Calculation and record flow

This map describes the calculator as it works now. It is a maintenance aid, not
a definition of clinical requirements or a recommendation for patient care.

## Current value flow

1. **Product data enters through `webapp/data.py`.** Master formula, modular,
   and ONS CSVs are loaded into data frames. Uploaded formulary workbooks pass
   through the same column and row validation before becoming the session's
   product lists. Serving-based ONS products retain per-serving values, while
   liquid ONS products use container size and per-mL values.

   A missing or blank disclosed-nutrient value is different from a declared
   zero. Formula micronutrients, adequacy fields, and specified modular fields
   remain null when the source does not disclose them. A declared zero remains
   numeric. Formula and ONS fibre are the documented exception: a blank fibre
   cell is normalized to zero under the existing fibre-free product convention.

2. **Assessment owns the goals and IV entries.** `webapp/assessment_ui.py`
   writes the authoritative `assessment_energy_target`,
   `assessment_protein_target`, and `assessment_water_target` values. The plan's
   “Adjust goals” controls update those same Assessment keys. Weight choices and
   the entered requirement ranges also remain Assessment state.

   IV names, rates, durations, and TKVO flags are stored as Assessment fields.
   `webapp/session_state.py` converts active IV entries into daily deliveries by
   calling `webapp/calculations.py`. The user explicitly authorized the current
   behavior in which IV sodium, potassium, calcium, and magnesium contribute to
   the intake table and totals. IV dextrose contributes energy and carbohydrate.
   IV volume is deliberately excluded from the reported water total because
   water goals are entered net of IV fluid.

   Propofol is plan state, handled by `webapp/propofol_ui.py` and
   `webapp/plan_ui.py`. Its energy reduces the energy left for a formula
   suggestion, while its fat and energy later appear in source totals.

3. **The plan turns a suggestion or entered order into one calculation
   shape.** `render_en_scenario` in `webapp/plan_ui.py` coordinates the current
   workflow. It subtracts IV energy and applicable propofol
   energy before suggesting a formula amount. ONS is counted in final intake,
   but it does not reduce the formula-energy suggestion. The same is true of
   modular energy under the preserved policy.

   `practical_feed_delivery` rounds a suggested pump rate or intermittent
   volume to the existing 5 mL increment. `ordered_feed_delivery` then converts
   the selected or manually entered order into daily volume and nutrients.
   Rate-and-duration intermittent orders are first converted to volume per
   feed. Manual order overrides remain authoritative across reruns. An explicit
   “Use suggested” action replaces the override with the current suggestion.
   A running regimen is otherwise protected from automatic replacement.

4. **Full and estimated delivery branch from that order.** The full result uses
   100% of the normalized formula order. The estimated result applies the
   entered delivery percentage to formula delivery. The selected display drives
   the on-screen intake and goal comparison. Modulars, ONS, propofol, IV fluids,
   and entered flushes remain separate source contributions rather than being
   scaled as formula delivery.

5. **Source rows become totals.** `plan_ui.py` builds rows for formula,
   modulars, ONS, propofol, IV fluids, and water administrations, then
   `combined_intake` in `webapp/calculations.py` sums the fixed intake fields.
   Unknown source values can display as an em dash while contributing nothing
   to the numeric sum; this does not turn them into declared zeros. ONS water is
   included in displayed and charted totals, but it is excluded from the
   goal-derived hydration-flush calculation.

6. **The chart note uses the planned result.** `webapp/chart_note.py` receives
   completed scenario result dictionaries. It reports the full planned regimen
   and its planned source total even when the screen is showing an estimated
   partial-delivery result. It names contributing IV dextrose, ONS, modular, and
   propofol sources when they affect the total. The editable chart-note draft is
   generated output and is not saved in the case workbook.

7. **Save and reopen preserve inputs and product snapshots.**
   `webapp/case_io.py` exports allowlisted calculator inputs plus the current
   formula, modular, and ONS tables. Import validates each restored input and
   revalidates product data before `session_state.py` replaces the active case.
   Formula-looking user text is stored as literal workbook text.

   Goal migration distinguishes an absent key from a present key whose value is
   `None`. An absent newer goal field may receive a legacy value or current default.
   For those goals, a present `None` means the user deliberately left or made the field blank and
   must remain blank.

## Module and regression map

- `data.py`: product schemas, missing-data semantics, and formulary workbooks.
- `assessment_ui.py`: measurements, requirement inputs, authoritative goals,
  and IV entry controls.
- `session_state.py`: initialization, import application, migrations, and IV
  aggregation.
- `calculations.py`: unit conversion, normalized delivery arithmetic, source
  delivery, hydration, and total summation.
- `plan_ui.py` and `propofol_ui.py`: order state, suggestions, overrides,
  displayed results, and source-row assembly.
- `chart_note.py`: planned-regimen chart-note output.
- `case_io.py`: case workbook snapshot, validation, export, and import.
- `tests/test_calculations.py`, `tests/test_plan_regressions.py`, and
  `tests/test_chart_note_regressions.py`: calculation and output paths.
- `tests/test_goal_state_regressions.py`: goal ownership and blank-state
  behavior.
- `tests/test_workflow_roundtrip.py`: complete intake tables and generated notes
  after saving, replacing, and reopening representative cases.
- `tests/test_data.py`, `tests/test_formulary_regressions.py`, and
  `tests/test_record_regressions.py`: product and workbook compatibility.

## Future extraction

There is not currently a separate normalized-order domain object or service.
`render_en_scenario` still combines UI rendering, state decisions, order
normalization, source assembly, and result selection. A future change could
extract a tested calculation input/result boundary so the full display,
estimated display, totals, and chart note consume explicit shared results. That
is a proposed maintenance direction; this extraction has not been implemented.

For a future AI-assisted change, use this copyable instruction:

> Trace the changed input through every affected calculation, display, chart-note, and saved-record output. Add a regression that fails before the fix, make the narrowest behavior change, run the related suites, and report the exact behavior, files, checks, and remaining limits.
