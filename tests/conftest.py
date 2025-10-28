"""
Pytest configuration and shared fixtures for tests.
"""
import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock, MagicMock, patch
from typing import Iterator

import pandas as pd
import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolCall


# ==============================================================================
# Environment Setup
# ==============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = "credit-chatbot-tests"

    # Set test database connection (using Docker Compose PostgreSQL)
    if "DB_HOST" not in os.environ:
        os.environ["DB_HOST"] = "localhost"
    if "DB_PORT" not in os.environ:
        os.environ["DB_PORT"] = "5432"
    if "DB_NAME" not in os.environ:
        os.environ["DB_NAME"] = "credit_analytics"
    if "DB_USER" not in os.environ:
        os.environ["DB_USER"] = "chatbot_reader"
    if "DB_PASSWORD" not in os.environ:
        os.environ["DB_PASSWORD"] = "senha_segura_leitura"

    # Mock OpenAI API key for tests that don't use real LLM
    if "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"


# ==============================================================================
# Fake LLM Fixtures
# ==============================================================================

@pytest.fixture
def fake_llm_simple() -> GenericFakeChatModel:
    """
    Simple fake LLM that returns predefined SQL query.
    """
    return GenericFakeChatModel(messages=iter([
        'SELECT "UF", AVG("TARGET") as taxa_inadimplencia FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20'
    ]))


@pytest.fixture
def fake_llm_with_tool_call() -> GenericFakeChatModel:
    """
    Fake LLM that returns a tool call (for agent trajectory testing).
    """
    return GenericFakeChatModel(messages=iter([
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="query_database",
                    args={"question": "Qual a taxa de inadimplência por UF?"},
                    id="call_1"
                )
            ]
        ),
        AIMessage(content="A taxa de inadimplência varia entre 5% e 12% dependendo do estado.")
    ]))


@pytest.fixture
def fake_llm_retry_scenario() -> GenericFakeChatModel:
    """
    Fake LLM for testing retry logic.
    First response has missing quotes (will fail), second is corrected.
    """
    return GenericFakeChatModel(messages=iter([
        # First attempt: missing double quotes (will fail validation)
        'SELECT UF, AVG(TARGET) FROM credit_train GROUP BY UF',
        # Corrected version
        'SELECT "UF", AVG("TARGET") FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20'
    ]))


# ==============================================================================
# Mock GCS Uploader Fixtures
# ==============================================================================

@pytest.fixture
def mock_gcs_client():
    """
    Mock Google Cloud Storage client.
    """
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.public_url = "https://storage.googleapis.com/neuro-test/test-chart-123.png"

    return mock_client


@pytest.fixture
def mock_gcs_uploader(mock_gcs_client):
    """
    Patch GCS uploader to return mock URL without real upload.
    """
    with patch("src.utils.gcs_uploader.storage.Client", return_value=mock_gcs_client):
        with patch("src.utils.gcs_uploader.upload_image") as mock_upload:
            mock_upload.return_value = "https://storage.googleapis.com/neuro-test/test-chart-123.png"
            yield mock_upload


# ==============================================================================
# Mock Database Fixtures
# ==============================================================================

@pytest.fixture
def mock_db_engine():
    """
    Mock SQLAlchemy engine for unit tests (no real DB connection).
    """
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_result = MagicMock()

    # Setup context manager
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_engine.connect.return_value.__exit__.return_value = None

    # Setup query execution
    mock_connection.execute.return_value = mock_result
    mock_result.fetchall.return_value = [
        {"UF": "SP", "taxa_inadimplencia": Decimal("0.0850")},
        {"UF": "RJ", "taxa_inadimplencia": Decimal("0.1200")},
    ]

    return mock_engine


@pytest.fixture
def mock_db_connection_manager(mock_db_engine):
    """
    Mock database connection manager.
    """
    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        from src.utils.db_connection import DatabaseManager
        manager = DatabaseManager()
        yield manager


