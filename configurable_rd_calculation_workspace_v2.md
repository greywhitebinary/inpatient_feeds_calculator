# Configurable RD Calculation Workspace — Working Notes

**Status:** Early concept / thinking document  
**Date:** August 23, 2026

## Product name and scope structure

The product is named **Adult Inpatient Enteral Nutrition Calculator**.

Its clinical workflow is organized as:

1. **General inpatient feeding** for the shared adult inpatient assessment, EN formula selection, modulars, water flushes, nutrition sources, and chart note.
2. **ICU additions** for features that are specifically relevant to critical care, such as propofol energy/fat scenarios and ventilator-dependent energy estimation.

Open abdomen, fistula, and other measurable surgical-loss situations should not be hidden inside ICU additions. These are clinical additions to the general workflow because a stable patient may be cared for outside an ICU according to local surgical and monitoring capacity. The calculation must retain wound or fistula output as an explicit, dated input and show its nutritional implications separately from EN delivery.

## The idea

Build a small, standalone web tool for dietitians that combines:

1. **Clinical nutrition equations** the RD chooses to use.
2. **A configurable enteral formula formulary** containing the products the RD or institution actually uses.
3. **Side-by-side comparison tools** for formulas and calculated requirements.
4. **A portable configuration file** that can be downloaded, shared, and uploaded again.

The goal is not to build an EMR-integrated clinical system. The first version should work independently, with the clinician deliberately entering the values needed for a calculation and interpreting the output themselves.

The underlying question is whether AI-assisted coding now makes this kind of small, configurable clinical tool practical to build and maintain even when the problem would previously have been handled with a spreadsheet.

## Implementation decision for V1

Build the first version as a **Python and Streamlit** application. This fits a standalone, form-heavy clinical calculator and the builder's existing experience maintaining a Streamlit nutrition tool.

Keep the validated calculation logic and product data separate from the Streamlit pages. If a later version genuinely needs institutional integration, multi-user workflows, or a more complex application interface, the user interface can be reconsidered without rewriting the clinical calculation layer.

React, Next.js, and FHIR/EMR integration are not V1 requirements.

---

## Agreed V1 workflow

The application should preserve the useful separation in the existing workbooks rather than compress everything into one calculator page.

### Assessment

The normal state is a **General Inpatient EN Record**. The Assessment page should be closer in structure to the longer nutrition-support workbook. It will collect the shared patient measurements and weight history, show several transparent energy estimates, and allow the RD to select or enter an assessment energy target. It should also carry forward the protein and fluid context needed for the next step.

The calculator presents the mathematics. It does not choose a target for the clinician. A measured energy-expenditure value, if the clinician already has one, is recorded as an optional manual input rather than calculated by the application.

Sex-specific equation rows should disappear once the sex used by the equations is entered, so that an inapplicable calculation cannot be selected. An optional **ICU additions** control should reveal ICU-specific calculations and contributors, while ventilator-dependent calculations should appear only after mechanical ventilation is identified. The interface should not leave blank rows behind when it hides an option.

The General inpatient feeding assessment should make a surgical-loss calculation understandable when it is relevant: for example, open-abdomen protein loss is entered as exudate volume multiplied by an RD-entered protein-loss factor, with a separate field for another quantified protein loss. Those amounts contribute to the total protein requirement. This remains available outside ICU additions because surgical patients may be managed outside the ICU according to local care capacity.

Protein adjustments should use progressive detail. The default is **no additional loss**. The RD can instead select a single manual addition, an open-abdomen exudate calculation, or a detailed surgical/critical-care addition that combines exudate with another quantified loss. The detailed choices appear only when selected, because the usefulness of detailed accounting depends on the reliability of the clinical input data.

### Enteral plan and water flushes

The EN page should be compact and spreadsheet-like, following the clearer workflow of the Ax and EN workbook. It begins with the assessment target but allows the RD to revise the EN energy target after accounting for non-enteral energy, such as propofol, and the planned feeding schedule.

It then calculates the formula volume, rate, nutrient delivery, free water, and water flushes for continuous or intermittent feeding. Propofol and other non-enteral energy should be calculated upstream in Assessment and handed to the EN page as the EN energy target and, when needed, propofol-rate scenarios. The EN page should show its assumptions and totals together so that the RD can inspect the calculation before using it.

