# Canadian formula micronutrient verification

`formulary_working/canada_formulas_working.csv` was reviewed on 2026-09-04
against the manufacturer document each row's `source` column cites. This
covers the 18 micronutrient columns that `VERIFICATION_BACKLOG.md` item 3 had
deferred: `vitamin_a_rae_ug_per_mL`, `retinol_ug_per_mL`,
`beta_carotene_ug_per_mL`, `vitamin_d_ug_per_mL`, `vitamin_e_mg_per_mL`,
`vitamin_c_mg_per_mL`, `thiamine_mg_per_mL`, `riboflavin_mg_per_mL`,
`vitamin_b6_mg_per_mL`, `pantothenic_acid_mg_per_mL`,
`niacin_preformed_mg_per_mL`, `iron_per_mL`, `zinc_mg_per_mL`,
`copper_mg_per_mL`, `manganese_mg_per_mL`, `folate_dfe_ug_per_mL`,
`vitamin_b12_ug_per_mL` and `selenium_ug_per_mL`. All 33 product rows and all
18 columns were checked — 594 cells in total — against the cited page of the
cited document, with every conversion recomputed from the panel's own basis
rather than read off a per-mL figure.

As item 3 records, these columns reach no displayed number today: they sit
outside `FORMULA_REQUIRED_COLUMNS` and `FORMULA_NUMERIC_COLUMNS`, so `data.py`
does not validate them and no module reads them. That did not change during
this review; the task was verification only, and no application or display
code was touched.

None of the 33 rows in this CSV are sourced from a Nutrition Facts panel. All
21 Nestlé rows and all 7 Abbott-guide rows come from a healthcare-professional
product guide, and the remaining 5 rows come from an Abbott product
information sheet. Under `DATA_CONVENTIONS.md` section 2, both of those
document classes can disclose vitamins, so the "Nutrition Facts panels
disclose few or no vitamins" caveat that motivated this task does not apply to
any cell checked here. That situation is confined to the three Medtrition/CMI
Canada modular rows, which live in `modular_products_working.csv` and were
out of scope for this review.

## Method and the conversion factors it confirmed

Both source guides print vitamins in International Units (IU) for vitamin A,
D and E rather than in the RAE/mcg units the CSV stores, so every one of
those three columns required a unit conversion, not just a per-mL division.
Working through product after product against known-correct neighbouring
values (protein, fibre, sodium, already verified in the 2026-09-02 pass)
let the following conversions be confirmed empirically before being applied
everywhere:

- **Retinol**: 1 IU retinol = 0.3 mcg.
- **Beta-carotene**: 1 IU beta-carotene = 0.6 mcg beta-carotene (this is a
  straight mass conversion, independent of source).
- **Vitamin A RAE total**: where the panel adds a supplemental beta-carotene
  to a vitamin A palmitate base (confirmed from the ingredient list), 1 mcg
  RAE = 1 mcg retinol + 0.5 mcg beta-carotene, which collapses to
  `vitamin_a_rae_ug_per_mL = total_vitaminA_IU_per_mL x 0.3` whenever the
  panel's printed "Vitamin A" total already equals retinol IU + beta-carotene
  IU. This matched every row that fortifies with added beta-carotene.
- **Vitamin D**: 1 IU = 0.025 mcg.
- **Vitamin E**: 1 IU = 0.45 mg when the ingredient list names
  **DL**-alpha-tocopheryl acetate (the synthetic, all-rac form), but 1 IU =
  0.67 mg when it names **D**-alpha-tocopheryl acetate or d-Alpha-Tocopheryl
  Acetate (the natural form). Nepro, Suplena and Pivot 1.5 Cal use the
  natural form; every other row in this file uses the synthetic form. The
  existing data already applied the correct factor per product — this review
  confirmed rather than changed it.
- **Folate DFE**: `folate_dfe_ug_per_mL = folic_acid_mcg_per_mL x 1.7`, the
  standard dietary-folate-equivalent factor for synthetic folic acid consumed
  with food. Confirmed against every row that lists folic acid.
- **Vitamin B12 and selenium**: printed in mg on every panel; converted to
  mcg by x1000, no other factor.
- **Iron, zinc, copper, manganese, thiamine, riboflavin, vitamin B6,
  pantothenic acid, niacin, vitamin C**: printed directly in the target units
  (mg), so only the basis division was needed.

Where a panel prints more than one basis column (100 mL and a larger
container, or 100 g and a reconstituted-volume packet), the higher-precision
column was used for the division, per `DATA_CONVENTIONS.md` section 5, and
cross-checked against the other column. The two elemental powders' "per
X mL" columns already state the reconstituted volume in a footnote (e.g.
"Each 80 g packet mixed with 255 mL water yields 300 mL of prepared
formula"), so those columns were divided by that reconstituted volume, not
treated as a second concentration basis.

