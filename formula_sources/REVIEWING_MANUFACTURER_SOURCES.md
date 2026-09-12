# Reviewing manufacturer sources: a briefing for independent reviewers

Written 2026-09-11 for the BTF-Calc side, which is reviewing product numbers
against the manufacturer websites independently of this repository. Everything
here was learned the expensive way on this side between 1 and 11 September 2026.
None of it needs learning twice.

This is a companion to `DATA_CONVENTIONS.md`, which holds the binding rules.
Where the two disagree, that file wins and this one should be corrected.

---

## The five things that cost the most time

Read these before opening anything.

**1. The Nestlé professional site returns an empty document to a fetcher, and
it is not broken.** `nhsc-pro.ca/pwa/en/products` is an offline-first Ionic
application. A plain `curl`, `fetch`, or fetch-based agent tool gets the empty
shell and nothing else. This wasted a full session here and produced a written
claim that the site was unusable, which was wrong. It loads normally in a real
browser once its catalogue downloads. See "Getting into the Nestlé site" below.

**2. Nestlé's nutrition data is a picture, not text.** Each product carries its
nutrition information as a single JPEG or PNG. There is no structured table to
scrape, in the page or in the app's data. You read the panels visually, so budget
for that.

**3. Nestlé publishes one panel per product; Abbott publishes per flavour.**
This is the central asymmetry and it decides what each review can even conclude.
Every Nestlé BOOST panel, in both the guide and the professional site, is headed
with a single flavour — "Vanilla Flavoured" for nine of the ten, "Orange
Flavoured" for BOOST Fruit Flavoured. Other flavours appear only as order codes
in the ordering table. Abbott, by contrast, publishes a full per-flavour table on
`nutrition.abbott/ca`, and its own product guide says so: "For nutritional values
and ingredients of other product flavours, refer to abbottnutrition.ca."

So a Nestlé chocolate figure does not exist to be found. Do not go looking for it
on the professional site; it is not there, and confirming that took a session.

**4. A date in an image URL is a publication date, not a revision date.** Nestlé
asset paths carry a month, like `/2022-08/` or `/2026-07/`, and it is tempting to
read an old one as stale. It is not. BOOST Plus Calories' web panel is dated
`2022-08`, four years older than the 2026 guide, and the two are identical row for
row — energy on both bases, the full fat breakdown, cholesterol, all thirteen
vitamins, choline and every mineral including chloride. An old panel usually means
a product that has not changed. Treat a date gap as a reason to look, never as a
finding.

**5. For an ONS row, the product package is the weakest source, not the best.**
Both manufacturers say packaging is the most current source, and for the
nutrients it prints that is true. But Canadian packaging carries the mandatory
**Nutrition Facts table**, whose contents are fixed by regulation rather than by
clinical need. It does not carry free water, phosphorus, magnesium, osmolality or
the trace minerals. Free water is what a hydration calculation runs on. A package
is the most current statement of a smaller set of facts.

---

## Getting into the Nestlé site

The professional site is at `https://www.nhsc-pro.ca/pwa/en/products`, and the
product list is at `/pwa/en/products/list`. Link-scraping the list finds nothing,
because it is an Ionic router rather than anchors.

Use a real browser. Once the app has booted it caches its whole catalogue —
51 products as of 2026-09-11 — in IndexedDB, which is far more reliable to read
than the rendered DOM:

```js
// database _ionicstorage, object store _ionickv, key produtos-en (or produtos-fr)
const db = await new Promise(r => { const q = indexedDB.open('_ionicstorage');
                                    q.onsuccess = () => r(q.result); });
const products = await new Promise(r => {
  const t = db.transaction('_ionickv', 'readonly').objectStore('_ionickv').get('produtos-en');
  t.onsuccess = () => r(t.result);
});
```

Each product object carries, among much else:

| Field | What it holds |
|---|---|
| `titulo`, `slug` | product name and URL slug |
| `tabelaNutricional` | the nutrition panel, as `[{image, imageAlt}]` — one entry |
| `accordionContent` | sections including **FEATURES AT-A-GLANCE**, also as an image |
| `caracteristicasTecnicas` | empty for the BOOST products; do not rely on it |

**Water content and osmolality are in the features image, not the nutrition
panel.** This catches people out, and it caught this project out: an earlier
version of our notes wrongly recorded that the site carried no water content at
all. The features panel also gives caloric density, the protein/carbohydrate/fat
energy split, ingredient sources, kosher and gluten-free status, lactose and
residue.

Image URLs are usually the `/styles/pwa_embed/public/...` or
`/styles/pwa_product_nutritional/public/...` derivative. The derivative and the
original were byte-identical in size where checked, so the derivative is fine to
read.

### A known defect on Nestlé's side

**BOOST 1.5's features image is broken on Nestlé's own site.** Its stored `src`
omits the `/styles/pwa_embed/public/` prefix every other product uses, and the
path it does use returns HTTP 404. A clinician reading that page sees no water
content, osmolality or lactose statement at all. The image itself is intact at
the standard derivative path. The printed guide carries the same block in full,
so nothing is actually lost to anyone using the guide — but it is worth reporting
to Nestlé, and worth not mistaking for your own tooling failing.

