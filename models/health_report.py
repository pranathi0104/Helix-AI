"""
models/health_report.py — Stores historical health reports.
"""

from datetime import datetime
from extensions import db
import json

class HealthReport(db.Model):
    __tablename__ = "health_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    risk_classification = db.Column(db.String(50), nullable=False)
    
    # Store a structured JSON snapshot of the report data
    snapshot_data = db.Column(db.Text, nullable=False)
    
    @property
    def parsed_snapshot(self) -> dict:
        return json.loads(self.snapshot_data) if self.snapshot_data else {}
        
    def __repr__(self) -> str:
        return f"<HealthReport {self.id} for user {self.user_id}>"
