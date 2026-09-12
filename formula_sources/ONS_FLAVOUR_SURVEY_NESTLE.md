# Nestlé ONS flavour survey

This is a survey of the per-flavour nutrition panels Nestlé publishes for the
ten Nestlé BOOST products in scope. It compares each published flavour against
the panel printed in `reference_documents/canada/2026_nestle-product-guide.pdf`
(read with `pdftotext -layout`, cross-checked against page images for the one
product where the text extraction needed verification) and, where a second
flavour's own panel could be found, against that sibling flavour. The data
lives in `formulary_working/ons_flavours_nestle_working.csv`. This survey does
not alter any stored value the application reads, and it does not touch
`formulary_working/ons_products_working.csv` or
`formulary_working/ons_flavours_working.csv`.

## What could be checked, and what could not

The professional site at `https://www.nhsc-pro.ca/pwa/en/products` was read on
2026-09-11, after this survey was first written. An earlier version of this
document said it could not be used, which was wrong: it returns an empty
document to a *fetcher* because it is an offline-first Ionic application that
caches its catalogue after boot, but it loads normally in a real browser.

**It publishes no per-flavour nutrition data.** Each product carries one
nutrition-information image, and every one of the ten in-scope BOOST products is
headed with a single flavour — "Vanilla Flavoured" for nine of them, and "Orange
Flavoured" for BOOST Fruit Flavoured, which confirms this survey's finding that
Nestlé publishes orange's panel for that product. Other flavours appear only as
order codes in the ordering table, and the ingredient list is headed
"INGREDIENTS (VANILLA FLAVOUR)". The site therefore reproduces the printed
guide's structure rather than improving on it. It does carry water content and
osmolality, in a separate "FEATURES AT-A-GLANCE" image rather than in the
nutrition panel, but that image is also one per product rather than one per
flavour. BOOST 1.5's copy of it is missing from Nestlé's own page through a
broken image path; see `VERIFICATION_BACKLOG.md` item 6.

What the site did settle is that the guide's transcription is sound. BOOST
Original vanilla and BOOST Fruit Flavoured orange were compared field by field
against the stored rows, and every value matched exactly. The full account is in
`VERIFICATION_BACKLOG.md` item 6.

Everything below therefore rests on the printed guide and, for four products, on
the consumer shop at `shop.nestlehealthscience.ca`, which remains the only
Nestlé source publishing a second flavour's panel. I found its product slugs
from the `/collections/boost` listing and from the site's own product sitemap
(`sitemap_products_1.xml`), rather than guessing any URL.

That sitemap turned out to carry only **four** of the ten products in scope:
BOOST 2.24, BOOST Fruit Flavoured, BOOST Soothe, and BOOST Pudding. The other
six — BOOST 1.5, BOOST CarbSmart, BOOST High Protein, BOOST Original, BOOST
Plus Calories, and BOOST Protein+ — are not sold on the consumer shop at all as
of 2026-09-10; I confirmed this by searching the full product sitemap for each
product's name and by paging through the boost collection, not merely by a
single failed guess. For those six products the only nutrition data available
anywhere is the printed guide, and the guide prints exactly one panel per
product, headed with a single flavour's name (usually "Vanilla Flavoured").
Where the guide's panel is not itself the flavour a row asks about, I left
every nutrient blank rather than copy the vanilla figures across — the whole
premise of this survey is that flavours can differ, so assuming they don't
would defeat the purpose.

Every fetch was preceded by an identity check against the page's own heading,
and every prompt instructed the fetcher to quote printed values verbatim, never
convert units, never rescale to a different serving size, and answer "not
listed" for an absent nutrient. For the four shop-listed products I also
downloaded the raw page HTML directly and confirmed the quoted figures against
the actual embedded table markup (not just the fetch summary), because the
Nutrition Information table on these pages is inline HTML rather than an
image, and this is the surest way to be certain the fetcher was reading the
page rather than reciting something it already knew. Every number reported
below for those four products was independently verified this way.

## Which products differ by flavour, and by how much

**BOOST 2.24 — differs.** Vanilla and Strawberry both list potassium at 420 mg
per 237 mL; Chocolate lists 450 mg. Every other value — calories, protein, fat,
carbohydrate, sodium, calcium, magnesium, phosphorus, and chloride — is
identical across all three. The guide's panel is headed "Vanilla Flavoured"
and its potassium figure (420 mg) matches Vanilla and Strawberry, not
Chocolate. This is the same relationship the task brief used as its worked
example, and the shop's own tables reproduce it exactly.

