"""
routes/treatment.py — Medication & Treatment Companion blueprint.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from extensions import db
from models.medication import Medication
from services.treatment_service import (
    get_user_medications,
    get_active_medications_count,
    calculate_adherence,
    get_todays_medications,
    get_upcoming_medications,
    get_missed_doses_count,
    mark_medication_status,
)

treatment_bp = Blueprint("treatment", __name__)


@treatment_bp.route("/")
@login_required
def index():
    """Main Treatment Companion dashboard."""
    # Summary cards data
    active_count = get_active_medications_count(current_user.id)
    adherence = calculate_adherence(current_user.id)
    missed_count = get_missed_doses_count(current_user.id)

    # Today's list and upcoming
    todays_logs = get_todays_medications(current_user.id)
    upcoming_meds = get_upcoming_medications(current_user.id)
    all_meds = get_user_medications(current_user.id)

    return render_template(
        "treatment/index.html",
        title="Treatment Companion",
        active_count=active_count,
        adherence=adherence,
        missed_count=missed_count,
        todays_logs=todays_logs,
        upcoming_meds=upcoming_meds,
        all_meds=all_meds,
    )


@treatment_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add a new medication."""
    if request.method == "POST":
        name = request.form.get("name")
        dosage = request.form.get("dosage")
        frequency = request.form.get("frequency")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        notes = request.form.get("notes")
        is_active = request.form.get("is_active") == "on"

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else datetime.utcnow().date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

        med = Medication(
            user_id=current_user.id,
            name=name,
            dosage=dosage,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
            is_active=is_active,
        )
        db.session.add(med)
        db.session.commit()
        flash(f"Medication '{name}' added successfully.", "success")
        return redirect(url_for("treatment.index"))

    return render_template("treatment/form.html", title="Add Medication", med=None)


@treatment_bp.route("/<int:med_id>/edit", methods=["GET", "POST"])
@login_required
def edit(med_id):
    """Edit an existing medication."""
    med = Medication.query.filter_by(id=med_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        med.name = request.form.get("name")
        med.dosage = request.form.get("dosage")
        med.frequency = request.form.get("frequency")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        med.notes = request.form.get("notes")
        med.is_active = request.form.get("is_active") == "on"

        if start_date_str:
            med.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if end_date_str:
            med.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            med.end_date = None

        db.session.commit()
        flash(f"Medication '{med.name}' updated successfully.", "success")
        return redirect(url_for("treatment.index"))

    return render_template("treatment/form.html", title="Edit Medication", med=med)


@treatment_bp.route("/<int:med_id>/delete", methods=["POST"])
@login_required
def delete(med_id):
    """Delete a medication."""
    med = Medication.query.filter_by(id=med_id, user_id=current_user.id).first_or_404()
    db.session.delete(med)
    db.session.commit()
    flash(f"Medication '{med.name}' deleted.", "info")
    return redirect(url_for("treatment.index"))


@treatment_bp.route("/log/<int:log_id>/<status>", methods=["POST"])
@login_required
def log_status(log_id, status):
    """Mark a medication dose log as taken, missed, or skipped."""
    if status not in ["taken", "missed", "skipped"]:
        flash("Invalid status update.", "danger")
        return redirect(url_for("treatment.index"))

    success = mark_medication_status(log_id, current_user.id, status)
    if success:
        flash(f"Medication dose marked as {status}.", "success")
    else:
        flash("Could not update medication log.", "danger")

    return redirect(url_for("treatment.index"))
