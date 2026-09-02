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
| `formulary_working/canada_formulas_working.csv` | Jevity 1.2 Cal, Jevity 1.5 Cal, Osmolite 1.2 Cal, and TwoCal HN product information sheets | [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/modular_products_working.csv` | Nestlé and Abbott documents above | [Nestlé Health Science Canada](https://www.nestlehealthscience.ca/) and [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/ons_products_working.csv` | `2026_nestle-product-guide.pdf` and `2024_abbott-adult-product-guide.pdf` | [Nestlé Health Science Canada](https://www.nestlehealthscience.ca/) and [Abbott Nutrition Canada](https://www.nutrition.abbott/ca/en/home.html) |
| `formulary_working/modular_products_working.csv` | `medtrition/ProSource-NoCarb_CMI-Canada_p2.jpg`, `medtrition/HiFibre_CMI-Canada_p2.jpg`, and `medtrition/BanatrAll-with-GOS_CMI-Canada_p2.jpg` | [CMI Canada](https://cmi-canada.com/) |
| Future regional pack | Store documents in `reference_documents/<country>/` | Use the relevant official manufacturer site |

The row-level `source` column is the authoritative map to document and page.
An official source-site link alone does not show that a value is current;
verify the local product information and update `verified` after each review.

## Local review workflow

For an update, tell a coding assistant the exact local folder and scope. For
example:

> Review the documents in `reference_documents/canada/` against the Canadian
> formula and modular CSVs. List each changed value with its document and
> page, update only the CSVs and this source register where needed, and do not
> add or commit the source documents.

Keep source documents in private backup storage that follows the
manufacturers' terms.
