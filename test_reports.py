import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from extensions import db
from models.user import User
from models.user_profile import UserProfile
from models.vitals_log import VitalsLog
from models.health_timeline import HealthTimeline
from models.health_report import HealthReport
from services.report_service import generate_report_snapshot, create_report
import json

app = create_app()

with app.app_context():
    # 1. Setup Test User
    user = User.query.filter_by(username="reportuser").first()
    if not user:
        user = User(username="reportuser", email="report@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    
    print(f"\n--- Testing AI Health Reports for user_id={user.id} ---")

    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id, full_name="Report User", age=30, gender="Male", blood_group="O+", existing_conditions="Diabetes")
        db.session.add(profile)
        db.session.commit()

    # Clear logs
    VitalsLog.query.filter_by(user_id=user.id).delete()
    HealthTimeline.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # Case 1: Empty Vitals
    print("\n--- Empty Vitals Case ---")
    rep1 = create_report(user.id)
    print(f"Report Generated: ID {rep1.id} with Risk Classification: {rep1.risk_classification}")
    parsed1 = rep1.parsed_snapshot
    print(f"Vitals keys: {list(parsed1['vitals'].keys()) if parsed1['vitals'] else 'Empty'}")
    
    # Case 2: Normal Vitals
    log1 = VitalsLog(user_id=user.id, systolic_bp=120, blood_sugar=90, heart_rate=70, body_temperature=36.5, spo2=98)
    db.session.add(log1)
    db.session.commit()
    
    rep2 = create_report(user.id)
    parsed2 = rep2.parsed_snapshot
    print("\n--- Normal Vitals Case ---")
    print(f"Risk Classification: {parsed2['risk']['classification']}")
    print(f"Lifestyle Categories: {list(parsed2['lifestyle'].keys())}")
    
    # Case 3: Critical Vitals with RAG References
    log2 = VitalsLog(user_id=user.id, systolic_bp=190, blood_sugar=200, heart_rate=110, body_temperature=38.5, spo2=95)
    db.session.add(log2)
    db.session.commit()
    
    rep3 = create_report(user.id)
    parsed3 = rep3.parsed_snapshot
    print("\n--- Critical Vitals Case ---")
    print(f"Risk Classification: {parsed3['risk']['classification']}")
    print(f"RAG References found: {len(parsed3['rag_references'])}")
    if parsed3['rag_references']:
        print(f"RAG Ref 1: {parsed3['rag_references'][0]['title']}")
        
    print("\nReport history total items:", HealthReport.query.filter_by(user_id=user.id).count())
