"""
routes/reports.py
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models.health_report import HealthReport
from services.report_service import create_report

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/")
@login_required
def index():
    reports = HealthReport.query.filter_by(user_id=current_user.id).order_by(HealthReport.generated_at.desc()).all()
    return render_template("reports/index.html", reports=reports)

@reports_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    try:
        report = create_report(current_user.id)
        flash("Health Report generated successfully.", "success")
        return redirect(url_for("reports.view", report_id=report.id))
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        return redirect(url_for("reports.index"))

@reports_bp.route("/<int:report_id>")
@login_required
def view(report_id):
    report = HealthReport.query.get_or_404(report_id)
    if report.user_id != current_user.id:
        from flask import abort
        abort(403)
        
    data = report.parsed_snapshot
    return render_template("reports/view.html", report=report, data=data)