#### EN page design decisions — August 26, 2026

The desktop workflow is deliberately ordered as:

1. **Feeds:** compare the clinically plausible formulas, choose one, and set the delivery schedule. The calculator works forward from the RD's EN energy target and the selected run time to propose a rounded rate or volume, rather than requiring the RD to enter a rate first.
2. **Modulars:** add a specific nutrient or property to the selected feed when needed.
3. **Water flushes:** account for free water, modular-related water, medication/patency flushes, and other counted water, then calculate a practical hydration-flush plan.

The saved feed formulary and saved modular library have no product-count cap. In a single EN plan, the active comparison may contain up to **nine feeds**, and the active plan may contain up to **six modular orders**. These are separate limits: feeds are candidates compared before choosing a formula, whereas modular orders are sources added to the chosen plan.

The Formulary page has separate **Feeds** and **Modulars** views. Each begins with the RD's saved cards, not with a wall of master-library cards. **Find a feed** or **Find a modular** opens a searchable, scrollable reference list that can be filtered to **All**, **Nestlé**, or **Abbott**. In that reference list, **Add to My Formulary** or **Add to My Modulars** saves a product locally, while each saved card has only **Remove**. Selecting up to nine feeds for a clinical comparison happens on the EN page, where it has a clear clinical purpose. This supports either a short personal list of usual products or a complete institutional formulary.

The EN page begins with a compact selector populated from My Formulary. The RD chooses up to nine candidates before viewing the calculated comparison, then chooses one formula for the planned-delivery and early-step-up views. The formula comparison presents the selected formula at 100% planned EN and at an RD-entered achieved percentage. The achieved-volume row shows the consequence of delivery, rather than being a second proposed order. Where a modular is separately ordered, it remains a distinct source rather than being hidden inside the feed calculation.

The modular library remains a plain saved list until there is evidence that a practical hospital formulary classification helps. Before the Modulars section, the EN page shows a compact **Protein check**: protein target, protein from planned EN, and protein still to cover. It informs the selection and quantity of a modular without making the modular order editor a protein dashboard. Each modular order shows its calculated nutrient and water contribution. The named final split, such as protein from EN plus protein from Beneprotein, belongs in the nutrition-source summary and chart text.

The first modular example is Beneprotein, using its own packet-based serving amount and editable local preparation-water input. This is an example, not a universal modular interface. The EN page can add up to six product-specific modular orders from My Modulars; each has its own serving amount, times-per-day frequency, and water-per-unit input.

Each modular product in the formulary needs product-specific metadata for:

- serving unit and label, such as packet, scoop, gram, mL, pouch, or bottle;
- nutrient contribution per unit, including relevant calories, macronutrients, fibre, electrolytes, and inherent water;
- any local default dose/frequency; and
- its water handling rule: no preparation water, an editable local default, or an RD-entered water amount.

Selecting a modular should adapt the dose controls to that product. A Beneprotein order may use packets per dose and doses per day, while a liquid protein product may use pouches per day and a fat modular may use mL per dose. The product's calculated nutrient contribution must flow to the relevant plan totals, and its preparation water must flow automatically into the water-flush calculation. Do not apply Beneprotein packet sizes or preparation assumptions to other modulars.

### Working formulary data — August 26, 2026

The copied BTF Canada formula dataset is kept as a project-only working file. It contains 33 adult formulas, with the per-mL macro, electrolyte, and free-water values needed for the calculator. All 33 product names were confirmed to appear on the source PDF page recorded in that file. It remains a working dataset until its values have been checked against the current manufacturer guide and locally reviewed.

For four Abbott feeds, the can and ready-to-hang bag labels did not normalize consistently in the earlier product guide. The hospital formulary uses the ready-to-hang bag values because that is the clinical presentation in use. The profiles for Jevity 1.2 Cal, Jevity 1.5 Cal, Osmolite 1.2 Cal, and TwoCal HN were re-verified from Abbott's 2025 product information sheets on 2026-08-27. Do not show container choice or source-format detail to the RD during feed selection.

Each initial formula record is one hospital-use profile with values drawn from the ready-to-hang bag label where that presentation exists. Source format, volume, document, and verification date are retained only as maintenance metadata. They do not become an RD-facing selector, and the calculator does not derive its hospital profile by converting can data.

