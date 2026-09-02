# Verification backlog

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

## 3. Verify the vitamin and trace-mineral columns — deferred

**Deferred deliberately (owner's call, 2026-09-02): these columns reach
nothing today, so verifying them changes no displayed number. Revisit when the
micronutrient display is built.**

`canada_formulas_working.csv` carries 18 micronutrient columns: iron, vitamin A
(with retinol and beta-carotene), D, E and C, thiamine, riboflavin, B6, B12,
folate, pantothenic acid, niacin, zinc, copper, manganese and selenium.

None of them is read by any module or any test. They are also outside
`FORMULA_REQUIRED_COLUMNS` and `FORMULA_NUMERIC_COLUMNS`, so `data.py` never
checks them for blanks, text or negative values the way it checks sodium or
protein. They are loaded, silently coerced to zero, and ignored.

That is 594 values (33 rows x 18 columns) that would need checking against the
source documents, which would be the largest single piece of the verification.

When the display is built, do these first: add the columns to the validated
numeric set in `data.py` so blanks and text stop passing silently; verify the
values against the source documents; and apply items 1 and 2 to them, since a
Nutrition Facts panel discloses no vitamins at all and every micronutrient
column for the three Medtrition modulars will be a structural blank.

## 4. Smaller items

- **Jevity 1.2 Cal `free_water_per_mL`** is 0.807333, taken from the product
  sheet's Per 1500 mL column (1211 g). The same sheet's per-100 mL column
  implies 0.810, and the general guide says 810 g/L. This sheet omits the
  `Water (g/L)` row the other three carry, so it offers no tiebreaker. The
  stored value is defensible; the gap is about 2.6 mL of water per litre.
- **Fibre representation is inconsistent between files.** Where a panel has no
  fibre row, `canada_formulas_working.csv` leaves the cell blank while
  `ons_products_working.csv` stores 0.
- **"Not a significant source of" is a labelling threshold, not a zero.**
  BOOST Soothe's potassium, calcium, magnesium and phosphorus, and several
  Beneprotein and MCT Oil fields, are stored as 0 on the strength of that
  phrase. Under §1 these are arguably unknowns.
- **Flavour rows inherit one panel.** Multi-flavour ONS products carry a single
  manufacturer panel measured on one flavour. Abbott states explicitly that
  other Glucerna flavours have "a similar nutritional profile", so three of the
  four Glucerna rows assert more than the guide supports.
- **`ONS_VERIFICATION.md` says 52 selectable rows**; the CSV has 54.
- **BanatrAll `dose_unit`** says "packet"; the label says "package".
