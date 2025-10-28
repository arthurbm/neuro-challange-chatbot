"""
Integration tests for Database Query Tool

Tests SQL generation, validation, and execution with fake LLM and real PostgreSQL.
Requires Docker Compose PostgreSQL to be running.
"""
import pytest
from unittest.mock import patch
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from src.tools.database_query_tool import _generate_sql_with_llm, _correct_sql_with_llm, query_database
from src.utils.sql_validator import sql_validator


# ==============================================================================
# Test SQL Generation with Fake LLM
# ==============================================================================

@pytest.mark.integration
def test_generate_sql_with_fake_llm():
    """Should generate SQL using fake LLM."""
    # Create fake LLM that returns a valid SQL query
    fake_llm = GenericFakeChatModel(messages=iter([
        'SELECT "UF", AVG("TARGET") as taxa_inadimplencia FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20'
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        sql = _generate_sql_with_llm("Qual a taxa de inadimplência por UF?")

        # Should return valid SQL
        assert sql is not None
        assert "SELECT" in sql.upper()
        assert "credit_train" in sql


@pytest.mark.integration
def test_generate_sql_removes_markdown():
    """Should remove markdown code blocks from LLM response."""
    # LLM returns SQL wrapped in markdown
    fake_llm = GenericFakeChatModel(messages=iter([
        '```sql\nSELECT * FROM credit_train LIMIT 10\n```'
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        sql = _generate_sql_with_llm("Mostre 10 registros")

        # Should have removed ```sql markers
        assert "```" not in sql
        assert sql.strip().startswith("SELECT")


# ==============================================================================
# Test SQL Validation After Generation
# ==============================================================================

@pytest.mark.integration
def test_generated_sql_passes_validation():
    """Generated SQL should pass security validation."""
    fake_llm = GenericFakeChatModel(messages=iter([
        'SELECT "UF", COUNT(*) as volume FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20'
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        sql = _generate_sql_with_llm("Volume por UF")

        # Should pass validation
        is_valid, formatted_sql = sql_validator.validate(sql)
        assert is_valid is True


# ==============================================================================
# Test SQL Correction
# ==============================================================================

@pytest.mark.integration
def test_correct_sql_with_llm():
    """Should correct SQL using LLM."""
    failed_sql = 'SELECT UF FROM credit_train'  # Missing double quotes
    error_msg = 'column "uf" does not exist'

    # Fake LLM returns corrected SQL
    fake_llm = GenericFakeChatModel(messages=iter([
        'SELECT "UF" FROM credit_train LIMIT 100'  # Corrected with quotes
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        corrected_sql = _correct_sql_with_llm(
            failed_sql=failed_sql,
            error_msg=error_msg,
            question="Liste os estados"
        )

        # Should return corrected SQL
        assert corrected_sql is not None
        assert '"UF"' in corrected_sql or corrected_sql != failed_sql


# ==============================================================================
# Test Full Tool Execution with Fake LLM
# ==============================================================================

@pytest.mark.integration
@pytest.mark.skip(reason="Requires real PostgreSQL - run manually with Docker")
def test_query_database_tool_with_fake_llm_and_real_db():
    """
    Test full query_database tool with fake LLM + real PostgreSQL.

    IMPORTANT: This test requires Docker Compose PostgreSQL to be running!
    Run: docker-compose up -d

    Skip by default in CI/CD.
    """
    # Fake LLM returns a simple, safe query
    fake_llm = GenericFakeChatModel(messages=iter([
        'SELECT COUNT(*) as total FROM credit_train'
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        result = query_database.invoke({
            "question_context": "Quantos registros existem?"
        })

        # Should return query results
        assert result is not None
        assert "sql" in result
        assert "result" in result
        assert isinstance(result["result"], list)


@pytest.mark.integration
@pytest.mark.skip(reason="Requires real PostgreSQL - run manually")
def test_query_database_with_aggregation():
    """Test query with GROUP BY and k-anonymity."""
    fake_llm = GenericFakeChatModel(messages=iter([
        'SELECT "SEXO", AVG("TARGET") as taxa, COUNT(*) as n FROM credit_train GROUP BY "SEXO" HAVING COUNT(*) >= 20'
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        result = query_database.invoke({
            "question_context": "Taxa de inadimplência por sexo"
        })

        # Should return aggregated results
        assert len(result["result"]) <= 2  # M, F (or less if filtered by k-anonymity)
        # Check k-anonymity was applied (n >= 20 for all groups)
        for row in result["result"]:
            if "n" in row:
                assert row["n"] >= 20


# ==============================================================================
# Test Retry Logic
# ==============================================================================

@pytest.mark.integration
def test_retry_logic_with_fake_llm():
    """Test retry logic when first SQL fails validation."""
    # First SQL is invalid (no quotes), second is corrected
    fake_llm = GenericFakeChatModel(messages=iter([
        'SELECT UF FROM credit_train',  # Missing quotes (will fail)
        'SELECT "UF" FROM credit_train LIMIT 100',  # Corrected
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        # This would test the retry mechanism
        # The actual implementation might not expose retry logic directly
        # This test documents expected behavior
        pass


# ==============================================================================
# Test Error Handling
# ==============================================================================

@pytest.mark.integration
def test_query_database_handles_invalid_sql():
    """Should handle and report invalid SQL from LLM."""
    # Fake LLM returns malicious SQL
    fake_llm = GenericFakeChatModel(messages=iter([
        'DROP TABLE credit_train',  # Blocked operation
        'DROP TABLE credit_train',  # Even after retry (stubborn LLM)
        'DROP TABLE credit_train',
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        result = query_database.invoke({
            "question_context": "Delete everything"
        })

        # Should return error message, not execute dangerous SQL
        assert "error" in str(result).lower() or "não permitida" in str(result).lower()


@pytest.mark.integration
@pytest.mark.skip(reason="Requires real PostgreSQL")
def test_query_database_handles_db_error():
    """Should handle database execution errors gracefully."""
    # Valid SQL syntax but causes DB error (e.g., invalid filter)
    fake_llm = GenericFakeChatModel(messages=iter([
        "SELECT * FROM credit_train WHERE invalid_function()",
    ]))

    with patch("src.tools.database_query_tool.ChatOpenAI", return_value=fake_llm):
        result = query_database.invoke({
            "question_context": "Some question"
        })

        # Should catch error and return error message
        assert result is not None
        # Either returns error dict or raises gracefully
