"""Shared rendering and formatting helpers for Streamlit pages."""

from __future__ import annotations

from base64 import b64encode
from html import escape
from numbers import Real
from pathlib import Path
from typing import Mapping

import pandas as pd
import streamlit as st

from calculations import mg_to_mmol
from constants import FORMULARY_TABLE_DECIMALS

def number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def render_worked_bounds(
    label: str, calculation_weight: float | None, lower: float | None,
    upper: float | None, unit: str, weight_basis: str | None = None,
) -> None:
    """Render a complete range or one entered weight-based target value.

    Pass `weight_basis` where the weight in play is not visible next to the
    figure. Water has no selector of its own and silently follows the energy
    weight, so naming the weight is the only way the reader can tell which one
    produced the range.
    """
    if calculation_weight is None:
        return
    values = []
    if lower is not None:
        values.append(f"{lower * calculation_weight:.0f}")
    if upper is not None:
        values.append(f"{upper * calculation_weight:.0f}")
    if values:
        result = "–".join(values)
        basis = (
            f' <span class="calculated-range-basis">using {calculation_weight:.1f} kg'
            f' ({weight_basis})</span>'
            if weight_basis else ""
        )
        st.markdown(
            f'<p class="calculated-range">{label}: '
            f'<strong>{result} {unit}</strong>{basis}</p>',
            unsafe_allow_html=True,
        )


def render_box_heading(label: str) -> None:
    """Render a compact heading inside workflow boxes."""
    st.markdown(
        f'<p class="box-heading"><strong>{escape(label)}</strong></p>',
        unsafe_allow_html=True,
    )


def compact_feed_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, item in frame.iterrows():
        rows.append({
            "Product": item["name"],
            "Energy\nkcal/mL": number(item["kcal_per_mL"]),
            "Protein\ng/L": number(item["protein_per_mL"]) * 1000,
            "Free water\nmL/L": number(item["free_water_per_mL"]) * 1000,
            "Na\nmmol/L": mg_to_mmol("sodium", number(item["sodium_per_mL"]) * 1000),
            "K\nmmol/L": mg_to_mmol("potassium", number(item["potassium_per_mL"]) * 1000),
            "Ca\nmmol/L": mg_to_mmol("calcium", number(item["calcium_per_mL"]) * 1000),
            "P\nmmol/L": mg_to_mmol("phosphorus", number(item["phosphorus_per_mL"]) * 1000),
            "Mg\nmmol/L": mg_to_mmol("magnesium", number(item["magnesium_per_mL"]) * 1000),
            "Fibre\ng/L": number(item["fibre_per_mL"]) * 1000,
        })
    return pd.DataFrame(rows)


def render_report_table(
    frame: pd.DataFrame,
    *,
    dense: bool = False,
    wide: bool = False,
    decimals: Mapping[str, int] | None = None,
    row_decimals: Mapping[str, int] | None = None,
    default_decimals: int = 1,
) -> None:
    """Render static clinical tables with one shared visual language."""
    def header(label: object) -> str:
        parts = escape(str(label)).split("\n", 1)
        return f"{parts[0]}<small>{parts[1]}</small>" if len(parts) == 2 else parts[0]

    def value(cell: object, column: object, row_label: object) -> tuple[str, str]:
        if cell is None or (not isinstance(cell, str) and pd.isna(cell)):
            return "—", ""
        if isinstance(cell, Real) and not isinstance(cell, bool):
            precision = (row_decimals or {}).get(
                str(row_label), (decimals or {}).get(str(column), default_decimals)
            )
            rounded = round(float(cell), precision)
            if rounded == 0:
                rounded = 0.0
            return f"{rounded:.{precision}f}", "report-number"
        display = escape(str(cell))
        display = display.replace(
            "[[", '<strong class="report-inline-emphasis">'
        ).replace("]]", "</strong>")
        return display, ""

    classes = "report-table"
    if dense:
        classes += " report-table--dense"
    if wide:
        classes += " report-table--wide"
    header_cells = "".join(f"<th>{header(column)}</th>" for column in frame.columns)
    body_rows = []
    for _, row in frame.iterrows():
        cells = []
        row_label = row.iloc[0] if len(row) else ""
        for index, (column, cell) in enumerate(row.items()):
            display, cell_class = value(cell, column, row_label)
            if index == 0:
                cells.append(f"<th scope=\"row\" class=\"{cell_class}\">{display}</th>")
            else:
                cells.append(f"<td class=\"{cell_class}\">{display}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f"<div class=\"report-table-wrap\"><table class=\"{classes}\">"
        f"<thead><tr>{header_cells}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_formulary_table(frame: pd.DataFrame) -> None:
    """Render the dense nutrition profile using the shared table system."""
    render_report_table(
        compact_feed_table(frame), dense=True, wide=True,
        decimals=FORMULARY_TABLE_DECIMALS,
    )


def apply_wireframe_theme() -> None:
    """Load the wireframe CSS that complements the Streamlit theme config."""
    stylesheet = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)


