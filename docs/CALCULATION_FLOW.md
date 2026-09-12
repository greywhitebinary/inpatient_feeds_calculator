# Calculation and record flow

This guide describes the implemented code structure and preserved behavior. It
is a maintenance aid, not a definition of clinical requirements or a
recommendation for patient care.

## Where the numbers travel

1. **Product data enters through `webapp/data.py`.** Master formula, modular,
   and ONS CSVs are loaded into data frames. Uploaded formularies pass through
   column and row validation. Serving-based ONS retains per-serving values;
   liquid ONS uses container size and per-mL values.

   Undisclosed formula micronutrients, adequacy fields, and specified modular
   fields remain null, while declared zeros remain numeric. Formula and ONS
   fibre retain the existing exception: blank fibre becomes zero under the
   documented fibre-free product convention.

2. **Assessment owns goals and IV entries.** `assessment_ui.py` writes the
   authoritative energy, protein, and water goals. The plan's “Adjust goals”
   controls update those same Assessment keys. `session_state.py` passes IV
   entries to `calculations.py` to calculate daily delivery.

   IV sodium, potassium, calcium, and magnesium contribute to intake totals as
   explicitly authorized by the user. IV dextrose contributes energy and
   carbohydrate. IV volume remains excluded from the reported water total
   because the water goal is entered net of IV fluid. `propofol_ui.py` and the
   feed controls manage propofol entries, whose energy and fat enter intake.

3. **Feed controls produce an explicit order.** `plan_feed_controls.py` handles
   the starting-versus-reviewing workflow, schedules, formula comparisons,
   suggestions, and entered orders. It returns a `FeedSelection` to the
   coordinating `plan_ui.py`.

   `plan_order.py` holds immutable `FormulaEnergy` and `FeedOrder` objects.
   `FormulaEnergy` distinguishes energy remaining after IV from energy remaining
   after both IV and propofol. Conditional suggestions apply their own propofol
   exposure to the first amount. Modular and ONS energy still do not reduce the
   formula suggestion.

   `FeedOrder` converts intermittent rate-and-duration entries to volume per
   feed once and retains conditional rates with their exposure hours. Its
   delivery method delegates arithmetic to `calculations.py`. Suggested orders
   retain the existing 5 mL rounding. Manual overrides survive reruns until an
   explicit “Use suggested” action replaces them; running orders remain
   protected from automatic replacement.

4. **Supplement and hydration controls collect separate contributions.**
   `plan_supplements.py` returns modular and ONS selections, calculated totals,
   and chart-note details. Incomplete supplement orders contribute nothing.
   `plan_hydration.py` handles flush entries and hydration results, using the
   existing calculation functions. ONS water counts in intake and charted
   totals, but remains excluded from goal-derived hydration-flush calculations.

5. **The same order produces full and estimated delivery.** The full result
   uses 100% of the formula order. Estimated delivery applies the entered
   percentage to formula alone. Modulars, ONS, propofol, IV fluids, and flushes
   retain their entered contributions.

   `plan_sources.py` receives those contributions through `IntakeSources`.
   Its pure `calculate_intake` function returns an `IntakeResult` containing
   source rows and totals for both planned and displayed delivery, without
   accessing widgets or session state. Both views use the same row builder and
   existing `combined_intake` arithmetic. Unknown values can display as an em
   dash while adding nothing to the numeric sum; they remain distinct from
   declared zeros. Shared mmol conversion helpers now live in
   `calculations.py`, with their arithmetic unchanged.

6. **Review and charting consume these results.** `plan_review.py` renders the
   delivery choice and goal comparison. Its calculated comparison totals retain
   the original addition order so half-unit rounding stays unchanged.
   `plan_ui.py` coordinates the sections
   and passes the planned results to `chart_note.py`. The chart note describes
   the full planned regimen even when the screen displays estimated partial
   delivery. The editable chart-note draft is not saved in the case workbook.

7. **Save and reopen preserve inputs and product snapshots.** `case_io.py`
   exports allowlisted inputs and the current product tables. Import validates
   restored inputs and product data before `session_state.py` replaces the
   active case. Formula-looking user text remains literal workbook text.
   Goal migration distinguishes absent keys from deliberately blank values:
   missing newer keys may receive legacy values or defaults, while an existing
   `None` stays blank.

## What this cleanup preserves

The user-visible layout, wording, control order, and starting-versus-reviewing
workflow remain the same. Moving code into modules does not itself justify
moving controls on screen. Any future UI rearrangement needs a clear,
user-relevant reason that explains the problem and the proposed improvement.

This extraction makes the order and intake boundaries explicit. It does not
claim that every module is now simple or every clinical case has been verified.
Feed-control state decisions could be divided further in a later change if
there is a concrete maintenance benefit.

## Regression map

- `tests/test_plan_order.py` checks equivalent order forms, full and partial
  delivery, conditional order snapshots, and formula-energy allocation.
- `tests/test_plan_sources.py` checks independently expected source totals,
  partial delivery, IV electrolyte and water handling, disclosure semantics,
  and input preservation.
- `tests/test_app_render.py` and `tests/test_plan_regressions.py` exercise the
  visible workflows, state transitions, and repaired calculation paths.
- `tests/test_workflow_roundtrip.py` compares complete intake tables and
  generated notes after saving, replacing, and reopening representative cases.
- `tests/test_calculations.py`, `tests/test_chart_note_regressions.py`, and
  `tests/test_goal_state_regressions.py` cover arithmetic, charting, and goals.
- Product and workbook compatibility are covered by `tests/test_data.py`,
  `tests/test_formulary_regressions.py`, and `tests/test_record_regressions.py`.

For a future AI-assisted change:

> Trace the changed input through every affected calculation, display, chart note, and saved-record output. Add a regression that fails before a bug fix. Preserve behavior during structural cleanup. Run the related suites and report the exact behavior, files, checks, and remaining limits. Preserve the established interface unless a concrete user need justifies a UI change.
