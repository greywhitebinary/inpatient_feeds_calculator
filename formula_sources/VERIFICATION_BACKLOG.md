# Verification backlog

> Dated verification and decision record. Completed sections describe the code
> and data at their stated dates; later entries may supersede earlier ones.
> Current application maintenance is recorded in
> [Calculation and record flow](../docs/CALCULATION_FLOW.md).
> Product-data rules live in [Data conventions](DATA_CONVENTIONS.md).
> Open data questions remain below with their original evidence and context.

Deferred work, recorded so it can be resumed without repeating the analysis.
Conventions referred to here are in `DATA_CONVENTIONS.md`.

## Completed 2026-09-02

Every row in `formulary_working/` was checked field by field against its cited
source document, recomputing each per-millilitre conversion rather than reading
it off. 94 rows across the three CSVs: 21 formula, 26 ONS and 3 modular rows
against the Nestlé guide; 8 formula, 28 ONS and 1 modular row against the
Abbott guide; 4 formula rows against the individual Abbott product information
sheets; 3 modular rows against the Medtrition/CMI Canada panels.

Scope was the eleven fields the application actually reads. The vitamin and
trace-mineral columns were **not** checked — see item 3.

Two numeric errors were found and corrected:

- **Pivot 1.5 Cal** — `fat_per_mL`, `carbohydrate_per_mL` and `fibre_per_mL`
  were understated about 2.4-fold. The Abbott product guide's "Per 237 mL"
  column prints the fat, carbohydrate and fibre blocks as per-100-mL values,
  and the transcription divided those by 237. Re-sourced to
  `Pivot-1.5-Cal-en.pdf` p.3.
- **Peptamen AF 1.2** — `fibre_per_mL` was 0.005 where the panel gives
  0.52 g/100 mL. Corrected to 0.0052.

`2026PRG.pdf` was deleted from the local reference folder: it is the Nutricia
Product Reference Guide for US clinicians, so it is off-scope on both country
and age, and no row cited it.

---

## Clinical and math review, 2026-09-02

A review of the equation layer, the unit boundaries, and the plan workflow,
covering `calculations.py` against published equation forms and the assessment,
plan and chart-note modules against how the numbers are actually used.

**Verified correct and unchanged.** Hamwi, Devine, adjusted body weight at 0.25,
Mifflin-St Jeor, Harris-Benedict (Roza-Shizgal 1984) and both Penn State forms
all match their published coefficients. Every atomic weight in
`ATOMIC_WEIGHTS_MG_PER_MMOL` is correct, and phosphorus is handled as elemental
P, matching how labels report it. Propofol at 1.1 kcal/mL and 0.1 g fat/mL is
right for a 10% emulsion, and its energy and fat are not double-counted.
`water_plan` counts each component exactly once, including through
`other_water_flushes`. The 5 mL rate rounding deviates up to 20% at low rates,
but the plan check displays goal, total and signed difference, so it is visible
rather than hidden; hydration flush rounding drifts by at most 20 mL.

### Penn State weight basis — fixed

The Mifflin term feeding both Penn State equations took whichever weight was
chosen in the assessment selector. Selecting an adjusted weight understated
Penn State 2003b by 538 kcal/day in a worked case (62-year-old man, 178 cm,
150 kg, Tmax 38.5 C, Ve 9.0 L/min), and the error reached the chart note.

The rule now: **Penn State uses only the current body weight or the
clinician-selected weight, whichever the selector names, and the rows are
withheld entirely when an ideal or adjusted weight is selected.**

Withheld rather than recomputed, deliberately. Substituting a different weight
would contradict the clinician's own selection and put two different weights on
one table; the whole table now uses one weight or omits the rows. Per-equation
weight pickers were considered and rejected as more friction than toggling one
selector, since an RD entering ventilation inputs has already used it.

This rule was reworked several times before settling. Earlier attempts pinned
Penn State to the measured weight always, then let an entered clinician weight
override the selector. Both produced a table showing two different weights,
which is the thing the final rule avoids. Do not reintroduce either without
also solving that.

