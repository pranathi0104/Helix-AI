import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from extensions import db
from models.user import User
from models.user_profile import UserProfile
from models.vitals_log import VitalsLog
from services.lifestyle_service import generate_recommendations

app = create_app()

with app.app_context():
    # 1. Setup Test User
    user = User.query.filter_by(username="safetytest").first()
    if not user:
        user = User(username="safetytest", email="safety@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    
    print(f"\n--- Testing Safety Overrides for user_id={user.id} ---")

    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id, gender="Other", height_cm=170, weight_kg=70)
        db.session.add(profile)
        db.session.commit()

    # Clear logs
    VitalsLog.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Test 1: Severe Hypoglycemia (35 mg/dL)
    log1 = VitalsLog(user_id=user.id, systolic_bp=120, blood_sugar=35, heart_rate=70, body_temperature=36.5, spo2=98)
    db.session.add(log1)
    db.session.commit()
    res = generate_recommendations(user.id)
    print("\n--- Severe Hypoglycemia ---")
    print(f"Nutrition: {res['recommendations']['Nutrition'][0]['title']}")
    print(f"General Health: {res['recommendations']['General Health'][0]['title']}")

    # Clear logs
    VitalsLog.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Test 2: Critical BP (190) and SpO2 (87%)
    log2 = VitalsLog(user_id=user.id, systolic_bp=190, blood_sugar=90, heart_rate=70, body_temperature=36.5, spo2=87)
    db.session.add(log2)
    db.session.commit()
    res2 = generate_recommendations(user.id)
    print("\n--- Critical BP and SpO2 ---")
    print(f"General Health: {res2['recommendations']['General Health'][0]['title']}")

    # Clear logs
    VitalsLog.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Test 3: Normal
    log3 = VitalsLog(user_id=user.id, systolic_bp=120, blood_sugar=90, heart_rate=70, body_temperature=36.5, spo2=98)
    db.session.add(log3)
    db.session.commit()
    res3 = generate_recommendations(user.id)
    print("\n--- Normal Vitals ---")
    print(f"Nutrition: {res3['recommendations']['Nutrition'][0]['title']}")
    print(f"General Health: {res3['recommendations']['General Health'][0]['title']}")
