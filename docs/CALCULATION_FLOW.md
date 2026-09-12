# Calculation and record flow

This is the maintained guide to the calculator's workflow decisions, code,
completed repairs, and remaining issues. Start here for application changes.
Use [README](../README.md) for setup and test commands, and
[data conventions](../formula_sources/DATA_CONVENTIONS.md) when changing product
data. Dated design and verification records remain linked from the README;
they supply history and evidence rather than another current task list.

This guide records project context, not a new request to change the application.
The user's current request determines the task. It does not prescribe care.

## Requirements, intended provision, and delivery

The user confirmed that assessed requirements come from equations and clinical
judgment. Final daily energy, protein, and water goals are shared: editing them
in Assessment or through Adjust goals on either planning tab updates the same
values.

The EN regimen target percentage expresses the clinician's intended provision
at this stage. For example, choosing 50% of the assessed energy requirement
must not overwrite that requirement. Under the existing implementation this
percentage scales the energy target; protein and water comparisons retain their
full goals. The calculator does not decide the appropriate percentage.

Achieved formula-delivery percentage answers a separate question: how much of
the entered formula order was delivered. It changes the estimated intake view;
it does not rewrite the prescription or the full planned chart note.

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
   explicitly authorized by the user. This adds no electrolyte paragraphs to
   the chart note. No Markdown instruction excluding IV electrolytes from the
   intake table was found in the searched history; older water and note-content
   instructions concern different outputs. IV dextrose contributes energy and
   carbohydrate. IV and propofol volume remain excluded from the reported water
   total because the water goal is entered net of IV fluid. `propofol_ui.py` and the
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

## Completed work

The reviewed starting commit was `d005f5f`. The following two commits separate
behavior repairs from structural cleanup:

- `b6dbad3` — Fix connected intake calculations and saved-record regressions.
- `e807ae2` — Separate feed orders and intake accounting from planning controls.

The repairs corrected partial intermittent rate/duration delivery, IV-energy
subtraction in conditional propofol suggestions, explicit suggestion buttons,
short intermittent schedules, cleared goals, and serving-based ONS record
restoration. They also preserved unknown micronutrients through workbook
round trips, corrected optional/serving schema handling, retained formula-like
workbook text literally, and made formulary searches treat punctuation literally.
Chart-note repairs preserve fractional ONS orders, distinguish IV durations,
identify ONS/IV/propofol nutrient sources accurately, and describe an existing
trickle feed as continuing.

## Verification evidence

At `e807ae2`, the local suite passed **286 tests and 116 subtests**. Ruff and
Black passed, and all 14 checked CSS hooks were present in Streamlit 1.62.0.
Commands are in [README](../README.md#tests). These are historical results;
rerun relevant checks when code changes rather than reporting them as a new test run.

A separate temporary AppTest harness compared 18 workflows before and after the
cleanup. Tables, generated notes, visible values, canonical goals/orders,
warnings/errors, and traversal-ordered rendered node types/keys/labels all
matched, including after an unrelated rerun. It covered continuous and both
intermittent forms, partial 0/50/100%, blank goals, both propofol methods with IV
and overrides, supplements, and the water-entry modes. That one-off harness is
not part of this repository's CI; the permanent regression files are mapped in
the calculation-flow guide.

The review read every runtime Python module and the embedded note JavaScript,
stylesheet, tests, and CI configuration. It did not independently certify
clinical equations or manufacturer values, exercise every clinical combination,
verify an EMR paste, or perform a full browser/device/security audit. Do not
present a passing suite or the code review as such a guarantee.

## Known remaining issues and boundaries

- A custom formula named exactly `Modulars` can be filtered from the daily
  intake rows when no modular is selected, because the existing filter uses a
  display label. This pre-existing edge was preserved during the structural
  change. A separately scoped fix should identify rows by role rather than
  product name and test the table and chart-note totals.
- The regimen check preserves its original water addition order. Regrouping
  floating-point additions can alter integer display rounding at a half-mL
  boundary. Its dedicated totals in `plan_sources.py` are intentional; tests
  cover this. Do not remove them as redundant without examining the behavior.
- Unsupported weight-choice strings in manually malformed case workbooks can
  pass import and then reset to UI defaults. Current UI exports cannot create
  those values. Broader saved-field validation remains a separate task.
- Clearing the adjusted-weight factor restores 0.25. Whether it should allow
  a meaningful blank was not resolved, so no policy change was made.
- Feed-control state handling is still substantial. Further splitting should
  serve a concrete maintenance need and preserve overrides, widget identity,
  and the different starting/reviewing behaviors.

Do not assume publication status from this document. Inspect Git and deployment
state when asked. In this session the user chose to push using GitHub Desktop;
that is not standing authorization for an AI to push later changes.
