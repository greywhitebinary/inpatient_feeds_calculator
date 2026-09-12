# Reviewing manufacturer sources: a briefing for independent reviewers

Written 2026-09-11 for the BTF-Calc side, which is reviewing product numbers
against the manufacturer websites independently of this repository. Everything
here was learned the expensive way on this side between 1 and 11 September 2026.
None of it needs learning twice.

This briefing keeps the source-access methods and cross-project scope notes.
[DATA_CONVENTIONS.md](DATA_CONVENTIONS.md) holds the maintained data rules; the
rule sections below link there rather than maintaining a second copy.
The website observations and verification counts are dated evidence.

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

---

## Getting into the Abbott site

`nutrition.abbott/ca/en/...` product pages are ordinary server-rendered pages and
need no special handling. They carry a per-flavour nutrition table, which is the
point of going there. Abbott's guide directs healthcare professionals to these
pages and says they "are updated on a regular basis".

---

## Which source wins

Use [the two rankings](DATA_CONVENTIONS.md#the-ranking): **completeness** decides
which source can supply a field, while **currency** resolves disagreement about
a field both sources publish. Keep that distinction when choosing a source.

### What each manufacturer actually says

The quotations and their implications are maintained under
[Nestlé's statements](DATA_CONVENTIONS.md#nestlés-own-statements) and
[Abbott's statements](DATA_CONVENTIONS.md#abbotts-own-statements).
Abbott publishes website-versus-guide precedence; Nestlé does not. A genuine
Nestlé website/guide conflict needs clarification from the manufacturer.

### When two sources disagree

Follow [the reconciliation procedure](DATA_CONVENTIONS.md#when-two-sources-disagree).
It checks product format, basis, flavour, rounding, and actual numerical
agreement before applying the manufacturer's precedence or escalating a conflict.

---

## Reading a panel without introducing an error

Use these sections of the maintained conventions during a review:

- [Cross-checks](DATA_CONVENTIONS.md#6-cross-checks-that-catch-transcription-errors)
  cover basis conversion and energy reconciliation; the
  [Pivot column trap](SOURCES.md#why-five-products-cite-a-sheet-rather-than-the-guide)
  is documented in the source register.
- [Precision](DATA_CONVENTIONS.md#4-precision) and
  [page citations](DATA_CONVENTIONS.md#5-page-citations) cover rounding and
  printed-versus-PDF page numbering.
- [Blank versus zero](DATA_CONVENTIONS.md#1-blank-versus-zero) governs disclosure.
- [Approximate versus absent figures](DATA_CONVENTIONS.md#an-approximate-figure-beats-a-field-the-source-never-carried)
  governs source selection without changing the missing-data rule.
- [Jurisdictions](DATA_CONVENTIONS.md#3-do-not-mix-jurisdictions) keeps Canadian
  rows based on Canadian documents.

---

## What has already been verified, so you need not repeat it

Completed checks as of 2026-09-11 are recorded in:

- [The September 2 field-by-field review](VERIFICATION_BACKLOG.md#completed-2026-09-02).
- The September 10 [Abbott](ONS_FLAVOUR_SURVEY.md) and [Nestlé](ONS_FLAVOUR_SURVEY_NESTLE.md)
  flavour surveys, which record the source investigations and their limits;
  those survey tasks did not themselves change the runtime CSV.
- [The September 11 professional-site investigation](VERIFICATION_BACKLOG.md#6-re-base-the-nestlé-ons-rows-on-the-professional-site--closed-2026-09-11-not-possible-from-this-source),
  including the four guide-versus-website comparisons that matched exactly.

The subsequent correction work on September 10 changed **twelve values across
seven flavour rows**: Ensure Advance chocolate, Ensure Protein Max chocolate,
Glucerna chocolate, BOOST 2.24 chocolate, BOOST Pudding chocolate, Ensure Regular
chocolate, and Ensure Plus Calories chocolate. These were the flavours whose
published panels differed from the guide's panel. Potassium was the nutrient
that changed most often. This records the applied corrections separately from
the surveys above.

These are dated results, not a guarantee about later product revisions.

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