Text was pulled from the PDFs with `pdftotext -layout` and cross-checked
against the rendered page image for a sample of pages in each source
document (Nestlé pages 18–21, 26, 33; Abbott guide page 17; all five Abbott
product information sheets in full) to confirm the text layer was not
dropping or misplacing digits. One transcription slip on my part during that
cross-check (misreading a manganese figure on a rendered Vivonex Plus page
image as 0.3 instead of 0.33) was caught by comparing against the text layer
before it could be reported as a data error — the CSV was already correct
there.

A value was treated as matching when it fell within about 3% of the
recomputed figure, which is inside the rounding a 2–3 significant-figure
label routinely introduces (for example, Compleat 1.06's iron works out to
0.0128 mg/mL from its 250 mL column and 0.0130 mg/mL from its 100 mL column;
the CSV's 0.013 is defensible against either). No genuine transcription error
was found sitting inside that tolerance band across the whole file — the
largest few remaining gaps, all under 3% and all traceable to which of two
basis columns was divided, are: Isosource Fibre 1.2 and Isosource 1.2 iron
(2.8%), Resource Diabetic 1.05 iron (1.8%), and NovaSource Renal's block of
values computed from its 237 mL column (all under 0.8%). None were changed.

## Results by source document

**Nestlé guide (`2026_nestle-product-guide.pdf`), 21 rows** — Isosource Fibre
1.5, Isosource Fibre 1.2, Isosource Fibre 1.0 HP, Peptamen AF 1.2, Peptamen
Intense 1.0 HP, Resource 2.0, Peptamen 1.5, Compleat 1.06, Compleat 1.5,
Compleat Organic Blends 1.25, Isosource 1.2, Isosource 1.5, Isosource 2.0,
NovaSource Renal, Peptamen 1.0, Peptamen 1.0 with Prebio1, Peptamen 1.5 with
Prebio1, Resource Diabetic 1.05, Tolerex, Vivonex Plus and Vivonex T.E.N. All
21 rows verified with no corrections needed, subject to the Compleat Organic
Blends note below.

**Abbott guide (`2024_abbott-adult-product-guide.pdf`), 7 rows** — Glucerna
1.2 Cal, Nepro, Jevity 1.0 Cal, Promote, Suplena, Vital Peptide 1 Cal and
Vital Peptide 1.5 Cal. All 7 rows verified with no corrections needed.

**Abbott product information sheets, 5 rows** — Jevity 1.2 Cal, Jevity 1.5
Cal, Osmolite 1.2 Cal, TwoCal HN and Pivot 1.5 Cal. Four corrections found
here (below); every other value in these 5 rows verified.

## Corrections made

Four cells were blank where the cited document actually discloses the
figure. These are not arithmetic slips in an existing number — every other
value in each of these rows checked out — they are cases where a real,
disclosed figure was never transcribed into the CSV.

| Row | Column | Before | After | Source and arithmetic |
|---|---|---|---|---|
| Jevity 1.2 Cal | `beta_carotene_ug_per_mL` | *(blank)* | `1.26667` | `Jevity_1.2_Cal…pdf` p.2, "Beta-Carotene, mg" row: 1.9 mg per 1500 mL. 1.9 / 1500 x 1000 = 1.26667 mcg/mL. |
| Osmolite 1.2 Cal | `beta_carotene_ug_per_mL` | *(blank)* | `1.26667` | `Osmolite 1.2 Cal…pdf` p.2, "Beta-Carotene, mg" row: 1.9 mg per 1500 mL (identical figure to Jevity 1.2 Cal). 1.9 / 1500 x 1000 = 1.26667 mcg/mL. |
| Jevity 1.5 Cal | `retinol_ug_per_mL` | *(blank)* | `0.9` | `Jevity 1.5 Cal…pdf` p.2 lists only "Vitamin A, IU" (4500 per 1500 mL) with no beta-carotene anywhere in the panel or the ingredient list, so the total is entirely retinol: 4500/1500 x 0.3 = 0.9 mcg/mL, the same figure already stored in `vitamin_a_rae_ug_per_mL`. |
| TwoCal HN | `retinol_ug_per_mL` | *(blank)* | `1.5819` | `TwoCal_HN…pdf` p.2 lists only "Vitamin A, IU" (5273 per 1000 mL) with no beta-carotene in the panel or ingredient list, so the total is entirely retinol: 5273/1000 x 0.3 = 1.5819 mcg/mL, matching the stored `vitamin_a_rae_ug_per_mL`. |

All four rows carry the "(1.5-L ready-to-hang)" / "(1-L ready-to-hang)" basis
label already, and the correction was computed on that same labelled basis,
so it is consistent with the rest of each row. Every other value in these
four rows, including every other vitamin and mineral, matched the source
exactly or within normal rounding and was left unchanged.

The precedent for filling in `retinol_ug_per_mL` as equal to
`vitamin_a_rae_ug_per_mL` when a panel discloses only a single "Vitamin A"
figure and no beta-carotene is already used elsewhere in this same file —
Nepro, Jevity 1.0 Cal, Promote, Suplena, Vital Peptide 1 Cal and Vital
Peptide 1.5 Cal all do this. Jevity 1.5 Cal and TwoCal HN were the two rows
where that pattern had not been applied, which is why they read as an
omission rather than a live judgment call.

## Judgment calls left to the owner

**Vitamin A RAE for whole-food beta-carotene (Compleat Organic Blends
1.25).** This is the one row in the file whose beta-carotene is not a listed
vitamin-premix ingredient — the ingredient list has no "beta-carotene" entry,
because the colour comes from real sweet potato, carrot and pumpkin. Its
stored `vitamin_a_rae_ug_per_mL` (1.27) does **not** match the
`total_IU x 0.3` shortcut used everywhere else (which would give 5.6) — it
instead matches `retinol_mcg + beta_carotene_mcg / 12`, the dietary (food)
RAE factor rather than the supplemental (2:1) factor used for a fortified
premix. This is almost certainly correct, and it is a subtler, already-correct
piece of work than a simple total-IU conversion — but it means the file
contains two different RAE formulas for beta-carotene depending on whether it
comes from a supplement or from food, decided row by row from the ingredient
list rather than from anything the "Vitamin A" line itself states. If a future
row is added with food-source carotenoids, this same judgment will need to be
made again by hand; nothing in the data flags which rule an existing row
uses. I did not add a comment column or otherwise mark this, since the task
scope was verification only.

**Retinol left blank on four rows despite a computable total.** Glucerna 1.2
Cal, Jevity 1.2 Cal, Osmolite 1.2 Cal and Pivot 1.5 Cal all disclose a total
"Vitamin A" figure plus a separate beta-carotene amount, but never an
explicit "Retinol" line, so `retinol_ug_per_mL` is left blank on all four
rather than backed out by subtraction. For the first three (Glucerna, Jevity
1.2 Cal, Osmolite 1.2 Cal), the beta-carotene figure is in mg while the
vitamin A total is in IU, so isolating retinol would require assuming an IU
split that the document does not state. For Pivot 1.5 Cal, though, both
figures are in IU on the same panel (Vitamin A 1420 IU, of which
Beta-Carotene is 943 IU, per 237 mL) — retinol is directly computable as
1420 − 943 = 477 IU, without assuming anything. I left it blank anyway, for
consistency with the other three rows and because the panel never prints
"Retinol" as its own line item; but this is a defensible case for filling it
in (477/237 x 0.3 = 0.604 mcg/mL on the 237 mL column, or
(600−398)/100 x 0.3 = 0.606 mcg/mL on the 100 mL column — the two are close
enough that the basis inconsistency noted below would not matter much here).
I am leaving the decision to the owner rather than making the call myself.

**Pivot 1.5 Cal's vitamin and mineral block reads from a different column
than its macronutrient block.** The prior verification round (2026-09-02)
fixed this row's fat, carbohydrate and fibre using the sheet's 237 mL column,
and the macronutrient values still stored today (e.g. `fat_per_mL` = 0.050633
= 12/237 exactly) confirm that basis. But every vitamin and mineral value in
the same row matches the sheet's **100 mL** column, not the 237 mL column
(e.g. `manganese_mg_per_mL` = 0.005 = 0.5/100 exactly, whereas 1.2/237 =
0.00506). The two columns of this particular sheet agree closely — every
difference is under 1.5% — so nothing here reads as a numeric error, and I
did not change any of these values. But the `source` column's label,
"(237-mL column)", does not accurately describe how the vitamin and mineral
figures were actually derived, and the row is not internally consistent on
one basis. The owner may want to either relabel the citation to describe both
columns, or recompute the vitamin/mineral block onto the 237 mL column for
consistency (the resulting changes would all be under 1.5%).

**Rounding noise from basis-column choice, left as is.** A handful of values
sit within 1–3% of the figure the *other* available basis column would give
(listed above, under Method). None of these look like a wrong-column
transcription of the kind `DATA_CONVENTIONS.md` section 6 describes — each
is explainable as ordinary rounding on a 2–3 significant-figure label — so
none were changed.

## Coverage

All 594 cells (33 rows x 18 columns) were checked against the document and
page the row's `source` column cites. No column and no row was skipped. Four
cells were corrected; everything else already matched the source, most of
them exactly.

This review did not re-verify the `source` and `verified` columns themselves
beyond confirming the cited page carries the panel used (i.e., it did not
audit whether "2026-08-27" is the correct verification date, or whether a
better/newer source document exists). It also did not touch
`ons_products_working.csv` or `modular_products_working.csv`, which were out
of scope, and it made no changes to `data.py`, `calculations.py`, or any
other application file — this was a data-correctness pass only, per the task
scope.
