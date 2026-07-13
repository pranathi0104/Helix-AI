"""
routes/chat.py — Secure Chat API connecting the authenticated user to watsonx Orchestrate.

This module provides endpoints for sending messages to the Orchestrate supervisor agent,
maintaining thread state, and clearing conversations.
"""

import os
import time
import requests
from flask import Blueprint, request, jsonify, session, current_app, render_template
from flask_login import login_required, current_user

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/", methods=["GET"])
@login_required
def chat_index():
    """Render the main chat interface."""
    return render_template("chat/index.html")

SUPERVISOR_AGENT_ID = "4aa624fa-6458-4ab8-8fd0-6a19075a6fd2"

def get_iam_token(api_key: str) -> str:
    """Exchange IBM Cloud API key for an IAM access token."""
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
    response = requests.post(url, headers=headers, data=data, timeout=10)
    response.raise_for_status()
    
    token = response.json().get("access_token")
    if not token:
        raise ValueError("IBM IAM response did not contain an access_token.")
    return token

@chat_bp.route("/message", methods=["POST"])
@login_required
def chat_message():
    """
    Send a message to the Orchestrate supervisor agent.
    Synchronously polls until the flow is complete.
    """
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing message content."}), 400
        
    raw_message = data["message"]
    if not isinstance(raw_message, str):
        return jsonify({"error": "Message must be a string."}), 400
        
    user_message = raw_message.strip()
    
    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400
        
    if len(user_message) > 4000:
        return jsonify({"error": "Message exceeds the maximum length of 4000 characters."}), 400

    # Deterministic diagnosis-intent intercept
    user_message_lower = user_message.lower()
    diagnosis_triggers = [
        "what disease do i have",
        "diagnose me",
        "what condition do i have",
        "what illness is this"
    ]
    
    is_diagnosis_request = False
    is_severe = False
    orchestrate_message = user_message

    if any(trigger in user_message_lower for trigger in diagnosis_triggers):
        is_diagnosis_request = True
        severe_symptoms = [
            "chest pain",
            "difficulty breathing",
            "shortness of breath",
            "loss of consciousness",
            "unconscious",
            "severe bleeding",
            "sudden weakness",
            "sudden numbness",
            "facial drooping",
            "difficulty speaking",
            "severe sudden headache",
            "seizure"
        ]
        if any(symptom in user_message_lower for symptom in severe_symptoms):
            is_severe = True
            
        orchestrate_message = f"Answer the user's symptom concern directly. Name relevant possible causes and conditions using uncertainty language. Provide concise safe guidance, identify warning signs, and recommend appropriate medical evaluation. Never claim a definitive diagnosis.\n\nUser concern: {user_message}"
        if is_severe:
            orchestrate_message += "\n\nSYSTEM NOTE: Severe symptom detected. Enforce emergency protocol: prioritize immediate emergency action, advise assisted transport or emergency services, and do not ask follow-up questions."

    ibm_api_key = current_app.config.get("IBM_API_KEY") or os.environ.get("IBM_API_KEY")
    orchestrate_url = os.environ.get("ORCHESTRATE_INSTANCE_URL")
    
    if not ibm_api_key or not orchestrate_url:
        current_app.logger.error("Missing IBM_API_KEY or ORCHESTRATE_INSTANCE_URL in environment/config.")
        return jsonify({"error": "Internal server configuration error."}), 500
        
    orchestrate_url = orchestrate_url.rstrip("/")
    
    try:
        iam_token = get_iam_token(ibm_api_key)
        
        headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": {
                "role": "user",
                "content": orchestrate_message
            },
            "capture_logs": False,
            "agent_id": SUPERVISOR_AGENT_ID,
            "context": {
                # Security constraint: Force patient_user_id to current authenticated user
                "patient_user_id": current_user.id
            }
        }
        
        # Continuation of an existing thread
        thread_id = session.get("orchestrate_thread_id")
        thread_user_id = session.get("orchestrate_thread_user_id")
        
        # Verify thread ownership
        if thread_id:
            if thread_user_id != current_user.id:
                # Clear invalid thread association
                session.pop("orchestrate_thread_id", None)
                session.pop("orchestrate_thread_user_id", None)
                session.modified = True
                thread_id = None
            else:
                payload["thread_id"] = thread_id
            
        # 1. Create Run
        run_endpoint = f"{orchestrate_url}/v1/orchestrate/runs"
        create_res = requests.post(run_endpoint, headers=headers, json=payload, timeout=10)
        create_res.raise_for_status()
        
        create_data = create_res.json()
        run_id = create_data.get("run_id")
        new_thread_id = create_data.get("thread_id")
        
        if not run_id or not new_thread_id:
            current_app.logger.error("Orchestrate run creation failed: Missing run_id or thread_id.")
            return jsonify({"error": "Internal error connecting to orchestration layer."}), 500
            
        # Save thread_id for subsequent requests
        if not thread_id:
            session["orchestrate_thread_id"] = new_thread_id
            session["orchestrate_thread_user_id"] = current_user.id
            thread_id = new_thread_id
            session.modified = True
            
        # 2. Poll for Completion
        poll_endpoint = f"{orchestrate_url}/v1/orchestrate/runs/{run_id}"
        status = "in_progress"
        start_time = time.time()
        timeout = 120
        
        while status not in ["completed", "failed", "cancelled"]:
            if time.time() - start_time > timeout:
                current_app.logger.error(f"Orchestrate run {run_id} timed out after {timeout} seconds.")
                return jsonify({"error": "The request timed out. Please try again."}), 504
                
            time.sleep(2)
            poll_res = requests.get(poll_endpoint, headers=headers, timeout=10)
            poll_res.raise_for_status()
            status = poll_res.json().get("status", "").lower()
            
        if status != "completed":
            current_app.logger.error(f"Orchestrate run {run_id} ended with status: {status}")
            return jsonify({"error": "The agent was unable to complete the request."}), 500
            
        # 3. Fetch final assistant message
        messages_endpoint = f"{orchestrate_url}/v1/orchestrate/threads/{thread_id}/messages"
        msg_res = requests.get(messages_endpoint, headers=headers, timeout=10)
        msg_res.raise_for_status()
        
        messages_json = msg_res.json()
        messages_array = messages_json.get("data", []) if isinstance(messages_json, dict) and "data" in messages_json else messages_json
        
        final_message_text = "I'm sorry, I could not generate a response."
        if isinstance(messages_array, list):
            assistant_msgs = [m for m in messages_array if isinstance(m, dict) and m.get("role") == "assistant"]
            if assistant_msgs:
                content = assistant_msgs[-1].get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(part["text"])
                    final_message_text = "\n".join(text_parts)
                else:
                    final_message_text = content
                    
        # Sanitize raw internal tool API errors from assistant
        error_patterns = [
            "error details:",
            "response_text",
            "failed to execute open api tool",
            "error calling the tool",
            "status_code",
            "error making request"
        ]
        if any(pattern in final_message_text.lower() for pattern in error_patterns):
            current_app.logger.warning("Internal tool error detected in Orchestrate response. Returning safe fallback message.")
            final_message_text = "I’m unable to retrieve your health information right now. Please try again shortly."
                    

        return jsonify({
            "message": final_message_text
        }), 200
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"External API Request Exception in chat_message: {e}")
        return jsonify({"error": "An error occurred while communicating with the orchestration service."}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected Exception in chat_message: {e}")
        return jsonify({"error": "An unexpected server error occurred."}), 500


@chat_bp.route("/clear", methods=["POST"])
@login_required
def chat_clear():
    """
    Clear the current Orchestrate conversation thread from the session.
    """
    session.pop("orchestrate_thread_id", None)
    session.pop("orchestrate_thread_user_id", None)
    session.modified = True
    return jsonify({"status": "success", "message": "Conversation thread cleared."}), 200