**BOOST Pudding — differs, and by more.** Vanilla lists potassium at 250 mg per
142 g serving; Chocolate lists 350 mg — a 100 mg gap, the largest flavour
difference found in this survey. Every other value is identical between the
two flavours. The guide's panel is headed "Vanilla Flavoured" and its
potassium figure (250 mg) matches the shop's Vanilla listing, not Chocolate.

**BOOST Fruit Flavoured — does not differ, as far as the numbers show.**
Orange, Peach, and Wildberry each have their own product page and their own
Nutrition Facts table, and all three tables are numerically identical: 180
Cal, 9 g protein, 0.5 g fat, 36 g carbohydrate, 15 mg sodium, 35 mg potassium,
79 mg calcium, 40 mg magnesium, 200 mg phosphorus, 60 mg chloride, and 205
mL/237 mL water content. See "the one thing to watch for," below, for a
caveat about what this apparent equality might be hiding.

**BOOST Soothe — single flavour, nothing to compare.** Only Strawberry-Kiwi is
sold, so there is no sibling flavour to check it against. The shop page matches
the guide on every value the guide prints.

**BOOST Protein+ — single flavour, nothing to compare.** Only Chocolate is
sold, so there is no sibling flavour to check it against.

**BOOST 1.5, BOOST CarbSmart, BOOST High Protein, BOOST Original, and BOOST
Plus Calories — unknown; not verifiable from any source I could reach.** The
guide prints one panel for each of these products, named for a single flavour
(Vanilla for all five), and none of the five is sold on the consumer shop, so
there is no second panel anywhere to compare it against. I recorded the
guide's own flavour's row with the guide's figures and left every other
flavour's row blank rather than assume parity. One piece of indirect evidence
argues against assuming parity: the guide states that BOOST CarbSmart's
sucralose content is 40 mg/237 mL for vanilla and strawberry but 45 mg/237 mL
for chocolate, which means the recipe is not identical across flavours even
though the printed nutrient panel is. I have not found anything comparable for
1.5, High Protein, Original, or Plus Calories, but the CarbSmart example
means "the guide only shows one flavour" should not be read as "the flavours
are the same."

## Where a shop listing disagreed with the guide

**BOOST Fruit Flavoured, osmolality.** The guide's 2026 panel gives 670
mOsm/kg water. The shop pages for Orange, Peach, and Wildberry — all three —
give 790 mOsm/kg water for the same 237 mL serving. This is a real
disagreement between the consumer listing and the printed guide, not a
transcription error on my part; I confirmed the 790 figure directly in each
page's raw HTML.

**BOOST Pudding, protein.** The guide's Vanilla panel prints 7 g of protein
per 142 g serving. The shop's Vanilla listing prints 6.8 g for the same
serving. The Chocolate listing also prints 6.8 g. This is a small but real
discrepancy — confirmed in the raw HTML, not a fetch artifact — and I have
recorded 6.8 g in the CSV because that is what the shop prints, not because I
have resolved which figure is right.

No other disagreements between a shop listing and the guide were found; every
other value the four shop-listed products print matches the guide's
corresponding flavour panel exactly.

## The one thing to watch for: BOOST Fruit Flavoured's "one panel" claim

The task brief states that Nestlé prints, on BOOST Fruit Flavoured, that the
nutritionals apply only to the orange flavour, and asked me to quote that
sentence and record the product's coverage as `manufacturer_states_one_panel`
if I found it. I looked for it in two places: the full text of the 2026 guide
(both the automated text extraction and a rendered image of the Fruit
Flavoured page, to rule out an extraction error) and the raw HTML of all three
shop listings. I did not find any such sentence in words in either place. What
I did find is that the guide's panel is headed "Orange Flavoured" — the same
naming convention used for every other single-panel BOOST product's "Vanilla
Flavoured" heading — and that the three shop pages, despite being separate
listings with their own tables, print numerically identical figures for
Orange, Peach, and Wildberry. A web search summary asserted that such a
disclaimer sentence exists, but I could not confirm it against either primary
source I'm permitted to use, so I have not quoted it and have not applied
`manufacturer_states_one_panel` as the coverage value; I have used `published`
instead, since three separate per-flavour tables genuinely exist, even though
their contents are the same. If the sentence exists on the product's physical
packaging or on a page outside the scope of this survey, that would explain
why I could not locate it. This is a gap in what I could verify, not a claim
that the disclaimer doesn't exist.

