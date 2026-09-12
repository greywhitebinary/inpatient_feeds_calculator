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

## 9. Source precedence

Both manufacturers rank their own sources, and neither ranks them the way a
reader might assume. This section records what each one actually says, in its
own words, and what this project holds at each rank. Section 2 is the companion
to it: that one says what a class of document is *capable* of disclosing, this
one says which document wins when two disclose the same field differently.

### The ranking

There are two rankings, they run in opposite directions, and using the wrong one
is how a source gets over-trusted.

**By currency — which source is most likely to be right today.** This is the
manufacturers' own ranking, and it is the one to use when two sources disagree
about a figure they both publish.

1. Product label or packaging. Both manufacturers place this above everything
   they publish themselves, including their own websites.
2. **The official manufacturer website** that each company directs healthcare
   professionals to, meaning `nutrition.abbott/ca` and `nhsc-pro.ca`. These are
   live surfaces, revised page by page as products change, and for Abbott this
   is the only published per-flavour source.
3. Product information sheets. Dated per-product PDFs, usually at higher
   precision than the collated guide, and demonstrably right where the guide was
   wrong.
4. Collated product guide. A PDF is a document assembled once and issued, so it
   is a snapshot that ages from that day and cannot receive a live update. A
   guide edition may therefore trail its own manufacturer's website by years,
   and that is the normal state of affairs rather than a fault.

The gap between ranks 2 and 4 is the practical one, because it is where most
disagreements in this project will arise. Treat a website figure as the later
statement unless there is reason to think otherwise, and see the Nestlé section
below for how to check that assumption cheaply.

**By completeness — which source carries the fields this project needs at all.**
This ranking is close to the reverse, and it is the one that decides which
source a row is built from in the first place.

1. Collated product guide, and the product information sheets where they exist.
   These carry free water, osmolality, chloride, the full vitamin and
   trace-mineral panel and, for Nestlé, the DRI volumes.
2. Manufacturer website product pages, which carry most nutrients but omit some
   of the above unevenly.
3. **Product label or packaging, which is the weakest source for an ONS row.**

That last point is the one most easily got wrong, so it is spelled out. Canadian
packaging carries a **Nutrition Facts table**, a mandatory regulated format
whose content is fixed by what regulation requires rather than by what a
dietitian needs. Section 2 sets out what that format can disclose: the core set
only, and no magnesium, phosphorus or water. For an ONS row that means the
package cannot supply `free_water_per_mL`, which the application's hydration
arithmetic depends on, nor phosphorus or magnesium, which matter in renal and
refeeding work. A package is the most current statement of a smaller set of
facts, not a better version of the guide's panel.

So the two rankings answer different questions. Completeness decides the source
of record, which is why most rows here cite a guide. Currency decides a
disagreement about a figure two sources both carry, which is why the newest
corrections cite a website. Neither is a defect to be tidied away.

### An approximate figure beats a field the source never carried

Stated by the owner, a dietitian, on 2026-09-11: an approximate value that may
not be exactly right is preferable to a nutrient going missing merely because
the Nutrition Facts table does not carry it.

This is a rule about **choosing a source**, and it is why the completeness
ranking decides the source of record. A guide panel used for a flavour it does
not name is a known, labelled approximation: the `value_source` column says so,
the figure is the manufacturer's own for that product, and the error is bounded
by however much flavours actually differ, which the 2026-09-10 survey measured
as mostly potassium and mostly small. A field the source never disclosed is
worse in a way that is easy to miss, because it does not read as uncertainty. It
reads as nothing, and nothing contributes zero to a daily total.

So do not re-base a row onto a thinner source for the sake of a better citation.
Prefer the source that discloses the field, and record how far from the asked-for
flavour its figure came.

This does not loosen section 1. A blank still means undisclosed and must never
be zero-filled, and the application still shows an em dash rather than a zero
where no ordered product declared a figure. The two rules work together: section
1 governs how an absent figure is *represented* once a source is chosen, and
this one governs *which source to choose* so that fewer figures are absent at
all.

### Nestlé's own statements

The 2026 product guide prints at the foot of **every spread**:

> ALWAYS REFER TO THE PRODUCT LABEL FOR THE MOST CURRENT NUTRITION INFORMATION.

The professional site at `nhsc-pro.ca` states in its footer, read 2026-09-11:

> In the event of a discrepancy between website information and product
> packaging, please refer to product packaging.

and adds that "the information provided is for educational purposes only" and
that "the products discussed in this site may have different product labeling in
different countries".

So Nestlé puts packaging first and, unlike Abbott, makes no statement ranking
its own website against its own guide. Two separate things follow, and they
should not be run together.

On **content**, the professional site adds nothing: it publishes the same
single-flavour panel per product that the guide prints, so it cannot answer a
flavour question. See `VERIFICATION_BACKLOG.md` item 6.

On **currency**, it is still a live surface and usually the later statement, but
not uniformly, and this one can be checked without reading anything. Each panel
is an image whose URL carries the month it was published, so the path is a
staleness stamp. Read on 2026-09-11, the ten BOOST products ranged from
`2022-08` to `2026-07`:

    six nutrition panels        2026-07
    BOOST Pudding, Fruit Flav.  2024-12
    BOOST 2.24                  2023-09
    BOOST Plus Calories         2022-08   ← older than the 2026 guide
    most features panels        2022-08

