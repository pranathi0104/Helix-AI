"""
services/lifestyle_service.py — Deterministic Lifestyle Recommendation Agent.
"""

from models.user_profile import UserProfile
from models.vitals_log import VitalsLog
from services.risk_service import calculate_risk

def generate_recommendations(user_id: int) -> dict:
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    risk_data = calculate_risk(user_id)
    latest_vital = VitalsLog.query.filter_by(user_id=user_id).order_by(VitalsLog.date_time.desc()).first()
    
    recommendations = {
        "Nutrition": [],
        "Physical Activity": [],
        "Sleep": [],
        "Hydration": [],
        "General Health": []
    }
    
    # Base logic & safety boundaries based on Risk Level
    is_critical_risk = risk_data["classification"] in ["High", "Critical"]
    
    # ── Physical Activity ──────────────────────────────────────────────────
    if is_critical_risk:
        recommendations["Physical Activity"].append({
            "title": "Strict Rest Recommended",
            "explanation": "Due to your currently high risk score, strenuous physical activity should be avoided. Rest until your vitals stabilize.",
            "priority": "High",
            "reason": f"Risk level is {risk_data['classification']}."
        })
    else:
        has_high_bp = latest_vital and latest_vital.systolic_bp and latest_vital.systolic_bp > 130
        if has_high_bp:
            recommendations["Physical Activity"].append({
                "title": "Light to Moderate Activity",
                "explanation": "Engage in gentle activities like walking. Avoid heavy lifting which can temporarily spike blood pressure.",
                "priority": "Medium",
                "reason": f"Latest systolic BP is elevated ({latest_vital.systolic_bp} mmHg)."
            })
        else:
            recommendations["Physical Activity"].append({
                "title": "Maintain Daily Activity",
                "explanation": "Aim for 30 minutes of moderate exercise daily to maintain cardiovascular health.",
                "priority": "Low",
                "reason": "Vitals are stable."
            })
            
    # ── Nutrition ──────────────────────────────────────────────────────────
    has_diabetes_factor = False
    if profile and profile.conditions_list:
        has_diabetes_factor = any("diabet" in c.lower() for c in profile.conditions_list)
        
    has_high_sugar = latest_vital and latest_vital.blood_sugar and latest_vital.blood_sugar > 140
    has_low_sugar = latest_vital and latest_vital.blood_sugar and latest_vital.blood_sugar < 70
    is_severe_low_sugar = latest_vital and latest_vital.blood_sugar and latest_vital.blood_sugar <= 50
    
    if is_severe_low_sugar:
        recommendations["Nutrition"].append({
            "title": "Severe Hypoglycemia Alert",
            "explanation": "Your blood sugar is critically low. Consume fast-acting carbohydrates immediately (e.g., fruit juice, glucose tablets) and seek urgent medical attention.",
            "priority": "High",
            "reason": f"Blood sugar is critically low ({latest_vital.blood_sugar} mg/dL)."
        })
    elif has_low_sugar:
        recommendations["Nutrition"].append({
            "title": "Hypoglycemia Alert",
            "explanation": "Your blood sugar is low. Consume 15 grams of fast-acting carbohydrates and recheck in 15 minutes.",
            "priority": "High",
            "reason": f"Blood sugar is low ({latest_vital.blood_sugar} mg/dL)."
        })
    elif has_diabetes_factor or has_high_sugar:
        reason_txt = "Blood sugar is elevated." if has_high_sugar else "Diabetes indicated in profile."
        recommendations["Nutrition"].append({
            "title": "Low Glycemic Diet",
            "explanation": "Focus on complex carbohydrates, lean proteins, and fiber. Avoid sugary snacks and processed foods.",
            "priority": "High" if has_high_sugar else "Medium",
            "reason": reason_txt
        })
        
    has_high_bp_risk = any("Blood Pressure" in factor for factor in risk_data.get("factors", []))
    if has_high_bp_risk:
        recommendations["Nutrition"].append({
            "title": "DASH Diet Principles",
            "explanation": "Reduce sodium intake (under 2,300mg/day). Increase potassium-rich foods like bananas and spinach.",
            "priority": "High",
            "reason": "Blood pressure risk factors detected."
        })
        
    if not recommendations["Nutrition"]:
        recommendations["Nutrition"].append({
            "title": "Balanced Whole-Food Diet",
            "explanation": "Maintain a diet rich in fruits, vegetables, lean proteins, and whole grains.",
            "priority": "Low",
            "reason": "General wellness maintenance."
        })
        
    # ── Hydration ──────────────────────────────────────────────────────────
    if latest_vital and latest_vital.body_temperature and latest_vital.body_temperature > 37.5:
        recommendations["Hydration"].append({
            "title": "Aggressive Rehydration",
            "explanation": "You have an elevated temperature. Increase water intake to prevent dehydration.",
            "priority": "High",
            "reason": f"Body temperature is {latest_vital.body_temperature}°C."
        })
    else:
        recommendations["Hydration"].append({
            "title": "Consistent Hydration",
            "explanation": "Drink at least 8 glasses of water a day. Adjust based on climate and activity levels.",
            "priority": "Low",
            "reason": "General wellness maintenance."
        })
        
    # ── Sleep ──────────────────────────────────────────────────────────────
    if latest_vital and latest_vital.heart_rate and latest_vital.heart_rate > 100:
        recommendations["Sleep"].append({
            "title": "Prioritize Restful Sleep",
            "explanation": "Your resting heart rate is high. Ensure you get 7-9 hours of quality sleep in a cool, dark room.",
            "priority": "Medium",
            "reason": f"Heart rate is elevated ({latest_vital.heart_rate} bpm)."
        })
    else:
        recommendations["Sleep"].append({
            "title": "Maintain Sleep Routine",
            "explanation": "Try to go to bed and wake up at the same time every day to regulate your circadian rhythm.",
            "priority": "Low",
            "reason": "General wellness maintenance."
        })
        
    # ── General Health ─────────────────────────────────────────────────────
    is_dangerous_spo2 = latest_vital and latest_vital.spo2 and latest_vital.spo2 < 90
    is_dangerous_bp = latest_vital and latest_vital.systolic_bp and latest_vital.systolic_bp >= 180
    is_severe_low_sugar = latest_vital and latest_vital.blood_sugar and latest_vital.blood_sugar <= 50

    is_emergency = is_critical_risk or is_dangerous_spo2 or is_dangerous_bp or is_severe_low_sugar

    if is_emergency:
        recommendations["General Health"].append({
            "title": "Seek Urgent Medical Attention",
            "explanation": "Your vitals indicate a potentially dangerous condition. Please seek immediate professional medical assistance or go to the nearest emergency room.",
            "priority": "High",
            "reason": "One or more vitals are in a critically dangerous range or your overall risk is Critical."
        })
        
    if risk_data["trend"] and ("increas" in risk_data["trend"].lower() or "rising" in risk_data["trend"].lower() or "decreas" in risk_data["trend"].lower()):
        recommendations["General Health"].append({
            "title": "Monitor Vitals Closely",
            "explanation": "Your recent readings show dynamic trends. Please continue logging your vitals daily.",
            "priority": "Medium",
            "reason": risk_data["trend"]
        })
    elif not is_emergency:
        recommendations["General Health"].append({
            "title": "Regular Monitoring",
            "explanation": "Keep logging your vitals periodically to establish a reliable health baseline.",
            "priority": "Low",
            "reason": "Stable health profile."
        })
        
    return {
        "risk_classification": risk_data["classification"],
        "recommendations": recommendations,
        "latest_date": latest_vital.date_time if latest_vital else None
    }
