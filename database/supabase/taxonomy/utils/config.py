"""
Configuration management for Supabase Taxonomy data loading.
Handles environment variables and settings for database connection,
API keys, and processing parameters.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class TaxonomyLoaderConfig(BaseSettings):
    """Configuration for taxonomy data loader with dual embeddings"""

    # Supabase Configuration
    supabase_structured_url: str = Field(
        ...,
        description="Supabase project URL (https://wjfypbbzucwmvsrkqytc.supabase.co)"
    )
    supabase_structured_service_key: str = Field(
        ...,
        description="Supabase service role key (for write access)"
    )

    # OpenAI Configuration (for embeddings)
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for embedding generation"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model to use"
    )
    embedding_dimensions: int = Field(
        default=2000,
        description="Embedding vector dimensions"
    )

    # Data Loading Configuration
    json_file_path: str = Field(
        default="database/supabase/taxonomy/output/final_value.json",
        description="Path to taxonomy JSON file"
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of records to process in each batch"
    )

    # Rate Limiting
    openai_rpm_limit: int = Field(
        default=3000,
        description="OpenAI API rate limit (requests per minute)"
    )
    openai_retry_attempts: int = Field(
        default=3,
        ge=1,
        description="Number of retry attempts for failed API calls"
    )
    openai_retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        description="Initial delay (seconds) between retries with exponential backoff"
    )

    # Processing Options
    generate_embeddings: bool = Field(
        default=True,
        description="Whether to generate embeddings (set False for dry-run)"
    )
    skip_existing: bool = Field(
        default=True,
        description="Skip records that already exist in database"
    )
    verbose: bool = Field(
        default=True,
        description="Enable detailed logging"
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Environment (development/staging/production)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("supabase_structured_url")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Ensure Supabase URL is properly formatted"""
        if not v.startswith("https://"):
            raise ValueError("Supabase URL must start with https://")
        if not v.endswith(".supabase.co"):
            # Allow custom domains, but warn
            print(f"Warning: Supabase URL does not end with .supabase.co: {v}")
        return v.rstrip("/")

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, v: int, info) -> int:
        """Validate embedding dimensions are valid for the model"""
        model = info.data.get("openai_embedding_model", "")

        # Valid dimension ranges for each model (text-embedding-3-* support shortening)
        valid_dimensions = {
            "text-embedding-3-small": (1, 1536),  # Supports 1 to 1536
            "text-embedding-3-large": (1, 3072),  # Supports 1 to 3072
            "text-embedding-ada-002": (1536, 1536),  # Only supports 1536
        }

        if model in valid_dimensions:
            min_dim, max_dim = valid_dimensions[model]
            if not (min_dim <= v <= max_dim):
                raise ValueError(
                    f"Embedding dimensions out of range: {model} supports {min_dim}-{max_dim} dimensions, got {v}"
                )

        return v

    @field_validator("json_file_path")
    @classmethod
    def validate_json_file_path(cls, v: str) -> str:
        """Check if JSON file exists"""
        if not os.path.exists(v):
            raise ValueError(f"JSON file not found: {v}")
        return v

    def get_openai_config(self) -> dict:
        """Get OpenAI client configuration"""
        return {
            "api_key": self.openai_api_key,
            "max_retries": self.openai_retry_attempts,
        }

    def get_supabase_config(self) -> dict:
        """Get Supabase client configuration"""
        return {
            "url": self.supabase_structured_url,
            "key": self.supabase_structured_service_key,
        }

    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration"""
        return {
            "rpm_limit": self.openai_rpm_limit,
            "retry_attempts": self.openai_retry_attempts,
            "retry_delay": self.openai_retry_delay,
        }


# ============================================================================
# GLOBAL CONFIGURATION INSTANCE
# ============================================================================

def load_config() -> TaxonomyLoaderConfig:
    """
    Load configuration from environment variables.

    Raises:
        ValueError: If required environment variables are missing
    """
    try:
        config = TaxonomyLoaderConfig()
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("\nRequired environment variables:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_SERVICE_KEY")
        print("  - OPENAI_API_KEY")
        print("\nOptional environment variables:")
        print("  - OPENAI_EMBEDDING_MODEL (default: text-embedding-3-large)")
        print("  - EMBEDDING_DIMENSIONS (default: 3072)")
        print("  - JSON_FILE_PATH (default: database/supabase/taxonomy/output/final_value.json)")
        print("  - BATCH_SIZE (default: 10)")
        print("  - GENERATE_EMBEDDINGS (default: true)")
        print("  - VERBOSE (default: true)")
        raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_absolute_path(relative_path: str) -> str:
    """
    Convert relative path to absolute path from project root.

    Args:
        relative_path: Path relative to project root

    Returns:
        Absolute path string
    """
    # Find project root (directory containing .env file)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = current_dir

    # Traverse up to find project root
    max_depth = 10
    for _ in range(max_depth):
        if os.path.exists(os.path.join(project_root, ".env")) or \
           os.path.exists(os.path.join(project_root, "pyproject.toml")):
            break
        parent = os.path.dirname(project_root)
        if parent == project_root:  # Reached filesystem root
            break
        project_root = parent

    return os.path.join(project_root, relative_path)


def validate_environment() -> bool:
    """
    Validate that the environment is properly configured.

    Returns:
        True if environment is valid, False otherwise
    """
    try:
        config = load_config()

        # Check Supabase connection
        print(f"✓ Supabase URL: {config.supabase_url}")

        # Check OpenAI API key
        if config.openai_api_key.startswith("sk-"):
            print(f"✓ OpenAI API key configured")
        else:
            print("⚠ Warning: OpenAI API key format may be invalid")

        # Check JSON file
        print(f"✓ JSON file found: {config.json_file_path}")

        # Check embedding configuration
        print(f"✓ Embedding model: {config.openai_embedding_model} ({config.embedding_dimensions}D)")

        print("\n✅ Environment validation successful!")
        return True

    except Exception as e:
        print(f"\n❌ Environment validation failed: {e}")
        return False


if __name__ == "__main__":
    # Validate environment when run directly
    validate_environment()