The formulary is primarily a local-stock and product-type picker, not a nutrient-comparison screen. Each My Formulary card shows the product, manufacturer, clinically meaningful formula type, and a fixed compact profile in this order: energy, protein, free water, sodium, potassium, calcium, P, magnesium, and fibre. The formulary manages saved products only; the EN page is where the RD selects the plausible feeds and inspects their calculated nutrient consequences.

My Modulars is simpler: each saved card shows the product, manufacturer, and dose basis only. Its energy, macronutrients, free water, and any local preparation-water assumption appear after the product is added to an EN plan, because they depend on the chosen dose and frequency. Product classification remains deliberately undecided until a useful hospital formulary convention is reviewed.

Manufacturer labels remain stored in their printed units. The fixed clinical display for Na, K, Ca, P, and Mg is mmol, to one decimal place; the normal formulary workflow does not expose a unit switch. Convert from mg to mmol by dividing by the atomic weight in mg/mmol: Na 22.99, K 39.10, Ca 40.078, P 30.974, and Mg 24.305. The original mg values remain available in the exported workbook and any later source-verification view. Other vitamins and trace minerals remain in their source units, usually mg or mcg, unless a later workflow establishes a clinical need for another display.

Modulars use a separate product table because their labelled dose bases differ. The first Canadian entries are Beneprotein (one packet or scoop, 7 g), Nestlé MCT Oil (10 mL), and Abbott LiquiProtein (6 mL). The table stores nutrients per labelled basis and a product-specific water rule. It does not prescribe a default clinical dose or frequency.

The final **Nutrition sources** table is a numeric source-and-total table only. Its headers carry the units, and it does not repeat the order or feeding schedule. Water is reported simply as **free water** plus one combined **Water flushes** total, rather than splitting modular-preparation, medication, patency, hydration, and other water into separate summary rows. Medication and patency flushes remain optional direct daily inputs that count toward the water target and reduce the calculated hydration-flush amount. The early step-up table remains above it because it serves a separate clinical purpose.

The separate, read-only **Chart note** is generated entirely from the current inputs and contains, in order:

1. EN schedule;
2. modular schedule;
3. hydration-flush schedule; and
4. planned daily intake, including energy, protein with EN/modular source split, carbohydrate, fat, and fluids as free water plus water flushes.

For generated modular frequencies, use `once daily`, `BID`, `TID`, and `QID` for one through four doses per day. Do not generate `OD`, `QD`, `QOD`, or `EOD`; write `daily` or `every other day` instead. For five or more doses daily, write the frequency in full. Local organizational documentation policy can be stricter and must take precedence.

Propofol instructions belong to the Assessment handoff. The handoff must retain the active propofol rate and any calculated EN-rate alternatives so that the chart note can state a conditional EN instruction. Its active-rate daily intake must count propofol energy and fat as separate sources.

### Wireframe completion notes — August 26, 2026

The wireframe phase is complete and the next work is implementation, not further app construction or a redesign.

- The shared navigation is **Formulary**, **Assessment**, and **EN plan**. ICU-specific inputs live in a collapsible **ICU additions** section within Assessment rather than as a top-level tab.
- Assessment height defaults to metres and may be entered as feet/inches. Calculations convert height internally to centimetres; the Hamwi, Mifflin–St Jeor, Harris–Benedict, and Penn State calculations must use that centimetre value.
- Assessment uses an RD-chosen calculation weight selected from current body weight, Hamwi IBW, adjusted body weight with an editable correction factor, or an estimated dry/clinician-selected weight. The selected option itself displays its calculated kg value; there is no redundant output cell.
- Indirect calorimetry is an optional entered result that informs, but does not override, the editable **Energy target for EN plan**. The target appears after the available estimates and is the value carried to EN.
- Protein and water targets remain RD-entered. Additional protein losses are a nested disclosure within Protein target, with **Protein from exudate** first and **Other protein losses** second. They are shown before the protein target so the RD can consider them, but they do not automatically adjust the entered target or handoff. Do not imply a 2 g/kg ceiling.
- The EN page works from the Assessment targets but allows the EN energy target, protein target, and water target to be revised. Its flow is feeds, then modulars, then water.
- The selected-formula table retains full planned EN plus an RD-entered alternate achieved-delivery percentage. The alternate row is a reference view, not a second order, and does not need a different colour.
- The final **Planned daily intake** source-and-total table can be switched between full planned EN and the entered alternate percentage. The chart note must identify an alternate delivery view clearly and continue to state the full planned EN schedule as the order.
- Water planning uses free water from the selected delivery view plus one combined **Water flushes** total in the summary and chart note. Medication and patency flushes are optional daily inputs. The patency field includes the reference: ASPEN minimum 30 mL q4h for continuous adult EN.
- In numerical EN tables, units appear in the column headers and not again in the values. Delivery schedule cells retain units because they are instructions. Assessment energy-equation and weight-result tables follow the same header-unit convention where applicable.
- The end of EN plan contains the numeric source-and-total table, then a read-only chart note. The chart note order is EN schedule, modular schedule, hydration-flush schedule, then daily intake. It is a review-and-copy aid; charting or locking remains a separate phase.

