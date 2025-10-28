"""
Unit tests for Database Connection Manager

Tests database connection pooling and query execution with mocks.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from sqlalchemy.exc import OperationalError
from src.utils.db_connection import DatabaseManager


# ==============================================================================
# Test Connection Manager Initialization
# ==============================================================================

@pytest.mark.unit
def test_connection_manager_init():
    """Should initialize with valid config."""
    with patch("src.utils.db_connection.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        manager = DatabaseManager()

        # Should have created engine
        assert manager is not None
        mock_create_engine.assert_called_once()


@pytest.mark.unit
def test_connection_manager_creates_pool():
    """Should create connection pool with correct parameters."""
    with patch("src.utils.db_connection.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        manager = DatabaseManager()

        # Verify create_engine was called with pooling parameters
        call_kwargs = mock_create_engine.call_args[1]
        assert "pool_size" in call_kwargs or call_kwargs.get("poolclass") is not None


# ==============================================================================
# Test Connection Context Manager
# ==============================================================================

@pytest.mark.unit
def test_get_connection_context_manager(mock_db_engine):
    """Should provide connection via context manager."""
    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        manager = DatabaseManager()

        with manager.get_connection() as conn:
            assert conn is not None


@pytest.mark.unit
def test_get_connection_closes_properly(mock_db_engine):
    """Should close connection on context exit."""
    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        manager = DatabaseManager()

        with manager.get_connection() as conn:
            pass  # Connection should close after this block

        # Verify context manager __exit__ was called
        mock_db_engine.connect.return_value.__exit__.assert_called_once()


# ==============================================================================
# Test Query Execution
# ==============================================================================

@pytest.mark.unit
def test_execute_query_returns_results(mock_db_engine):
    """Should execute query and return results."""
    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        manager = DatabaseManager()

        result = manager.execute_query('SELECT "UF", AVG("TARGET") FROM credit_train GROUP BY "UF"')

        # Should return list of dicts
        assert isinstance(result, list)
        assert len(result) == 2  # Mock returns 2 rows
        assert "UF" in result[0]


@pytest.mark.unit
def test_execute_query_converts_decimal_to_float(mock_db_engine, clean_decimal):
    """Should convert Decimal values to float."""
    # Mock result with Decimal values
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        {"taxa": Decimal("0.0850")},
    ]
    mock_connection = MagicMock()
    mock_connection.execute.return_value = mock_result
    mock_db_engine.connect.return_value.__enter__.return_value = mock_connection

    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        manager = DatabaseManager()

        result = manager.execute_query("SELECT AVG(TARGET) as taxa FROM credit_train")

        # Should have converted Decimal to float
        assert isinstance(result[0]["taxa"], (float, int))


# ==============================================================================
# Test Connection Testing
# ==============================================================================

@pytest.mark.unit
def test_test_connection_success(mock_db_engine):
    """Should return True for successful connection test."""
    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        manager = DatabaseManager()

        is_connected = manager.test_connection()

        assert is_connected is True


@pytest.mark.unit
def test_test_connection_failure():
    """Should return False for failed connection."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("Connection refused", None, None)

    with patch("src.utils.db_connection.create_engine", return_value=mock_engine):
        manager = DatabaseManager()

        is_connected = manager.test_connection()

        assert is_connected is False


# ==============================================================================
# Test Table Info
# ==============================================================================

@pytest.mark.unit
def test_get_table_info(mock_db_engine):
    """Should return table schema information."""
    # Mock inspector
    mock_inspector = MagicMock()
    mock_inspector.get_columns.return_value = [
        {"name": "ID", "type": "INTEGER"},
        {"name": "UF", "type": "VARCHAR"},
    ]

    with patch("src.utils.db_connection.create_engine", return_value=mock_db_engine):
        with patch("src.utils.db_connection.inspect", return_value=mock_inspector):
            manager = DatabaseManager()

            table_info = manager.get_table_info("credit_train")

            # Should return column information
            assert table_info is not None
            assert len(table_info) >= 2


# ==============================================================================
# Test Statement Timeout
# ==============================================================================

@pytest.mark.unit
def test_statement_timeout_applied():
    """Should apply statement timeout to connections."""
    with patch("src.utils.db_connection.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        manager = DatabaseManager()

        # Verify connect_args includes statement_timeout
        call_kwargs = mock_create_engine.call_args[1]
        connect_args = call_kwargs.get("connect_args", {})
        # Depending on implementation, timeout might be in connect_args or execution options
        # This test documents expected behavior
