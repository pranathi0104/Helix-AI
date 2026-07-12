"""
config.py — Application configuration for Helix AI.

Supports Development and Production environments.
IBM watsonx.ai / Granite credentials are activated from Milestone 2 onward.
RAG and watsonx Orchestrate credentials will be added in later milestones.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "helix-ai-dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------------------------------------------------------------------------
    # Milestone 2 — IBM watsonx.ai / Granite
    # These are read from the .env file. The app starts without them — the
    # granite_service module handles the missing-credential case gracefully.
    # ---------------------------------------------------------------------------
    IBM_API_KEY    = os.environ.get("IBM_API_KEY")
    IBM_PROJECT_ID = os.environ.get("IBM_PROJECT_ID")
    IBM_URL        = os.environ.get("IBM_URL", "https://us-south.ml.cloud.ibm.com")
    MODEL_ID       = os.environ.get("MODEL_ID", "ibm/granite-3-8b-instruct")

    # ---------------------------------------------------------------------------
    # Future Milestone 5 — RAG Knowledge Base
    # ---------------------------------------------------------------------------
    # RAG_DOCS_DIR      = os.path.join(BASE_DIR, "rag_docs")
    # RAG_INDEX_DIR     = os.path.join(BASE_DIR, "rag_docs", "index")
    # RAG_CHUNK_SIZE    = 500
    # RAG_CHUNK_OVERLAP = 50
    # RAG_TOP_K         = 3

    # ---------------------------------------------------------------------------
    # Future Milestone 6 — watsonx Orchestrate
    # ---------------------------------------------------------------------------
    ORCHESTRATE_API_KEY      = os.environ.get("ORCHESTRATE_API_KEY", "helix-orchestrate-dev-key")
    # ORCHESTRATE_INSTANCE_URL = os.environ.get("ORCHESTRATE_INSTANCE_URL")


class DevelopmentConfig(Config):
    """Development configuration — uses local SQLite database."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "database.db"),
    )


class ProductionConfig(Config):
    """Production configuration — set DATABASE_URL in environment."""

    DEBUG = False
    
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///helix_prod.db")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = _db_url


# Map name strings to config classes for app factory use
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
