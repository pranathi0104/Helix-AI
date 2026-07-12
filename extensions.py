"""
extensions.py — Shared Flask extension instances.

Create extension objects here (without binding them to an app) so
that models and routes can import them without circular imports.
The actual app binding happens in app.py via init_app().
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

# SQLAlchemy ORM — the single source of truth for all database operations
db = SQLAlchemy()

# Flask-Login — manages user sessions
login_manager = LoginManager()
login_manager.login_view = "auth.login"          # Redirect unauthenticated users here
login_manager.login_message = "Please log in to access Helix AI."
login_manager.login_message_category = "warning"

# Flask-Bcrypt — password hashing
bcrypt = Bcrypt()

# Flask-Migrate — Alembic database migration support
migrate = Migrate()
