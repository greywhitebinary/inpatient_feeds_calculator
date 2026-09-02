# Canadian ONS data verification

`formulary_working/ons_products_working.csv` was reviewed on 2026-09-01
against the local Canadian manufacturer guides listed below. The public CSV
contains 52 selectable rows, with one row per flavour. The guides present one nutrient panel
for each product and list the available flavours separately, rather than
providing a separate nutrient panel for every flavour. The CSV therefore
repeats the product-level guide values for each listed flavour; it does not
claim that flavour-specific labels are identical when the guide does not show
those labels.

The nutrient values in this report are per labelled container. The CSV stores
them per millilitre so the same product can be calculated either as an oral ONS
order or, when selected in the formula workflow, as EN. Abbott reports water as
g/L in its technical data; the CSV records the corresponding per-millilitre
coefficient. Nestlé reports water content directly per container.

## Abbott Nutrition Canada

Source: `2024_abbott-adult-product-guide.pdf`.

| Product and flavours | Page | Container | kcal | Protein (g) | CHO (g) | Fat (g) | Fibre (g) | Na (mg) | K (mg) | Ca (mg) | Mg (mg) | P (mg) | Water basis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Ensure Advance — Vanilla, Chocolate | 10 | 235 mL | 350 | 20 | 44 | 11 | 3 | 259 | 470 | 249 | 66 | 251 | 681 g/L (0.681 mL/mL) |
| Ensure Protein Max 30 g — Vanilla, Chocolate | 12 | 330 mL | 150 | 30 | 6 | 1.5 | 2 | 140 | 450 | 600 | 110 | 500 | 905 g/L (0.905 mL/mL) |
| Ensure Compact — Vanilla, Chocolate | 14 | 118 mL | 218 | 9 | 32 | 6 | 0 | 162 | 330 | 326 | 43 | 188 | 721 g/L (0.721 mL/mL) |
| Ensure Regular — Vanilla, Chocolate, Strawberry, Butter Pecan | 16–17 | 235 mL | 240 | 9 | 36 | 6 | 0 | 210 | 450 | 350 | 80 | 250 | 831 g/L (0.831 mL/mL) |
| Ensure High Protein 16 g — Vanilla, Chocolate | 18 | 235 mL | 160 | 16 | 19 | 2 | 0.89 | 204 | 465 | 324 | 42 | 186 | 838 g/L (0.838 mL/mL) |
| Ensure High Protein 12 g — Vanilla, Chocolate, Strawberry | 20 | 235 mL | 225 | 12 | 31 | 6 | 0 | 289 | 428 | 275 | 65 | 275 | 837 g/L (0.837 mL/mL) |
| Ensure Plus Calories — Vanilla, Chocolate, Strawberry, Butter Pecan | 22–23 | 235 mL | 350 | 13 | 50 | 11 | 0 | 210 | 450 | 350 | 80 | 175 | 762 g/L (0.762 mL/mL) |
| Ensure Plus — Vanilla, Chocolate, Strawberry | 24 | 235 mL | 355 | 13 | 54 | 9.5 | 0 | 251 | 461 | 301 | 65.1 | 275 | 770 g/L (0.770 mL/mL) |
| Ensure Clear — Apple, Mixed Berry | 26 | 237 mL | 240 | 8 | 52 | 0 | 0 | 70 | 30 | 40 | 8 | 225 | 827 g/L (0.827 mL/mL) |
| Glucerna nutritional drink — Vanilla, Chocolate, Strawberry, Mixed Berry | 28 | 237 mL | 225 | 11.3 | 28 | 8.8 | 5.6 | 250 | 380 | 275 | 60.4 | 275 | 833 g/L (0.833 mL/mL) |

Abbott identifies the Vanilla Glucerna panel as the tested profile and describes
the other listed flavours as having a similar nutritional profile.

The Nestlé guide also lists BOOST Just Protein, BOOST Powder, and BOOST
Pudding. BOOST Just Protein is recorded in `modular_products_working.csv`
because the guide identifies it as a modular that can be used as a protein
flush. BOOST Powder and BOOST Pudding are labelled for oral use and are not
included in ENCalc's liquid ONS or tube-modular tables.

## Nestlé Health Science Canada

Source: `2026_nestle-product-guide.pdf`.

| Product and flavours | Page | Container | kcal | Protein (g) | CHO (g) | Fat (g) | Fibre (g) | Na (mg) | K (mg) | Ca (mg) | Mg (mg) | P (mg) | Water content |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BOOST CarbSmart — Vanilla, Chocolate, Strawberry | 10 | 237 mL | 190 | 16 | 17 | 7 | 3 | 125 | 350 | 280 | 54 | 260 | 195 mL |
| BOOST Fruit Flavoured — Orange, Peach, Wildberry | 12 | 237 mL | 180 | 9 | 36 | 0.5 | 0 | 15 | 35 | 79 | 40 | 200 | 205 mL |
| BOOST High Protein — Vanilla, Chocolate, Strawberry | 14 | 237 mL | 240 | 15 | 34 | 5 | 0 | 250 | 450 | 370 | 90 | 300 | 197 mL |
| BOOST Original — Vanilla, Chocolate, Strawberry, Chocolate Latte | 18 | 237 mL | 230 | 10 | 34 | 6 | 0 | 265 | 410 | 308 | 90 | 265 | 200 mL |
| BOOST Plus Calories — Vanilla, Chocolate, Strawberry | 20 | 237 mL | 360 | 14 | 45 | 14 | 3 | 200 | 360 | 350 | 100 | 300 | 183 mL |
| BOOST Protein+ — Chocolate | 24 | 325 mL | 270 | 27 | 22 | 8 | 2 | 265 | 700 | 450 | 100 | 400 | 280 mL |
| BOOST Soothe — Strawberry-Kiwi | 28 | 237 mL | 300 | 10 | 65 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 186 mL |
| BOOST 1.5 — Vanilla, Chocolate, Strawberry | 30 | 237 mL | 360 | 13 | 52 | 11 | 0 | 310 | 460 | 300 | 100 | 250 | 180 mL |
| BOOST 2.24 — Vanilla, Chocolate, Strawberry | 32 | 237 mL | 530 | 22 | 52 | 26 | 0 | 280 | 420 | 250 | 80 | 250 | 159 mL |

BOOST Soothe is labelled as not being a significant source of other nutrients,
so the CSV records zero for the listed mineral fields. The calculator continues
to show that product's energy and macronutrients.
