"""
services/granite_service.py — IBM Granite integration for Helix AI.

Model: ibm/granite-3-1-8b-base  (IBM SkillsBuild / Edunet Foundation submission)

Architecture note
-----------------
granite-3-1-8b-base is a BASE (pre-instruction-tuned) model.  Unlike instruct
models it does not natively follow a "system / user" chat template.  The most
reliable technique for base models is few-shot prompting inside a single
plain-text prompt string — we show the model exactly one complete example of
the expected JSON output, then give it the real patient data and let it
complete the pattern.

Prompt strategy
---------------
1. ROLE statement    — tells the model it is a healthcare triage assistant that
                       returns ONLY JSON (no diagnoses, educational only).
2. SCHEMA block      — the exact JSON structure with field types and allowed
                       values, written once in plain text.
3. FEW-SHOT example  — a complete synthetic Patient / JSON pair the model can
                       mirror.  Chosen to be representative but clearly fictional.
4. REAL patient data — the actual inputs, followed by "JSON:" to signal the
                       model to start its completion immediately.

JSON schema (v2 — expanded from Milestone 2)
---------------------------------------------
{
  "summary":             string  — 1-2 sentence plain-English triage summary
  "possible_conditions": list    — educational guesses, NOT diagnoses
  "severity":            string  — "low" | "medium" | "high" | "emergency"
  "confidence":          string  — "low" | "medium" | "high"
  "red_flags":           list    — warning signs that must trigger urgent care
  "home_care":           list    — safe self-care steps for non-emergency cases
  "recommendation":      string  — primary recommended next action
  "urgent_if":           list    — conditions under which to seek immediate care
  "missing_information": list    — questions that would improve the assessment
  "emergency":           boolean — true only if symptoms are life-threatening NOW
}

Backward-compatibility
-----------------------
All fields from the original 5-key schema are still present.  The route and
template for Milestone 2 still work because the validator fills in defaults
for every field.

Error hierarchy (unchanged)
---------------------------
GraniteError
  GraniteConfigError    — missing / invalid credentials in .env
  GraniteConnectionError — network or IBM Cloud unreachable
  GraniteResponseError  — model returned unparseable / invalid JSON

Future milestones
-----------------
  - RAG context injection  (Milestone 5)
  - Multi-turn chat        (Milestone 6)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------

class GraniteError(Exception):
    """Base class for all Granite service errors."""


class GraniteConfigError(GraniteError):
    """Raised when IBM credentials are missing or structurally invalid."""


class GraniteConnectionError(GraniteError):
    """Raised when the IBM watsonx.ai endpoint cannot be reached."""


class GraniteResponseError(GraniteError):
    """Raised when Granite returns a response that cannot be parsed."""


# ---------------------------------------------------------------------------
# Valid field values
# ---------------------------------------------------------------------------

VALID_SEVERITIES   = {"low", "medium", "moderate", "high", "emergency", "unknown"}
VALID_CONFIDENCES  = {"low", "medium", "high", "unknown"}


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

# The few-shot example is written as realistic but clearly fictional data.
# It is short enough not to waste tokens but complete enough to show the model
# exactly what format we expect.
_FEW_SHOT_EXAMPLE = """\
=== EXAMPLE ===
Patient: Age 34, Female. Existing conditions: None.
Symptoms: Mild headache for 2 days, slightly runny nose, low-grade temperature of 37.4 C, feeling tired.

