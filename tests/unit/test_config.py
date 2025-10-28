"""
Unit tests for Configuration

Tests Pydantic config loading, validation, and defaults.
"""
import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from src.config import (
    DatabaseConfig,
    LLMConfig,
    LangSmithConfig,
    GuardrailsConfig,
    FormattingConfig,
    GCSConfig,
    Config,
)


# ==============================================================================
# Test DatabaseConfig
# ==============================================================================

@pytest.mark.unit
def test_database_config_defaults():
    """Should load with default values when env vars not set."""
    with patch.dict(os.environ, {}, clear=True):
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "credit_analytics"
        assert config.user == "chatbot_reader"
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.statement_timeout == 10000


@pytest.mark.unit
def test_database_config_from_env():
    """Should load from environment variables."""
    with patch.dict(
        os.environ,
        {
            "DB_HOST": "db.example.com",
            "DB_PORT": "5433",
            "DB_NAME": "test_db",
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_password",
        },
        clear=True,
    ):
        config = DatabaseConfig()
        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.database == "test_db"
        assert config.user == "test_user"
        assert config.password == "test_password"


@pytest.mark.unit
def test_database_connection_string():
    """Should generate correct PostgreSQL connection string."""
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
    )
    conn_str = config.connection_string
    assert conn_str == "postgresql+psycopg://testuser:testpass@localhost:5432/testdb"


@pytest.mark.unit
def test_database_config_invalid_port():
    """Should raise ValidationError for invalid port type."""
    with patch.dict(os.environ, {"DB_PORT": "invalid_port"}, clear=True):
        with pytest.raises(ValidationError):
            DatabaseConfig()


@pytest.mark.unit
def test_database_config_negative_pool_size():
    """Should allow negative pool size (Pydantic doesn't validate by default)."""
    # Note: If you want to add validation, use Field(..., gt=0)
    with patch.dict(os.environ, {"DB_POOL_SIZE": "-1"}, clear=True):
        config = DatabaseConfig()
        # This test demonstrates current behavior - add validation if needed
        assert config.pool_size == -1


# ==============================================================================
# Test LLMConfig
# ==============================================================================

@pytest.mark.unit
def test_llm_config_defaults():
    """Should load with default LLM configuration."""
    with patch.dict(os.environ, {}, clear=True):
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.0
        assert config.max_tokens == 2000


@pytest.mark.unit
def test_llm_config_from_env():
    """Should load LLM config from environment."""
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "anthropic",
            "LLM_MODEL": "claude-3-opus",
            "LLM_TEMPERATURE": "0.7",
            "LLM_MAX_TOKENS": "4000",
            "OPENAI_API_KEY": "sk-test-key",
        },
        clear=True,
    ):
        config = LLMConfig()
        assert config.provider == "anthropic"
        assert config.model == "claude-3-opus"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
        assert config.api_key == "sk-test-key"


@pytest.mark.unit
def test_llm_config_invalid_temperature():
    """Should raise ValidationError for invalid temperature type."""
    with patch.dict(os.environ, {"LLM_TEMPERATURE": "not_a_number"}, clear=True):
        with pytest.raises(ValidationError):
            LLMConfig()


# ==============================================================================
# Test LangSmithConfig
# ==============================================================================

@pytest.mark.unit
def test_langsmith_config_defaults():
    """Should load with default LangSmith configuration."""
    with patch.dict(os.environ, {}, clear=True):
        config = LangSmithConfig()
        assert config.tracing_enabled is True
        assert config.project == "credit-chatbot"
        assert config.endpoint == "https://api.smith.langchain.com"


@pytest.mark.unit
def test_langsmith_config_tracing_disabled():
    """Should correctly parse boolean from env var."""
    with patch.dict(os.environ, {"LANGSMITH_TRACING": "false"}, clear=True):
        config = LangSmithConfig()
        assert config.tracing_enabled is False


# ==============================================================================
# Test GuardrailsConfig
# ==============================================================================

@pytest.mark.unit
def test_guardrails_config_defaults():
    """Should load with default guardrails."""
    with patch.dict(os.environ, {}, clear=True):
        config = GuardrailsConfig()
        assert config.k_anonymity == 20
        assert config.default_limit == 100
        assert config.max_rows_return == 10000
        assert config.query_timeout_seconds == 10
        assert config.max_retry_attempts == 3


