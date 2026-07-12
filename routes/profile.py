"""
routes/profile.py — User health profile blueprint.

Handles viewing and editing the UserProfile record.
The profile form collects demographic and lifestyle data
that future AI agents will consume.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models.user_profile import UserProfile

profile_bp = Blueprint("profile", __name__)

# Allowed values for select fields
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
BLOOD_GROUP_OPTIONS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "Unknown"]
CONDITION_OPTIONS = ["Diabetes", "Hypertension", "Heart Disease", "Asthma", "Obesity", "Other"]
EXERCISE_OPTIONS = ["never", "occasionally", "regularly"]
DIET_OPTIONS = ["poor", "average", "good"]


@profile_bp.route("/")
@login_required
def view():
    """Display the current user's health profile."""
    profile = current_user.profile
    if not profile:
        return redirect(url_for("profile.edit"))
    return render_template(
        "profile/view.html",
        title="My Health Profile",
        profile=profile,
    )


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    """Create or update the user's health profile."""
    profile = current_user.profile

    if request.method == "POST":
        # Collect form values
        full_name = request.form.get("full_name", "").strip()
        age_raw = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        height_raw = request.form.get("height_cm", "").strip()
        weight_raw = request.form.get("weight_kg", "").strip()
        conditions = request.form.getlist("conditions")   # multi-select returns a list
        smoking = request.form.get("smoking") == "on"
        alcohol = request.form.get("alcohol") == "on"
        exercise_frequency = request.form.get("exercise_frequency", "occasionally")
        diet_quality = request.form.get("diet_quality", "average")

        # --- Validation ---
        errors = []
        age = None
        height_cm = None
        weight_kg = None

        if age_raw:
            try:
                age = int(age_raw)
                if not (1 <= age <= 120):
                    errors.append("Age must be between 1 and 120.")
            except ValueError:
                errors.append("Age must be a whole number.")

        if height_raw:
            try:
                height_cm = float(height_raw)
                if not (50 <= height_cm <= 300):
                    errors.append("Height must be between 50 and 300 cm.")
            except ValueError:
                errors.append("Height must be a number.")

        if weight_raw:
            try:
                weight_kg = float(weight_raw)
                if not (1 <= weight_kg <= 500):
                    errors.append("Weight must be between 1 and 500 kg.")
            except ValueError:
                errors.append("Weight must be a number.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "profile/edit.html",
                title="Edit Profile",
                profile=profile,
                gender_options=GENDER_OPTIONS,
                blood_group_options=BLOOD_GROUP_OPTIONS,
                condition_options=CONDITION_OPTIONS,
                exercise_options=EXERCISE_OPTIONS,
                diet_options=DIET_OPTIONS,
            )

        # --- Save / update ---
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)

        profile.full_name = full_name
        profile.age = age
        profile.gender = gender
        profile.blood_group = blood_group
        profile.height_cm = height_cm
        profile.weight_kg = weight_kg
        profile.existing_conditions = ",".join(conditions) if conditions else ""
        profile.smoking = smoking
        profile.alcohol = alcohol
        profile.exercise_frequency = exercise_frequency
        profile.diet_quality = diet_quality
        profile.updated_at = datetime.utcnow()

        db.session.commit()
        flash("Health profile updated successfully.", "success")
        return redirect(url_for("dashboard.home"))

    return render_template(
        "profile/edit.html",
        title="Edit Profile",
        profile=profile,
        gender_options=GENDER_OPTIONS,
        blood_group_options=BLOOD_GROUP_OPTIONS,
        condition_options=CONDITION_OPTIONS,
        exercise_options=EXERCISE_OPTIONS,
        diet_options=DIET_OPTIONS,
    )
