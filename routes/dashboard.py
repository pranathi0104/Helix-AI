"""
routes/dashboard.py — Health Command Center blueprint.

Updated in Milestone 3 to pass live vitals and health timeline data
to the dashboard template. No AI calls are made here.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from services.monitoring_service import (
    get_latest_vitals,
    classify_vitals,
    get_recent_timeline,
)
from services.risk_service import calculate_risk

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/home")
@login_required
def home():
    """Render the Health Command Center dashboard."""
    # Redirect first-time users to complete their profile
    if not current_user.has_profile:
        return redirect(url_for("profile.edit"))

    # Fetch live data from Milestone 3 services
    latest_vitals = get_latest_vitals(current_user.id)
    vitals_status = classify_vitals(latest_vitals) if latest_vitals else None
    timeline      = get_recent_timeline(current_user.id, limit=6)
    
    # Calculate deterministic risk score for Top Cards
    risk_data = calculate_risk(current_user.id)
    
    # Synthesize Today's Summary
    if risk_data.get("factors"):
        primary_concern = risk_data["factors"][0].lower()
        todays_summary = f"Your latest readings indicate a {risk_data['classification']} risk level. Your primary concern is {primary_concern}."
    elif latest_vitals:
        todays_summary = "Your latest readings are normal with no active health concerns detected."
    else:
        todays_summary = "No recent vitals logged. Please log your vitals to receive a health summary."

    return render_template(
        "dashboard/index.html",
        title="Health Command Center",
        user=current_user,
        profile=current_user.profile,
        latest_vitals=latest_vitals,
        vitals_status=vitals_status,
        timeline=timeline,
        risk_data=risk_data,
        todays_summary=todays_summary,
    )
