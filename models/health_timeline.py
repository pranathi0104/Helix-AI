"""
models/health_timeline.py — Unified health event timeline (Milestone 3).

Append-only log.  Every module writes an event row here when something
clinically relevant happens (vitals logged, symptom assessed, report
generated, etc.).  The dashboard reads this table to populate the
Health Timeline panel.

Event types used in this milestone:
    "vitals"      — user logged a vitals reading
    "alert"       — an abnormal vitals threshold was breached

Future milestone event types (added as those modules are built):
    "symptom"          — AI Clinical Assessment completed
    "symptom_emergency"— emergency flag raised
    "medication"       — dose logged
    "score"            — daily health score generated
    "report"           — health report generated
    "risk_alert"       — risk prediction agent flagged worsening trend
"""

from datetime import datetime
from extensions import db


class HealthTimeline(db.Model):
    """One row per clinically significant event for a user."""

    __tablename__ = "health_timeline"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Short type tag used for icon/colour selection in the template
    event_type    = db.Column(db.String(40),  nullable=False, index=True)

    # One-line human-readable description shown in the timeline list
    event_summary = db.Column(db.String(255), nullable=False)

    # Optional JSON payload for richer detail (not rendered in MVP)
    event_detail  = db.Column(db.Text,        nullable=True)

    # The moment the event occurred (indexed for DESC ordering)
    event_date    = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<HealthTimeline id={self.id} user_id={self.user_id} "
            f"type={self.event_type!r} date={self.event_date.strftime('%Y-%m-%d %H:%M')}>"
        )
