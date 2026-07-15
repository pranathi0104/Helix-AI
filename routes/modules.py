"""
routes/modules.py — Placeholder module blueprint.

Each route renders a "coming soon" page for modules that will be
fully implemented in later milestones:
  - Treatment Companion  (Milestone 5)
  - AI Health Reports    (Milestone 7)
  - Settings             (future)

NOTE: Routes replaced by full implementations:
  - /assessment  → routes/assessment.py  (Milestone 2)
  - /monitoring  → routes/monitoring.py  (Milestone 3)
  - /treatment   → routes/treatment.py   (Milestone 5)
"""

from flask import Blueprint, render_template
from flask_login import login_required

modules_bp = Blueprint("modules", __name__)

# Module metadata — drives the placeholder pages
MODULE_META = {
    "reports": {
        "title": "AI Health Reports",
        "icon": "bi-file-earmark-medical",
        "description": (
            "The AI Health Reports module will generate comprehensive health summaries "
            "combining vitals trends, symptom history, medication adherence, and "
            "AI-generated narratives with references to trusted medical sources."
        ),
        "milestone": "Milestone 7",
        "features": [
            "Weekly, monthly, and on-demand report generation",
            "Health summary with trend analysis",
            "Risk assessment from AI Risk Prediction Agent",
            "Lifestyle recommendations grounded in medical literature",
            "IBM Granite AI narrative and PDF export",
        ],
    },
    "settings": {
        "title": "Settings",
        "icon": "bi-gear",
        "description": (
            "Application settings and preferences will be available here in a future update."
        ),
        "milestone": "Future",
        "features": [
            "Notification preferences",
            "Theme and display settings",
            "Data export and account management",
        ],
    },
}


def _render_module(key: str):
    """Internal helper to render a module placeholder page."""
    meta = MODULE_META.get(key)
    if not meta:
        from flask import abort
        abort(404)
    return render_template(
        "modules/placeholder.html",
        title=meta["title"],
        meta=meta,
    )






@modules_bp.route("/settings")
@login_required
def settings():
    return render_template("settings/index.html", title="Settings")