Note the open clinical question the rule deliberately does not answer: whether
a measured weight remains right after fluid resuscitation. The equations were
fitted using measured weight, but the Penn State work is not known to address
gross fluid overload, and practice varies. The tool hands that judgment to the
clinician through the weight selector rather than deciding it.

Both equations are labelled with their population in the `Method` column and
both are always shown; age and BMI gate nothing.

### Water goal now optional — fixed

The plan was blocked until energy, protein **and** water goals were entered. On
a patient receiving IV fluid the enteral water calculation is not the one being
managed, so the clinician had to type a placeholder — and the tool then sized
hydration flushes against it and emitted "Hydration: Provide N mL water flushes
q6h" into the chart note. A placeholder became an order.

`water_plan` now accepts `None` as the target, which is a different state from a
zero goal. With no goal the hydration schedule controls are hidden, the water
row drops out of the plan check, and the chart note omits the hydration line.
Medication and patency flushes still apply, since those are ordered
independently, and free water still appears in the daily intake table.

Goals are shared across the EN plan and Propofol tabs: `render_assessment_goals`
mirrors the single assessment goal into the `en_` and `icu_` keys on every run.
One patient, one goal, two planning modes. That is why a second example record
demonstrating the no-goal path is not worth carrying.

### Daily totals table notes — added

Three cells in that table do not mean what a reader scanning it would assume.
Each note is conditional, so a plain plan carries none, and they now render on
both the EN plan and the Propofol tabs (previously only the former).

- ONS free water counts toward the total but does not size hydration flushes.
- Propofol volume is fluid but is not counted as free water. It is displayed,
  not subtracted: the clinician already sets the water goal net of IV, so
  subtracting it again would double-count.
- Undisclosed modular minerals render as a dash rather than a zero.

### Withdrawn

Additional protein losses are computed and displayed but not carried into the
protein goal. That is by design — the RD sees the figure and decides whether to
include it. Not a defect.

### Terminology

"RD" was removed from everything a clinician sees — the assessment table, the
chart note, and the `administration_note` text that ships in the exported My
Modulars sheet. It now reads "clinician" throughout. The dietitian designation
is a protected title and varies by jurisdiction, so the neutral term avoids
implying a credential the reader may not hold. Two internal uses remain and are
not displayed: the `preparation_water_rule` enum value `rd_entered`, and a
docstring in `session_state.py`.

Weight terms are introduced in full with their acronym in the Measurements and
weight history table, and used as acronyms alone everywhere after it. Only the
Hamwi row carries `IBW`, because that is the ideal weight the calculator uses;
the Devine row is spelled out as a medication-dosing reference so the two are
not confused.

### Example record

Gained `assessment_temperature` and `assessment_minute_ventilation` so the Penn
State rows appear at all. The record's patient has a BMI of 23.5, so the
population labels demonstrate that the modified 2010 equation does not apply and
2003b does.

---

## 1. Blank versus zero at runtime — DONE 2026-09-02

`data.py` keeps the six modular mineral and free-water columns null through
loading and through the workbook export/import round trip, so a saved formulary
no longer converts an unknown into a zero on reload.
`calculations.disclosed_value()` splits each cell into its value and whether the
label declared it; `modular_delivery` reports per-nutrient disclosure and counts
a product only when a dose is actually entered; `total_modular_delivery`
accumulates both. The daily intake table renders an em dash instead of `0.0`
where no ordered product declared a figure, with a caption naming the nutrient
and the products.

Before this, the modular row of that table always showed 0.0 mmol phosphorus and
0.0 mmol magnesium, because every modular row has those cells blank.

Scoped to the modular columns, where the panels genuinely do not declare the
figure. Formula and ONS fibre blanks were left zero-filled on purpose; see
`DATA_CONVENTIONS.md` section 1.

Not done, and worth considering later:

- The **Total** row is now a lower bound whenever a contributor is undisclosed.
  It renders as an ordinary number, with the caption as the only signal.