---

## Getting into the Abbott site

`nutrition.abbott/ca/en/...` product pages are ordinary server-rendered pages and
need no special handling. They carry a per-flavour nutrition table, which is the
point of going there. Abbott's guide directs healthcare professionals to these
pages and says they "are updated on a regular basis".

---

## Which source wins

There are two rankings and they run in opposite directions. Using the wrong one
is how a source gets over-trusted.

**By currency**, which settles a disagreement about a figure two sources both
publish:

1. Product label or packaging — both manufacturers place this above everything
   they publish themselves, including their own websites.
2. The official manufacturer website for healthcare professionals.
3. Product information sheets — dated, per-product, usually higher precision.
4. The collated product guide — a snapshot that ages from the day it is issued
   and cannot receive a live update.

**By completeness**, which decides which source a value should be built from:

1. The collated guide and the product information sheets. These carry free
   water, osmolality, chloride, the full vitamin and trace-mineral panel, and for
   Nestlé the DRI adequacy volumes.
2. The manufacturer website, which carries most nutrients but omits some of the
   above unevenly.
3. Packaging, for the reason in point 5 above.

### What each manufacturer actually says

Nestlé's guide, at the foot of every spread: "ALWAYS REFER TO THE PRODUCT LABEL
FOR THE MOST CURRENT NUTRITION INFORMATION." Its professional site footer: "In
the event of a discrepancy between website information and product packaging,
please refer to product packaging." Nestlé never ranks its website against its
own guide.

Abbott's guide and product pages both say "Please refer to the product label or
packaging for the most current ingredient, allergen and nutrient profile". The
guide additionally defers to the website twice, for currency and for flavours.

**So Abbott publishes a rule and Nestlé does not.** For Abbott, website beats
guide. For Nestlé, if the two ever genuinely conflict, there is no published rule
to apply and the conflict should be escalated to the manufacturer rather than
settled by preferring the newer-looking file.

### When two sources disagree

1. Establish they describe the same thing — container, basis column, and format.
   A ready-to-hang pack is not a bottle.
2. Ask whether it is a flavour difference or a rounding difference. A difference
   that appears in *every* flavour is not a flavour difference. BOOST Pudding
   reads 7 g protein in the guide and 6.8 g on the consumer shop in both vanilla
   and chocolate; that is rounding, and the guide's figure was kept.
3. Check the numbers actually differ. A date gap is not a difference.
4. Apply the ranking, using the manufacturer's own precedence.
5. Where only packaging could settle it, record the disagreement and ask the
   manufacturer. Do not pick a winner by feel.

---

## Reading a panel without introducing an error

- **Recompute, never transcribe a converted figure.** Where a panel prints two
  bases, convert both to a common basis and compare. This is how three real
  errors were found here.
- **Watch for a mislabelled column.** Abbott's guide prints Pivot 1.5 Cal's fat,
  carbohydrate and fibre blocks as per-100-mL values inside a column headed
  "Per 237 mL". Transcribing that column understated all three about 2.4-fold.
  Where a product information sheet exists, it beat the collated guide every time
  this was tested.
- **Reconcile the energy.** `protein x 4 + fat x 9 + carbohydrate x 4` against the
  declared energy should land between 98% and 106%. Pivot read 57% before it was
  fixed. Run this after any bulk change.
- **Cite the page unambiguously.** Both guides are printed as spreads, so each
  PDF page carries two printed folio numbers and the two schemes collide. Say
  which you mean. For the Nestlé guide, `printed = 2 x pdf_page - 2`.
- **A blank is not a zero.** A blank means the manufacturer did not disclose the
  value; a zero means they disclosed a zero. Never fill a blank with zero to tidy
  a table.
- **Prefer an approximate figure to an absent one.** A panel used for a flavour it
  does not name is a labelled approximation with bounded error. A field the source
  never carried does not read as uncertainty — it reads as nothing, and nothing
  contributes zero to a daily total. Choose the source that discloses the field.
- **Do not mix jurisdictions.** Canadian rows come from Canadian documents. A US
  sheet may corroborate that two documents describe the same formulation, or
  raise a question for the manufacturer. It is never a source of values.

---

## What has already been verified, so you need not repeat it

As of 2026-09-11, on this side:

- **Every row of all three CSVs** was checked field by field against its cited
  source on 2026-09-02, recomputing each conversion rather than reading it off.
  Two numeric errors were found and corrected then.
- **Twelve values across seven flavour rows** were corrected on 2026-09-10, being
  every flavour whose own published panel differs from the panel the guide
  prints: Ensure Advance chocolate, Ensure Protein Max chocolate, Glucerna
  chocolate, BOOST 2.24 chocolate, BOOST Pudding chocolate, and Ensure Regular
  and Ensure Plus Calories chocolate. Potassium is the nutrient that moves most
  often, which is what cocoa would predict.
