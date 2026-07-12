"""
models/vitals_log.py — Vitals log model for Chronic Disease Monitoring (Milestone 3).

Each record represents one manual vitals entry by a user.
All measurements are nullable so users can log whichever vitals are
relevant to their condition without being forced to fill every field.

Clinical thresholds and status classification are handled in
services/monitoring_service.py — not here — to keep the model clean.
"""

from datetime import datetime
from extensions import db


class VitalsLog(db.Model):
    """Stores a single vitals reading submitted by the user."""

    __tablename__ = "vitals_logs"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign key — every record belongs to one user
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Timestamp of the reading (defaults to now, but user can specify)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # ── Blood Pressure ────────────────────────────────────────────────────────
    systolic_bp  = db.Column(db.Integer,  nullable=True)   # mmHg
    diastolic_bp = db.Column(db.Integer,  nullable=True)   # mmHg

    # ── Blood Sugar (Glucose) ─────────────────────────────────────────────────
    blood_sugar  = db.Column(db.Float,    nullable=True)   # mg/dL

    # ── Heart Rate ────────────────────────────────────────────────────────────
    heart_rate   = db.Column(db.Integer,  nullable=True)   # bpm

    # ── Oxygen Saturation ─────────────────────────────────────────────────────
    spo2         = db.Column(db.Float,    nullable=True)   # percentage (e.g. 98.5)

    # ── Body Temperature ─────────────────────────────────────────────────────
    body_temperature = db.Column(db.Float, nullable=True)  # °C

    # ── Weight ───────────────────────────────────────────────────────────────
    weight       = db.Column(db.Float,    nullable=True)   # kg

    # ── Free-text note ────────────────────────────────────────────────────────
    notes        = db.Column(db.Text,     nullable=True)

    def __repr__(self) -> str:
        return (
            f"<VitalsLog id={self.id} user_id={self.user_id} "
            f"date={self.date_time.strftime('%Y-%m-%d %H:%M')}>"
        )
