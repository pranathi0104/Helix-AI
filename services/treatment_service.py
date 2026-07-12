"""
services/treatment_service.py — Business logic for Medication & Treatment Companion.
"""

from datetime import date, datetime
from extensions import db
from models.medication import Medication, MedicationLog


def get_user_medications(user_id: int):
    """Retrieve all medications for a user, ordered by name."""
    return Medication.query.filter_by(user_id=user_id).order_by(Medication.name).all()


def get_active_medications_count(user_id: int) -> int:
    """Count active medications for a user."""
    return Medication.query.filter_by(user_id=user_id, is_active=True).count()


def calculate_adherence(user_id: int) -> int:
    """
    Calculate medication adherence percentage.
    (Taken doses / Total scheduled doses) * 100
    """
    total_logs = MedicationLog.query.join(Medication).filter(
        Medication.user_id == user_id,
        MedicationLog.scheduled_date <= date.today()
    ).count()

    if total_logs == 0:
        return 100

    taken_logs = MedicationLog.query.join(Medication).filter(
        Medication.user_id == user_id,
        MedicationLog.scheduled_date <= date.today(),
        MedicationLog.status == "taken"
    ).count()

    return int((taken_logs / total_logs) * 100)


def get_todays_medications(user_id: int):
    """
    Get medications scheduled for today.
    Creates pending logs if they don't exist yet for today.
    """
    today = date.today()
    medications = Medication.query.filter(
        Medication.user_id == user_id,
        Medication.is_active == True,
        Medication.start_date <= today,
        (Medication.end_date == None) | (Medication.end_date >= today)
    ).all()

    todays_logs = []
    for med in medications:
        log = MedicationLog.query.filter_by(medication_id=med.id, scheduled_date=today).first()
        if not log:
            # Create a pending log for today
            log = MedicationLog(medication_id=med.id, scheduled_date=today, status="pending")
            db.session.add(log)
            db.session.commit()
        todays_logs.append(log)
    
    return todays_logs


def get_upcoming_medications(user_id: int):
    """
    Get active medications as a simple list for upcoming schedule.
    """
    today = date.today()
    return Medication.query.filter(
        Medication.user_id == user_id,
        Medication.is_active == True,
        Medication.start_date <= today,
        (Medication.end_date == None) | (Medication.end_date >= today)
    ).order_by(Medication.name).all()


def get_missed_doses_count(user_id: int) -> int:
    """Count missed doses for a user."""
    return MedicationLog.query.join(Medication).filter(
        Medication.user_id == user_id,
        MedicationLog.status == "missed"
    ).count()


def mark_medication_status(log_id: int, user_id: int, status: str):
    """Mark a medication log as taken, missed, or skipped."""
    log = MedicationLog.query.join(Medication).filter(
        MedicationLog.id == log_id,
        Medication.user_id == user_id
    ).first()

    if log:
        log.status = status
        if status == "taken":
            log.taken_at = datetime.utcnow()
        else:
            log.taken_at = None
        db.session.commit()
        return True
    return False

