import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from extensions import db
from models.user import User
from models.user_profile import UserProfile
from models.vitals_log import VitalsLog
from models.health_timeline import HealthTimeline
from services.lifestyle_service import generate_recommendations

app = create_app()

with app.app_context():
    # 1. Setup Test User
    user = User.query.filter_by(username="lifestyletestuser").first()
    if not user:
        user = User(username="lifestyletestuser", email="lifestyle@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    
    print(f"\n--- Testing Lifestyle Recommendations for user_id={user.id} ---")

    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id, gender="Other", height_cm=170, weight_kg=70)
        db.session.add(profile)
        db.session.commit()

    # Clear logs
    VitalsLog.query.filter_by(user_id=user.id).delete()
    HealthTimeline.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # 2. Test Missing Data (Should fallback safely)
    res_missing = generate_recommendations(user.id)
    print("\n--- Missing Data Case ---")
    print(f"Risk Classification: {res_missing['risk_classification']}")
    for cat, items in res_missing['recommendations'].items():
        if items: print(f"{cat}: {items[0]['title']}")

    # 3. Test Normal Vitals (Low Risk)
    log_normal = VitalsLog(user_id=user.id, systolic_bp=120, blood_sugar=90, heart_rate=70, body_temperature=36.5)
    db.session.add(log_normal)
    db.session.commit()
    res_normal = generate_recommendations(user.id)
    print("\n--- Normal Vitals (Low Risk) ---")
    print(f"Risk Classification: {res_normal['risk_classification']}")
    for cat, items in res_normal['recommendations'].items():
        if items: print(f"{cat}: {items[0]['title']} ({items[0]['priority']} Priority)")

    # 4. Test Abnormal Vitals (Critical Risk, high temp, high HR, high sugar)
    log_abnormal = VitalsLog(user_id=user.id, systolic_bp=190, blood_sugar=200, heart_rate=110, body_temperature=38.0)
    db.session.add(log_abnormal)
    db.session.commit()
    res_abnormal = generate_recommendations(user.id)
    print("\n--- Abnormal Vitals (Critical Risk) ---")
    print(f"Risk Classification: {res_abnormal['risk_classification']}")
    for cat, items in res_abnormal['recommendations'].items():
        if items: print(f"{cat}: {items[0]['title']} ({items[0]['priority']} Priority) - {items[0]['explanation'][:30]}...")

    # 5. Timeline Duplicate Prevention Test
    print("\n--- Timeline Duplicate Test ---")
    # Simulate route logic for inserting timeline
    def simulate_route():
        data = generate_recommendations(user.id)
        from datetime import datetime, timedelta
        twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)
        recent = HealthTimeline.query.filter(HealthTimeline.user_id==user.id, HealthTimeline.event_type=="lifestyle_alert", HealthTimeline.event_date>=twelve_hours_ago).first()
        if not recent:
            alert = HealthTimeline(user_id=user.id, event_type="lifestyle_alert", event_summary="Test Alert")
            db.session.add(alert)
            db.session.commit()
            print("Action: Created new timeline event.")
        else:
            print("Action: Suppressed duplicate timeline event.")

    simulate_route() # 1st time
    simulate_route() # 2nd time (should suppress)