- **Free water for the two liquid Medtrition modulars** is undisclosed but is
  not flagged, because each row's `administration_note` already documents that
  the water content is not counted. Revisit if that note stops being displayed.
- An explicit **"3 of 4 sources" column** was not added. The caption carries the
  same information in prose and names the products, which is more use to a
  dietitian than a bare ratio, but a column is a small addition if wanted.

## 2. Page citations — DONE 2026-09-02

Every guide citation now states its numbering scheme, `(pdf page)` or
`(printed folio)`. 28 formula, 3 modular and 54 ONS citations were labelled;
one modular row (BOOST Just Protein) is a folio citation and is labelled as
such. Product information sheets and Medtrition images are not spreads and
carry no label. The rule and the conversion arithmetic are in
`DATA_CONVENTIONS.md` section 5.

Labels were added rather than converting the numbers, because recomputing 54
verified page references would risk introducing errors to remove an ambiguity
that a label already removes.

## 3. Verify the vitamin and trace-mineral columns — values verified 2026-09-04

**The owner reopened this on 2026-09-04, wanting the micronutrients tracked, so
the deferral from 2026-09-02 no longer stands.** All 594 values in
`canada_formulas_working.csv` were checked against the cited page of the cited
document, and the full account is in `MICRONUTRIENT_VERIFICATION.md`. Four
blank cells were filled where the source discloses the figure: beta-carotene
for Jevity 1.2 Cal and Osmolite 1.2 Cal, and retinol for Jevity 1.5 Cal and
TwoCal HN, whose sheets name no beta-carotene in either the panel or the
ingredient list, so their vitamin A is entirely retinyl palmitate. Nothing else
was changed.

