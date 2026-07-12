"""
models/__init__.py

Import all models here so Flask-SQLAlchemy can discover them
during `db.create_all()` / Flask-Migrate operations.
"""

from .user import User                    # noqa: F401
from .user_profile import UserProfile    # noqa: F401
from .vitals_log import VitalsLog        # noqa: F401  — Milestone 3
from .health_timeline import HealthTimeline  # noqa: F401  — Milestone 3

# Future milestone models will be imported here:
from .medication import Medication, MedicationLog          # Milestone 5
# from .health_score import HealthScore      # Milestone 4
# from .health_report import HealthReport    # Milestone 7