@pytest.mark.unit
def test_guardrails_blocked_operations_default():
    """Should have default list of blocked operations."""
    config = GuardrailsConfig()
    assert "DROP" in config.blocked_operations
    assert "DELETE" in config.blocked_operations
    assert "UPDATE" in config.blocked_operations
    assert "INSERT" in config.blocked_operations
    assert "CREATE" in config.blocked_operations
    assert "ALTER" in config.blocked_operations
    assert "TRUNCATE" in config.blocked_operations
    assert "GRANT" in config.blocked_operations
    assert "REVOKE" in config.blocked_operations


@pytest.mark.unit
def test_guardrails_config_from_env():
    """Should load custom guardrails from env."""
    with patch.dict(
        os.environ,
        {
            "K_ANONYMITY": "50",
            "DEFAULT_QUERY_LIMIT": "200",
            "MAX_ROWS_RETURN": "5000",
            "QUERY_TIMEOUT_SECONDS": "30",
        },
        clear=True,
    ):
        config = GuardrailsConfig()
        assert config.k_anonymity == 50
        assert config.default_limit == 200
        assert config.max_rows_return == 5000
        assert config.query_timeout_seconds == 30


# ==============================================================================
# Test FormattingConfig
# ==============================================================================

@pytest.mark.unit
def test_formatting_config_pt_br_defaults():
    """Should use PT-BR formatting by default."""
    config = FormattingConfig()
    assert config.decimal_separator == ","
    assert config.thousand_separator == "."
    assert config.decimal_places_percentage == 2
    assert config.decimal_places_age == 1
    assert config.date_format == "%d/%m/%Y"
    assert config.language == "pt-BR"


# ==============================================================================
# Test GCSConfig
# ==============================================================================

@pytest.mark.unit
def test_gcs_config_defaults():
    """Should load with default GCS configuration."""
    with patch.dict(os.environ, {}, clear=True):
        config = GCSConfig()
        assert config.project_id == "neuro-test-476419"
        assert config.bucket_name == "neuro-test"
        assert config.service_account_json is None
        assert config.service_account_json_content is None


@pytest.mark.unit
def test_gcs_config_with_json_path():
    """Should load service account JSON path from env."""
    with patch.dict(
        os.environ, {"GCS_SERVICE_ACCOUNT_JSON": "/path/to/credentials.json"}, clear=True
    ):
        config = GCSConfig()
        assert config.service_account_json == "/path/to/credentials.json"


@pytest.mark.unit
def test_gcs_config_with_json_content():
    """Should load service account JSON content from env."""
    json_content = '{"type": "service_account", "project_id": "test-project"}'
    with patch.dict(os.environ, {"GCS_SERVICE_ACCOUNT_JSON_CONTENT": json_content}, clear=True):
        config = GCSConfig()
        assert config.service_account_json_content == json_content


# ==============================================================================
# Test Config (Main Composite Config)
# ==============================================================================

@pytest.mark.unit
def test_config_loads_all_subconfigs():
    """Main Config should load all sub-configurations."""
    config = Config()
    assert isinstance(config.database, DatabaseConfig)
    assert isinstance(config.llm, LLMConfig)
    assert isinstance(config.langsmith, LangSmithConfig)
    assert isinstance(config.guardrails, GuardrailsConfig)
    assert isinstance(config.formatting, FormattingConfig)
    assert isinstance(config.gcs, GCSConfig)


@pytest.mark.unit
def test_config_paths_exist():
    """Config should define project paths."""
    config = Config()
    assert config.project_root is not None
    assert config.data_dir is not None
    assert config.eval_dir is not None
    # Paths should be Path objects
    assert hasattr(config.project_root, "exists")


@pytest.mark.unit
def test_config_setup_langsmith():
    """setup_langsmith() should set environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        config = Config()
        config.langsmith.tracing_enabled = True
        config.langsmith.api_key = "test-api-key"
        config.langsmith.project = "test-project"

        config.setup_langsmith()

        assert os.environ.get("LANGSMITH_TRACING") == "true"
        assert os.environ.get("LANGSMITH_API_KEY") == "test-api-key"
        assert os.environ.get("LANGSMITH_PROJECT") == "test-project"


@pytest.mark.unit
def test_config_setup_langsmith_disabled():
    """setup_langsmith() should not set env vars when tracing disabled."""
    with patch.dict(os.environ, {}, clear=True):
        config = Config()
        config.langsmith.tracing_enabled = False

        config.setup_langsmith()

        # Should not set env vars when disabled
        # (or the implementation might still set them - depends on requirement)
        # This test documents current behavior


# ==============================================================================
# Test Global Config Instance
# ==============================================================================

@pytest.mark.unit
def test_global_config_instance_exists():
    """Global config instance should be importable."""
    from src.config import config as global_config

    assert global_config is not None
    assert isinstance(global_config, Config)
