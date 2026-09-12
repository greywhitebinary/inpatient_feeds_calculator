"""Render supplement orders and collect their calculated daily contributions.

These controls preserve incomplete entries in session state, but only complete
orders contribute nutrients or appear in the chart note. Nutrient arithmetic
continues to live in calculations.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st
from calculations import (
    modular_delivery,
    ons_delivery,
    total_modular_delivery,
    total_ons_delivery,
)
from session_state import reset_new_modular_orders, scenario_key
from ui_common import (
    modular_chart_amount,
    modular_daily_amount,
    modular_unit,
    number,
    render_box_heading,
)


@dataclass(frozen=True)
class ModularSelection:
    """Calculated delivery and reporting details for the selected modulars."""

    totals: dict[str, object]
    chart_orders: list[dict[str, object]]
    note_parts: list[str]
    undisclosed: dict[str, list[str]]
    protein_sources: list[str]


@dataclass(frozen=True)
class OnsSelection:
    """Calculated delivery and chart orders for the selected ONS products."""

    totals: dict[str, float]
    chart_orders: list[dict[str, object]]


def render_modular_orders(
    scenario_id: str, saved_modulars: pd.DataFrame
) -> ModularSelection:
    """Render modular selection, doses, frequencies, and preparation water."""
    modular_orders: list[dict[str, object]] = []
    modular_note_parts: list[str] = []
    # Products whose label does not publish a figure for each electrolyte, so
    # the intake table can say so instead of implying a measured zero.
    modular_undisclosed: dict[str, list[str]] = {
        "sodium": [],
        "potassium": [],
        "calcium": [],
        "phosphorus": [],
        "magnesium": [],
    }
    modular_protein_sources: list[str] = []
    chart_modulars: list[dict[str, object]] = []
    chosen_modulars: list[str] = []
    with st.container(border=True):
        render_box_heading("Add modulars")
        if saved_modulars.empty:
            st.caption("Missing a modular? Add it to My Modulars on the Formulary tab.")
        else:
            modular_ids_by_name = {
                str(product["name"]): str(product["id"])
                for _, product in saved_modulars.iterrows()
            }
            chosen_modulars = st.multiselect(
                "Modulars",
                saved_modulars["name"].tolist(),
                max_selections=6,
                key=scenario_key(scenario_id, "chosen_modulars"),
                on_change=reset_new_modular_orders,
                args=(scenario_id, modular_ids_by_name),
            )
            st.caption("Missing a modular? Add it to My Modulars on the Formulary tab.")
            for modular_name in chosen_modulars:
                product = (
                    saved_modulars.loc[saved_modulars["name"] == modular_name]
                    .iloc[0]
                    .to_dict()
                )
                st.markdown(f"**{modular_name}** — {product['basis_description']}")
                a, b, c = st.columns(3)
                product_id = str(product["id"])
                units_key = scenario_key(scenario_id, f"modular_units_{product_id}")
                doses_key = scenario_key(scenario_id, f"modular_doses_{product_id}")
                unit_label = (
                    "Packets each time"
                    if modular_unit(product) == "packet"
                    else f"{product['dose_unit']} each time"
                )
                packet_order = modular_unit(product) == "packet"
                units = a.number_input(
                    unit_label,
                    min_value=0.0,
                    step=1.0 if packet_order else 0.5,
                    format="%.0f" if packet_order else "%.1f",
                    key=units_key,
                )
                doses = b.number_input(
                    "Times per day",
                    min_value=0.0,
                    step=1.0,
                    format="%.0f",
                    key=doses_key,
                )
                preparation = 0.0
                if str(product.get("preparation_water_rule", "none")) != "none":
                    preparation = c.number_input(
                        "Preparation water (mL each time)",
                        min_value=0.0,
                        step=5.0,
                        format="%.0f",
                        key=scenario_key(scenario_id, f"modular_water_{product_id}"),
                    )
                else:
                    c.caption("No preparation water.")
                order_is_complete = number(units) > 0 and number(doses) > 0
                order = modular_delivery(
                    product,
                    number(units) if order_is_complete else 0,
                    number(doses) if order_is_complete else 0,
                    number(preparation) if order_is_complete else 0,
                )
                modular_orders.append(order)
                if order_is_complete:
                    for nutrient in (
                        "sodium",
                        "potassium",
                        "calcium",
                        "phosphorus",
                        "magnesium",
                    ):
                        if not order["disclosed"][f"{nutrient}_mg"]:
                            modular_undisclosed[nutrient].append(modular_name)
                    daily_amount = modular_daily_amount(
                        product, number(units), number(doses)
                    )
                    modular_note_parts.append(
                        f"{modular_name} {modular_chart_amount(product, number(units), number(doses))}"
                    )
                    if order["protein_g"]:
                        modular_protein_sources.append(
                            f"{order['protein_g']:.0f} g from {modular_name} ({daily_amount})"
                        )
                    chart_modulars.append(
                        {
                            "name": modular_name,
                            "order": modular_chart_amount(
                                product, number(units), number(doses)
                            ),
                            "daily_amount": daily_amount,
                            "energy_kcal": order["energy_kcal"],
                            "protein_g": order["protein_g"],
                            "carbohydrate_g": order["carbohydrate_g"],
                            "fat_g": order["fat_g"],
                            "free_water_ml": order["free_water_ml"],
                            "preparation_water_ml": order["preparation_water_ml"],
                            "preparation_water_per_dose_ml": number(preparation),
                        }
                    )
                else:
                    st.caption(
                        "Enter both the amount and frequency to include this modular."
                    )
    modular_totals = total_modular_delivery(modular_orders)
    return ModularSelection(
        totals=modular_totals,
        chart_orders=chart_modulars,
        note_parts=modular_note_parts,
        undisclosed=modular_undisclosed,
        protein_sources=modular_protein_sources,
    )


def render_ons_orders(scenario_id: str, saved_ons: pd.DataFrame | None) -> OnsSelection:
    """Render ONS selection and orders when an ONS formulary is available."""
    ons_orders: list[dict[str, float]] = []
    chart_ons: list[dict[str, object]] = []
    if saved_ons is not None:
        chosen_key = scenario_key(scenario_id, "chosen_ons")
        available_ons_names = set(saved_ons["name"].tolist())
        if chosen_key in st.session_state:
            st.session_state[chosen_key] = [
                name
                for name in st.session_state[chosen_key]
                if name in available_ons_names
            ]
        with st.container(border=True):
            render_box_heading("Add ONS")
            if saved_ons.empty:
                st.caption("Missing an ONS? Add it to My ONS on the Formulary tab.")
            else:
                chosen_ons = st.multiselect(
                    "ONS orders",
                    saved_ons["name"].tolist(),
                    max_selections=6,
                    key=chosen_key,
                )
                st.caption("Missing an ONS? Add it to My ONS on the Formulary tab.")
                for ons_name in chosen_ons:
                    product = (
                        saved_ons.loc[saved_ons["name"] == ons_name].iloc[0].to_dict()
                    )
                    serving_based = (
                        str(product.get("calculation_basis", "container_ml"))
                        .strip()
                        .casefold()
                        == "serving"
                    )
                    if serving_based:
                        basis_description = (
                            f"{number(product['serving_size_g']):g} g per "
                            f"{escape(str(product['serving_unit']))}"
                        )
                        quantity_label = "Servings each time"
                        quantity_prefix = "ons_servings_"
                        quantity_caption = "servings"
                    else:
                        basis_description = (
                            f"{number(product['container_size_ml']):g} mL "
                            f"{escape(str(product['package_unit']))}"
                        )
                        quantity_label = "Containers each time"
                        quantity_prefix = "ons_containers_"
                        quantity_caption = "containers"
                    st.markdown(f"**{escape(ons_name)}** — {basis_description}")
                    a, b = st.columns(2)
                    product_id = str(product["id"])
                    quantity_each_time = a.number_input(
                        quantity_label,
                        min_value=0.0,
                        step=0.5,
                        format="%.1f",
                        key=scenario_key(scenario_id, f"{quantity_prefix}{product_id}"),
                    )
                    times_per_day = b.number_input(
                        "Times per day",
                        min_value=0.0,
                        step=1.0,
                        format="%.0f",
                        key=scenario_key(scenario_id, f"ons_times_{product_id}"),
                    )
                    order_is_complete = (
                        number(quantity_each_time) > 0 and number(times_per_day) > 0
                    )
                    order = ons_delivery(
                        product,
                        number(quantity_each_time) if order_is_complete else 0,
                        number(times_per_day) if order_is_complete else 0,
                    )
                    ons_orders.append(order)
                    if order_is_complete:
                        chart_ons.append(
                            {
                                "name": ons_name,
                                "product_name": product["product_name"],
                                "flavour": product["flavour"],
                                "package_unit": product["package_unit"],
                                "quantity_each_time": number(quantity_each_time),
                                "quantity_unit": (
                                    product["serving_unit"]
                                    if serving_based
                                    else product["package_unit"]
                                ),
                                "calculation_basis": (
                                    "serving" if serving_based else "container_ml"
                                ),
                                "containers_each_time": (
                                    number(quantity_each_time)
                                    if not serving_based
                                    else 0
                                ),
                                "servings_each_time": (
                                    number(quantity_each_time) if serving_based else 0
                                ),
                                "times_per_day": number(times_per_day),
                                **order,
                            }
                        )
                    else:
                        st.caption(
                            f"Enter both the number of {quantity_caption} and frequency "
                            "to include this ONS."
                        )
    ons_totals = total_ons_delivery(ons_orders)
    return OnsSelection(totals=ons_totals, chart_orders=chart_ons)
