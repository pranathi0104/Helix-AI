"""
routes/monitoring.py — Chronic Disease Monitoring blueprint (Milestone 3).

Routes
------
  GET  /monitoring          — Dashboard: latest vitals cards + trend charts + timeline
  GET  /monitoring/add      — Empty add-vitals form
  POST /monitoring/add      — Save a new vitals record
  GET  /monitoring/history  — Full paginated history table

No IBM Granite calls are made here.  The service layer (monitoring_service.py)
handles all threshold classification and timeline event creation.
AI analysis will be added on top of this data in a later milestone.
"""

from __future__ import annotations

import logging
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required, current_user

from extensions import db
from models.vitals_log import VitalsLog
from services.monitoring_service import (
    classify_vitals,
    get_latest_vitals,
    get_chart_data,
    write_timeline_event,
    get_recent_timeline,
)

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/monitoring")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(value: str, name: str, errors: list,
              lo: int = 0, hi: int = 9999) -> int | None:
    """Parse an integer form field; append an error and return None on failure."""
    v = value.strip() if value else ""
    if not v:
        return None
    try:
        n = int(v)
    except ValueError:
        errors.append(f"{name} must be a whole number.")
        return None
    if not (lo <= n <= hi):
        errors.append(f"{name} must be between {lo} and {hi}.")
        return None
    return n


def _safe_float(value: str, name: str, errors: list,
                lo: float = 0.0, hi: float = 9999.0) -> float | None:
    """Parse a float form field; append an error and return None on failure."""
    v = value.strip() if value else ""
    if not v:
        return None
    try:
        f = float(v)
    except ValueError:
        errors.append(f"{name} must be a number.")
        return None
    if not (lo <= f <= hi):
        errors.append(f"{name} must be between {lo} and {hi}.")
        return None
    return f


# ---------------------------------------------------------------------------
# GET /monitoring — monitoring dashboard
# ---------------------------------------------------------------------------

@monitoring_bp.route("/")
@login_required
def index():
    """Render the monitoring dashboard with latest vitals, charts, and timeline."""
    latest = get_latest_vitals(current_user.id)
    status = classify_vitals(latest) if latest else None
    chart_data = get_chart_data(current_user.id, n=30)
    timeline = get_recent_timeline(current_user.id, limit=8)

    return render_template(
        "monitoring/index.html",
        title="Chronic Disease Monitoring",
        latest=latest,
        status=status,
        chart_data=chart_data,
        timeline=timeline,
    )


# ---------------------------------------------------------------------------
# GET /monitoring/add — empty form
# POST /monitoring/add — save record
# ---------------------------------------------------------------------------

@monitoring_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Display the add-vitals form and process submissions."""

    if request.method == "GET":
        now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
        return render_template(
            "monitoring/add.html",
            title="Log Vitals",
            now_str=now_str,
        )

    # ── POST — validate and save ──────────────────────────────────────────
    errors: list[str] = []

    # Date / time
    dt_raw = request.form.get("date_time", "").strip()
    try:
        if dt_raw:
            # Parse as local time, convert to UTC for DB
            import zoneinfo
            local_dt = datetime.strptime(dt_raw, "%Y-%m-%dT%H:%M").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
            record_dt = local_dt.astimezone(zoneinfo.ZoneInfo("UTC")).replace(tzinfo=None)
        else:
            record_dt = datetime.utcnow()
    except ValueError:
        record_dt = datetime.utcnow()

    # Numeric fields with range guards
    systolic_bp      = _safe_int  (request.form.get("systolic_bp",      ""), "Systolic BP",      errors, 50,  300)
    diastolic_bp     = _safe_int  (request.form.get("diastolic_bp",     ""), "Diastolic BP",     errors, 30,  200)
    blood_sugar      = _safe_float(request.form.get("blood_sugar",      ""), "Blood Sugar",      errors, 20,  800)
    heart_rate       = _safe_int  (request.form.get("heart_rate",       ""), "Heart Rate",       errors, 20,  300)
    spo2             = _safe_float(request.form.get("spo2",             ""), "SpO₂",             errors, 50,  100)
    body_temperature = _safe_float(request.form.get("body_temperature", ""), "Body Temperature", errors, 30,  45 )
    weight           = _safe_float(request.form.get("weight",           ""), "Weight",           errors, 1,   500)
    notes            = request.form.get("notes", "").strip()[:500]

    # At least one vital must be provided
    all_none = all(v is None for v in [
        systolic_bp, diastolic_bp, blood_sugar,
        heart_rate, spo2, body_temperature, weight,
    ])
    if all_none:
        errors.append("Please enter at least one vital measurement.")

    if errors:
        for e in errors:
            flash(e, "danger")
        now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
        return render_template(
            "monitoring/add.html",
            title="Log Vitals",
            now_str=now_str,
            form_data=request.form,
        ), 422

    # ── Build and save the record ─────────────────────────────────────────
    record = VitalsLog(
        user_id          = current_user.id,
        date_time        = record_dt,
        systolic_bp      = systolic_bp,
        diastolic_bp     = diastolic_bp,
        blood_sugar      = blood_sugar,
        heart_rate       = heart_rate,
        spo2             = spo2,
        body_temperature = body_temperature,
        weight           = weight,
        notes            = notes or None,
    )
    db.session.add(record)

    # ── Classify and write timeline events ───────────────────────────────
    status = classify_vitals(record)

    # Primary vitals-logged event
    bp_str    = (f"{systolic_bp}/{diastolic_bp} mmHg" if systolic_bp and diastolic_bp
                 else "—")
    hr_str    = f"{heart_rate} bpm" if heart_rate else "—"
    sugar_str = f"{blood_sugar} mg/dL" if blood_sugar else "—"
    summary   = f"Vitals logged — BP: {bp_str}, HR: {hr_str}, Sugar: {sugar_str}"

    write_timeline_event(
        user_id    = current_user.id,
        event_type = "vitals",
        summary    = summary,
        detail     = {
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "blood_sugar": blood_sugar,
            "heart_rate": heart_rate,
            "spo2": spo2,
            "body_temperature": body_temperature,
            "weight": weight,
        },
    )

    # Alert event for any threshold breach
    if status.get("has_alert"):
        alerts = [
            f"{k.replace('_', ' ').title()}: {v['label']}"
            for k, v in status.items()
            if isinstance(v, dict) and v.get("alert")
        ]
        write_timeline_event(
            user_id    = current_user.id,
            event_type = "alert",
            summary    = "⚠ Abnormal vitals — " + ", ".join(alerts),
            detail     = {"alerts": alerts},
        )

    db.session.commit()
    flash("Vitals logged successfully.", "success")
    return redirect(url_for("monitoring.index"))


# ---------------------------------------------------------------------------
# GET /monitoring/history — full history table
# ---------------------------------------------------------------------------

@monitoring_bp.route("/history")
@login_required
def history():
    """Display a searchable, paginated history of all vitals records."""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = (
        VitalsLog.query
        .filter_by(user_id=current_user.id)
        .order_by(VitalsLog.date_time.desc())
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items

    # Classify every record so the template can show status badges
    classified = [(r, classify_vitals(r)) for r in records]

    return render_template(
        "monitoring/history.html",
        title="Vitals History",
        classified=classified,
        pagination=pagination,
    )
