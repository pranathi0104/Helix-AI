"""
models/user.py — User authentication model.

Stores login credentials only. Profile information is held in UserProfile
to keep the auth model focused and allow easy extension later.

Future milestone tables that reference users will use `user_id` as a
foreign key pointing to `users.id`.
"""

from datetime import datetime
from flask_login import UserMixin
from extensions import db, bcrypt


class User(UserMixin, db.Model):
    """Core authentication model."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # One-to-one relationship with UserProfile
    profile = db.relationship(
        "UserProfile",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ---------------------------------------------------------------------------
    # Future milestone relationships will be added below, e.g.:
    # symptom_logs  = db.relationship("SymptomLog",  backref="user", lazy="dynamic")
    # vitals_logs   = db.relationship("VitalsLog",   backref="user", lazy="dynamic")
    medications   = db.relationship("Medication",  backref="user", lazy="dynamic")
    # health_scores = db.relationship("HealthScore", backref="user", lazy="dynamic")
    # ---------------------------------------------------------------------------

    def set_password(self, password: str) -> None:
        """Hash and store the user's password using bcrypt."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Return True if the provided password matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def has_profile(self) -> bool:
        """Return True if a UserProfile record exists for this user."""
        return self.profile is not None

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