## What a healthcare professional would expect that these consumer pages cannot supply

These are consumer Nutrition Facts listings, not the professional product
guide, and they are weaker evidence for that reason. Specifically:

- **Fibre.** Not one of the ten products' shop or guide panels lists a
  separate fibre figure for BOOST 2.24, Fruit Flavoured, Soothe, or the two
  Pudding flavours (the four products with a shop listing). BOOST CarbSmart
  and BOOST Plus Calories do print fibre, but only in the guide, which is the
  sole source for those two products.
- **Water content / free water.** Only the Fruit Flavoured pages show it (205
  mL/237 mL, matching the guide). BOOST 2.24, Soothe, and both Pudding
  listings do not show it at all, even though the guide prints a water-content
  figure for every one of these products. The application's stored ONS rows
  carry a free-water figure it uses for hydration math, and for three of the
  four shop-listed products that figure simply is not on the consumer page —
  it would have to keep coming from the guide.
- **Osmolality.** Only the Fruit Flavoured pages show it, and, as noted above,
  the figure they show (790 mOsm/kg water) disagrees with the guide's (670).
  BOOST 2.24, Soothe, and Pudding show no osmolality figure at all.
  Osmolality is also entirely unlisted, in either the guide or a shop page,
  for the six products with no shop listing.
- **Chloride.** Shown on BOOST 2.24 (300 mg), Fruit Flavoured (60 mg), and
  Pudding (110 mg), but not on Soothe.
  Chloride figures were unchanged across every sibling flavour checked.
- **Full micronutrient list.** The Canadian consumer panels declare only the
  handful of nutrients above plus a short vitamin list; they do not carry the
  guide's complete vitamin and trace-mineral panel (selenium, molybdenum,
  chromium, iodine, and the rest), which is otherwise only available from the
  guide.

None of this stops the comparison this survey was asked to make — the guide
remains the source for everything a consumer page omits — but a reader should
not treat "not listed" in the CSV as evidence the nutrient is absent from the
product; it is evidence only that this consumer page does not print it.

## Pages I could not reach or that do not exist

- The professional `nestlehealthscience.ca` product pages: reachable after all,
  at `nhsc-pro.ca/pwa/en/products`, and read on 2026-09-11. They are
  client-rendered, so they return an empty document to a fetcher and need a
  real browser. They publish one single-flavour panel per product and no
  per-flavour data, as described above.
- `madewithnestle.ca` (the Nestlé consumer brand site): returned HTTP 403 to
  every fetch attempt, including the BOOST Fruit Flavoured page that might
  have carried the "applies only to orange" wording.
- No shop.nestlehealthscience.ca listing exists for BOOST 1.5, BOOST
  CarbSmart, BOOST High Protein, BOOST Original, or BOOST Plus Calories, in
  any flavour. No shop listing exists for BOOST Protein+ either, though that
  product has only one flavour to begin with. I confirmed each absence
  against the site's full product sitemap, not only against the boost
  collection page.

## Coverage summary

| Product | Coverage | Why |
|---|---|---|
| BOOST 1.5 | not_published | Guide prints one Vanilla-only panel; no shop listing |
| BOOST 2.24 | published | Three separate, genuinely differing shop panels |
| BOOST CarbSmart | not_published | Guide prints one Vanilla-only panel; no shop listing |
| BOOST Fruit Flavoured | published | Three separate shop panels, numerically identical |
| BOOST High Protein | not_published | Guide prints one Vanilla-only panel; no shop listing |
| BOOST Original | not_published | Guide prints one Vanilla-only panel; no shop listing |
| BOOST Plus Calories | not_published | Guide prints one Vanilla-only panel; no shop listing |
| BOOST Protein+ | published | Single flavour; guide's one panel covers it fully |
| BOOST Pudding | published | Two separate, genuinely differing shop panels |
| BOOST Soothe | published | Single flavour; guide's one panel covers it fully |

## Where I stopped

I completed all ten products in scope; nothing was left partial. Every row in
`formulary_working/ons_flavours_nestle_working.csv` reflects either a verified
figure or a deliberately blank one, and none of the ten products is missing a
coverage value.
