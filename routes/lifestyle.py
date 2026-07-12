"""
routes/lifestyle.py
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from services.lifestyle_service import generate_recommendations
from models.health_timeline import HealthTimeline
from extensions import db
from datetime import datetime, timedelta

lifestyle_bp = Blueprint("lifestyle", __name__)

@lifestyle_bp.route("/")
@login_required
def index():
    data = generate_recommendations(current_user.id)
    
    # Timeline duplicate prevention (12 hours)
    twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)
    recent_alert = HealthTimeline.query.filter(
        HealthTimeline.user_id == current_user.id,
        HealthTimeline.event_type == "lifestyle_alert",
        HealthTimeline.event_date >= twelve_hours_ago
    ).first()
    
    if not recent_alert:
        # Generate a concise summary
        alert = HealthTimeline(
            user_id=current_user.id,
            event_type="lifestyle_alert",
            event_summary=f"Lifestyle recommendations updated. Active risk level: {data['risk_classification']}."
        )
        db.session.add(alert)
        db.session.commit()
        
    return render_template("lifestyle/index.html", data=data)
