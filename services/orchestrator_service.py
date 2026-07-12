"""
services/orchestrator_service.py — watsonx Orchestrate multi-agent coordinator (Milestone 6).

This service connects to IBM watsonx Orchestrate and routes conversational
messages from the AI Health Companion to the correct specialist agent.

Agent skills that will be registered in Orchestrate:
    assess_symptoms       → symptom_agent.py
    check_emergency       → symptom_agent.py (emergency path)
    analyse_vitals        → chronic_disease_agent.py
    predict_risk          → risk_prediction_agent.py
    check_medications     → medication_agent.py
    get_lifestyle_advice  → lifestyle_agent.py
    retrieve_health_info  → rag_agent.py
    generate_report       → report_agent.py

TODO (Milestone 6):
    1. Implement connect() to authenticate with the Orchestrate API using
       ORCHESTRATE_API_KEY and ORCHESTRATE_INSTANCE_URL from .env.
    2. Implement register_skills() to declare each agent function as a
       named skill in the Orchestrate skill registry.
    3. Implement dispatch() to send a user message + session context to
       Orchestrate, receive the classified intent, invoke the correct agent
       skill, and return the structured result.
    4. Implement fallback() to call granite_service.call_granite() directly
       with a generic healthcare system prompt if Orchestrate is unreachable.
    5. Document the Orchestrate skill registration steps in README.md under
       "Milestone 6 — Orchestrate Configuration".

Environment variables required (.env):
    ORCHESTRATE_API_KEY       — watsonx Orchestrate API key
    ORCHESTRATE_INSTANCE_URL  — e.g. https://api.us-south.assistant.watson.cloud.ibm.com
"""


def dispatch(message: str, session_context: dict) -> dict:
    """
    TODO (Milestone 6): Route a user message to the correct specialist agent via Orchestrate.

    Args:
        message:         The user's natural-language input.
        session_context: Dict containing user profile, conditions, and conversation history.

    Returns:
        Dict with keys: agent_used, response_text, rag_references.
    """
    # TODO: Implement in Milestone 6
    raise NotImplementedError("Orchestrate dispatch will be implemented in Milestone 6.")


def fallback(message: str, session_context: dict) -> dict:
    """
    TODO (Milestone 6): Direct Granite fallback when Orchestrate is unavailable.

    Returns:
        Dict with keys: agent_used, response_text, rag_references.
    """
    # TODO: Implement in Milestone 6
    raise NotImplementedError("Orchestrate fallback will be implemented in Milestone 6.")