- **Four Nestlé products** were compared between the professional site and the
  2026 guide on 2026-09-11 — BOOST Original, BOOST 1.5, BOOST Fruit Flavoured
  orange and BOOST Plus Calories — spanning site asset dates from 2022 to 2026.
  All four agree exactly, and the stored rows agree with both. **No disagreement
  between Nestlé's website and Nestlé's guide has yet been observed.**

Every row also carries a `value_source` column saying which state it is in:
`own_panel` for a flavour's own published panel, `representative` where the
guide's single panel is being carried because nothing flavour-specific exists,
and `stated_representative` where the manufacturer prints one flavour's figures
for another and says so. That last case is BOOST Fruit Flavoured peach and
wildberry, which carry orange's numbers because orange's panel is the only one
Nestlé publishes — confirmed independently on the professional site.

---

## Micronutrients in ONS: you are starting from nothing here

This is the biggest scope difference between the two projects, and the thing
most likely to be assumed wrongly.

**ENCalc's ONS file carries no vitamin or trace-mineral columns whatsoever.** It
has 35 columns: identifiers, the macronutrients, five minerals (sodium,
potassium, calcium, magnesium, phosphorus), free water, the serving-basis
equivalents, and the provenance columns. There is no vitamin A, no vitamin K, no
zinc, no selenium — none of it, for any of the 54 ONS rows.

That is deliberate rather than an oversight. ENCalc is an acute inpatient tool,
many micronutrients do not change an acute decision, and this project ranks
verification work by whether a value reaches something displayed. A column no
module reads earns no review time.

**The BTF side is expected to carry them, and that divergence is intentional.**
The two repositories deliberately keep five things byte-identical — the
chart-note copy control, `render_alert`, the alert CSS, the colour tokens, the
CSS hook guard and the canary workflow — but the product data files are not
among them and must not be synced. A wider micronutrient set on the BTF side is
the right answer for what that tool is for, not a drift to be reconciled.

**So nothing on this side can be inherited for ONS micronutrients.** In
particular, do not read across from the verification work that has been done:

- The 594 micronutrient values verified on 2026-09-04 are **18 columns in
  `canada_formulas_working.csv`**, the tube-feed file. Different file, different
  products, no overlap with ONS. The account is in
  `MICRONUTRIENT_VERIFICATION.md`.
- The application's on-screen micronutrient panel lists sixteen micronutrients,
  and those also come from the formula file, not from ONS.

**The good news is that the source data exists and is rich.** Both the Nestlé
guide and the professional site panels carry a full list: vitamin A with its
retinol and beta-carotene split, D, E, K, C, thiamine, riboflavin, niacin,
pantothenate, B6, biotin, folate, B12, choline, plus iron, zinc, manganese,
copper, iodine, selenium, molybdenum, chromium and chloride. A consumer listing
does not; Canadian consumer panels declare a short vitamin list only. For this
work the professional guide and the professional site are the only usable
sources, which makes the completeness ranking above matter far more to your
review than it does to ours.

### Two unit traps that will bite a micronutrient review

**Vitamin A, D and E units are not consistent between products in the same
guide.** BOOST Original's panel gives vitamin A in **µg** and vitamin D in µg.
BOOST 1.5, BOOST Plus Calories and BOOST Fruit Flavoured give both in **IU** on
the same basis columns in the same document. Converting an IU figure as though
it were µg, or the reverse, is a large error in a nutrient where it matters.
Check the units column on every product rather than once per manufacturer.

**Folate is printed two different ways.** BOOST Original prints "Folate, µg
DFE". BOOST 1.5 and BOOST Plus Calories print "Folic Acid, mg". Dietary folate
equivalents and folic acid are not interchangeable, and converting between them
depends on whether the source is supplemental or dietary. A related question is
already open on the ENCalc side for vitamin A: Compleat Organic Blends 1.25 uses
the dietary 12:1 RAE factor while every other row uses the supplemental 2:1
factor, and how to mark that is unresolved. Expect to meet the same class of
problem across the ONS range and decide a convention before transcribing rather
than after.

**Vitamin K is absent from both ENCalc CSVs but present in the sources.** The
guide and the site both print it — BOOST 1.5 at 0.02 mg per 237 mL, BOOST Plus
Calories at 0.032 mg, BOOST Fruit Flavoured orange at 0.009 mg. It is the one
micronutrient in a feed that changes a drug decision, through warfarin and the
INR, so it is worth capturing on your side even though ENCalc has not yet added
the column.

---

## The one gap worth knowing about

Fourteen of the 26 Nestlé ONS rows carry the guide's single panel rather than
their own flavour's, because no flavour-specific figures are published anywhere
that could be found. They are labelled, not hidden. The remaining routes to
per-flavour Nestlé figures are the consumer shop at `shop.nestlehealthscience.ca`,
which lists only four of the ten BOOST products and omits free water for three of
those four, or asking Nestlé directly.

If your review finds a per-flavour Nestlé source that this one did not, that is a
genuinely new finding and worth sending back.
