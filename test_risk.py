import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from extensions import db
from models.user import User
from models.vitals_log import VitalsLog
from services.risk_service import calculate_risk

app = create_app()

with app.app_context():
    # Find or create a test user
    user = User.query.filter_by(username="risktestuser2").first()
    if not user:
        user = User(username="risktestuser2", email="risk2@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    
    print(f"Testing Trend Logic for user_id={user.id}")
    
    # 1. Insufficient History Case
    VitalsLog.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    log1 = VitalsLog(user_id=user.id, systolic_bp=120)
    db.session.add(log1)
    db.session.commit()
    print("Insufficient History Test:", calculate_risk(user.id)["trend"])

    # 2. Stable Readings Case
    log2 = VitalsLog(user_id=user.id, systolic_bp=125, diastolic_bp=80, blood_sugar=90, spo2=98)
    db.session.add(log2)
    db.session.commit()
    print("Stable Readings Test:", calculate_risk(user.id)["trend"])

    # 3. Normal to Critical Case (Worsening)
    log3 = VitalsLog(user_id=user.id, systolic_bp=190, diastolic_bp=80, blood_sugar=90, spo2=87)
    db.session.add(log3)
    db.session.commit()
    print("Normal to Critical Test:", calculate_risk(user.id)["trend"])

    # 4. Critical to Normal Case (Improving)
    log4 = VitalsLog(user_id=user.id, systolic_bp=115, diastolic_bp=80, blood_sugar=90, spo2=99)
    db.session.add(log4)
    db.session.commit()
    print("Critical to Normal Test:", calculate_risk(user.id)["trend"])