The display and validation work described as pending in earlier versions of
this section has been completed. See [the display decision](#5-micronutrients-on-screen--built-2026-09-04)
and [the current calculation and missing-data behavior](../docs/CALCULATION_FLOW.md).
The 18 formula micronutrient columns are consumed by the application, and the
September 12 repairs preserve unknown values rather than silently filling zeros.

Two owner questions from this review remain: how to mark Compleat Organic
Blends 1.25's dietary beta-carotene conversion, and whether to derive Pivot
1.5 Cal retinol by subtraction. Their evidence is retained in
[the micronutrient review](MICRONUTRIENT_VERIFICATION.md#judgment-calls-left-to-the-owner).
The separate Pivot citation question was resolved below.

## 4. Smaller items

### Done 2026-09-02

- **Fibre representation is now consistent.** 13 formula rows carried a blank
  where the panel has no fibre row; they now carry an explicit `0`, matching the
  37 ONS rows and the one formula row (Osmolite 1.2 Cal) that already did. All
  13 were verified fibre-free, so `0` states a declared absence rather than
  guessing. This is the precondition `DATA_CONVENTIONS.md` section 1 names
  before formula fibre blanks could ever be treated as undisclosed.
- **BanatrAll** `dose_unit` and `basis_description` now say "package", matching
  the label.
- **`ONS_VERIFICATION.md`** row count corrected from 52 to 54.

### Decided 2026-09-04

- **Pivot 1.5 Cal citation.** The row's values are unchanged and stay as they
  are. Its sheet prints a 237 mL and a 100 mL column, and the row divides by
  each in turn: the macronutrients by 237, the vitamins and minerals by 100.
  That is defensible under section 4 of `DATA_CONVENTIONS.md`, because neither
  column is uniformly finer — folic acid reads 0.037 mg per 100 mL against
  0.09 mg per 237 mL, while copper reads 0.52 mg per 237 mL against 0.2 mg per
  100 mL — and the two columns agree to within 1.5% throughout. What was wrong
  was the citation, which claimed the 237 mL column for the whole row. It now
  names both columns and the block each one supplied, the page range is
  corrected to p.3-4 because the trace minerals sit on the following page, and
  the reasoning is recorded in the row's new `data_note`.

- **Jevity 1.2 Cal `free_water_per_mL`** is now `0.807`, down from `0.807333`.
  The stored figure came from the product sheet's Per 1500 mL column (1211 g),
  while the same sheet's per-100 mL column implies 0.810 and the general guide
  says 810 g/L. The owner ruled that the disagreement is rounding in the source
  document rather than a real difference, so the value keeps the column it was
  sourced from and drops the trailing digits that document cannot support. The
  spread across the three readings is about 3 mL of water per litre of feed, and
  a plan running 1.5 L/day now reports roughly half a millilitre less free water
  than before, which no clinical decision turns on.

### Still open — each needs an owner decision, not a fix

- **"Not a significant source of" is a labelling threshold, not a zero.** BOOST
  Soothe's potassium, calcium, magnesium and phosphorus, and several Beneprotein
  and MCT Oil fields, are stored as 0 on the strength of that phrase. Under
  section 1 these are arguably undisclosed. Storing 0 slightly understates a
  real but sub-threshold amount; storing a blank would render them as a dash and
  lose the information that the amount is known to be small. Neither is clearly
  right.
- **Flavour annotation — resolved in later work.** The original annotation
  question is addressed by the `own_panel`, `representative`, and
  `stated_representative` provenance values. See the
  [flavour surveys](ONS_FLAVOUR_SURVEY.md) and
  [September 11 investigation](#6-re-base-the-nestlé-ons-rows-on-the-professional-site--closed-2026-09-11-not-possible-from-this-source).
  Missing flavour-specific manufacturer figures remain an evidence limitation,
  rather than an instruction to replace them with invented values.

## 5. Micronutrients on screen — built 2026-09-04

The owner's position is that vitamins are rarely looked at in acute care, so an
18-nutrient table would not earn its place on the plan screen. The question that
does get asked is whether the patient is receiving enough volume for the feed's
micronutrients to add up to anything, which matters on a fluid restriction, on a
concentrated 2.0 kcal/mL feed, on trophic feeds, and for anyone living on ONS
alone.

`dri_volume_ml` and `dri_micronutrients_met` now carry the manufacturer's own
answer for the 21 Nestlé rows, transcribed from the same product page each row
already cites. See `DATA_CONVENTIONS.md` section 8 for what the figures mean and
for the reference population the claim is written against.

**The display shows amounts and passes no judgment (owner's call, 2026-09-04).**
An earlier proposal here was a plan-check line comparing planned volume against
the stated volume. The owner rejected it: the tool reports what the feed
delivers, and whether that is enough is the clinician's call. So
`render_micronutrient_panel` lists the sixteen micronutrients a panel declares,
scaled to the volume on screen, inside an expander that stays shut. No amount is
compared with a reference intake anywhere in the application.

That decision also settles the Abbott gap, since nothing is being computed
against a reference. `dri_volume_ml` and `dri_micronutrients_met` stay in the
data as verified manufacturer figures, reaching no module, available if the
question is ever asked again.

Still to do:

- **Vitamin K.** Not in the CSV at all, though both guides print it on every
  panel. It is the one micronutrient in a feed that changes a drug decision,
  through warfarin and the INR. Adding it means one column and 33 values.

---

## 6. Re-base the Nestlé ONS rows on the professional site — CLOSED 2026-09-11, not possible from this source

**The question.** Fourteen of the 26 Nestlé rows in `ons_products_working.csv`
carry the guide's single panel rather than their own flavour's, marked
`representative` (twelve) or `stated_representative` (two) in `value_source`.
A patient on chocolate is shown vanilla's numbers. Two further rows, BOOST 2.24
— Chocolate and BOOST Pudding — Chocolate, cite the consumer shop because the
guide prints no chocolate panel. This item asked whether the professional site
at `https://www.nhsc-pro.ca/pwa/en/products` could re-base them.

**It cannot.** The site was read on 2026-09-11 through a real browser, which is
what it needs; it is an offline-first Ionic application that caches its whole
catalogue (51 products) in IndexedDB under `_ionicstorage`, key `produtos-en`.
Each product carries its nutrition information as a **single image**, not as
structured data, in `tabelaNutricional`. Every one of the ten in-scope BOOST
products has exactly one such image, and every one is headed with a single
flavour:

- Nine are headed **"Vanilla Flavoured"**: BOOST 1.5, 2.24, CarbSmart, High
  Protein, Original, Plus Calories, Protein+, Pudding, Soothe.
- BOOST Fruit Flavoured is headed **"Orange Flavoured"**, which independently
  confirms the `stated_representative` marking on its peach and wildberry rows.

Other flavours appear on the site only as **order codes** in the ordering table
(for example "24 x 237 ml Tetra Prisma chocolate latte"), never as nutrition
figures, and the ingredient list is explicitly headed "INGREDIENTS (VANILLA
FLAVOUR)". The site publishes exactly the structure the printed guide does: one
panel per product, named for one flavour. No chocolate, strawberry or
chocolate-latte panel exists on it.

So the fourteen rows stay as they are, correctly labelled. **No stored value
changed as a result of this work.** The remaining routes to per-flavour figures
are the consumer shop, which covers only four products and is weaker evidence,
or asking Nestlé directly, which is the escalation `DATA_CONVENTIONS.md`
section 3 prescribes when a Canadian document omits a clinically important
figure.

**Where the site does carry water content.** Not in the nutrition panel, and
not in `caracteristicasTecnicas`, which is empty for these products. It is in
the **"FEATURES AT-A-GLANCE"** accordion section, which is a second image
carrying caloric density, the protein/carbohydrate/fat energy split, the
ingredient sources, **water content**, osmolality, kosher and gluten-free
status, lactose and residue. BOOST 1.5 reads "Water content 180 ml/237 ml" and
"Osmolality 920 mOsm/kg water", and its stored `free_water_per_mL` of 0.75949
matches exactly. Like the nutrition panel, this is one image per product rather
than one per flavour, so it does not bear on the flavour question either.

An earlier version of this item claimed the panels carry no water content at
all. That was wrong, and was written after checking only the nutrition table
and the technical-characteristics field. The owner pointed to the features
section, and it is there.

**BOOST 1.5 re-verified, 2026-09-11.** The guide carries the same FEATURES
AT-A-GLANCE block in full at printed folio 30 (pdf page 16), and every stored
value for vanilla, chocolate and strawberry matches the guide's 237 mL column
exactly, free water included at 180 mL/237 mL.

**What the visit was worth.** Two rows were verified against a source
independent of the guide, and every field matched exactly, per 237 mL:

    BOOST Original — Vanilla        230 Cal, 10 g protein, 34 g carbohydrate,
                                    6 g fat, Na 265, K 410, Ca 308, P 265, Mg 90 mg
    BOOST Fruit Flavoured — Orange  180 Cal, 9 g protein, 36 g carbohydrate,
                                    0.5 g fat, Na 15, K 35, Ca 79, P 200, Mg 40 mg

That is the cross-check `DATA_CONVENTIONS.md` section 6 asks for, and it is
reassurance about the guide transcription rather than a new source of record.
The remaining eight vanilla panels could be checked the same way if the
guide's transcription is ever doubted; the images are one HTTP request each,
listed in `produtos-en`.

**Guide against website, tested 2026-09-11.** Four Nestlé products were
compared field by field between the professional site and the 2026 guide:
BOOST Original and BOOST 1.5 (site assets dated 2026-07), BOOST Fruit Flavoured
orange (2024-12) and BOOST Plus Calories (2022-08). **All four agree exactly,
and the stored rows agree with both.** BOOST Plus Calories is the useful case:
its web panel is four years older than the guide edition and is nonetheless
identical row for row, including the full fat breakdown, all thirteen vitamins,
choline and chloride. An old asset date means the panel has not been reissued,
not that its figures are stale, so a date gap is not evidence of divergence.
No disagreement between Nestlé's website and its guide has yet been observed.

**A provenance note worth keeping.** The site's own footer says: "In the event
of a discrepancy between website information and product packaging, please
refer to product packaging." Nestlé puts the package above its own website, so
the site does not automatically outrank the printed guide where the two
disagree; a disagreement is a question, not an automatic correction.
