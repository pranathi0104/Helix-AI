"""
routes/orchestrate_api.py — Secure read-only REST API endpoints for watsonx Orchestrate.

These endpoints expose deterministic Helix AI service functions as JSON-only APIs.
They require an API key in the Authorization header.
"""

import hmac
from functools import wraps
from flask import Blueprint, jsonify, request, current_app, abort

from models.user_profile import UserProfile
from services.monitoring_service import get_latest_vitals, get_chart_data, classify_vitals
from services.risk_service import calculate_risk
from services.lifestyle_service import generate_recommendations
from services.treatment_service import get_user_medications, calculate_adherence
from services.report_service import generate_report_snapshot

orchestrate_api_bp = Blueprint("orchestrate_api", __name__)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # We expect a Bearer token or direct token in the Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401
       
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Invalid Authorization scheme"}), 401

        token = auth_header[7:].strip()
        expected_key = current_app.config.get("ORCHESTRATE_API_KEY")

        if not expected_key or not hmac.compare_digest(token, expected_key):
            return jsonify({"error": "Unauthorized"}), 403
            
        return f(*args, **kwargs)
    return decorated_function

@orchestrate_api_bp.route("/<int:user_id>/vitals", methods=["GET"])
@require_api_key
def api_get_patient_vitals(user_id):
    """Retrieve the latest clinical vitals for a specific patient."""
    import os
    pid = os.getpid()
    req_path = request.path
    
    current_app.logger.warning(f"--- ORCHESTRATE API HIT --- PID: {pid} | Path: {req_path} | User ID: {user_id}")
    try:
        record = get_latest_vitals(user_id)
        if not record:
            current_app.logger.warning(f"--- ORCHESTRATE API RESPONSE --- PID: {pid} | Status: 200 | Reason: No vitals found")
            return jsonify({"message": "No vitals found for this patient."}), 200
            
        classified = classify_vitals(record)
        current_app.logger.warning(f"--- ORCHESTRATE API RESPONSE --- PID: {pid} | Status: 200 | Reason: Vitals found")
        return jsonify({
            "date": record.date_time.isoformat() if record.date_time else None,
            "systolic_bp": record.systolic_bp,
            "diastolic_bp": record.diastolic_bp,
            "blood_sugar": record.blood_sugar,
            "heart_rate": record.heart_rate,
            "spo2": record.spo2,
            "body_temperature": record.body_temperature,
            "weight": record.weight,
            "classification": classified
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_get_patient_vitals: {e}")
        return jsonify({"error": "Internal server error."}), 500

@orchestrate_api_bp.route("/<int:user_id>/vitals/trends", methods=["GET"])
@require_api_key
def api_get_vital_trends(user_id):
    """Retrieve the last 30 days of vital records formatted as trends for a specific patient."""
    try:
        data = get_chart_data(user_id, n=30)
        return jsonify(data), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_get_vital_trends: {e}")
        return jsonify({"error": "Internal server error."}), 500

@orchestrate_api_bp.route("/<int:user_id>/risk", methods=["GET"])
@require_api_key
def api_get_patient_risk(user_id):
    """Calculate and retrieve the deterministic health risk classification for a patient."""
    try:
        risk_data = calculate_risk(user_id)
        return jsonify(risk_data), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_get_patient_risk: {e}")
        return jsonify({"error": "Internal server error."}), 500

@orchestrate_api_bp.route("/<int:user_id>/lifestyle", methods=["GET"])
@require_api_key
def api_get_lifestyle_recommendations(user_id):
    """Retrieve lifestyle recommendations for a patient based on their profile."""
    try:
        recs = generate_recommendations(user_id)
        return jsonify(recs), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_get_lifestyle_recommendations: {e}")
        return jsonify({"error": "Internal server error."}), 500

@orchestrate_api_bp.route("/<int:user_id>/treatment", methods=["GET"])
@require_api_key
def api_get_treatment_information(user_id):
    """Retrieve current active medications and treatment adherence percentage for a patient."""
    try:
        meds = get_user_medications(user_id)
        adherence = calculate_adherence(user_id)
        
        med_list = []
        for m in meds:
            med_list.append({
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "instructions": m.notes,
                "is_active": m.is_active,
                "start_date": m.start_date.isoformat() if m.start_date else None,
                "end_date": m.end_date.isoformat() if m.end_date else None
            })
            
        return jsonify({
            "adherence_percentage": adherence,
            "medications": med_list
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_get_treatment_information: {e}")
        return jsonify({"error": "Internal server error."}), 500

@orchestrate_api_bp.route("/<int:user_id>/report", methods=["GET"])
@require_api_key
def api_get_health_report_snapshot(user_id):
    """Retrieve the latest aggregated deterministic health report snapshot for a patient."""
    try:
        snapshot = generate_report_snapshot(user_id)
        return jsonify(snapshot), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_get_health_report_snapshot: {e}")
        return jsonify({"error": "Internal server error."}), 500

@orchestrate_api_bp.route("/<int:user_id>/bmi", methods=["GET"])
@require_api_key
def api_calculate_bmi(user_id):
    """Calculate Body Mass Index (BMI) using a patient's saved profile."""
    try:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return jsonify({"error": "Patient profile not found."}), 404
        
        bmi_val = profile.bmi
        if bmi_val is None:
            return jsonify({"error": "Height or weight is missing from profile."}), 400
            
        return jsonify({"bmi": bmi_val}), 200
    except Exception as e:
        current_app.logger.error(f"Error in api_calculate_bmi: {e}")
        return jsonify({"error": "Internal server error."}), 500
