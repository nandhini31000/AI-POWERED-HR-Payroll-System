"""
config.py
----------
Central configuration for the AI HR Assistant with Payroll Management System.
All sensitive values are read from environment variables so the same code
works in development, testing, and production without code changes.
"""

import os
from datetime import timedelta
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

basedir = os.path.abspath(os.path.dirname(__file__))


def build_database_uri():
    """Build a SQLAlchemy database URI from environment variables."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    db_user = os.environ.get("DB_USER", "root")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "3306")
    db_name = os.environ.get("DB_NAME", "payroll_ai_system")

    user = quote_plus(db_user)
    password = quote_plus(db_password)
    auth = f"{user}:{password}" if db_password else user

    return f"mysql+pymysql://{auth}@{db_host}:{db_port}/{db_name}"


class Config:
    """Base configuration shared by all environments."""

    # ---------------------------------------------------------------
    # Flask core
    # ---------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

    # ---------------------------------------------------------------
    # Database (MySQL via SQLAlchemy)
    # Format: mysql+pymysql://<user>:<password>@<host>:<port>/<db_name>
    # ---------------------------------------------------------------
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "payroll_ai_system")

    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------------------------------------------------------------
    # Session / Security
    # ---------------------------------------------------------------
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # auto logout / session timeout
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True  # CSRF protection

    # ---------------------------------------------------------------
    # File uploads (employee photos, company logo)
    # ---------------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "images", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload size
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # ---------------------------------------------------------------
    # Payslip / Reports output folders
    # ---------------------------------------------------------------
    PAYSLIP_FOLDER = os.path.join(basedir, "database", "payslips")
    REPORTS_FOLDER = os.path.join(basedir, "database", "reports")

    # ---------------------------------------------------------------
    # AI / LLM Configuration (Agentic AI Assistant)
    # Supports OpenAI, Google Gemini, or OpenRouter -- configurable
    # via AI_PROVIDER without changing any code.
    # ---------------------------------------------------------------
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai")  # openai | gemini | openrouter
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-flash-latest")

    # Company info shown on payslips
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Acme Technologies Pvt. Ltd.")
    COMPANY_ADDRESS = os.environ.get("COMPANY_ADDRESS", "123 Business Park, Chennai, India")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # HTTPS only cookies in production


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
