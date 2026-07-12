"""
models/user_profile.py — Extended user health profile.

Stores demographic and health baseline information used across modules.
The lifestyle fields (smoking, alcohol, exercise, diet) will feed the
Health Score calculation in Milestone 4.
"""

from datetime import datetime
from extensions import db


class UserProfile(db.Model):
    """Health profile linked one-to-one with a User."""

    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # --- Demographics ---
    full_name = db.Column(db.String(120), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)          # Male / Female / Other / Prefer not to say
    blood_group = db.Column(db.String(10), nullable=True)     # A+, B-, O+, AB+, etc.

    # --- Physical measurements ---
    height_cm = db.Column(db.Float, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)

    # --- Existing conditions ---
    # Stored as a comma-separated string; e.g. "Diabetes,Hypertension"
    # Future Milestone 4 will parse this for per-condition agent context
    existing_conditions = db.Column(db.Text, nullable=True)

    # --- Lifestyle factors (used by Health Score in Milestone 4) ---
    smoking = db.Column(db.Boolean, default=False, nullable=False)
    alcohol = db.Column(db.Boolean, default=False, nullable=False)
    exercise_frequency = db.Column(db.String(20), default="occasionally", nullable=False)
    # Options: never / occasionally / regularly
    diet_quality = db.Column(db.String(20), default="average", nullable=False)
    # Options: poor / average / good

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    @property
    def bmi(self) -> float | None:
        """Calculate and return BMI, or None if height/weight are not set."""
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @property
    def conditions_list(self) -> list[str]:
        """Return existing conditions as a Python list."""
        if not self.existing_conditions:
            return []
        return [c.strip() for c in self.existing_conditions.split(",") if c.strip()]

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} name={self.full_name!r}>"
