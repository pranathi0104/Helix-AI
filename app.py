"""
app.py — Application factory for Helix AI.

Uses the factory pattern so the app can be created with different
configurations (e.g., testing vs. development vs. production) and
to avoid circular imports between extensions, models, and routes.
"""

import os
from flask import Flask
from config import config_map
from extensions import db, login_manager, bcrypt, migrate


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application instance.

    Args:
        config_name: Key from config_map ('development', 'production', 'default').

    Returns:
        A fully configured Flask application.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # -------------------------------------------------------------------------
    # Load configuration
    # -------------------------------------------------------------------------
    app.config.from_object(config_map[config_name])

    # -------------------------------------------------------------------------
    # Initialise extensions
    # -------------------------------------------------------------------------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # -------------------------------------------------------------------------
    # Register Flask-Login user loader
    # -------------------------------------------------------------------------
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # -------------------------------------------------------------------------
    # Import models so Flask-Migrate / db.create_all() can discover them
    # -------------------------------------------------------------------------
    from models import user, user_profile, vitals_log, health_timeline, medication, health_report  # noqa: F401

    # -------------------------------------------------------------------------
    # Register blueprints
    # -------------------------------------------------------------------------
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.profile import profile_bp
    from routes.modules import modules_bp
    from routes.assessment import assessment_bp
    from routes.monitoring import monitoring_bp
    from routes.treatment import treatment_bp
    from routes.rag import rag_bp
    from routes.risk import risk_bp
    from routes.lifestyle import lifestyle_bp
    from routes.reports import reports_bp
    from routes.orchestrate_api import orchestrate_api_bp
    from routes.chat import chat_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(assessment_bp)   # url_prefix="/assessment" set on blueprint
    app.register_blueprint(monitoring_bp)   # url_prefix="/monitoring"  set on blueprint
    app.register_blueprint(treatment_bp, url_prefix="/treatment")
    app.register_blueprint(rag_bp, url_prefix="/rag")
    app.register_blueprint(risk_bp, url_prefix="/risk")
    app.register_blueprint(lifestyle_bp, url_prefix="/lifestyle")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(orchestrate_api_bp, url_prefix="/api/v1/orchestrate/patient")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(modules_bp)      # catch-all placeholders — must be last

    # -------------------------------------------------------------------------
    # Create database tables on first run (development convenience)
    # -------------------------------------------------------------------------
    with app.app_context():
        db.create_all()

    # -------------------------------------------------------------------------
    # Root redirect — send visitors straight to the dashboard (or login)
    # -------------------------------------------------------------------------
    from flask import redirect, url_for

    @app.route("/")
    def index():
        return redirect(url_for("dashboard.home"))

    # -------------------------------------------------------------------------
    # Template Filters
    # -------------------------------------------------------------------------
    import zoneinfo
    
    @app.template_filter('format_ist')
    def format_ist(dt, format_string="%d %b %Y, %H:%M"):
        if not dt:
            return ""
            
        from datetime import datetime, date
        
        if isinstance(dt, str):
            original_dt = dt
            if dt.endswith('Z'):
                dt = dt[:-1] + '+00:00'
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return original_dt

        if isinstance(dt, datetime):
            # Ensure UTC timezone if naive
            if getattr(dt, 'tzinfo', None) is None:
                dt = dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
            # Convert to IST
            dt_ist = dt.astimezone(zoneinfo.ZoneInfo("Asia/Kolkata"))
            return dt_ist.strftime(format_string)
        elif isinstance(dt, date):
            # Plain date value: do not apply timezone conversion
            return dt.strftime(format_string)
        
        return str(dt)

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    env = os.environ.get("FLASK_ENV", "development")
    application = create_app(env)
    application.run(debug=(env == "development"), host="0.0.0.0", port=5000)
