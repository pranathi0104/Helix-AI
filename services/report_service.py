"""
services/report_service.py — AI Health Reports Aggregation logic.
"""

import json
from datetime import datetime
from flask import current_app
from extensions import db
from models.user_profile import UserProfile
from models.vitals_log import VitalsLog
from models.health_timeline import HealthTimeline
from models.medication import Medication, MedicationLog
from models.health_report import HealthReport
from services.risk_service import calculate_risk
from services.lifestyle_service import generate_recommendations
from services.rag_service import retrieve

def generate_report_snapshot(user_id: int) -> dict:
    # 1. Profile Summary
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    profile_data = {
        "full_name": profile.full_name if profile and profile.full_name else "Not available",
        "age": profile.age if profile and profile.age else "Not available",
        "gender": profile.gender if profile and profile.gender else "Not available",
        "blood_group": profile.blood_group if profile and profile.blood_group else "Not available",
        "conditions": profile.conditions_list if profile and profile.conditions_list else ["None reported"]
    }
    
    # 2. Vitals & Trends
    latest_vital = VitalsLog.query.filter_by(user_id=user_id).order_by(VitalsLog.date_time.desc()).first()
    vitals_data = {}
    if latest_vital:
        dt = latest_vital.date_time
        if getattr(dt, 'tzinfo', None) is None:
            import zoneinfo
            dt = dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        vitals_data = {
            "date_time": dt.isoformat(),
            "systolic_bp": latest_vital.systolic_bp,
            "diastolic_bp": latest_vital.diastolic_bp,
            "heart_rate": latest_vital.heart_rate,
            "blood_sugar": latest_vital.blood_sugar,
            "spo2": latest_vital.spo2,
            "body_temperature": latest_vital.body_temperature,
            "weight": latest_vital.weight
        }
        
    # 3. Risk & Lifestyle
    risk = calculate_risk(user_id)
    lifestyle = generate_recommendations(user_id)
    
    # 4. Medications
    meds = Medication.query.filter_by(user_id=user_id).all()
    medications_data = []
    for m in meds:
        logs = MedicationLog.query.filter_by(medication_id=m.id).all()
        taken = sum(1 for log in logs if log.status == "taken")
        missed = sum(1 for log in logs if log.status == "missed")
        adherence = f"{int((taken / (taken + missed)) * 100)}%" if taken + missed > 0 else "N/A"
        
        medications_data.append({
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "adherence": adherence
        })
        
    # 5. Timeline Events
    events = HealthTimeline.query.filter_by(user_id=user_id).order_by(HealthTimeline.event_date.desc()).limit(10).all()
    timeline_data = []
    for e in events:
        edt = e.event_date
        if getattr(edt, 'tzinfo', None) is None:
            import zoneinfo
            edt = edt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        timeline_data.append({"date": edt.isoformat(), "summary": e.event_summary, "type": e.event_type})
    
    # 6. RAG References (only if health context exists)
    rag_refs = []
    if risk.get("factors"):
        query = risk["factors"][0]
        results = retrieve(query, top_k=2)
        if results:
            rag_refs = [{"title": r["title"], "source": r["source"], "text": r["text"][:150] + "..."} for r in results]
    elif profile and profile.conditions_list:
        query = profile.conditions_list[0]
        results = retrieve(query, top_k=2)
        if results:
            rag_refs = [{"title": r["title"], "source": r["source"], "text": r["text"][:150] + "..."} for r in results]
            
    snapshot = {
        "profile": profile_data,
        "vitals": vitals_data,
        "risk": {
            "score": risk["score"],
            "classification": risk["classification"],
            "factors": risk["factors"],
            "trend": risk["trend"]
        },
        "lifestyle": lifestyle["recommendations"],
        "medications": medications_data,
        "timeline": timeline_data,
        "rag_references": rag_refs
    }
    
    # Add Granite Narration Layer
    try:
        from services.granite_service import generate_report_narration
        snapshot["ai_narration"] = generate_report_narration(snapshot)
    except Exception as e:
        current_app.logger.error("Granite narration failed.")
        snapshot["ai_narration"] = "AI narration is currently unavailable. Please review the deterministic report below."
        

    
    return snapshot

def create_report(user_id: int) -> HealthReport:
    snapshot = generate_report_snapshot(user_id)
    report = HealthReport(
        user_id=user_id,
        risk_classification=snapshot["risk"]["classification"],
        snapshot_data=json.dumps(snapshot)
    )
    db.session.add(report)
    db.session.commit()
    return report
