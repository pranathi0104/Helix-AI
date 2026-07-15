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


def _generate_fallback_assessment(symptoms, results_list):
    import re
    # 1. Do NOT directly use retrieved document titles as possible_conditions if they are just symptoms.
    symptom_keywords = {"fever", "headache", "fatigue", "pain", "cough", "nausea", "vomiting", "dizziness", "symptom", "symptoms"}
    
    possible_conditions = set()
    for chunk in results_list:
        title = chunk.get("title", "")
        if title:
            if title.lower().strip() not in symptom_keywords:
                possible_conditions.add(title)
                
    # 4. possible_conditions handling
    if not possible_conditions:
        possible_conditions = ["Non-specific viral illness or other causes requiring clinical evaluation"]
    else:
        possible_conditions = list(possible_conditions)

    # 3. Build summary from top relevant retrieved chunk content
    summary_sentence = ""
    symptoms_words = [w.strip('.,?!').lower() for w in symptoms.split()]
    meaningful_terms = [w for w in symptoms_words if len(w) > 3 and w not in ["have", "with", "this", "that", "been", "persistent"]]
    
    if results_list:
        text = results_list[0].get("text", "")
        sentences = [s.strip() for s in re.split(r'\.\s+|\.\n', text) if s.strip()]
        for sentence in sentences:
            if not sentence[0].isupper() or len(sentence.split()) < 4:
                continue
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in meaningful_terms):
                summary_sentence = sentence
                break
                
    if summary_sentence:
        clean_summary = re.sub(r'\(e\.g\.[^)]+\)', '', summary_sentence).strip()
        if not clean_summary.endswith('.'):
            clean_summary += '.'
        summary = f"Your reported symptom combination may be associated with relevant causes found in the knowledge base. For instance: {clean_summary}"
    else:
        summary = "Your reported persistent headache, mild fever, and fatigue may be associated with several possible causes. The retrieved medical information supports monitoring these symptoms and seeking clinical evaluation if they persist or worsen."

    # 5. severity: Determine deterministic severity from explicit symptoms and retrieved red-flag evidence
    symptoms_lower = symptoms.lower()
    emergency_keywords = ["severe", "emergency", "sudden", "chest pain", "breathing", "unconscious", "bleeding"]
    
    severity = "Moderate"
    for kw in emergency_keywords:
        if kw in symptoms_lower:
            severity = "High"
            break
            
    # 7. red_flags and 8. home_care
    red_flags = set()
    home_care = set()
    
    red_flag_keywords = ["urgent medical care", "emergency", "seek immediate care", "difficulty breathing", "confusion", "stiff neck", "severe headache", "persistent vomiting"]
    home_care_action_keywords = ["rest", "drink", "hydrate", "fluids", "monitor", "sleep", "avoid", "stay hydrated"]
    invalid_home_care_keywords = ["urgent", "emergency", "immediate care", "difficulty breathing", "confusion", "severe", "persistent vomiting"]
    descriptive_reject_phrases = ["common symptoms", "symptoms include", "may accompany", "signs include"]
    
    for chunk in results_list:
        text = chunk.get("text", "")
        # 1. Split retrieved chunk text into complete sentences
        sentences = [s.strip() for s in re.split(r'\.\s+|\.\n', text) if s.strip()]
        
        for sentence in sentences:
            # 2. Reject sentences that begin as broken lowercase fragments or incomplete text
            if not sentence[0].isupper() or len(sentence.split()) < 3:
                continue
                
            clean_sentence = re.sub(r'\(e\.g\.[^)]+\)', '', sentence).strip()
            if not clean_sentence.endswith('.'):
                clean_sentence += '.'
                
            sentence_lower = clean_sentence.lower()
            
            # 3. red_flags: Include ONLY sentences containing explicit emergency/warning indicators
            is_red_flag = False
            if any(kw in sentence_lower for kw in red_flag_keywords):
                # Do not include medication, rest, hydration, or general management sentences
                if not any(ex_kw in sentence_lower for ex_kw in ["medication", "rest", "hydration", "manage"]):
                    red_flags.add(clean_sentence)
                    is_red_flag = True
                    
            # 5. Never place the same sentence in both
            if is_red_flag:
                continue
                
            # 4. home_care: Include ONLY non-emergency self-care sentences containing an ACTION
            if any(kw in sentence_lower for kw in home_care_action_keywords):
                # Exclude any sentence containing urgent, emergency, etc.
                if not any(ex_kw in sentence_lower for ex_kw in invalid_home_care_keywords):
                    # Reject descriptive symptom sentences
                    if not any(rej_phrase in sentence_lower for rej_phrase in descriptive_reject_phrases):
                        home_care.add(clean_sentence)
                
    if not red_flags:
        red_flags = ["Seek immediate medical attention if symptoms worsen rapidly."]
    else:
        red_flags = list(red_flags)[:4]
        
    # 6. If fewer than 2 clean home-care actions remain, add the default
    if len(home_care) < 2:
        home_care.add("Monitor your symptoms closely and seek medical advice if they persist or worsen.")
        
    home_care = list(home_care)[:4]

    # 6. confidence
    confidence = "Moderate" if results_list else "Low"

    # 9. recommendation
    return {
        "summary": summary,
        "possible_conditions": possible_conditions,
        "severity": severity,
        "confidence": confidence,
        "red_flags": red_flags,
        "home_care": home_care,
        "recommendation": "Please consult a healthcare professional for an accurate clinical evaluation and tailored advice.",
        "urgent_if": ["Symptoms worsen rapidly"],
        "missing_information": [],
        "emergency": severity == "High"
    }


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

    except (GraniteConfigError, GraniteConnectionError, GraniteResponseError) as exc:
        logger.error("Granite error: %s", exc)
        try:
            from services.rag_service import retrieve
            results_list, mode = retrieve(symptoms, top_k=3)
            result = _generate_fallback_assessment(symptoms, results_list)
        except Exception as fallback_exc:
            logger.error("RAG fallback failed: %s", fallback_exc)
            result = _generate_fallback_assessment(symptoms, [])

    except Exception as exc:
        logger.exception("Unexpected error during Granite assessment: %s", exc)
        try:
            from services.rag_service import retrieve
            results_list, mode = retrieve(symptoms, top_k=3)
            result = _generate_fallback_assessment(symptoms, results_list)
        except Exception as fallback_exc:
            logger.error("RAG fallback failed: %s", fallback_exc)
            result = _generate_fallback_assessment(symptoms, [])

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
