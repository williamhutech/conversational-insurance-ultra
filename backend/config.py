"""
Backend Configuration Module

Type-safe configuration management using Pydantic Settings.
Loads environment variables from .env file and validates them.

Usage:
    from backend.config import settings

    # Access configuration
    db_url = settings.supabase_url
    api_key = settings.anthropic_api_key
"""

from pathlib import Path
from typing import List, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get project root directory (assuming config.py is in backend/)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are type-validated and required unless given defaults.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # -----------------------------------------------------------------------------
    # Application Settings
    # -----------------------------------------------------------------------------
    app_name: str = "Conversational Insurance Ultra"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Backend API
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_reload: bool = True

    # MCP Server
    mcp_server_name: str = "insurance-ultra-mcp"
    mcp_server_version: str = "0.1.0"

    # -----------------------------------------------------------------------------
    # Database: Supabase (Postgres + pgvector)
    # -----------------------------------------------------------------------------
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon/public key")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    supabase_db_url: str = Field(..., description="Direct Postgres connection string")

    # -----------------------------------------------------------------------------
    # Database: Neo4j (Graph Database)
    # -----------------------------------------------------------------------------
    neo4j_policy_uri: str = Field(..., description="Neo4j connection URI")
    neo4j_policy_username: str = "neo4j"
    neo4j_policy_password: str = Field(..., description="Neo4j password")
    neo4j_policy_database: str = "neo4j"

    # -----------------------------------------------------------------------------
    # Database: DynamoDB (Payment Records)
    # -----------------------------------------------------------------------------
    dynamodb_payments_table: str = "lea-payments-local"
    dynamodb_endpoint: str | None = "http://localhost:8000"  # None for AWS DynamoDB
    aws_region: str = "ap-southeast-1"
    aws_access_key_id: str | None = "dummy"  # For local; real creds for AWS
    aws_secret_access_key: str | None = "dummy"  # For local; real creds for AWS

    # -----------------------------------------------------------------------------
    # Memory: Mem0 (Customer Conversation Memory)
    # -----------------------------------------------------------------------------
    mem0_api_key: str = Field(..., description="Mem0 API key")
    mem0_org_id: str | None = None
    mem0_project_id: str | None = None

    # -----------------------------------------------------------------------------
    # AI Models
    # -----------------------------------------------------------------------------
    anthropic_api_key: str = Field(..., description="Anthropic Claude API key")
    openai_api_key: str | None = None
    openai_api_base_url: str = "https://api.openai.com/v1/"

    default_llm_model: str = "claude-3-5-sonnet-20241022"
    default_embedding_model: str = "text-embedding-3-small"

    # -----------------------------------------------------------------------------
    # Payment Processing: Stripe
    # -----------------------------------------------------------------------------
    stripe_secret_key: str = Field(..., description="Stripe secret key")
    stripe_publishable_key: str = Field(..., description="Stripe publishable key")
    stripe_webhook_secret: str | None = None
    stripe_currency: str = "SGD"

    # Payment Page URLs
    payment_success_url: str = "http://localhost:8085/success"
    payment_cancel_url: str = "http://localhost:8085/cancel"

    # Widget Base URL (for OpenAI Apps SDK widgets)
    widget_base_url: str = "http://localhost:8085/widgets"
    backend_api_url: str = "http://localhost:8085"

    # -----------------------------------------------------------------------------
    # OCR & Document Processing
    # -----------------------------------------------------------------------------
    tesseract_cmd: str = "/usr/bin/tesseract"
    tesseract_lang: str = "eng"

    easyocr_langs: List[str] = ["en"]
    easyocr_gpu: bool = False

    max_upload_size_mb: int = 10
    allowed_document_types: List[str] = ["pdf", "png", "jpg", "jpeg"]

    # -----------------------------------------------------------------------------
    # Security & Authentication
    # -----------------------------------------------------------------------------
    secret_key: str = Field(..., description="Secret key for JWT encoding")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True

    # -----------------------------------------------------------------------------
    # Feature Flags
    # -----------------------------------------------------------------------------
    enable_block_1: bool = True  # Policy Intelligence Engine
    enable_block_2: bool = True  # Conversational FAQ
    enable_block_3: bool = True  # Document Intelligence & Auto-Quotation
    enable_block_4: bool = True  # Purchase Execution
    enable_block_5: bool = True  # Data-Driven Recommendations

    # -----------------------------------------------------------------------------
    # External Services (Optional)
    # -----------------------------------------------------------------------------
    sentry_dsn: str | None = None
    redis_url: str | None = "redis://localhost:6379/0"

    # -----------------------------------------------------------------------------
    # Development & Testing
    # -----------------------------------------------------------------------------
    seed_database: bool = True
    load_sample_policies: bool = True
    test_mode: bool = False
    mock_payments: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string if provided as string."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator("easyocr_langs", mode="before")
    @classmethod
    def parse_easyocr_langs(cls, v):
        """Parse EasyOCR languages from JSON string if provided as string."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator("allowed_document_types", mode="before")
    @classmethod
    def parse_allowed_types(cls, v):
        """Parse allowed document types from JSON string if provided as string."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


# Global settings instance
# Import this throughout the application
settings = Settings()


# TODO: Add settings validation on startup
# TODO: Add settings logging (mask sensitive values)
# TODO: Add environment-specific overrides
# TODO: Add configuration hot-reloading for development