def render_record_title(record_label: str) -> None:
    """Show the shared food motif with ENFit, modular, and water symbols."""
    icon_path = Path(__file__).parent / "assets" / "enteral-enfit-tubing.svg"
    icon = b64encode(icon_path.read_bytes()).decode("ascii")
    title = escape(record_label or "EN record")
    st.markdown(
        f'<h1 class="record-title"><span class="record-title-food">🥕🥦</span><span>{title}</span><img src="data:image/svg+xml;base64,{icon}" '
        'alt="Enteral tubing with purple ENFit connectors"><span>🫙</span><span>💧</span></h1>',
        unsafe_allow_html=True,
    )


def modular_unit(product: dict[str, object]) -> str:
    """Use the acute-care packet convention for Beneprotein orders."""
    return "packet" if product.get("id") == "nestle-beneprotein" else str(product["dose_unit"])


def modular_daily_amount(product: dict[str, object], units: float, doses: float) -> str:
    total_units = units * doses
    unit = modular_unit(product)
    if unit == "packet":
        return f"{total_units:g} {'packet' if total_units == 1 else 'packets'} daily"
    return f"{total_units:g} {unit} daily"


def modular_chart_amount(product: dict[str, object], units: float, doses: float) -> str:
    """Describe one modular administration using familiar chart frequencies."""
    unit = modular_unit(product)
    if unit in {"packet", "scoop", "sachet", "bottle"} and units != 1:
        unit = f"{unit}s"
    frequency_count = int(doses) if float(doses).is_integer() else None
    frequency = {
        1: "daily",
        2: "BID",
        3: "TID",
        4: "QID",
    }.get(frequency_count, f"{doses:g} times per day")
    return f"{units:g} {unit} {frequency}"


def mmol_from_delivery(delivery: dict[str, float], nutrient: str) -> float:
    return mg_to_mmol(nutrient, delivery.get(f"{nutrient}_mg", 0))


def mmol_if_disclosed(totals: Mapping[str, object], nutrient: str) -> float | None:
    """Return mmol/day, or None when no contributing product declared a figure.

    Returning None makes the table render an em dash rather than a confident
    zero. A zero would read as a measured absence and would be indistinguishable
    from a product that genuinely contains none of the nutrient.
    """
    disclosed = totals.get("disclosed") or {}
    if not disclosed.get(f"{nutrient}_mg", 0):
        return None
    return mg_to_mmol(nutrient, totals.get(f"{nutrient}_mg", 0))


def uncounted_volume_note(sources: "list[tuple[float, str]]") -> str:
    """List the infusions whose volume is deliberately outside the water total.

    Both intravenous fluids and propofol are real volume the patient receives,
    but the water goal is entered net of anything given intravenously, so
    counting them here would subtract them twice. One heading with a list keeps
    that from becoming a separate sentence per infusion.
    """
    listed = [
        f"- {volume:,.0f} mL/day from {name}"
        for volume, name in sources if volume
    ]
    if not listed:
        return ""
    return "Not counted as free water:\n\n" + "\n".join(listed)


def undisclosed_note(
    undisclosed_sources: Mapping[str, list[str]],
    labels: Mapping[str, str],
) -> str:
    """Describe which nutrients are missing a figure, and from which products.

    Nutrients sharing the same set of products are grouped, so a plan with one
    modular reads "P and Mg not declared by Beneprotein" rather than naming that
    product once per nutrient. This sits under a table people scan, so it stays
    to one line.
    """
    grouped: dict[tuple[str, ...], list[str]] = {}
    for nutrient, products in undisclosed_sources.items():
        if not products:
            continue
        key = tuple(sorted(set(products)))
        grouped.setdefault(key, []).append(labels.get(nutrient, nutrient))
    if not grouped:
        return ""
    parts = [
        f"{_join_words(nutrients)} not declared by {', '.join(products)}"
        for products, nutrients in grouped.items()
    ]
    return "; ".join(parts) + "."


def _join_words(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"
