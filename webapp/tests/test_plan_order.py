"""An entered order has the same meaning in every delivery view."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constants import (
    ORDER_FORM_RATE_AND_HOURS,
    ORDER_FORM_RATE_PER_FEED,
    ORDER_FORM_VOLUME_PER_FEED,
)
from plan_order import FeedOrder, FormulaEnergy

FORMULA = {
    "kcal_per_mL": 1.5,
    "protein_per_mL": 0.06,
    "carbohydrate_per_mL": 0.18,
    "fat_per_mL": 0.05,
    "free_water_per_mL": 0.8,
}


@pytest.mark.parametrize(
    "amount,form,schedule,hours,per_feed,feeds",
    [
        (100, ORDER_FORM_RATE_AND_HOURS, "Continuous / cyclic", 8, 1, 1),
        (100, ORDER_FORM_RATE_PER_FEED, "Intermittent", 8, 2, 4),
        (200, ORDER_FORM_VOLUME_PER_FEED, "Intermittent", 8, 2, 4),
    ],
)
def test_equivalent_orders_share_full_and_partial_results(
    amount, form, schedule, hours, per_feed, feeds
):
    order = FeedOrder.from_entry(
        entered_amount=amount,
        order_form=form,
        hours_per_feed=per_feed,
        hours=hours,
        schedule_type=schedule,
        feeds_per_day=feeds,
    )
    for percentage, volume in [(100, 800), (50, 400), (0, 0)]:
        result = order.delivery(FORMULA, percentage)
        assert result["planned_volume_ml"] == 800
        assert result["delivered_volume_ml"] == volume
        assert result["energy_kcal"] == volume * 1.5
        assert result["protein_g"] == volume * 0.06
    assert order.delivery(FORMULA)["energy_kcal"] == 1200


def test_conditional_order_snapshots_inputs_and_scales_only_delivery():
    conditions = [{"hours": 18}, {"hours": 6}]
    rates = [70, 30]
    order = FeedOrder.from_conditions(24, conditions, rates)
    conditions[0]["hours"] = 0
    rates[0] = 0
    assert order.delivery(FORMULA)["delivered_volume_ml"] == 1440
    assert order.delivery(FORMULA, 50)["delivered_volume_ml"] == 720
    assert order.delivery(FORMULA)["energy_kcal"] == 2160


@pytest.mark.parametrize(
    "target,iv,propofol,expected",
    [
        (1800, 408, 528, (1392, 864)),
        (100, 200, 50, (0, 0)),
        (None, 408, 528, (None, None)),
    ],
)
def test_energy_allocations_distinguish_condition_specific_propofol(
    target, iv, propofol, expected
):
    result = FormulaEnergy.from_target(target, iv, propofol)
    assert (result.after_iv, result.after_iv_and_propofol) == expected
