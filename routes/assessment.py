"""
routes/assessment.py — AI Clinical Assessment blueprint (Milestone 2).

Provides:
  GET  /assessment        — Symptom input form (pre-populated from user profile)
  POST /assessment/submit — Send symptoms to Granite, show structured result

All IBM Granite calls are delegated to services/granite_service.py.
This route does not depend on RAG, Orchestrate, or any future-milestone service.

Error handling strategy:
  GraniteConfigError     → show a clear "credentials not configured" notice
  GraniteConnectionError → show a "service unavailable" notice
  GraniteResponseError   → show a "could not parse AI response" notice
  Any other exception    → log + show generic error notice
"""

import logging

from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
)
from flask_login import login_required, current_user

from services.granite_service import (
    run_assessment,
    GraniteConfigError,
    GraniteConnectionError,
    GraniteResponseError,
)

logger = logging.getLogger(__name__)

assessment_bp = Blueprint("assessment", __name__, url_prefix="/assessment")

# Allowed select-field values (server-side whitelist)
GENDER_OPTIONS    = ["Male", "Female", "Other", "Prefer not to say"]
CONDITION_OPTIONS = ["Diabetes", "Hypertension", "Heart Disease",
                     "Asthma", "Obesity", "Other"]


@assessment_bp.route("/", methods=["GET"])
@login_required
def index():
    """
    Render the AI Clinical Assessment form.
    Pre-populate age, gender, and conditions from the user's saved profile.
    """
    profile = current_user.profile

    # Build pre-fill values from profile (empty strings if profile not complete)
    prefill = {
        "age":        str(profile.age)              if profile and profile.age      else "",
        "gender":     profile.gender                if profile and profile.gender   else "",
        "conditions": profile.existing_conditions   if profile                      else "",
    }

    return render_template(
        "assessment/index.html",
        title="AI Clinical Assessment",
        prefill=prefill,
        gender_options=GENDER_OPTIONS,
        condition_options=CONDITION_OPTIONS,
        model_id=current_app.config.get("MODEL_ID", "ibm/granite-3-1-8b-base"),
    )


@assessment_bp.route("/submit", methods=["POST"])
@login_required
def submit():
    """
    Receive the symptom form, call IBM Granite, and render the results page.

    On any error the form is re-rendered with an inline error message so
    the user never sees a raw exception.
    """
    # ------------------------------------------------------------------ #
    # 1. Collect and basic-validate form inputs                           #
    # ------------------------------------------------------------------ #
    symptoms   = request.form.get("symptoms",   "").strip()
    age        = request.form.get("age",        "").strip()
    gender     = request.form.get("gender",     "").strip()
    conditions = request.form.getlist("conditions")          # multi-select → list
    conditions_str = ", ".join(conditions) if conditions else ""

    if not symptoms:
        return render_template(
            "assessment/index.html",
            title="AI Clinical Assessment",
            error="Please describe your symptoms before submitting.",
            prefill={"age": age, "gender": gender, "conditions": conditions_str},
            gender_options=GENDER_OPTIONS,
            condition_options=CONDITION_OPTIONS,
        )

    # Enforce a reasonable symptom length (prevent accidental huge prompts)
    if len(symptoms) > 2000:
        return render_template(
            "assessment/index.html",
            title="AI Clinical Assessment",
            error="Symptom description is too long. Please keep it under 2 000 characters.",
            prefill={"age": age, "gender": gender, "conditions": conditions_str},
            gender_options=GENDER_OPTIONS,
            condition_options=CONDITION_OPTIONS,
        )

    # ------------------------------------------------------------------ #
    # 2. Call IBM Granite                                                  #
    # ------------------------------------------------------------------ #
    try:
        result = run_assessment(
            symptoms   = symptoms,
            age        = age,
            gender     = gender,
            conditions = conditions_str,
        )

    except GraniteConfigError as exc:
        logger.warning("Granite config error: %s", exc)
        return render_template(
            "assessment/index.html",
            title="AI Clinical Assessment",
            error=(
                "IBM Granite is not configured. "
                "Please add IBM_API_KEY, IBM_PROJECT_ID, and IBM_URL to your .env file."
            ),
            prefill={"age": age, "gender": gender, "conditions": conditions_str},
            gender_options=GENDER_OPTIONS,
            condition_options=CONDITION_OPTIONS,
        )

    except GraniteConnectionError as exc:
        logger.error("Granite connection error: %s", exc)
        return render_template(
            "assessment/index.html",
            title="AI Clinical Assessment",
            error=(
                "Could not reach IBM watsonx.ai. "
                "Please check your internet connection and try again."
            ),
            prefill={"age": age, "gender": gender, "conditions": conditions_str},
            gender_options=GENDER_OPTIONS,
            condition_options=CONDITION_OPTIONS,
        )

    except GraniteResponseError as exc:
        logger.error("Granite response error: %s", exc)
        return render_template(
            "assessment/index.html",
            title="AI Clinical Assessment",
            error=(
                "The AI returned an unexpected response. "
                "Please try again — if the problem persists, try rephrasing your symptoms."
            ),
            prefill={"age": age, "gender": gender, "conditions": conditions_str},
            gender_options=GENDER_OPTIONS,
            condition_options=CONDITION_OPTIONS,
        )

    except Exception as exc:
        logger.exception("Unexpected error during Granite assessment: %s", exc)
        return render_template(
            "assessment/index.html",
            title="AI Clinical Assessment",
            error="An unexpected error occurred. Please try again.",
            prefill={"age": age, "gender": gender, "conditions": conditions_str},
            gender_options=GENDER_OPTIONS,
            condition_options=CONDITION_OPTIONS,
        )

    # ------------------------------------------------------------------ #
    # 3. Render results                                                    #
    # ------------------------------------------------------------------ #
    return render_template(
        "assessment/result.html",
        title="Assessment Result — AI Clinical Assessment",
        result=result,
        # Echo back the user inputs so they are shown on the result page
        submitted={
            "symptoms":   symptoms,
            "age":        age,
            "gender":     gender,
            "conditions": conditions_str,
        },
    )