Current editable wireframes are saved outside the implementation project at:

- `/Users/hjc/.codex/visualizations/2026/08/26/01a03c8a-fee3-7192-8285-c2988d79e9ef/formulary-feed-profile-wireframe.html`
- `/Users/hjc/.codex/visualizations/2026/08/26/01a03c8a-fee3-7192-8285-c2988d79e9ef/assessment-targets-wireframe.html`
- `/Users/hjc/.codex/visualizations/2026/08/26/01a03c8a-fee3-7192-8285-c2988d79e9ef/en-regimen-collapsed-delivery-wireframe.html`

---

## Why this came up

I have previously built clinical nutrition spreadsheets for my own practice. One was deliberately designed so another RD could maintain it without changing any formulas.

The vendor's tube-feed information appeared in a predictable order on a PDF. I created a section of the spreadsheet where the RD could update those product numbers in corresponding columns while leaving the cells containing the calculation formulas untouched.

Years later, another RD emailed asking whether I had a Nestlé version of a spreadsheet that contained Abbott feeds. I did not. I explained how I had structured it so the product data could be updated transparently. She was able to update it herself.

That design solved an important spreadsheet problem: **the tool was not completely dependent on the person who originally built it.**

A web tool could potentially make the same separation clearer:

- **stable calculation logic** stays in the application;
- **changeable local information** such as the enteral formulary stays editable by the user;
- the user does not need to understand Excel formulas or application code.

---

## Existing example: EnteralCalc

**Website:** https://enteralcalc.net/

EnteralCalc is a useful example of this pattern.

As of August 2026, the site allows a clinician to:

- select an enteral formula;
- enter a rate, feeding hours, and water flushes;
- calculate calories, protein, free water, total fluid, carbohydrate, fat, potassium, and phosphorus;
- enter calorie and/or protein goals to suggest a feeding rate;
- add, edit, or delete formulas;
- export the formula list;
- import a formulary from a **JSON file**;
- reset the formula list to the supplied defaults.

The site explicitly tells users to verify product information against their facility's label/product information and allows them to maintain their own formulas.

What is particularly useful here is not simply the enteral calculation. It is the separation between the **calculator** and the **user's formulary**.

A dietitian can maintain a small working set of the formulas they actually use instead of repeatedly entering product information or searching a very large master list.

### Pattern worth borrowing

**Shared calculator logic → configurable local formulary → portable JSON file**

The JSON file is not intended to be the clinician's editing interface. The website provides the forms. JSON is simply the portable representation underneath.

---

## Proposed RD workspace

The concept would extend that pattern beyond an enteral formula calculator.

### 1. Nutrition equations

The application contains validated implementations of equations such as:

- Mifflin–St Jeor
- Harris–Benedict
- other equations added only after deciding that they belong in scope

The RD chooses which equations appear in their workspace.

The configuration file might record something conceptually like:

```json
{
  "energy_equations": [
    "mifflin_st_jeor",
    "harris_benedict"
  ]
}
```

The **actual equation should remain in the application's validated code**. Users should not be expected to enter or modify equation logic in JSON.

### 2. My Formulary

Start with a master list of common Canadian enteral products, likely including Abbott and Nestlé products.

