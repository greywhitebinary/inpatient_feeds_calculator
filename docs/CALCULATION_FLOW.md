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

The starting-feed target defaults to 100%. Switching to review mode and back
preserves the selected planning percentage, including a custom value such as
50%. Review mode compares the running order with the full assessed requirement;
it does not overwrite the saved planning percentage. The percentage input must
also reopen with that saved value in the browser, rather than its minimum (1%).

For starting feeds, changing formula resets the entered order to the new
formula's suggestion. With the same formula, changing the energy goal or
feeding hours preserves a manually entered rate while updating the suggestion.
For example, 40 mL/hour stays 40 when hours change from 24 to 16; daily delivery
falls accordingly. “Use suggested rate” explicitly applies the new suggestion.

Changing between continuous feeding and intermittent entry forms while starting
feeds uses the target to suggest the new rate or volume, rather than converting
the previous manual order to preserve its daily volume. For example, with a
1,800 kcal target, a 1.5 kcal/mL formula and no IV or propofol calories, switching
from a manual 40 mL/hour continuous order to four volume-based feeds suggests
300 mL per feed, not 240 mL per feed.

Changing IV dextrose or propofol inputs updates the suggested enteral-feed rate
without replacing a manually entered feed rate. The user may deliberately
explore higher or lower provision. Keep the suggestion visible and let “Use
suggested rate” (or “Use suggested volume”) apply it explicitly. This is a rule
about the feed order, not about automatically altering the entered IV or
propofol dose.

Achieved formula-delivery percentage answers a separate question: how much of
the entered formula order was delivered. It changes the estimated intake view;
it does not rewrite the prescription or the full planned chart note.

The user reconfirmed the IV-water rule on 2026-09-12: IV fluid is not
subtracted automatically from the entered water goal. For example, a goal of
2,000 mL with 600 mL of formula water and no other counted water contributions
produces 1,400 mL of additional hydration flushes, even with an IV running.
The clinician may leave the goal blank or enter a lower goal after considering
IV provision. Keep IV volume visible separately; do not reinterpret the goal
as total fluid inclusive of IV, or add IV volume to the reported water total.

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

The subsequent mode-switch repair preserves the planning target while its
input is hidden and explicitly initializes the returning browser input from
the saved value. A real browser reproduced the original 100% → 1% display
failure, which AppTest's reported value alone did not expose. Regression tests
cover repeated mode switches with default and custom targets on both feeding
tabs, the serialized input default, and manual-rate preservation when hours
change. The UI layout and clinical equations are unchanged.
The focused validation passed 129 tests across planning regressions, application
rendering, workflow save/reopen, case import/export, and goal-state handling;
Ruff and Black passed for the changed Python files. Browser checks confirmed
100% and 50% restoration on the standard tab and 100% on the propofol tab.
After the final workflow decisions, all 28 planning-regression tests passed,
including added checks for goal, IV, and propofol changes preserving manual
feed rates until “Use suggested” is clicked, and continuous-to-intermittent
conversion using the target. Ruff and Black passed again for the changed files.

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
  change. The user considers this naming collision unrealistic for the actual
  formulary, so it is not a repair priority.
- The regimen check preserves its original water addition order. Regrouping
  floating-point additions can alter integer display rounding at a half-mL
  boundary. Its dedicated totals in `plan_sources.py` are intentional; tests
  cover this. This display-rounding difference does not feed back into the
  rate or hydration-flush calculation and is not a repair priority.
- Unsupported weight-choice strings in manually malformed case workbooks can
  pass import and then reset to UI defaults. Current UI exports cannot create
  those values. This is low-priority validation of externally altered files,
  not a demonstrated failure of ordinary saved-case restoration.
- The user confirmed that the adjusted-weight factor should default to 0.25
  and remain editable. Restoring that default after clearing is accepted
  behavior, not an unresolved defect.
- Feed-control state handling is still substantial. Further splitting should
  serve a concrete maintenance need and preserve overrides, widget identity,
  and the different starting/reviewing behaviors.

Do not assume publication status from this document. Inspect Git and deployment
state when asked. In this session the user chose to push using GitHub Desktop;
that is not standing authorization for an AI to push later changes.

## Application file map

- `webapp/app.py` is the small Streamlit entry point and page orchestrator.
- `webapp/assessment_ui.py` contains the assessment workflow and its authoritative EN goals.
- `webapp/plan_ui.py` coordinates the shared EN workflow and passes results to reporting.
- `webapp/plan_order.py` defines explicit feed orders and formula-energy allocations.
- `webapp/plan_sources.py` calculates source rows and totals without screen or session state.
- `webapp/plan_feed_controls.py`, `webapp/plan_supplements.py`, `webapp/plan_hydration.py`, and `webapp/plan_review.py` render the existing workflow sections.
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


## UI compatibility checks

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
