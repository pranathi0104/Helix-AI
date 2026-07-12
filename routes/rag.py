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
        raw_results = retrieve(query, top_k=5)
        # Apply a threshold to avoid weak unrelated results
        results = [r for r in raw_results if r.get('relevance_score', 0) >= 0.65]
        
        if results:
            context = format_context(results)
            try:
                answer = generate_rag_answer(query, context)
            except Exception as e:
                logger.error("Granite generation failed: %s", e)
                error = "We're currently experiencing issues generating an AI summary. Please review the relevant sources below."
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
        
    results = retrieve(query, top_k=5)
    return jsonify({"results": results})
