"""
routes/risk.py — Risk Prediction Agent blueprint.
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from services.risk_service import calculate_risk
from models.health_timeline import HealthTimeline
from extensions import db
from datetime import datetime, timedelta

risk_bp = Blueprint("risk", __name__)

@risk_bp.route("/")
@login_required
def index():
    risk_data = calculate_risk(current_user.id)
    
    # Log to Health Timeline if risk is High or Critical
    # Prevent spamming by checking if we already logged one recently
    if risk_data["classification"] in ["High", "Critical"]:
        recent_alert = HealthTimeline.query.filter(
            HealthTimeline.user_id == current_user.id,
            HealthTimeline.event_type == "risk_alert",
            HealthTimeline.event_date >= datetime.utcnow() - timedelta(hours=12)
        ).first()
        
        if not recent_alert:
            alert = HealthTimeline(
                user_id=current_user.id,
                event_type="risk_alert",
                event_summary=f"Risk Prediction Agent flagged {risk_data['classification']} risk (Score: {risk_data['score']})."
            )
            db.session.add(alert)
            db.session.commit()
            
    return render_template(
        "risk/index.html",
        title="Risk Prediction Agent",
        risk=risk_data
    )