The RD can then create **My Formulary**:

- select the formulas their site actually stocks;
- hide products they never use;
- add a local or new product;
- edit nutrient information when a manufacturer changes a product;
- attach the manufacturer's product/label source;
- export the resulting formulary;
- import a formulary prepared by another RD or institution.

The persistence flow is intentionally visible: upload a saved local formulary at the top of the page and download **My Formulary (.xlsx)** at the bottom. The exported workbook contains separate **My Formulary** and **My Modulars** worksheets, with saved products and their nutrient profiles only; it contains no patient information. The workbook is the RD-facing import/export format because it can be read and reviewed in Excel; import validation remains mandatory. JSON may remain an internal representation, but it is not the default clinician-facing file.

This avoids forcing an RD to enter the same six commonly used feeds every day.

### 3. Current-plan comparison

A working formulary and a case comparison are not the same thing.

An institution might routinely use six formulas, but only two or three may be sensible possibilities for a particular case.

The tool should therefore allow:

**master product library → my formulary → products selected for this comparison**

Possible side-by-side fields might include:

- kcal/mL;
- protein;
- free water;
- volume needed to meet a selected calorie target;
- resulting protein;
- fluid contribution;
- selected electrolytes or micronutrients where clinically useful.

The clinician remains responsible for deciding which products are reasonable comparators and how the results should influence care.

---

## Why JSON may be useful

For this use case, JSON has several advantages as the portable configuration format:

- small and easy for a website to read;
- straightforward to export and import;
- can be validated before the application accepts it;
- separates local configuration from application code;
- easy to share between colleagues;
- does not contain spreadsheet formulas that can accidentally be overwritten;
- can preserve a user's selected equations, formulary, and preferences in one file;
- does not require an account or a central institutional database simply to move a configuration between computers.

The RD should not need to edit raw JSON. They make changes through the website and click something like **Export configuration**.

Excel still has an important strength: it is directly inspectable by people who know spreadsheets. A future design does not have to treat Excel and JSON as competitors. For example, a master product dataset could still be maintained in a human-reviewable table while user configurations are exported as JSON.

---

## Why a web tool instead of another spreadsheet?

This needs to remain an open question rather than an assumption.

A spreadsheet may already be the better tool when:

- one institution has a stable formulary;
- a competent person maintains it;
- the calculations are transparent;
- sharing/version control is manageable;
- the workflow does not benefit much from a different interface.

A web tool starts to add value if it makes it easier to:

- configure a local formulary without spreadsheet skills;
- reuse that configuration;
- share it with colleagues;
- compare formulas cleanly;
- maintain calculation logic separately from product data;
- add new calculation modules without requiring users to understand formulas or workbook structure;
- provide a consistent interface across organizations while allowing local differences.

The point is not to replace Excel because a website looks more modern. The website needs to solve a real maintenance, usability, portability, or workflow problem.

---

## Validation criterion: can we define what "right" means?

Before treating a clinical calculation as suitable for a small standalone tool, ask whether correctness can be defined tightly enough to test.

For a deterministic nutrition calculator, this may be tractable:

- verify source values against CNF/manufacturer data;
- use known input/output cases;
- test unit and household-measure conversions;
- confirm formula totals independently;
- test edge cases and regressions after changes.

This is different from an open-ended clinical reasoning or evidence-synthesis system, where a correct response depends on retrieval, interpretation, uncertainty, conflicting evidence, and a large clinical context. Those systems require a fundamentally different level of validation.

A calculation being mathematically simple does not automatically make the surrounding clinical task simple. TPN is an example: arithmetic can be tested, but a useful tool rapidly becomes dependent on labs, pharmacy decisions, and a changing clinical picture.

For this project, the preferred territory is therefore not merely "low-risk" or "no PHI." It is work where **the intended output is bounded enough that we can specify and test what correct means**.

---

## Explicitly out of scope for V1

### No EMR integration / FHIR

Do not start by trying to pull weight, height, labs, orders, or other patient information automatically from an EMR.

FHIR and EMR integration may be worth learning later, but they introduce a different class of technical and organizational questions: authentication, permissions, privacy/security review, vendor implementation differences, data mapping, testing, and possibly write-back governance.