# ==============================================================================
# Sample Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_credit_data() -> pd.DataFrame:
    """
    Sample credit data for testing (mirrors credit_train table structure).
    """
    return pd.DataFrame({
        "ID": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "REF_DATE": pd.to_datetime([
            "2017-01-01", "2017-01-01", "2017-02-01", "2017-02-01", "2017-03-01",
            "2017-03-01", "2017-04-01", "2017-04-01", "2017-05-01", "2017-05-01"
        ]),
        "TARGET": [0, 1, 0, 0, 1, 0, 1, 0, 0, 1],
        "SEXO": ["M", "F", "M", "F", "M", "F", "M", "F", "M", "F"],
        "IDADE": [25, 35, 45, 55, 30, 40, 50, 28, 33, 48],
        "OBITO": [False, False, False, False, False, False, False, False, False, False],
        "UF": ["SP", "RJ", "MG", "SP", "RJ", "MG", "SP", "RJ", "MG", "SP"],
        "CLASSE_SOCIAL": ["c", "b", "c", "d", "c", "b", "c", "b", "d", "c"],
    })


@pytest.fixture
def sample_aggregated_data() -> pd.DataFrame:
    """
    Sample aggregated data (result of GROUP BY query).
    """
    return pd.DataFrame({
        "UF": ["SP", "RJ", "MG", "PR", "BA"],
        "taxa_inadimplencia": [0.085, 0.120, 0.095, 0.078, 0.110],
        "volume": [5000, 3200, 2800, 1500, 2100],
    })


@pytest.fixture
def sample_temporal_data() -> pd.DataFrame:
    """
    Sample temporal data for line charts.
    """
    return pd.DataFrame({
        "mes": pd.to_datetime(["2017-01", "2017-02", "2017-03", "2017-04", "2017-05"]),
        "taxa_inadimplencia": [0.082, 0.085, 0.090, 0.087, 0.091],
    })


@pytest.fixture
def sample_distribution_data() -> pd.DataFrame:
    """
    Sample distribution data for histograms.
    """
    return pd.DataFrame({
        "idade": [25, 28, 30, 32, 35, 38, 40, 42, 45, 48, 50, 52, 55, 58, 60] * 10
    })


# ==============================================================================
# Mock SQL Responses
# ==============================================================================

@pytest.fixture
def mock_sql_responses() -> dict:
    """
    Dictionary of mock SQL queries and their expected results.
    """
    return {
        "taxa_por_uf": {
            "sql": 'SELECT "UF", AVG("TARGET") as taxa_inadimplencia FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20 ORDER BY taxa_inadimplencia DESC',
            "result": [
                {"UF": "RJ", "taxa_inadimplencia": 0.120},
                {"UF": "MG", "taxa_inadimplencia": 0.095},
                {"UF": "SP", "taxa_inadimplencia": 0.085},
            ]
        },
        "taxa_geral": {
            "sql": 'SELECT AVG("TARGET") as taxa_inadimplencia FROM credit_train',
            "result": [{"taxa_inadimplencia": 0.0923}]
        },
        "evolucao_mensal": {
            "sql": 'SELECT DATE_TRUNC(\'month\', "REF_DATE") as mes, AVG("TARGET") as taxa FROM credit_train GROUP BY mes HAVING COUNT(*) >= 20 ORDER BY mes',
            "result": [
                {"mes": datetime(2017, 1, 1), "taxa": 0.082},
                {"mes": datetime(2017, 2, 1), "taxa": 0.085},
                {"mes": datetime(2017, 3, 1), "taxa": 0.090},
            ]
        }
    }


# ==============================================================================
# Pytest Markers
# ==============================================================================

def pytest_configure(config):
    """
    Register custom markers.
    """
    config.addinivalue_line("markers", "unit: fast unit tests without external dependencies")
    config.addinivalue_line("markers", "integration: integration tests requiring external services")
    config.addinivalue_line("markers", "langsmith: tests that log results to LangSmith")


# ==============================================================================
# Test Helpers
# ==============================================================================

@pytest.fixture
def assert_sql_valid():
    """
    Helper fixture to assert SQL is valid and safe.
    """
    from src.utils.sql_validator import sql_validator

    def _assert_valid(sql: str) -> tuple[bool, str]:
        """Validate SQL and return (is_valid, formatted_sql)."""
        return sql_validator.validate(sql)

    return _assert_valid


@pytest.fixture
def clean_decimal():
    """
    Helper to convert Decimal to float (mirrors production behavior).
    """
    def _clean(value):
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, dict):
            return {k: _clean(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_clean(v) for v in value]
        return value

    return _clean