JSON:
{
  "summary": "The patient presents with mild upper-respiratory symptoms consistent with a common viral illness. There is no indication of emergency at this time.",
  "possible_conditions": ["Common cold", "Viral upper respiratory infection", "Mild influenza"],
  "severity": "low",
  "confidence": "medium",
  "red_flags": ["High fever above 39 C", "Difficulty breathing", "Severe headache or stiff neck"],
  "home_care": ["Rest adequately", "Stay well hydrated", "Use paracetamol or ibuprofen for fever and headache as directed", "Honey and warm fluids may ease throat discomfort"],
  "recommendation": "Self-care at home. Consult a GP if symptoms worsen or persist beyond 7 days.",
  "urgent_if": ["Temperature rises above 39 C", "Difficulty breathing develops", "Rash appears", "Confusion or extreme weakness occurs"],
  "missing_information": ["Has the patient been in contact with anyone diagnosed with flu recently?", "Any recent travel?"],
  "emergency": false
}
=== END EXAMPLE ==="""


def _build_prompt(symptoms: str, age: str, gender: str, conditions: str) -> str:
    """
    Build the complete single-string prompt for granite-3-1-8b-base.

    The prompt uses few-shot completion style: role + schema + example +
    real patient data + "JSON:" to cue the model's completion.
    """

    # ── Role and rules ──────────────────────────────────────────────────────
    role_block = (
        "You are a healthcare triage assistant for Helix AI.\n"
        "Your purpose is to provide EDUCATIONAL HEALTH GUIDANCE ONLY.\n"
        "You MUST NOT claim to diagnose any disease.\n"
        "You MUST return ONLY a single valid JSON object.\n"
        "Do NOT include markdown, code fences, or any text outside the JSON.\n"
        "Do NOT add explanations before or after the JSON object.\n"
        "If information is insufficient, still return the JSON with safe defaults.\n"
    )

    # ── Schema description ──────────────────────────────────────────────────
    schema_block = (
        "Return JSON with EXACTLY these keys:\n"
        '  "summary"             : string  — 1-2 sentence plain-English educational triage summary\n'
        '  "possible_conditions" : array   — educational guesses only, NOT diagnoses\n'
        '  "severity"            : string  — one of: "low", "medium", "high", "emergency"\n'
        '  "confidence"          : string  — one of: "low", "medium", "high"\n'
        '  "red_flags"           : array   — specific warning signs that require urgent care\n'
        '  "home_care"           : array   — safe self-care steps for non-emergency situations\n'
        '  "recommendation"      : string  — the single most important next action\n'
        '  "urgent_if"           : array   — specific conditions under which to seek immediate care\n'
        '  "missing_information" : array   — questions whose answers would improve this assessment\n'
        '  "emergency"           : boolean — true ONLY if symptoms suggest immediate life threat\n'
    )

    # ── Real patient data ────────────────────────────────────────────────────
    patient_block = (
        "=== PATIENT ===\n"
        f"Patient: Age {age or 'unknown'}, {gender or 'gender not specified'}. "
        f"Existing conditions: {conditions or 'None reported'}.\n"
        f"Symptoms: {symptoms.strip()}\n\n"
        "JSON:"
    )

    return (
        role_block + "\n"
        + schema_block + "\n"
        + _FEW_SHOT_EXAMPLE + "\n\n"
        + patient_block
    )


# ---------------------------------------------------------------------------
# IBM SDK client factory
# ---------------------------------------------------------------------------

def get_client():
    """
    Create and return an IBM watsonx.ai ModelInference instance.

    Reads credentials from Flask's current_app.config (populated from .env).
    Uses GREEDY decoding for deterministic, structured JSON output.

    Returns:
        ibm_watsonx_ai.foundation_models.ModelInference

    Raises:
        GraniteConfigError     — credentials missing or SDK import fails
        GraniteConnectionError — IBM Cloud unreachable or credentials rejected
    """
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
    except ImportError as exc:
        raise GraniteConfigError(
            "The ibm-watsonx-ai SDK is not installed. Run: pip install ibm-watsonx-ai"
        ) from exc

    from flask import current_app
    api_key    = current_app.config.get("IBM_API_KEY")
    project_id = current_app.config.get("IBM_PROJECT_ID")
    url        = current_app.config.get("IBM_URL", "https://us-south.ml.cloud.ibm.com")
    model_id   = current_app.config.get("MODEL_ID", "ibm/granite-3-1-8b-base")

    missing = [k for k, v in {"IBM_API_KEY": api_key, "IBM_PROJECT_ID": project_id}.items() if not v]
    if missing:
        raise GraniteConfigError(
            f"Missing IBM credentials in .env: {', '.join(missing)}. "
            "Add them to your .env file and restart the application."
        )

    try:
        credentials = Credentials(url=url, api_key=api_key)
        model = ModelInference(
            model_id   = model_id,
            credentials= credentials,
            project_id = project_id,
            params={
                # Greedy decoding gives deterministic, reproducible output —
                # important for structured JSON generation on a base model.
                "decoding_method":  DecodingMethods.GREEDY,
                # 700 tokens is enough for the full expanded schema.
                "max_new_tokens":   700,
                
            },
        )
        return model

    except Exception as exc:
        err_str = str(exc).lower()
        if any(kw in err_str for kw in ("unauthorized", "403", "401",
                                         "invalid api key", "invalid project",
                                         "forbidden")):
            raise GraniteConfigError(
                "IBM rejected the provided credentials. "
                "Check IBM_API_KEY and IBM_PROJECT_ID in your .env file."
            ) from exc
        raise GraniteConnectionError(
            f"Could not connect to IBM watsonx.ai ({url}). "
            "Check your network connection and IBM_URL."
        ) from exc


# ---------------------------------------------------------------------------
# JSON extraction — hardened multi-strategy parser
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> dict:
    """
    Extract and parse the first valid JSON object from a Granite response.

    Tries five strategies in order from strictest to most lenient so that
    any well-formed JSON embedded in the response is reliably recovered.

    Strategy 1 — direct parse of the stripped string.
    Strategy 2 — strip markdown fences (``` or ```json) then parse.
    Strategy 3 — take the substring from the first '{' to the last '}'.
    Strategy 4 — regex: find the outermost balanced brace block.
    Strategy 5 — take everything from 'JSON:' or 'JSON :' to end-of-string.

    Args:
        raw: The raw generated_text string from the IBM SDK.

    Returns:
        Parsed dict.

    Raises:
        GraniteResponseError — all five strategies failed.
    """
    if not raw or not raw.strip():
        raise GraniteResponseError("IBM Granite returned an empty response.")

    text = raw.strip()

    # Strategy 1 — raw string is already valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — strip markdown code fences
    no_fences = re.sub(r"```(?:json)?[ \t]*\r?\n?", "", text, flags=re.IGNORECASE)
    no_fences = re.sub(r"```[ \t]*$", "", no_fences, flags=re.MULTILINE).strip()
    try:
        return json.loads(no_fences)
    except json.JSONDecodeError:
        pass

    # Strategy 3 — slice from first '{' to last '}'
    first_brace = text.find("{")
    last_brace  = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Strategy 4 — regex: match a top-level JSON object (handles nested braces)
    # Walk the string counting brace depth to find the complete object.
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    # Keep scanning — there might be another object later
                    start = None

    # Strategy 5 — look for everything after a "JSON:" cue line
    json_cue = re.search(r"JSON\s*:\s*(\{[\s\S]*)", text, re.IGNORECASE)
    if json_cue:
        candidate = json_cue.group(1).strip()
        # Trim to the matching closing brace
        depth = 0
        end_idx = None
        for i, ch in enumerate(candidate):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        if end_idx is not None:
            try:
                return json.loads(candidate[: end_idx + 1])
            except json.JSONDecodeError:
                pass

    logger.error("All JSON extraction strategies failed. Raw response:\n%s", raw)
    raise GraniteResponseError(
        "IBM Granite did not return parseable JSON. "
        "The raw response has been logged. Please try again."
    )


# ---------------------------------------------------------------------------
# Schema validator — maps raw parsed dict → clean, type-safe result dict
# ---------------------------------------------------------------------------

def _validate_assessment(data: dict) -> dict:
    """
    Normalise a parsed dict against the expanded v2 schema.

    Every field that is missing or has the wrong type is replaced with a
    safe default so the template never raises a KeyError or AttributeError.

    Args:
        data: The dict returned by _extract_json().

    Returns:
        A clean dict guaranteed to contain all ten schema keys.
    """

    def _coerce_list(value: Any, default: list | None = None) -> list:
        """Return value as a list, coercing strings and None to list form."""
        if default is None:
            default = []
        if value is None:
            return default
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return default

    def _coerce_str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        s = str(value).strip()
        return s if s else default

    # ── summary ─────────────────────────────────────────────────────────────
    result: dict[str, Any] = {}
    result["summary"] = _coerce_str(
        data.get("summary"),
        "Educational triage assessment generated by IBM Granite. "
        "Please consult a healthcare professional for medical advice."
    )

    # ── possible_conditions ──────────────────────────────────────────────────
    result["possible_conditions"] = _coerce_list(data.get("possible_conditions"))

    # ── severity ────────────────────────────────────────────────────────────
    sev = _coerce_str(data.get("severity"), "unknown").lower()
    result["severity"] = sev if sev in VALID_SEVERITIES else "unknown"

    # ── confidence ──────────────────────────────────────────────────────────
    conf = _coerce_str(data.get("confidence"), "medium").lower()
    result["confidence"] = conf if conf in VALID_CONFIDENCES else "medium"

    # ── red_flags ────────────────────────────────────────────────────────────
    result["red_flags"] = _coerce_list(data.get("red_flags"))

    # ── home_care ────────────────────────────────────────────────────────────
    result["home_care"] = _coerce_list(data.get("home_care"))

    # ── recommendation ───────────────────────────────────────────────────────
    result["recommendation"] = _coerce_str(
        data.get("recommendation"),
        "Please consult a qualified healthcare professional."
    )

    # ── urgent_if ────────────────────────────────────────────────────────────
    result["urgent_if"] = _coerce_list(data.get("urgent_if"))

    # ── missing_information ──────────────────────────────────────────────────
    result["missing_information"] = _coerce_list(data.get("missing_information"))

    # ── emergency ────────────────────────────────────────────────────────────
    emerg = data.get("emergency", False)
    # Accept boolean True, string "true", integer 1
    if isinstance(emerg, bool):
        result["emergency"] = emerg
    elif isinstance(emerg, str):
        result["emergency"] = emerg.strip().lower() in ("true", "yes", "1")
    elif isinstance(emerg, int):
        result["emergency"] = emerg != 0
    else:
        result["emergency"] = False

    # Auto-escalate: if severity is "emergency" but flag was missed, set it
    if result["severity"] == "emergency":
        result["emergency"] = True

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_assessment(
    symptoms: str,
    age: str = "",
    gender: str = "",
    conditions: str = "",
) -> dict:
    """
    Run a structured symptom assessment through IBM watsonx.ai Chat API.

    The AI provides educational triage guidance only.
    It does not provide a medical diagnosis.
    """

    model = get_client()

    system_message = (
        "You are the symptom triage assistant for Helix AI. "
        "Provide educational health guidance only. "
        "You must not claim to diagnose a disease. "
        "Return exactly one valid JSON object and nothing else. "
        "Do not use markdown or code fences. "
        "Do not include explanations outside the JSON."
    )

    user_message = f"""
    Assess the following patient symptoms for educational triage guidance.

    PATIENT INFORMATION:
    Age: {age or "Unknown"}
    Gender: {gender or "Not specified"}
    Existing conditions: {conditions or "None reported"}
    Symptoms: {symptoms.strip()}

    Return a JSON object with EXACTLY these keys:

    {{
    "summary": "1-2 sentence educational triage summary",
    "possible_conditions": ["educational possibilities only"],
    "severity": "low | medium | high | emergency",
    "confidence": "low | medium | high",
    "red_flags": ["warning signs requiring urgent care"],
    "home_care": ["safe self-care guidance"],
    "recommendation": "single most important next action",
    "urgent_if": ["specific reasons to seek immediate care"],
    "missing_information": ["questions that would improve assessment"],
    "emergency": false
    }}

    STRICT RULES:
    - Return JSON only.
    - Use valid double-quoted JSON.
    - Do not diagnose.
    - possible_conditions are educational possibilities, not confirmed conditions.
    - Do not prescribe prescription medication.
    - Do not invent patient information.
    - Set emergency to true only when the provided symptoms suggest an immediate life-threatening situation.
    - severity must be low, medium, high, or emergency.
    - confidence must be low, medium, or high.
    """

    logger.info(
        "Sending symptom assessment to watsonx.ai chat API | symptoms_len=%d",
        len(symptoms),
    )

    try:
        response = model.chat(
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            params={
                "max_tokens": 700,
                "temperature": 0.1,
            },
        )

        raw_text = response["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        logger.error(
            "Unexpected watsonx.ai chat response structure: %r",
            response if "response" in locals() else None,
        )

        raise GraniteResponseError(
            "watsonx.ai returned an unexpected assessment response structure."
        ) from exc

    except Exception:
        logger.error(
            "watsonx.ai symptom assessment failed",
            exc_info=True,
        )
        raise

    if not raw_text or not raw_text.strip():
        raise GraniteResponseError(
            "watsonx.ai returned an empty symptom assessment."
        )

    logger.debug(
        "Assessment raw response:\n%s",
        raw_text,
    )

    parsed = _extract_json(raw_text)
    result = _validate_assessment(parsed)

    logger.info(
        "Assessment complete | severity=%s | emergency=%s | conditions=%d",
        result["severity"],
        result["emergency"],
        len(result["possible_conditions"]),
    )

    return result

def generate_report_narration(snapshot: dict) -> str:
    """
    Generate a concise AI narration of an existing deterministic
    Helix AI health report snapshot.

    The AI explains existing results only.
    It must not diagnose, recalculate risk, or prescribe treatment.
    """
    try:
        model = get_client()
    except Exception as exc:
        logger.error("Failed to get AI model client: %s", exc)
        raise

    clean_snapshot = {
        key: value
        for key, value in snapshot.items()
        if key != "ai_narration"
    }

    snapshot_json = json.dumps(
        clean_snapshot,
        indent=2,
        ensure_ascii=False
    )

    system_message = (
        "You are the AI Health Report Narrator for Helix AI. "
        "You explain an already-generated deterministic health report. "
        "You do not diagnose diseases. "
        "You do not calculate or change risk scores. "
        "You do not prescribe medication or change medication doses. "
        "You do not invent facts that are absent from the report. "
        "Use a professional, neutral, concise healthcare tone."
    )

    user_message = f"""
    Review the patient report snapshot below and write the final patient-facing
    health narration.

    STRICT OUTPUT RULES:
    - Return narrative text only.
    - Write exactly 2 or 3 short paragraphs.
    - Maximum 180 words total.
    - Do not use headings, bullet points, markdown, or labels.
    - Do not mention these instructions.
    - Do not say "revised narration", "requirements", or discuss paragraph count.
    - Do not repeat the same advice or conclusion.
    - Explain only the existing vitals, trends, risk classification, and provided recommendations.
    - If previous abnormal readings improved, state that clearly but do not claim the underlying issue is cured.
    - End with one concise monitoring or follow-up sentence.
    - Never add a diagnosis.

    PATIENT REPORT SNAPSHOT:
    {snapshot_json}
    """

    logger.info("Generating report narration using watsonx.ai chat API")

    try:
        response = model.chat(
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            params={
                "max_tokens": 300,
                "temperature": 0.2,
            },
        )

        text = response["choices"][0]["message"]["content"]

        if not text or not text.strip():
            raise GraniteResponseError(
                "watsonx.ai returned an empty report narration."
            )

        narration = text.strip()

        # Defensive cleanup for unwanted model meta-commentary.
        forbidden_phrases = (
            "revised narration",
            "paragraphs have been removed",
            "to meet the requirements",
            "paragraph count",
        )

        lowered = narration.lower()

        if any(phrase in lowered for phrase in forbidden_phrases):
            raise GraniteResponseError(
                "AI narration contained unwanted meta-commentary."
            )

        logger.info(
            "AI report narration generated successfully | chars=%d",
            len(narration),
        )

        return narration

    except GraniteResponseError:
        raise

    except Exception as exc:
        logger.error(
            "AI narration generation failed",
            exc_info=True,
        )
        raise


def generate_rag_answer(query: str, context: str) -> str:
    """Generate a grounded answer based on the provided RAG context."""
    query_lower = query.lower()
    diagnosis_triggers = [
        "what disease do i have",
        "diagnose me",
        "what condition do i have",
        "what illness is this"
    ]
    if any(trigger in query_lower for trigger in diagnosis_triggers):
        return "I cannot determine a diagnosis from symptoms alone. Chest pain and difficulty breathing can be potentially serious symptoms. Please seek urgent medical evaluation or emergency care. A qualified healthcare professional must assess the cause and provide appropriate treatment."

    try:
        model = get_client()
    except Exception as exc:
        logger.error("Failed to get AI model client for RAG: %s", exc)
        raise

    system_message = (
        "You are the Helix AI Knowledge Base Medical Assistant. "
        "Your task is to provide information about the user's query/topic using ONLY the provided context snippets. "
        "Do not use outside knowledge. "
        "If the user asks for a diagnosis based on symptoms: refuse to diagnose or guess the disease, do not name or speculate about a specific possible disease, state that a qualified healthcare professional must determine the cause, state that symptoms may be potentially serious when appropriate, and recommend urgent medical evaluation/emergency care for severe symptoms such as chest pain or difficulty breathing. "
        "If the context does not contain the answer to a general educational question, say 'I cannot answer this based on the available knowledge base.' "
        "Provide educational information only. Do not diagnose the user. Do not prescribe medication. "
        "IMPORTANT: Answer directly and naturally. Do not use phrases like 'According to the provided context snippets', 'Based on the provided context', or 'The context states'."
    )

    user_message = f"Context:\n{context}\n\nQuery/Topic: {query}"

    logger.info("Generating RAG answer using watsonx.ai chat API")

    try:
        response = model.chat(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            params={
                "max_tokens": 500,
                "temperature": 0.1,
            },
        )

        text = response["choices"][0]["message"]["content"]
        if not text or not text.strip():
            return "I cannot determine a diagnosis from symptoms alone. Chest pain and difficulty breathing can be potentially serious symptoms. Please seek urgent medical evaluation or emergency care. A qualified healthcare professional must assess the cause and provide appropriate treatment."

        return text.strip()
    except GraniteResponseError:
        raise
    except Exception as exc:
        logger.error("RAG generation failed", exc_info=True)
        raise