For the first version, typing a handful of values manually may be a very favourable trade if it keeps the tool independent of enterprise integration.

### No autonomous clinical decisions

The tool calculates, organizes, and compares.

It does not decide which formula should be ordered or what the patient's treatment should be.

### No server-side patient records; optional local case file

A first version must not create a database of patient cases or identifiers, and it must include no application feature that stores or exposes entered case data to the site owner. Assessment and EN-plan values are held for the active Streamlit session, which processes them on the server hosting the Python application while the calculator is in use. An RD may voluntarily download a local Excel case-record file and later upload it to restore the same assessment, EN-plan inputs, and formulary snapshot. The application does not retain the file or create a case record from it.

The application must not provide separate PHN, date-of-birth, room-number, or other identifier fields. The patient / record label is part of the clinician's downloaded local file and must follow local privacy policy. The clinician and institution remain responsible for storing and transferring that file appropriately.

### No user-defined equation code

Users can choose which validated equations they want available. They should not be able to replace the underlying equation with arbitrary code or an unvalidated formula through the configuration file.

---

## Possible V1

Keep the first build small enough to inspect.

1. Python and Streamlit application.
2. Assessment with transparent energy estimates and an RD-selected or entered target.
3. EN plan and water-flush calculation, including continuous and intermittent schedules.
4. A master enteral formula library.
5. **My Formulary** and **My Modulars** selection.
6. Add/edit a custom product.
7. Compare up to 9 selected formulas and add up to 6 modular orders to an EN plan.
8. Export My Formulary as an Excel workbook (.xlsx).
9. Import My Formulary from an Excel workbook (.xlsx), with validation.
10. No login.
11. No patient database or application-level case storage; voluntary local case-file download/upload only. A hosted Streamlit session still processes input on its active host.
12. No EMR/FHIR integration.

Then use it before deciding what belongs in V2.

---

## Next design task

Design the **EN plan and water-flush page** next, using the Ax and EN workbook as the structural reference. It needs to receive the Assessment target, allow the RD to revise the EN energy target after non-enteral energy such as propofol, and show formula selection, delivery schedule, rate, nutrient totals, and hydration/flush calculations together.

Assessment refinements to return to later: a source-and-reference presentation for optional protein factors, a clearer amputation workflow that distinguishes adjusted reference IBW from estimated intact-equivalent current weight, and the final selection of equations and ICU details.

---

## Questions to answer before building too far

- Which equations do RDs actually want together in one workspace?
- What calculations are sufficiently standardized to belong in the core application?
- Which data should be centrally maintained versus locally editable?
- Should product data include provenance and a **last verified** date?
- Should a user be able to override master product data, or only create a local copy?
- How should the tool warn users when product information may be stale?
- Is JSON import/export enough, or would browser-local persistence materially improve usability?
- Is there enough advantage over existing websites, MDCalc, manufacturer calculators, and well-designed spreadsheets to justify another tool?
- What level of testing and validation is appropriate before colleagues use it in clinical practice?
- If the original builder disappears, what documentation and structure allow the next person to maintain the tool safely?

---

## Later: revisit the original spreadsheet

I still need to locate the clinical nutrition spreadsheet I built years ago.

When I find it, review:

- how the vendor product data was separated from calculation formulas;
- which calculations it actually included;
- how the layout mirrored the manufacturer PDF;
- what assumptions were embedded in it;
- what another RD had to understand in order to convert the Abbott version to Nestlé;
- which parts of that design should survive in a web version;
- which parts are now unnecessary because the application can manage configuration differently.

The spreadsheet is important evidence because it shows how I previously tried to make a clinician-built tool maintainable **before AI-assisted software development was an option**.

---

## Related essay thought

This project also provides a concrete way to think about a broader question:

> When I notice an irritating healthcare problem, how do I decide whether it is one I can reasonably try to build my way out of with AI?

The current answer is provisional. This tool was attractive because it appears possible to make it:

- bounded;
- standalone;
- useful in real clinical work;
- configurable to local practice;
- based on inspectable calculations and source data;
- usable without EMR integration;
- reviewable by the clinician before the result affects care;
- maintainable without requiring the original builder to personally update every local version.

That list is not a finished framework. Part of the point of building more tools is to see which of these assumptions survive.