**That stamp was then tested, and it proved not to mean what it looks like.**
It records when the image was last published, not when the figures in it were
last revised, and an old panel is most often an old panel because nothing about
the product changed. BOOST Plus Calories is the worked example: its website
panel is dated `2022-08`, four years older than the guide edition held here, and
the two are **identical**. Every row was compared — energy on both bases, the
full fat breakdown, cholesterol, all thirteen vitamins, choline, and every
mineral including chloride — and nothing differs. The stored rows match both.

The same held everywhere else it was checked on 2026-09-11. BOOST Original and
BOOST 1.5 at `2026-07`, BOOST Fruit Flavoured at `2024-12` and BOOST Plus
Calories at `2022-08` all agree with the 2026 guide exactly, and with the stored
rows. Across asset dates spanning four years, **no disagreement between Nestlé's
website and Nestlé's guide has yet been found.**

So do not treat a date gap as a disagreement, and do not prefer one source over
the other because its file is newer. A date difference is a reason to look; only
a numeric difference is a finding. The asset date earns its place as a cheap way
to spot which panels are worth re-checking first, and nothing more.

### Abbott's own statements

The 2024 adult product guide prints at the foot of its product pages:

> Please refer to the product label or packaging for the most current
> ingredient, allergen and nutrient profile

and states elsewhere that "the most current information may be obtained by
referring to product labels". It then defers to its own website twice, which
Nestlé's guide never does:

> Individual product information pages can also be found on abbottnutrition.ca
> in the Products section and are updated on a regular basis.

> For nutritional values and ingredients of other product flavours, refer to
> abbottnutrition.ca.

The Abbott product pages themselves carry the same deferral to packaging, read
2026-09-11 on the Ensure Regular page:

> Please refer to the product label or packaging for the most current
> ingredients, allergen and nutrient profile information.

**Read those three together carefully.** Abbott does not say its website is more
current than its label; it says the opposite. What it does say is that the
website's product pages are updated regularly, and that other flavours' values
live there rather than in the guide. So for Abbott the website outranks the
guide on currency and is the *only* published route to a second flavour's panel,
while packaging still outranks both. The practical consequence is that an Abbott
guide page and an Abbott web page disagreeing is expected rather than alarming,
and the web page wins.

### Where the two manufacturers differ

| | Nestlé | Abbott |
|---|---|---|
| Puts packaging first | Yes, on every page | Yes, on every product page and on the website |
| Defers to its own website | No | Yes, explicitly, and for flavours in particular |
| Publishes per-flavour panels | No; one panel per product on both guide and professional site | Yes, on the website |
| Guide edition held here | 2026 | 2024 |
| Website's role for this project | Corroboration; agrees with the guide everywhere checked so far | Source of record for flavours, and the currency check |
| Guide's relationship to the website | Never mentions it | Directs readers to it, and says its pages are updated regularly |

The Abbott guide being two years older than the Nestlé one sharpens this. An
Abbott figure that has not been checked against the website is the more likely
of the two to have drifted, which is where the twelve corrections of 2026-09-10
came from.

### When two sources disagree

Work down this list rather than taking the newer number automatically.

1. **Establish that they describe the same thing.** Most apparent conflicts are
   a different container, a different basis column, or a ready-to-hang format
   rather than a bottle. Section 6 covers how to test this.
2. **Ask whether it is a flavour difference or a rounding difference.** BOOST
   Pudding reads 7 g protein in the guide and 6.8 g on the consumer shop, in
   both vanilla and chocolate. That is two sources rounding, so the guide's
   figure stays and only the genuinely flavour-specific value, potassium, was
   changed. A difference that appears in every flavour is not a flavour
   difference.
3. **Check that the sources actually differ in their numbers.** A difference in
   publication date is not a difference in figures. For Nestlé, four products
   spanning asset dates from 2022 to 2026 were compared against the 2026 guide
   on 2026-09-11 and every one agreed exactly, so a date gap there has so far
   never indicated divergence.
4. **Apply the ranking above**, using the manufacturer's own precedence rather
   than a general preference for whichever source is newer. Abbott ranks its
   website above its guide and says so. Nestlé ranks neither against the other,
   so where its two sources genuinely conflict there is no published rule to
   apply, and the conflict should be escalated rather than settled by choosing
   the newer-looking file.
5. **Where packaging would settle it and no other source can**, the honest
   outcome is to record the disagreement and ask the manufacturer, which is the
   escalation section 3 already prescribes. Do not pick a winner by feel.

### Citation practice this implies

A PDF page is stable, so `2026_nestle-product-guide.pdf p.30 (printed folio)`
identifies the same figures permanently. A URL is not stable, so a website
citation means nothing without the `verified` date beside it; the pairing is
what makes a web-sourced row auditable. This is why `verified` is filled on
every row rather than only on the ones that changed.

### What this project holds, and what it does not

Nothing here is sourced from a product label or a package photograph. By the
currency ranking that means every stored value is second-tier by its own
manufacturer's reckoning. By the completeness ranking it means very little for
ONS, because a package could not supply most of what these rows carry anyway.

The practical position is therefore narrower than "we are missing the best
source". A package can settle a disagreement about energy, protein,
carbohydrate, fat, fibre, sodium, potassium, calcium or iron, and it is the
final word on those. It cannot speak to free water, phosphorus, magnesium,
osmolality or the trace minerals, and a package that is silent on a field is not
evidence against the guide's figure for it; section 1's rule about blanks
applies to documents as well as to cells.

That is also the answer to give a clinician who finds a package disagreeing with
the tool. Where the package prints the nutrient, the package wins and the row
should be raised for re-verification. Where it does not print it, there is
nothing to reconcile.

