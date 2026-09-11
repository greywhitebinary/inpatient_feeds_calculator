# Per-flavour survey of Abbott's Ensure and Glucerra product pages

This report covers the ten Abbott products named in the survey request. For
each product I fetched the Canadian product page at
`nutrition.abbott/ca/en/adult/<slug>` and read its published nutrition
table, which is broken out by flavour and printed on two bases: the labelled
container and 100 mL. The raw per-row data is in
`formulary_working/ons_flavours_working.csv`, retrieved 2026-09-10. That file
is a separate evidence record; it is not read by the application and
`formulary_working/ons_products_working.csv` was not touched.

Because the page content was read through an automated fetch rather than a
browser, I treated every "the other flavours are identical" claim as
unproven until I re-fetched that specific flavour's table on its own and
confirmed the number match myself. That re-check is what the "confirmed on a
separate fetch" notes in the CSV refer to. I also worked out, for every basis
pair on every page, whether dividing the container figure by its volume and
multiplying by 100 lands within about 3% of the printed 100 mL figure, since
the two columns are supposed to describe the same product.

## Slugs used

Five slugs were supplied as confirmed: `ensure-clear`, `ensure-plus`,
`ensure-plus-calories`, `ensure-protein-max-30-g`, `ensure-high-protein-12-g`.
For the other five products I found the slug from Abbott's Ensure hub page
and cross-checked it against web search results before fetching:
`ensure-advance`, `ensure-compact`, `ensure-regular`,
`ensure-high-protein-16-g`, `glucerna-nutritional-drink`. Every fetch began by
asking the page to state its own product name, and in every case the name
returned matched the product I asked for. No mis-served page was encountered
in this survey.

## Which products differ by flavour, and by how much

**Ensure Advance** (Vanilla, Chocolate) genuinely differs by flavour. At the
235 mL basis, Chocolate carries 46 g carbohydrate and 588 mg potassium against
Vanilla's 44 g and 470 mg; the 100 mL columns show the same split (200 mg vs
250 mg potassium) and agree with the container figures once scaled. All other
nutrients, including sodium, calcium, magnesium and phosphorus, are identical
between the two flavours. This had not previously been recorded in the
working CSV, which carries one panel for both Ensure Advance flavours.

**Ensure Protein Max 30 g** (Vanilla, Chocolate) is the product that prompted
this survey, and the web page confirms the difference already on record:
Vanilla carries 140 mg sodium and 600 mg calcium per 330 mL, Chocolate 240 mg
and 500 mg. The page also shows the two flavours differing in potassium at
this basis (450 mg Vanilla vs 400 mg Chocolate), which was not previously
recorded.

**Ensure High Protein 16 g** (Vanilla, Chocolate) differs by a small margin in
calcium only: 324 mg (Vanilla) vs 322 mg (Chocolate) per 235 mL, and 138 mg vs
137 mg per 100 mL. Every other nutrient is identical between the two
flavours.

**Ensure Plus Calories** (Vanilla, Chocolate, Strawberry, Butter Pecan) shows
Chocolate carrying slightly more carbohydrate and fibre than the other three
flavours, which are identical to each other: 51 g carbohydrate and 1 g fibre
for Chocolate against 50 g and 0 g for Vanilla, Strawberry and Butter Pecan,
at the 235 mL basis; the 100 mL basis shows the same split (21.56 g/0.46 g
fibre for Chocolate vs 21.1 g/0 g for the others).

**Ensure Regular** (Vanilla, Chocolate, Strawberry, Butter Pecan) shows the
same pattern as Ensure Plus Calories: Chocolate carries 37 g carbohydrate and
1 g fibre per 235 mL against 36 g and 0 g for the other three flavours, which
are identical to each other. The page also lists a fifth flavour, White
Chocolate Raspberry, which is outside the ten-flavour list given for this
survey; its table matches Vanilla, Strawberry and Butter Pecan exactly, so it
does not change the picture, but the owner should know Abbott now sells a
flavour this survey did not cover.

**Glucerna nutritional drink** (Vanilla, Chocolate, Strawberry, Mixed Berry)
shows Chocolate differing from the other three flavours in potassium only:
450 mg vs 380 mg per 237 mL, 190 mg vs 160 mg per 100 mL. Every other nutrient
is identical across all four flavours. The page states in words: "Current
formulation differs slightly from the Glucerna vanilla tested. Other Glucerna
flavours have a similar nutritional profile" — which describes the potassium
figure as approximate for three of the four flavours even though the page
also prints a specific number for each.

**Ensure Clear** (Apple, Mixed Berry), **Ensure Compact** (Vanilla,
Chocolate), **Ensure High Protein 12 g** (Vanilla, Chocolate, Strawberry) and
**Ensure Plus** (Vanilla, Chocolate, Strawberry) each print exactly the same
nutrition figures for every flavour they carry. I confirmed this by
re-fetching each individual flavour's table on its own rather than trusting
the first pass's "matches the other flavour" summaries, and the independently
re-fetched tables came back numerically identical in each case.

## Products that publish one table for the whole product

