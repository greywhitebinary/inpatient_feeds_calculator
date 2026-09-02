"""Formatted, temporary chart-note draft generation and rendering."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from typing import Mapping, Sequence

import streamlit as st

from calculations import (
    adjusted_body_weight_kg,
    hamwi_ibw_kg,
    harris_benedict_kcal,
    mifflin_st_jeor_kcal,
    penn_state_2003b_kcal,
    penn_state_2010_kcal,
)


CHART_NOTE_EDITOR_HTML = """
<div class="chart-note-toolbar">
  <button data-action="copy" type="button">Copy chart note</button>
  <button data-action="refresh" type="button">Update chart note from calculator</button>
  <span data-role="status">Calculations changed. Updating the note will replace your edits.</span>
  <span data-role="copy-status"></span>
</div>
<div class="chart-note-editor" contenteditable="true" role="textbox" aria-multiline="true" aria-label="Editable chart note"></div>
"""

CHART_NOTE_EDITOR_CSS = """
:host { color: var(--st-text-color); font-family: var(--st-font); }
.chart-note-toolbar { background: transparent; display: flex; gap: .55rem; align-items: center; flex-wrap: wrap; margin-bottom: .65rem; }
button { border: 1px solid color-mix(in srgb, var(--st-text-color) 20%, transparent); border-radius: .5rem; background: var(--st-background-color); color: var(--st-text-color); cursor: pointer; font: inherit; padding: .25rem .75rem; }
button:hover { background: color-mix(in srgb, var(--st-primary-color) 15%, transparent); filter: none; }
button[data-action="refresh"] { display: none; }
[data-role="status"] { background: transparent !important; border: 0; box-shadow: none; color: var(--st-text-color); display: none; font-size: .875rem; opacity: 1; padding: 0; }
[data-role="copy-status"] { color: #176a3a; font-size: .9rem; }
.chart-note-editor { border: 1px solid var(--st-border-color); border-radius: .45rem; min-height: 610px; padding: .9rem 1rem; font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.45; overflow-wrap: anywhere; }
.chart-note-editor:focus { border-color: var(--st-primary-color); box-shadow: 0 0 0 2px color-mix(in srgb, var(--st-primary-color) 18%, transparent); outline: none; }
"""

CHART_NOTE_EDITOR_JS = """
export default function(component) {
  const { data, parentElement } = component;
  const editor = parentElement.querySelector('.chart-note-editor');
  const refresh = parentElement.querySelector('[data-action="refresh"]');
  const status = parentElement.querySelector('[data-role="status"]');
  const copyStatus = parentElement.querySelector('[data-role="copy-status"]');
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem(data.storageKey)); } catch (_) { saved = null; }
  if (!saved) {
    saved = {html: data.generatedHtml, generatedHtml: data.generatedHtml, signature: data.signature};
  } else if (saved.signature !== data.signature) {
    if (saved.html === saved.generatedHtml) {
      saved = {html: data.generatedHtml, generatedHtml: data.generatedHtml, signature: data.signature};
    } else {
      refresh.style.display = 'inline-block';
      status.style.display = 'inline';
    }
  }
  editor.innerHTML = saved.html;
  sessionStorage.setItem(data.storageKey, JSON.stringify(saved));
  editor.oninput = () => {
    saved.html = editor.innerHTML;
    sessionStorage.setItem(data.storageKey, JSON.stringify(saved));
    copyStatus.textContent = '';
  };
  refresh.onclick = () => {
    saved = {html: data.generatedHtml, generatedHtml: data.generatedHtml, signature: data.signature};
    editor.innerHTML = saved.html;
    sessionStorage.setItem(data.storageKey, JSON.stringify(saved));
    refresh.style.display = 'none';
    status.style.display = 'none';
  };
  parentElement.querySelector('[data-action="copy"]').onclick = async () => {
    const plain = editor.innerText;
    try {
      if (window.ClipboardItem && navigator.clipboard.write) {
        await navigator.clipboard.write([new ClipboardItem({
          'text/html': new Blob([editor.innerHTML], {type: 'text/html'}),
          'text/plain': new Blob([plain], {type: 'text/plain'})
        })]);
      } else {
        await navigator.clipboard.writeText(plain);
      }
      copyStatus.textContent = 'Copied.';
    } catch (_) {
      const range = document.createRange();
      range.selectNodeContents(editor);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copyStatus.textContent = 'Select Copy in your browser to finish copying.';
    }
  };
}
"""

def _number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _entered(state: Mapping[str, object], key: str) -> float | None:
    value = state.get(key)
    return float(value) if value is not None else None


def _fmt(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}"


def _range(values: Sequence[float], decimals: int = 0) -> str:
    return "–".join(_fmt(value, decimals) for value in values)


def _compact_range(values: Sequence[float]) -> str:
    return "–".join(f"{value:g}" for value in values)


def _calculation_weight(state: Mapping[str, object]) -> tuple[float | None, str]:
    current = _entered(state, "assessment_current_weight")
    height = _entered(state, "assessment_height_cm")
    sex = str(state.get("assessment_sex") or "")
    choice = str(state.get("assessment_weight_choice") or "")
    ibw = hamwi_ibw_kg(sex, height) if sex and height is not None else None
    factor = _entered(state, "assessment_adjusted_weight_factor")
    adjusted = (
        adjusted_body_weight_kg(current, ibw, factor)
        if current is not None and ibw is not None and factor is not None
        else None
    )
    estimated = _entered(state, "assessment_estimated_weight")
    options = {
        "Current body weight": (current, "CBW"),
        "Hamwi IBW": (ibw, "IBW"),
        "Ideal body weight (Hamwi — SI units)": (ibw, "IBW"),
        "Adjusted body weight": (adjusted, "AdjBW"),
        "Adjusted body weight (Hamwi-based)": (adjusted, "AdjBW"),
        "Adjusted body weight (Hamwi IBW)": (adjusted, "AdjBW"),
        "Estimated dry / clinician-selected weight": (
            estimated,
            "RD-selected weight",
        ),
    }
    return options.get(choice, (None, "calculation weight"))


def _anthropometrics_html(state: Mapping[str, object]) -> str:
    lines: list[str] = []
    height = _entered(state, "assessment_height_cm")
    current = _entered(state, "assessment_current_weight")
    usual = _entered(state, "assessment_usual_weight")
    sex = str(state.get("assessment_sex") or "")
    if height is not None:
        lines.append(f"Height: {_fmt(height / 100, 2)} m")
    if current is not None:
        lines.append(f"Current body weight: {_fmt(current, 1)} kg")
    if current is not None and height:
        lines.append(f"BMI: {_fmt(current / (height / 100) ** 2, 1)} kg/m²")
    if sex and height is not None:
        ibw = hamwi_ibw_kg(sex, height)
        lines.append(f"IBW: {_fmt(ibw, 1)} kg (Hamwi)")
        factor = _entered(state, "assessment_adjusted_weight_factor")
        if current is not None and factor is not None:
            adjusted = adjusted_body_weight_kg(current, ibw, factor)
            lines.append(
                f"AdjBW: {_fmt(adjusted, 1)} kg "
                f"(IBW + {_fmt(factor, 2)} × [CBW − IBW])"
            )
    estimated = _entered(state, "assessment_estimated_weight")
    if estimated is not None:
        lines.append(
            f"Estimated dry / clinician-selected weight: {_fmt(estimated, 1)} kg"
        )
    if usual is not None:
        lines.append(f"UBW: {_fmt(usual, 1)} kg")
        if current is not None and usual > 0:
            change = current - usual
            percent = change / usual * 100
            lines.append(
                f"Weight change: {change:+.1f} kg ({percent:+.1f}%)"
            )
    return "<br>".join(escape(line) for line in lines) or "—"


def _requirements_html(state: Mapping[str, object]) -> str:
    weight, weight_label = _calculation_weight(state)
    sex = str(state.get("assessment_sex") or "")
    height = _entered(state, "assessment_height_cm")
    age = _entered(state, "assessment_age")
    energy_lines: list[str] = []
    comparable_energy_values: list[float] = []

    low_kcal = _entered(state, "assessment_energy_low_kcal_kg")
    high_kcal = _entered(state, "assessment_energy_high_kcal_kg")
    energy_bounds = [value for value in (low_kcal, high_kcal) if value is not None]
    if weight is not None and energy_bounds:
        results = [weight * value for value in energy_bounds]
        comparable_energy_values.extend(results)
        label = "Weight-based range" if len(results) == 2 else "Weight-based estimate"
        energy_lines.append(
            f"{label}: {_range(results)} kcal/day "
            f"({weight_label} {_fmt(weight, 1)} kg × "
            f"{_compact_range(energy_bounds)} kcal/kg)"
        )

    measured = _entered(state, "assessment_indirect_calorimetry")
    if measured is not None:
        comparable_energy_values.append(measured)
        energy_lines.append(f"Measured REE: {_fmt(measured)} kcal/day")

    ready = bool(sex and weight is not None and height is not None and age is not None)
    if ready:
        mifflin = mifflin_st_jeor_kcal(sex, weight, height, age)
        harris = harris_benedict_kcal(sex, weight, height, age)
        activity = _entered(state, "assessment_activity_factor")
        stress = _entered(state, "assessment_stress_factor")
        activity = 1.0 if activity is None else activity
        stress = 1.0 if stress is None else stress
        mifflin_adjusted = mifflin * activity * stress
        harris_adjusted = harris * activity * stress
        comparable_energy_values.extend([mifflin_adjusted, harris_adjusted])
        factor_text = f"AF {activity:g} × SF {_fmt(stress, 2)}"
        energy_lines.extend([
            f"MSJ: {_fmt(mifflin_adjusted)} kcal/day ≈ "
            f"{_fmt(mifflin)} kcal/day × {factor_text}",
            f"HB: {_fmt(harris_adjusted)} kcal/day ≈ "
            f"{_fmt(harris)} kcal/day × {factor_text}",
        ])
        temperature = _entered(state, "assessment_temperature")
        minute_ventilation = _entered(state, "assessment_minute_ventilation")
        if temperature is not None and minute_ventilation is not None:
            penn_2003b = penn_state_2003b_kcal(mifflin, temperature, minute_ventilation)
            penn_2010 = penn_state_2010_kcal(mifflin, temperature, minute_ventilation)
            comparable_energy_values.extend([penn_2003b, penn_2010])
            inputs = (
                f"Mifflin–St Jeor {_fmt(mifflin)} kcal/day, Tmax "
                f"{_fmt(temperature, 1)} °C, Ve "
                f"{_fmt(minute_ventilation, 1)} L/min"
            )
            energy_lines.extend([
                f"Penn State 2003b: {_fmt(penn_2003b)} kcal/day ({inputs})",
                f"Modified Penn State 2010: {_fmt(penn_2010)} kcal/day ({inputs})",
            ])

    target = _entered(state, "assessment_energy_target")
    target_is_represented = False
    if target is not None and weight is not None and len(energy_bounds) == 2:
        low_result, high_result = sorted(weight * value for value in energy_bounds)
        target_is_represented = low_result <= target <= high_result
    if target is not None and not target_is_represented:
        target_is_represented = any(
            abs(value - target) < 1 for value in comparable_energy_values
        )
    if target is not None and not target_is_represented:
        energy_lines.append(f"Energy goal used for EN plan: {_fmt(target)} kcal/day")

    if not energy_lines:
        energy_lines.append("—")

    protein_parts: list[str] = []
    protein_low = _entered(state, "assessment_protein_low_gkg")
    protein_high = _entered(state, "assessment_protein_high_gkg")
    protein_bounds = [value for value in (protein_low, protein_high) if value is not None]
    if weight is not None and protein_bounds:
        protein_results = [weight * value for value in protein_bounds]
        protein_parts.append(
            f"{_range(protein_results)} g/day "
            f"({weight_label} {_fmt(weight, 1)} kg × "
            f"{_compact_range(protein_bounds)} g/kg)"
        )
    else:
        protein_target = _entered(state, "assessment_protein_target")
        protein_parts.append(
            f"{_fmt(protein_target)} g/day" if protein_target is not None else "—"
        )

    water_parts: list[str] = []
    water_low = _entered(state, "assessment_water_low_mlkg")
    water_high = _entered(state, "assessment_water_high_mlkg")
    water_bounds = [value for value in (water_low, water_high) if value is not None]
    if weight is not None and water_bounds:
        water_results = [weight * value for value in water_bounds]
        water_parts.append(
            f"{_range(water_results)} mL/day "
            f"({weight_label} {_fmt(weight, 1)} kg × "
            f"{_range(water_bounds, 0)} mL/kg)"
        )
    else:
        water_target = _entered(state, "assessment_water_target")
        water_parts.append(
            f"{_fmt(water_target)} mL/day" if water_target is not None else "—"
        )

    other_lines: list[str] = []
    exudate = _entered(state, "assessment_exudate_ml")
    loss_factor = _entered(state, "assessment_protein_loss_factor")
    if exudate is not None and loss_factor is not None:
        other_lines.append(
            f"Estimated open-abdomen protein loss: {_fmt(exudate / 1000 * loss_factor)} "
            f"g/day ({_fmt(exudate)} mL/day × {_fmt(loss_factor)} g/L)"
        )
    other_loss = _entered(state, "assessment_other_protein_loss")
    if other_loss is not None:
        other_lines.append(f"Other estimated protein loss: {_fmt(other_loss)} g/day")

    energy_html = "<br>".join(escape(line) for line in energy_lines)
    protein_html = "<br>".join(escape(line) for line in protein_parts)
    water_html = "<br>".join(escape(line) for line in water_parts)
    other_html = "<br>".join(escape(line) for line in other_lines)
    return (
        f"<strong>Energy:</strong><br>{energy_html}<br><br>"
        f"<strong>Protein:</strong> {protein_html}<br>"
        f"<strong>Fluid:</strong> {water_html}<br>"
        f"<strong>Other:</strong>{('<br>' + other_html) if other_html else ''}"
    )


def _source_breakdown(sources: Sequence[tuple[float, str]], unit: str) -> str:
    used = [(amount, label) for amount, label in sources if round(amount, 6) != 0]
    if len(used) <= 1:
        return ""
    return " (" + " + ".join(
        f"{label} {_fmt(amount)} {unit}" for amount, label in used
    ) + ")"


def _ons_order_text(item: Mapping[str, object]) -> str:
    quantity = _number(
        item.get("quantity_each_time", item.get("containers_each_time", 0))
    )
    times = _number(item.get("times_per_day"))
    unit = str(
        item.get(
            "quantity_unit",
            item.get("serving_unit", item.get("package_unit", "container")),
        )
    )
    if quantity != 1:
        unit += "s"
    frequency = {
        1: "daily",
        2: "BID",
        3: "TID",
        4: "QID",
    }.get(int(times) if times.is_integer() else -1, f"{_fmt(times)} times/day")
    return f"{item['name']}, {_fmt(quantity)} {unit} {frequency}"


def _intervention_html(result: Mapping[str, object], include_label: bool) -> str:
    formula = dict(result["formula"])
    delivery = dict(result["delivery"])
    modular_totals = dict(result["modular_totals"])
    propofol = dict(result["propofol"])
    hydration = dict(result["hydration"])
    modulars = list(result.get("chart_modulars", []))
    ons = list(result.get("chart_ons", []))
    ons_totals = dict(result.get("ons_totals", {}))
    lines: list[str] = []
    prescription_target_pct = _number(result.get("prescription_target_pct", 100))
    if prescription_target_pct and prescription_target_pct != 100:
        estimated_requirement = _number(
            result.get("estimated_energy_requirement")
        )
        target_text = (
            f"EN prescription target: {_fmt(prescription_target_pct)}% of estimated "
            "energy requirement"
        )
        if estimated_requirement > 0:
            prescription_energy = (
                estimated_requirement * prescription_target_pct / 100
            )
            target_text += f" ({_fmt(prescription_energy)} kcal/day)"
        if (
            prescription_target_pct > 100
            and bool(result.get("prescription_interruption_note"))
        ):
            target_text += " to account for anticipated interruptions"
        lines.append(target_text + ".")

    propofol_method = result.get("propofol_method")
    if propofol_method in {"Single Propofol rate", "Single daily EN rate"}:
        rate = _number(result.get("propofol_rate"))
        hours = _number(result.get("propofol_hours"))
        if rate > 0 and hours > 0:
            lines.append(
                f"With projected Propofol at {_fmt(rate)} mL/hr for "
                f"{_fmt(hours)} hours/day:"
            )
        elif rate <= 0 or hours <= 0:
            lines.append("When Propofol is not running:")
    elif include_label:
        rate = _number(result.get("propofol_rate"))
        hours = _number(result.get("propofol_hours"))
        if rate > 0:
            scenario = (
                f"When Propofol is running at {rate:g} mL/hr for "
                f"{hours:g} hours/day, use this EN plan:"
            )
        else:
            scenario = "When Propofol is not running, use this EN plan:"
        lines.append(f"<strong>{escape(scenario)}</strong>")

    if propofol_method in {"Changing Propofol rates", "Conditional EN rates"}:
        exposure_parts = []
        for condition in result.get("propofol_conditions", []):
            condition_map = dict(condition)
            rate = _number(condition_map.get("rate_ml_hr"))
            hours = _number(condition_map.get("hours"))
            if rate > 0 and hours > 0:
                exposure_parts.append(
                    f"{_fmt(rate)} mL/hr for {_fmt(hours)} hours/day"
                )
        if exposure_parts:
            lines.append(
                "Projected Propofol exposure: " + " and ".join(exposure_parts) + "."
            )
        plan_label = (
            f"Initiate trickle EN with {formula['name']}."
            if bool(result.get("describe_as_trickle"))
            else f"Enteral nutrition plan: {formula['name']}."
        )
        lines.append(escape(plan_label))
        for order in result.get("conditional_orders", []):
            order_map = dict(order)
            propofol_rate = _number(order_map.get("propofol_rate_ml_hr"))
            formula_rate = _number(order_map.get("formula_rate_ml_hr"))
            if propofol_rate > 0:
                condition_text = f"Propofol is at {_fmt(propofol_rate)} mL/hr"
            else:
                condition_text = "Propofol is not running"
            lines.append(
                f"When {condition_text}, provide feed at {_fmt(formula_rate)} mL/hr."
            )
        lines.append(
            f"Projected formula delivery is {_fmt(_number(delivery.get('planned_volume_ml')))} "
            f"mL/day over {_fmt(_number(result.get('feeding_hours')))} feeding hours."
        )
    elif bool(result.get("describe_as_trickle")):
        lines.append(
            f"Initiate trickle EN with {escape(str(formula['name']))} at "
            f"{escape(str(result['schedule_description']))}."
        )
    else:
        lines.append(
            f"Enteral nutrition plan: {escape(str(formula['name']))} at "
            f"{escape(str(result['schedule_description']))}."
        )
    if modulars:
        modular_descriptions = []
        for item in modulars:
            description = f"{item['name']} {item['order']}"
            if _number(item.get("preparation_water_per_dose_ml")) > 0:
                description += (
                    f", administered with {_fmt(_number(item['preparation_water_per_dose_ml']))} "
                    "mL water each time"
                )
            modular_descriptions.append(description)
        lines.append("Modulars: " + "; ".join(escape(text) for text in modular_descriptions) + ".")
    if ons:
        lines.append(
            "ONS: " + "; ".join(
                escape(_ons_order_text(item)) for item in ons
            ) + "."
        )

    hydration_each = _number(hydration.get("hydration_flush_each_ml"))
    if hydration_each > 0:
        lines.append(
            f"Hydration: Provide {_fmt(hydration_each)} mL water flushes "
            f"{escape(str(result['hydration_chart_schedule_text']))}."
        )

    total = dict(result["chart_total"])
    energy_sources = [(delivery["energy_kcal"], "Formula")]
    energy_sources.extend(
        (_number(item["energy_kcal"]), str(item["name"])) for item in modulars
    )
    energy_sources.append((_number(propofol.get("kcal")), "Propofol"))
    protein_sources = [(delivery["protein_g"], "Formula")]
    protein_sources.extend(
        (_number(item["protein_g"]), str(item["name"])) for item in modulars
    )
    fat_sources = [(delivery["fat_g"], "Formula")]
    fat_sources.extend(
        (_number(item["fat_g"]), str(item["name"])) for item in modulars
    )
    fat_sources.append((_number(propofol.get("fat_g")), "Propofol"))

    formula_water = _number(delivery.get("free_water_ml"))
    modular_free_water = _number(modular_totals.get("free_water_ml"))
    water_sources = [f"Free water {_fmt(formula_water)} mL"]
    if modular_free_water:
        water_sources.append(f"Modular free water {_fmt(modular_free_water)} mL")
    ons_water = _number(ons_totals.get("free_water_ml"))
    if ons_water:
        water_sources.append(f"ONS water {_fmt(ons_water)} mL")
    for item in modulars:
        administration_water = _number(item.get("preparation_water_ml"))
        if administration_water:
            water_label = (
                f"{item['name']} flushes"
                if str(item["name"]) == "Beneprotein"
                else f"{item['name']} administration water"
            )
            water_sources.append(f"{water_label} {_fmt(administration_water)} mL")
    medication = _number(result.get("medication_flushes_ml"))
    patency = _number(result.get("patency_flushes_ml"))
    hydration_total = _number(hydration.get("hydration_flush_total_ml"))
    if medication:
        water_sources.append(f"Med flushes {_fmt(medication)} mL")
    if patency:
        water_sources.append(f"Patency flushes {_fmt(patency)} mL")
    if hydration_total:
        water_sources.append(
            f"Hydration flushes {_fmt(hydration_each)} mL "
            f"{result['hydration_chart_schedule_text']}"
        )

    total_water = _number(total["Free water (mL)"]) + _number(total["Water flushes (mL)"])
    if ons:
        ons_energy = _number(ons_totals.get("energy_kcal"))
        ons_protein = _number(ons_totals.get("protein_g"))
        ons_carbohydrate = _number(ons_totals.get("carbohydrate_g"))
        ons_fat = _number(ons_totals.get("fat_g"))
        regimen = (
            "At goal, EN and ONS orders provide "
            f"energy {_fmt(_number(total['Energy (kcal)']))} kcal "
            f"(EN {_fmt(_number(total['Energy (kcal)']) - ons_energy)} kcal + "
            f"ONS {_fmt(ons_energy)} kcal), "
            f"protein {_fmt(_number(total['Protein (g)']))} g "
            f"(EN {_fmt(_number(total['Protein (g)']) - ons_protein)} g + "
            f"ONS {_fmt(ons_protein)} g), "
            f"CHO {_fmt(_number(total['Carbohydrate (g)']))} g "
            f"(EN {_fmt(_number(total['Carbohydrate (g)']) - ons_carbohydrate)} g + "
            f"ONS {_fmt(ons_carbohydrate)} g), and "
            f"fat {_fmt(_number(total['Fat (g)']))} g "
            f"(EN {_fmt(_number(total['Fat (g)']) - ons_fat)} g + "
            f"ONS {_fmt(ons_fat)} g)."
        )
    else:
        regimen = (
            "At goal, the complete regimen provides "
            f"energy {_fmt(_number(total['Energy (kcal)']))} kcal"
            f"{_source_breakdown(energy_sources, 'kcal')}, "
            f"protein {_fmt(_number(total['Protein (g)']))} g"
            f"{_source_breakdown(protein_sources, 'g')}, "
            f"CHO {_fmt(_number(total['Carbohydrate (g)']))} g, and "
            f"fat {_fmt(_number(total['Fat (g)']))} g"
            f"{_source_breakdown(fat_sources, 'g')}."
        )
    water = (
        f"Total water provided is {_fmt(total_water)} mL/day ("
        + " + ".join(water_sources)
        + ")."
    )
    lines.extend([escape(regimen), escape(water)])
    return "<br>".join(lines)


def build_chart_note_html(
    state: Mapping[str, object],
    results: Sequence[Mapping[str, object]],
) -> str:
    """Build one ADIME-style note from calculation outputs without adding diagnoses."""
    interventions = "<br><br>".join(
        _intervention_html(result, include_label=len(results) > 1)
        for result in results
    )
    return (
        "<div><strong>Assessment</strong><br><br>"
        "<strong>Anthropometrics</strong><br>"
        f"{_anthropometrics_html(state)}<br><br>"
        "<strong>Estimated Nutrition Requirements</strong><br>"
        f"{_requirements_html(state)}<br><br>"
        "<strong>Nutrition Diagnosis</strong><br>"
        "[Complete in EMR]<br><br>"
        "<strong>Nutrition Intervention(s)</strong><br>"
        f"{interventions}<br><br>"
        "<strong>Monitoring, Evaluation, and Follow-Up Plan</strong><br>"
        "[Complete in EMR]</div>"
    )


def render_chart_note_editor(
    generated_html: str,
    *,
    editor_id: str,
    case_token: str,
    height: int = 760,
) -> None:
    """Render a rich, browser-local draft that is excluded from saved records."""
    signature = sha256(generated_html.encode("utf-8")).hexdigest()
    storage_key = f"encalc-chart-note:{case_token}:{editor_id}"
    st.session_state[f"_chart_note_generated_{editor_id}"] = generated_html
    editor_component = st.components.v2.component(
        f"encalc_chart_note_editor_{editor_id}",
        html=CHART_NOTE_EDITOR_HTML,
        css=CHART_NOTE_EDITOR_CSS,
        js=CHART_NOTE_EDITOR_JS,
    )
    editor_component(
        data={
            "generatedHtml": generated_html,
            "signature": signature,
            "storageKey": storage_key,
        },
        key=f"_chart_note_editor_{case_token}_{editor_id}",
        height=height,
    )
