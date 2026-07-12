"""
models/medication.py — Medication tracking models.
"""

from datetime import datetime, date
from extensions import db


class Medication(db.Model):
    """Stores user medication details."""

    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)  # e.g. "Daily", "Twice a day", "Weekly"
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    logs = db.relationship("MedicationLog", backref="medication", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name!r}>"


class MedicationLog(db.Model):
    """Tracks each scheduled dose and whether it was taken."""

    __tablename__ = "medication_logs"

    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False)
    scheduled_date = db.Column(db.Date, nullable=False)
    taken_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, taken, missed, skipped

    def __repr__(self) -> str:
        return f"<MedicationLog id={self.id} med_id={self.medication_id} status={self.status}>"
