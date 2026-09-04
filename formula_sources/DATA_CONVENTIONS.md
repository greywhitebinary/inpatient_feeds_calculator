# Data conventions for the runtime CSVs

This file states the rules that `formulary_working/*.csv` follow. It is the
document that `reference_documents/canada/medtrition/README.md` refers to.

## 1. Blank versus zero

A blank cell means **the manufacturer did not disclose the value**. A zero
means they disclosed a zero.

These are different facts and must not be merged. A blank should count the
product as "not supplying a figure" and say so, whereas a zero is a measured
absence that legitimately drags a total down. Never fill a blank with 0 to
tidy the table.

The application honours this for the modular mineral and free-water columns.
`data.py` keeps those columns null through loading and through the workbook
round trip, `calculations.py` splits each cell with `disclosed_value()`, and the
daily intake table shows an em dash with an explanatory caption where no ordered
product declared a figure.

**One deliberate exception.** Formula and ONS `fibre_per_mL` blanks are still
zero-filled. A blank there means the panel has no fibre row because the product
is fibre-free, which is a declared absence rather than a missing figure. Ten
products are in that position, and flagging them would raise an alarm where
nothing is unknown, which trains the reader to ignore the flag. Give those rows
an explicit 0 before changing this.

## 2. What a source document is capable of disclosing

Whether a blank is expected depends on the *class* of document the row was
read from, not on the manufacturer's choice.

| Class | Rows | Discloses magnesium, phosphorus, water? |
|---|---|---|
| Nutrition Facts panel | the three Medtrition/CMI Canada modulars | No. A Canadian Nutrition Facts table carries only the core set: energy, fat, carbohydrate, fibre, sugars, protein, cholesterol, sodium, potassium, calcium and iron. |
| Healthcare-professional product guide | Nestlé and Abbott product-guide rows | Yes |
| Healthcare-professional product information sheet | the Abbott per-product sheets | Yes, and usually at higher precision |

A blank in a field the document class cannot carry is a structural unknown and
is expected. A blank in a field the class normally carries is an anomaly and
should be reviewed.

This distinction matters clinically. ProSource NoCarb lists Phosphoric Acid and
Sodium Phosphate among its ingredients, so phosphorus is certainly present, but
its Nutrition Facts panel cannot disclose a figure. The honest statement is
"not disclosed by this document type", not zero.

## 3. Do not mix jurisdictions

Canadian rows are populated only from Canadian documents. US product documents
must never be cited in a `source` column or copied into a Canadian row, even
when they disclose a figure the Canadian document omits.

Medtrition, Inc. is represented in Canada by CMI Canada, whose range is smaller
and differently named than the US catalogue. US sheets have two legitimate uses
only: corroborating that two documents describe the same formulation, and
raising a question to put to the manufacturer. Neither is a source of values.

Where a Canadian document omits a clinically important figure, the escalation
is to ask CMI Canada, not to borrow the US number.

## 4. Precision

Store values at the precision the arithmetic gives; do not round in the CSV.
The web interface rounds for display, usually to one decimal place or to a
whole number, because most stored decimal places are not clinically meaningful.
Display rounding is deliberate and is not a reason to round the stored data.

## 5. Page citations

The `source` column is the row-level map to document and page.

Both manufacturer product guides are printed as spreads, so each physical PDF
page carries two printed folio numbers. A bare page number is therefore
ambiguous, and the two schemes collide: `p.18` is Compleat 1.06 under one and
BOOST Original under the other.

**Every guide citation states its scheme explicitly**, as `(pdf page)` or
`(printed folio)`. Resolve a citation the way its own label says, and label any
citation you add. Product information sheets and the Medtrition images are not
spreads, so they carry no label.

The Nestlé guide converts as `printed = 2 x pdf_page - 2`; the Abbott guide's
PDF sheet *N* carries printed pages *2N-4* and *2N-3*. Prefer `(pdf page)` for
new citations, since that is the number a reader types into a PDF viewer.
Existing folio citations were labelled rather than converted, because
recomputing 54 verified page numbers would risk introducing errors to fix an
ambiguity that a label removes.

## 6. Cross-checks that catch transcription errors

Two independent checks have each caught a real error in this data.

**Column cross-comparison.** Where a document prints the same product on more
than one basis (per 100 mL, per container, per litre, bag versus carton),
convert each column to a common basis and compare. Divergence means either the
document is defective or the transcription used the wrong column. This is how
the Jevity, Osmolite, and TwoCal HN errors were found.

**Energy reconciliation.** Compute `protein x 4 + fat x 9 + carbohydrate x 4`
and compare with the declared `kcal_per_mL`. Every correct row in this file
lands between 98% and 106%. Pivot 1.5 Cal read 57% before it was corrected on
2026-09-02. Run this after any bulk data change:

```sh
python3 -c "
import csv
for r in csv.DictReader(open('formulary_working/canada_formulas_working.csv',encoding='utf-8-sig')):
    k=float(r['kcal_per_mL'])
    calc=float(r['protein_per_mL'])*4+float(r['fat_per_mL'])*9+float(r['carbohydrate_per_mL'])*4
    pct=calc/k*100
    if pct<95 or pct>110: print(f'{pct:6.1f}%  {r[\"name\"]}')
"
```

## 7. The `data_note` column

`canada_formulas_working.csv` carries a free-text `data_note` beside `source`
and `verified`. It records why a row holds the value it does where the citation
alone does not explain it, such as which basis column of a panel that prints
two was divided, or which conversion factor the ingredient list dictates. It is
maintainer-facing and is displayed nowhere in the application.

An empty cell means the row needs no explanation, so `data.py` fills a blank
note with an empty string rather than the zero every other column receives.
Write a note whenever a future maintainer re-deriving the row from the cited
page would get a different answer than the one stored.

## 8. Micronutrient adequacy volumes

`dri_volume_ml` is the daily volume at which the manufacturer states the feed
meets the Dietary Reference Intakes, and `dri_micronutrients_met` is how many
micronutrients that claim covers. The count travels with the volume because it
varies and changes what the claim is worth: most products meet 25, but Compleat
1.5 meets 24, NovaSource Renal 22, Tolerex and Vivonex Plus 21, and Vivonex
T.E.N. 20. A renal or elemental formula reaching its volume is therefore not
the same assurance as a standard polymeric one reaching its own.

Only the Nestlé guide publishes these figures, one per product page, so all 21
Nestlé rows carry them and all 12 Abbott rows are blank. Neither the Abbott
adult product guide nor any of the four Abbott product information sheets makes
an adequacy claim of any kind. A blank therefore means the manufacturer states
no volume, not that the feed never meets the DRIs, and it must not be
zero-filled: a zero here would read as "meets the DRIs in 0 mL". `data.py`
keeps both columns null through loading and the workbook round trip.

Nestlé's comparison group matters when the figure is shown to a clinician. The
guide's DRI page (printed folio 123, pdf page 62) states that adult products
are compared against the DRIs for **males 31-50 years**, and names its own
exceptions: vitamin D for ages 71+, calcium for males and females 51+, and iron
for females. Anything that displays this volume should say which group it
refers to, since a woman over 50 is not the person the claim was written about.