None of the ten products fell into this category. Every page presents a
separate table per flavour, on the site's own terms — the "coverage" column
in the CSV is `published` for all 56 rows. What that column cannot capture is
that six of the ten products (Ensure Clear, Compact, High Protein 12 g, Plus,
and three of Plus Calories' and Regular's four flavours) turn out to carry
identical figures across their flavours regardless. That distinction is
recorded in the CSV's notes column and in the section above, since it affects
how much weight a reader should put on "per-flavour" here.

## Cross-check disagreements found

The 3%-agreement check between the container and 100 mL columns turned up
disagreements on four of the ten products, in addition to the two already
known to the owner.

- **Ensure Clear** (both flavours, identical panels): calcium 40 mg/237 mL
  implies about 16.9 mg/100 mL, but the page prints 14.8 mg (about -12%, the
  disagreement already known to the owner). Two further disagreements on the
  same page were not previously on record: magnesium 8 mg/237 mL implies
  about 3.4 mg/100 mL against a printed 3.6 mg (about +7%), and phosphorus
  225 mg/237 mL implies about 94.9 mg/100 mL against a printed 90 mg (about
  -5%).

- **Ensure Protein Max 30 g**: the already-known disagreement is confirmed —
  the 100 mL column prints 197 mg calcium for both Vanilla and Chocolate, but
  neither container figure divides down to that number (600 mg/330 mL implies
  about 181.8 mg/100 mL for Vanilla; 500 mg/330 mL implies about 151.5 mg/100
  mL for Chocolate). Two smaller disagreements were also found on the same
  page: potassium (450 mg and 400 mg per 330 mL imply about 136.4 mg and 121.2
  mg per 100 mL respectively, against printed values of 142 mg and 127 mg,
  both about +4-5%) and magnesium (110 mg/330 mL implies about 33.3 mg/100 mL
  against a printed 31.8 mg, about -5%).

- **Ensure Plus Calories** (all four flavours share this pattern): calcium
  350 mg/235 mL implies about 148.9 mg/100 mL against a printed 139 mg (about
  -7%); phosphorus 175 mg/235 mL implies about 74.5 mg/100 mL against a
  printed 79 mg (about +6%); potassium and magnesium show smaller gaps of
  about +3% and +4% respectively.

- **Ensure Regular** (Vanilla, Strawberry and Butter Pecan): the same
  calcium, potassium and magnesium pattern as Ensure Plus Calories appears
  here too, at very close to the same magnitudes (calcium about -7%, magnesium
  about +4%, potassium about +3%). Because Ensure Regular and Ensure Plus
  Calories share several exact mineral figures at the 235 mL and 100 mL
  bases despite different macronutrient profiles, this reads like a
  recurring rounding pattern in Abbott's shared mineral premix rather than
  two unrelated transcription errors, but I have not confirmed that beyond
  what the two pages print, so I am recording the disagreement rather than
  explaining it away.

**Ensure Regular's Chocolate flavour carries a further, more serious
anomaly that I could not resolve.** Its page prints the exact same numbers
in the 100 mL column as in the 235 mL column — 240 kcal, 9 g protein, 6 g
fat, 37 g carbohydrate, 1 g fibre, 210 mg sodium, 450 mg potassium, 350 mg
calcium, 80 mg magnesium, 250 mg phosphorus, both columns identical figure
for figure. Every other basis pair on every other product in this survey
shows the 100 mL figures at roughly 40% of the container figures, so this is
not how the page is supposed to read. I fetched this specific flavour and
basis pair twice, with an explicit instruction to look for a difference
rather than assume proportional scaling, and got the same identical pair of
columns both times. I cannot rule out that this is an artifact of how the
automated fetch tool renders that particular part of the page rather than a
genuine defect in Abbott's table, since I have no way to load the live page
in a browser from here. I recorded the figures as printed in the CSV and
flagged them there as unresolved; this row needs a human to open the live
Ensure Regular page, select Chocolate, and confirm what the 100 mL column
actually shows before it is relied on for anything.

## Pages that could not be reached

None. All ten product pages loaded and returned a nutrition table on the
first or second attempt.

## Values I could not verify

- **Ensure Compact**'s fibre cell reads the word "No" rather than a gram
  figure, on both flavours and both bases. I left `fibre_g` blank for all
  four Ensure Compact rows rather than reading "No" as zero, since that would
  be an interpretation rather than a quotation, and the survey's rule is to
  quote only what is printed.
- **Ensure High Protein 12 g** and **Ensure Plus** do not list fibre at all in
  their per-flavour web tables (Ensure Plus's 235 mL basis is the one
  exception, where it prints 0 g; its own 100 mL basis omits the figure).
  Both are recorded as blank where the page is silent, per the same rule.
- **Ensure Regular, Chocolate, 100 mL basis** — see the anomaly described
  above. Every figure in that row is unverified in the sense that it may not
  represent the true 100 mL panel at all.

No other figure in the survey looked computed, rescaled, or implausible on
inspection, and I did not need to discard any fetch for returning the wrong
product.
