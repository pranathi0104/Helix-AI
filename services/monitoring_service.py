"""
services/monitoring_service.py — Chronic Disease Monitoring business logic (Milestone 3).

Responsibilities:
  1. classify_vitals(record)     — classify each vital against clinical thresholds,
                                   returning a dict of { vital_name: status_dict }.
  2. get_latest_vitals(user_id)  — fetch the most recent VitalsLog for a user.
  3. get_chart_data(user_id, n)  — fetch the last n records formatted for Chart.js.
  4. write_timeline_event(...)   — write a HealthTimeline row after a vitals save.

Clinical thresholds used
------------------------
Blood Pressure (systolic / diastolic, mmHg) — AHA 2017 guidelines
  Normal          systolic < 120  AND  diastolic < 80
  Elevated        120 ≤ systolic ≤ 129  AND  diastolic < 80
  High (Stage 1)  130 ≤ systolic ≤ 139  OR   80 ≤ diastolic ≤ 89
  High (Stage 2)  systolic ≥ 140  OR   diastolic ≥ 90
  Critical        systolic ≥ 180  OR   diastolic ≥ 120

Blood Sugar (mg/dL) — fasting reference
  Low             < 70
  Normal          70 – 99
  Pre-diabetic    100 – 125
  High            ≥ 126

Heart Rate (bpm) — resting adult
  Bradycardia     < 60
  Normal          60 – 100
  Tachycardia     > 100

SpO₂ (%)
  Normal          ≥ 95
  Low             90 – 94
  Critical        < 90

Body Temperature (°C)
  Normal          36.1 – 37.2
  Low-grade Fever 37.3 – 38.0
  Fever           38.1 – 39.9
  High Fever      ≥ 40.0

IBM watsonx / Granite AI analysis will be layered on top of this
service in a future milestone.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Threshold classification helpers
# ---------------------------------------------------------------------------

def _bp_status(systolic: Optional[int], diastolic: Optional[int]) -> dict:
    """Return a status dict for a blood pressure reading."""
    if systolic is None and diastolic is None:
        return {"label": "No Data", "css": "secondary", "alert": False}

    s = systolic or 0
    d = diastolic or 0

    if s >= 180 or d >= 120:
        return {"label": "Critical",       "css": "danger",  "alert": True}
    if s >= 140 or d >= 90:
        return {"label": "High (Stage 2)", "css": "danger",  "alert": True}
    if s >= 130 or d >= 80:
        return {"label": "High (Stage 1)", "css": "warning", "alert": True}
    if 120 <= s <= 129 and d < 80:
        return {"label": "Elevated",       "css": "warning", "alert": False}
    return         {"label": "Normal",     "css": "success", "alert": False}


def _sugar_status(value: Optional[float]) -> dict:
    if value is None:
        return {"label": "No Data", "css": "secondary", "alert": False}
    if value < 70:
        return {"label": "Low",          "css": "warning", "alert": True}
    if value <= 99:
        return {"label": "Normal",       "css": "success", "alert": False}
    if value <= 125:
        return {"label": "Pre-Diabetic", "css": "warning", "alert": True}
    return     {"label": "High",         "css": "danger",  "alert": True}


def _hr_status(value: Optional[int]) -> dict:
    if value is None:
        return {"label": "No Data",     "css": "secondary", "alert": False}
    if value < 60:
        return {"label": "Bradycardia", "css": "warning",   "alert": True}
    if value <= 100:
        return {"label": "Normal",      "css": "success",   "alert": False}
    return     {"label": "Tachycardia", "css": "danger",    "alert": True}


def _spo2_status(value: Optional[float]) -> dict:
    if value is None:
        return {"label": "No Data",  "css": "secondary", "alert": False}
    if value >= 95:
        return {"label": "Normal",   "css": "success",   "alert": False}
    if value >= 90:
        return {"label": "Low",      "css": "warning",   "alert": True}
    return     {"label": "Critical", "css": "danger",    "alert": True}


def _temp_status(value: Optional[float]) -> dict:
    if value is None:
        return {"label": "No Data",         "css": "secondary", "alert": False}
    if value < 36.1:
        return {"label": "Hypothermia",     "css": "warning",   "alert": True}
    if value <= 37.2:
        return {"label": "Normal",          "css": "success",   "alert": False}
    if value <= 38.0:
        return {"label": "Low-grade Fever", "css": "warning",   "alert": True}
    if value <= 39.9:
        return {"label": "Fever",           "css": "danger",    "alert": True}
    return     {"label": "High Fever",      "css": "danger",    "alert": True}


def _weight_status(value: Optional[float]) -> dict:
    """Weight has no universal 'normal' threshold without height — just report the value."""
    if value is None:
        return {"label": "No Data",  "css": "secondary", "alert": False}
    return     {"label": "Recorded", "css": "info",      "alert": False}


# ---------------------------------------------------------------------------
# Public: classify a full VitalsLog record
# ---------------------------------------------------------------------------

def classify_vitals(record) -> dict:
    """
    Accept a VitalsLog ORM instance and return a classification dict.

    Returns:
        {
          "blood_pressure": { "label": str, "css": str, "alert": bool },
          "blood_sugar":    { ... },
          "heart_rate":     { ... },
          "spo2":           { ... },
          "temperature":    { ... },
          "weight":         { ... },
          "has_alert":      bool   # True if ANY vital is flagged
        }
    """
    result = {
        "blood_pressure": _bp_status(record.systolic_bp, record.diastolic_bp),
        "blood_sugar":    _sugar_status(record.blood_sugar),
        "heart_rate":     _hr_status(record.heart_rate),
        "spo2":           _spo2_status(record.spo2),
        "temperature":    _temp_status(record.body_temperature),
        "weight":         _weight_status(record.weight),
    }
    result["has_alert"] = any(v["alert"] for v in result.values() if isinstance(v, dict))
    return result


# ---------------------------------------------------------------------------
# Public: latest vitals query
# ---------------------------------------------------------------------------

def get_latest_vitals(user_id: int):
    """
    Return the most recently logged VitalsLog for a user, or None.
    Imports the model here to avoid circular imports at module level.
    """
    from models.vitals_log import VitalsLog
    return (
        VitalsLog.query
        .filter_by(user_id=user_id)
        .order_by(VitalsLog.date_time.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Public: chart data
# ---------------------------------------------------------------------------

def get_chart_data(user_id: int, n: int = 30) -> dict:
    """
    Return the last `n` vitals records formatted for Chart.js consumption.

    Returns a dict with keys:
        labels          — list of date strings (oldest → newest)
        systolic        — list of values (None → null handled in template)
        diastolic
        blood_sugar
        heart_rate
        spo2
        temperature
        weight
    """
    from models.vitals_log import VitalsLog

    records = (
        VitalsLog.query
        .filter_by(user_id=user_id)
        .order_by(VitalsLog.date_time.desc())
        .limit(n)
        .all()
    )
    # Reverse so oldest data is on the left of the chart
    records = list(reversed(records))

    def _fmt(v):
        """Return float/int or None — JSON-serialisable."""
        return v if v is not None else None

    return {
        "labels":      [r.date_time.strftime("%d %b") for r in records],
        "systolic":    [_fmt(r.systolic_bp)       for r in records],
        "diastolic":   [_fmt(r.diastolic_bp)      for r in records],
        "blood_sugar": [_fmt(r.blood_sugar)        for r in records],
        "heart_rate":  [_fmt(r.heart_rate)         for r in records],
        "spo2":        [_fmt(r.spo2)               for r in records],
        "temperature": [_fmt(r.body_temperature)   for r in records],
        "weight":      [_fmt(r.weight)             for r in records],
    }


# ---------------------------------------------------------------------------
# Public: timeline event writer
# ---------------------------------------------------------------------------

def write_timeline_event(
    user_id: int,
    event_type: str,
    summary: str,
    detail: Optional[dict] = None,
) -> None:
    """
    Append a HealthTimeline row for `user_id`.

    Args:
        user_id:    The user who triggered the event.
        event_type: Short tag string (e.g. "vitals", "alert").
        summary:    One-line human-readable description.
        detail:     Optional dict that will be JSON-serialised into event_detail.
    """
    from models.health_timeline import HealthTimeline
    from extensions import db

    event = HealthTimeline(
        user_id=user_id,
        event_type=event_type,
        event_summary=summary,
        event_detail=json.dumps(detail) if detail else None,
        event_date=datetime.utcnow(),
    )
    db.session.add(event)
    # Flush only — the calling route commits the full transaction
    db.session.flush()
    logger.debug("Timeline event written: user=%s type=%s", user_id, event_type)


# ---------------------------------------------------------------------------
# Public: recent timeline events
# ---------------------------------------------------------------------------

def get_recent_timeline(user_id: int, limit: int = 10) -> list:
    """
    Return the `limit` most recent HealthTimeline rows for `user_id`.
    Used by the dashboard and monitoring index pages.
    """
    from models.health_timeline import HealthTimeline
    return (
        HealthTimeline.query
        .filter_by(user_id=user_id)
        .order_by(HealthTimeline.event_date.desc())
        .limit(limit)
        .all()
    )
