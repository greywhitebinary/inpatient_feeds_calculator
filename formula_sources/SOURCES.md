# Product-data source register

The CSV files in `formulary_working/` are the public runtime data used by
ENCalc. The manufacturer documents used to review those values belong locally
in `reference_documents/canada/`, which is ignored by Git. The application
does not read those documents at runtime.

Before changing a formula or modular row, obtain the current manufacturer
document from its official Canadian source, place it in the local reference
folder, and verify every changed value. Record the document filename, page,
and review date in the CSV `source` and `verified` columns. Do not commit the
document itself.

## Current Canadian sources

| Public data | Local reference document | Official source |
|---|---|---|
| `formulary_working/canada_formulas_working.csv` | `2026_nestle-product-guide.pdf` | [Nestlé Health Science Canada](https://www.nestlehealthscience.ca/) |
| `formulary_working/canada_formulas_working.csv` | `2024_abbott-adult-product-guide.pdf` | [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/canada_formulas_working.csv` | Jevity 1.2 Cal, Jevity 1.5 Cal, Osmolite 1.2 Cal, TwoCal HN, and Pivot 1.5 Cal product information sheets | [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/modular_products_working.csv` | Nestlé and Abbott documents above | [Nestlé Health Science Canada](https://www.nestlehealthscience.ca/) and [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/ons_products_working.csv` | `2026_nestle-product-guide.pdf` and `2024_abbott-adult-product-guide.pdf` | [Nestlé Health Science Canada](https://www.nestlehealthscience.ca/) and [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/modular_products_working.csv` | `medtrition/ProSource-NoCarb_CMI-Canada_p2.jpg`, `medtrition/HiFibre_CMI-Canada_p2.jpg`, and `medtrition/BanatrAll-with-GOS_CMI-Canada_p2.jpg` | [CMI Canada](https://cmi-canada.com/) |
| Future regional pack | Store documents in `reference_documents/<country>/` | Use the relevant official manufacturer site |

The row-level `source` column is the authoritative map to document and page.
An official source-site link alone does not show that a value is current;
verify the local product information and update `verified` after each review.

For source selection and disagreements, follow
[Data conventions, section 9](DATA_CONVENTIONS.md#9-source-precedence).

## Why five products cite a sheet rather than the guide

Jevity 1.2 Cal, Jevity 1.5 Cal, Osmolite 1.2 Cal, TwoCal HN and Pivot 1.5 Cal
cite their own product information sheets because the collated Abbott guide was
wrong or insufficient for those rows, not because more reading is better.

Pivot 1.5 Cal is the clearest case. The guide's "Per 237 mL" column prints the
fat, carbohydrate and fibre blocks as per-100-mL values, so transcribing that
column understated all three by about 2.4-fold. The row was re-sourced to
`Pivot-1.5-Cal-en.pdf` on 2026-09-02. The four ready-to-hang products are here
for a narrower reason: the guide's figures describe a different container
format, and sodium, potassium and free water differ in the ready-to-hang
product a ward actually hangs.

Both defects surfaced from arithmetic rather than closer reading, which is the
part worth carrying forward. Converting a document's two basis columns to a
common basis and comparing them exposes a column that does not mean what its
heading says, and Pivot separately failed an energy reconciliation at 57% of
its declared calories where every sound row lands between 98% and 106%. Neither
check needs the right answer in advance. Both are set out in
`DATA_CONVENTIONS.md` section 6, with a script for the second.

The three Ensure sheets added on 2026-09-10 are a different matter. They record
one flavour each rather than correcting the guide, and Ensure Protein Max 30 g
is what first showed that two flavours of one product can differ.

See `DATA_CONVENTIONS.md` for the blank-versus-zero rule, what each class of
source document is capable of disclosing, the jurisdiction rule, and the two
cross-checks that catch transcription errors. Outstanding work and the record
of the 2026-09-02 full verification are in `VERIFICATION_BACKLOG.md`.

## Local review workflow

For an update, tell a coding assistant the exact local folder and scope. For
example:

> Review the documents in `reference_documents/canada/` against the Canadian
> formula and modular CSVs. List each changed value with its document and
> page, update only the CSVs and this source register where needed, and do not
> add or commit the source documents.

Keep source documents in private backup storage that follows the
manufacturers' terms.
