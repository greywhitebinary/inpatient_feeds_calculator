"""Explicit feed orders shared by full and partial delivery calculations.

These objects have no widgets or session state. Construct an order once after
reading the controls, then calculate each delivery view from that same order.
The clinical arithmetic and rounding remain in calculations.py.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from calculations import conditional_feed_delivery, ordered_feed_delivery
from constants import ORDER_FORM_RATE_PER_FEED


@dataclass(frozen=True)
class ConditionalFeedRate:
    exposure_hours: float
    formula_rate_ml_hr: float


@dataclass(frozen=True)
class FeedOrder:
    """A rate or volume-per-feed order, or a set of conditional rates.

    `amount` is mL/hour for continuous feeding and mL/feed for intermittent
    feeding. A rate-and-duration entry is normalized by from_entry before
    reaching the calculator. Conditional orders retain their exposure hours
    separately from total feeding hours, as the existing calculator requires.
    """

    hours: float
    schedule_type: str = "Continuous / cyclic"
    amount: float = 0
    feeds_per_day: int = 1
    conditional_rates: tuple[ConditionalFeedRate, ...] | None = None

    @classmethod
    def from_entry(
        cls,
        *,
        entered_amount: float,
        order_form: str,
        hours_per_feed: float,
        hours: float,
        schedule_type: str,
        feeds_per_day: int,
    ) -> FeedOrder:
        amount = max(float(entered_amount), 0)
        if order_form == ORDER_FORM_RATE_PER_FEED:
            amount *= max(hours_per_feed, 0)
        return cls(hours, schedule_type, amount, feeds_per_day)

    @classmethod
    def from_conditions(
        cls,
        hours: float,
        conditions: Sequence[Mapping[str, object]],
        rates: Sequence[float],
    ) -> FeedOrder:
        if len(conditions) != len(rates):
            raise ValueError("Each propofol condition requires one formula rate.")
        return cls(
            hours=hours,
            conditional_rates=tuple(
                ConditionalFeedRate(float(condition.get("hours", 0)), float(rate))
                for condition, rate in zip(conditions, rates)
            ),
        )

    def delivery(
        self, formula: Mapping[str, object], achieved_percent: float = 100
    ) -> dict[str, float]:
        if self.conditional_rates is not None:
            return conditional_feed_delivery(
                formula,
                self.hours,
                [{"hours": rate.exposure_hours} for rate in self.conditional_rates],
                [rate.formula_rate_ml_hr for rate in self.conditional_rates],
                achieved_percent,
            )
        return ordered_feed_delivery(
            formula,
            self.amount,
            self.hours,
            achieved_percent,
            self.schedule_type,
            self.feeds_per_day,
        )


@dataclass(frozen=True)
class FormulaEnergy:
    """Formula energy allocations for single and conditional suggestions."""

    after_iv: float | None
    after_iv_and_propofol: float | None

    @classmethod
    def from_target(
        cls, target: float | None, iv_energy: float, propofol_energy: float
    ) -> FormulaEnergy:
        if target is None:
            return cls(None, None)
        # Conditional suggestions deduct their own 24-hour propofol exposure
        # from after_iv. Single-rate suggestions use the combined remainder.
        return cls(
            max(target - iv_energy, 0), max(target - propofol_energy - iv_energy, 0)
        )
