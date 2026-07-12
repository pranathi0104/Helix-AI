import json
from app import create_app
app = create_app()
from extensions import db
from models.user import User
from models.user_profile import UserProfile
from services.granite_service import generate_report_narration
from services.report_service import generate_report_snapshot

def test_granite_inference():
    print("--- Testing Granite Inference ---")
    dummy_snapshot = {
        "profile": {"age": 45, "gender": "male", "conditions": ["hypertension"]},
        "vitals": {"systolic_bp": 145, "diastolic_bp": 90},
        "risk": {"score": 75, "classification": "high", "trend": "worsening", "factors": ["high BP"]},
        "lifestyle": ["reduce sodium", "exercise 30 mins a day"],
        "medications": [],
        "timeline": [],
        "rag_references": []
    }
    
    with app.app_context():
        try:
            narration = generate_report_narration(dummy_snapshot)
            print("Granite Inference Successful!")
            print("Narration Result:")
            print(narration)
            return True
        except Exception as e:
            print("Granite Inference Failed:", e)
            return False

def test_report_generation():
    print("\n--- Testing Report Generation ---")
    with app.app_context():
        # find a user
        user = User.query.first()
        if not user:
            print("No users found in database.")
            return False
            
        try:
            snapshot = generate_report_snapshot(user.id)
            print("Report Generation Successful!")
            print("Narration contained in snapshot:")
            print(snapshot.get("ai_narration"))
            return True
        except Exception as e:
            print("Report Generation Failed:", e)
            return False

def test_fallback_behavior():
    print("\n--- Testing Fallback Behavior ---")
    with app.app_context():
        # forcefully break IBM_API_KEY
        original_key = app.config.get("IBM_API_KEY")
        app.config["IBM_API_KEY"] = "invalid_key_to_force_failure"
        
        user = User.query.first()
        if user:
            try:
                snapshot = generate_report_snapshot(user.id)
                print("Fallback successful, report still generated.")
                print("Narration fallback message:", snapshot.get("ai_narration"))
            except Exception as e:
                print("Fallback failed, report generation crashed:", e)
                
        # restore
        app.config["IBM_API_KEY"] = original_key

if __name__ == "__main__":
    test_granite_inference()
    test_report_generation()
    test_fallback_behavior()
