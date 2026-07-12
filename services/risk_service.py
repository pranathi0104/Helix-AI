"""
services/risk_service.py — Deterministic Risk Prediction Agent.
"""

from models.vitals_log import VitalsLog

def calculate_risk(user_id: int) -> dict:
    """
    Calculates a rule-based deterministic risk score (0-100) and classification.
    """
    logs = VitalsLog.query.filter_by(user_id=user_id).order_by(VitalsLog.date_time.desc()).all()
    
    if not logs:
        return {
            "score": 0,
            "classification": "Unknown",
            "factors": [],
            "trend": "No vitals data available to calculate risk.",
            "latest_date": None
        }
        
    latest = logs[0]
    score = 0
    factors = []
    
    # Blood Pressure (Systolic)
    if latest.systolic_bp:
        if latest.systolic_bp > 180:
            score += 30
            factors.append("Critically High Systolic Blood Pressure (>180 mmHg)")
        elif latest.systolic_bp > 140:
            score += 15
            factors.append("High Systolic Blood Pressure (>140 mmHg)")
        elif latest.systolic_bp < 90:
            score += 10
            factors.append("Low Systolic Blood Pressure (<90 mmHg)")
            
    # Blood Pressure (Diastolic)
    if latest.diastolic_bp:
        if latest.diastolic_bp > 120:
            score += 20
            factors.append("Critically High Diastolic BP (>120 mmHg)")
        elif latest.diastolic_bp > 90:
            score += 10
            factors.append("High Diastolic BP (>90 mmHg)")
            
    # Blood Sugar
    if latest.blood_sugar:
        if latest.blood_sugar > 250:
            score += 25
            factors.append("Dangerously High Blood Sugar (>250 mg/dL)")
        elif latest.blood_sugar > 180:
            score += 10
            factors.append("Elevated Blood Sugar (>180 mg/dL)")
        elif latest.blood_sugar < 70:
            score += 20
            factors.append("Hypoglycemia (Low Blood Sugar <70 mg/dL)")
            
    # Heart Rate
    if latest.heart_rate:
        if latest.heart_rate > 120:
            score += 15
            factors.append("Tachycardia (High Heart Rate >120 bpm)")
        elif latest.heart_rate < 50:
            score += 10
            factors.append("Bradycardia (Low Heart Rate <50 bpm)")
            
    # SpO2
    if latest.spo2:
        if latest.spo2 < 90:
            score += 30
            factors.append("Hypoxemia (Dangerously Low SpO2 <90%)")
        elif latest.spo2 < 95:
            score += 10
            factors.append("Low Oxygen Saturation (<95%)")
            
    # Body Temperature
    if latest.body_temperature:
        if latest.body_temperature > 39.0:
            score += 15
            factors.append("High Fever (>39.0°C)")
        elif latest.body_temperature < 35.0:
            score += 15
            factors.append("Hypothermia (<35.0°C)")
            
    # Cap score at 100
    score = min(score, 100)
    
    # Classification
    if score >= 60:
        classification = "Critical"
    elif score >= 40:
        classification = "High"
    elif score >= 20:
        classification = "Moderate"
    else:
        classification = "Low"
        
    # Trend Analysis
    if len(logs) < 2:
        trend = "Insufficient historical data for trend analysis."
    else:
        trend_messages = []
        
        def get_prev(vital_attr):
            for l in logs[1:]:
                val = getattr(l, vital_attr)
                if val is not None:
                    return val
            return None

        # Systolic BP
        latest_sys = latest.systolic_bp
        prev_sys = get_prev('systolic_bp')
        if latest_sys is not None and prev_sys is not None:
            if latest_sys >= prev_sys + 15:
                trend_messages.append(f"Systolic blood pressure increased from {prev_sys} to {latest_sys} mmHg.")
            elif latest_sys <= prev_sys - 15:
                trend_messages.append(f"Systolic blood pressure decreased from {prev_sys} to {latest_sys} mmHg.")
                
        # Diastolic BP
        latest_dia = latest.diastolic_bp
        prev_dia = get_prev('diastolic_bp')
        if latest_dia is not None and prev_dia is not None:
            if latest_dia >= prev_dia + 10:
                trend_messages.append(f"Diastolic blood pressure increased from {prev_dia} to {latest_dia} mmHg.")
            elif latest_dia <= prev_dia - 10:
                trend_messages.append(f"Diastolic blood pressure decreased from {prev_dia} to {latest_dia} mmHg.")

        # Blood Sugar
        latest_bs = latest.blood_sugar
        prev_bs = get_prev('blood_sugar')
        if latest_bs is not None and prev_bs is not None:
            if latest_bs >= prev_bs + 30:
                trend_messages.append(f"Blood sugar increased from {prev_bs} to {latest_bs} mg/dL.")
            elif latest_bs <= prev_bs - 30:
                trend_messages.append(f"Blood sugar decreased from {prev_bs} to {latest_bs} mg/dL.")
                
        # Heart Rate
        latest_hr = latest.heart_rate
        prev_hr = get_prev('heart_rate')
        if latest_hr is not None and prev_hr is not None:
            if latest_hr >= prev_hr + 20:
                trend_messages.append(f"Heart rate increased from {prev_hr} to {latest_hr} bpm.")
            elif latest_hr <= prev_hr - 20:
                trend_messages.append(f"Heart rate decreased from {prev_hr} to {latest_hr} bpm.")
                
        # SpO2
        latest_spo2 = latest.spo2
        prev_spo2 = get_prev('spo2')
        if latest_spo2 is not None and prev_spo2 is not None:
            if latest_spo2 <= prev_spo2 - 3:
                trend_messages.append(f"SpO2 decreased from {prev_spo2}% to {latest_spo2}%.")
            elif latest_spo2 >= prev_spo2 + 3:
                trend_messages.append(f"SpO2 increased from {prev_spo2}% to {latest_spo2}%.")
                
        # Body Temperature
        latest_temp = latest.body_temperature
        prev_temp = get_prev('body_temperature')
        if latest_temp is not None and prev_temp is not None:
            if latest_temp >= prev_temp + 1.0:
                trend_messages.append(f"Body temperature increased from {prev_temp}°C to {latest_temp}°C.")
            elif latest_temp <= prev_temp - 1.0:
                trend_messages.append(f"Body temperature decreased from {prev_temp}°C to {latest_temp}°C.")
                
        # Weight
        latest_weight = latest.weight
        prev_weight = get_prev('weight')
        if latest_weight is not None and prev_weight is not None:
            if latest_weight >= prev_weight + 2.0:
                trend_messages.append(f"Weight increased from {prev_weight} to {latest_weight} kg.")
            elif latest_weight <= prev_weight - 2.0:
                trend_messages.append(f"Weight decreased from {prev_weight} to {latest_weight} kg.")

        if trend_messages:
            trend = " ".join(trend_messages)
        else:
            has_comparable = False
            for attr in ['systolic_bp', 'diastolic_bp', 'blood_sugar', 'heart_rate', 'spo2', 'body_temperature', 'weight']:
                if getattr(latest, attr) is not None and get_prev(attr) is not None:
                    has_comparable = True
                    break
            
            if has_comparable:
                trend = "Vitals patterns are stable based on recent logs."
            else:
                trend = "Insufficient historical data for trend analysis."
            
    return {
        "score": score,
        "classification": classification,
        "factors": factors,
        "trend": trend,
        "latest_date": latest.date_time
    }
