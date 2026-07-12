"""
utils/helpers.py — Shared helper utilities for Helix AI.

Provides small, reusable functions used across routes and services.
"""

from datetime import datetime


def format_date(dt: datetime | None, fmt: str = "%d %b %Y") -> str:
    """Return a human-readable date string, or 'N/A' if dt is None."""
    if dt is None:
        return "N/A"
    return dt.strftime(fmt)


def format_datetime(dt: datetime | None, fmt: str = "%d %b %Y, %H:%M") -> str:
    """Return a human-readable datetime string, or 'N/A' if dt is None."""
    if dt is None:
        return "N/A"
    return dt.strftime(fmt)


def bmi_category(bmi: float | None) -> str:
    """Return a plain-English BMI category label.

    Reference thresholds (WHO standard):
        Underweight  < 18.5
        Normal       18.5 – 24.9
        Overweight   25.0 – 29.9
        Obese        >= 30.0
    """
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal"
    if bmi < 30.0:
        return "Overweight"
    return "Obese"


def bmi_badge_class(bmi: float | None) -> str:
    """Return a Bootstrap badge colour class for a given BMI value."""
    if bmi is None:
        return "secondary"
    if bmi < 18.5:
        return "warning"
    if bmi < 25.0:
        return "success"
    if bmi < 30.0:
        return "warning"
    return "danger"


def conditions_display(conditions_str: str | None) -> list[str]:
    """Parse a comma-separated conditions string into a clean list."""
    if not conditions_str:
        return []
    return [c.strip() for c in conditions_str.split(",") if c.strip()]
