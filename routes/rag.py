"""
routes/rag.py — Knowledge Base blueprint.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import logging

from services.rag_service import retrieve, build_index, is_index_built, format_context
from services.granite_service import generate_rag_answer

logger = logging.getLogger(__name__)

rag_bp = Blueprint("rag", __name__)

@rag_bp.route("/")
@login_required
def index():
    """Main Knowledge Base search page."""
    # Build index on first visit if not built
    if not is_index_built():
        build_index()
        
    query = request.args.get("q", "")
    results = []
    answer = None
    error = None
    
    import re
    if query:
        raw_results, mode = retrieve(query, top_k=5)
        # Apply threshold only for semantic mode; fallback relies on strict topic filtering
        if mode == "semantic":
            results = [r for r in raw_results if r.get('relevance_score', 0) >= 0.65]
        else:
            results = raw_results
        
        if results:
            context = format_context(results)
            try:
                answer = generate_rag_answer(query, context)
            except Exception as e:
                logger.error("Granite generation failed: %s", e)
                answer_parts = []
                
                # Extract first sentence as explanation from the top chunk
                top_chunk = results[0]
                text = top_chunk.get("text", "")
                title = top_chunk.get("title", "this topic")
                
                first_sentence = text.split(". ")[0].strip()
                if first_sentence:
                    answer_parts.append(f"Regarding {title}: {first_sentence}.")
                else:
                    answer_parts.append(f"Educational information regarding {title} has been retrieved.")
                
                has_symptoms = any("symptom" in r.get("text", "").lower() or "sign" in r.get("text", "").lower() for r in results)
                has_risks = any("risk" in r.get("text", "").lower() or "complication" in r.get("text", "").lower() for r in results)
                has_care = any("treatment" in r.get("text", "").lower() or "care" in r.get("text", "").lower() or "prevent" in r.get("text", "").lower() for r in results)
                
                if has_symptoms:
                    answer_parts.append("The retrieved documents describe specific symptoms and signs to monitor.")
                if has_risks:
                    answer_parts.append("They also outline potential risks, complications, or emergency indicators.")
                if has_care:
                    answer_parts.append("Guidance on prevention, home care, or medical treatment is provided.")
                    
                answer_parts.append("Please review the complete excerpts below for detailed clinical information. Always consult a qualified healthcare professional for an accurate diagnosis.")
                
                answer = " ".join(answer_parts)
        else:
            answer = "This topic is not currently covered by the Helix Knowledge Base."
            
    return render_template(
        "rag/index.html",
        title="Knowledge Base",
        query=query,
        results=results,
        answer=answer,
        error=error
    )

@rag_bp.route("/api/search")
@login_required
def api_search():
    """API endpoint for Knowledge Base search."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"results": []})
        
    results, mode = retrieve(query, top_k=5)
    return jsonify({"results": results})
