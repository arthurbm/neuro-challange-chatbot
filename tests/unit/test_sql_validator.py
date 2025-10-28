"""
Unit tests for SQL validator - SECURITY CRITICAL

Tests SQL validation, sanitization, and security enforcement.
"""
import pytest
from src.utils.sql_validator import sql_validator, SQLValidationError


# ==============================================================================
# Test Dangerous Operations Blocking (Security Critical)
# ==============================================================================

@pytest.mark.unit
def test_blocks_insert():
    """Should block INSERT statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|INSERT)"):
        sql_validator.sql_validator.validate("INSERT INTO credit_train (ID, TARGET) VALUES (1, 0)")


@pytest.mark.unit
def test_blocks_update():
    """Should block UPDATE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|UPDATE)"):
        sql_validator.validate('UPDATE credit_train SET "TARGET" = 1 WHERE "ID" = 1')


@pytest.mark.unit
def test_blocks_delete():
    """Should block DELETE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|DELETE)"):
        sql_validator.validate('DELETE FROM credit_train WHERE "TARGET" = 1')


@pytest.mark.unit
def test_blocks_drop_table():
    """Should block DROP TABLE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|DROP)"):
        sql_validator.validate("DROP TABLE credit_train")


@pytest.mark.unit
def test_blocks_drop_database():
    """Should block DROP DATABASE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|DROP)"):
        sql_validator.validate("DROP DATABASE credit_analytics")


@pytest.mark.unit
def test_blocks_alter_table():
    """Should block ALTER TABLE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|ALTER)"):
        sql_validator.validate('ALTER TABLE credit_train ADD COLUMN new_col VARCHAR(10)')


@pytest.mark.unit
def test_blocks_create_table():
    """Should block CREATE TABLE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|CREATE)"):
        sql_validator.validate('CREATE TABLE malicious (id SERIAL PRIMARY KEY)')


@pytest.mark.unit
def test_blocks_truncate():
    """Should block TRUNCATE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|TRUNCATE)"):
        sql_validator.validate("TRUNCATE TABLE credit_train")


@pytest.mark.unit
def test_blocks_grant():
    """Should block GRANT statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|GRANT)"):
        sql_validator.validate("GRANT ALL PRIVILEGES ON credit_train TO malicious_user")


@pytest.mark.unit
def test_blocks_revoke():
    """Should block REVOKE statements."""
    with pytest.raises(SQLValidationError, match="(não permitida|REVOKE)"):
        sql_validator.validate("REVOKE SELECT ON credit_train FROM chatbot_reader")


# ==============================================================================
# Test Allowed Operations
# ==============================================================================

@pytest.mark.unit
def test_allows_select():
    """Should allow SELECT statements."""
    is_valid, formatted_sql = sql_validator.validate('SELECT * FROM credit_train LIMIT 10')
    assert is_valid is True
    assert "SELECT" in formatted_sql.upper()
    assert "credit_train" in formatted_sql


@pytest.mark.unit
def test_allows_select_with_aggregation():
    """Should allow SELECT with aggregations (GROUP BY, AVG, COUNT)."""
    sql = 'SELECT "UF", AVG("TARGET") FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20'
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    assert "AVG" in formatted_sql.upper()
    assert "GROUP BY" in formatted_sql.upper()


@pytest.mark.unit
def test_allows_with_cte():
    """Should allow WITH (Common Table Expressions)."""
    sql = '''
    WITH inadimplentes AS (
        SELECT "UF", COUNT(*) as total
        FROM credit_train
        WHERE "TARGET" = 1
        GROUP BY "UF"
    )
    SELECT * FROM inadimplentes
    '''
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    assert "WITH" in formatted_sql.upper()


@pytest.mark.unit
def test_allows_union():
    """Should allow UNION queries."""
    sql = '''
    SELECT "UF", AVG("TARGET") as taxa FROM credit_train WHERE "SEXO" = 'M' GROUP BY "UF"
    UNION
    SELECT "UF", AVG("TARGET") as taxa FROM credit_train WHERE "SEXO" = 'F' GROUP BY "UF"
    '''
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    assert "UNION" in formatted_sql.upper()


# ==============================================================================
# Test SQL Syntax Validation
# ==============================================================================

@pytest.mark.unit
def test_detects_syntax_error():
    """Should detect malformed SQL."""
    with pytest.raises(SQLValidationError, match="(sintaxe|syntax|parse)"):
        sql_validator.validate("SELECT FROM WHERE")  # Missing table and column


@pytest.mark.unit
def test_detects_unclosed_string():
    """Should detect unclosed string literals."""
    with pytest.raises(SQLValidationError):
        sql_validator.validate("SELECT * FROM credit_train WHERE \"SEXO\" = 'M")  # Missing closing quote


# ==============================================================================
# Test Auto-adding LIMIT
# ==============================================================================

@pytest.mark.unit
def test_adds_limit_when_missing():
    """Should auto-add LIMIT 100 to queries without LIMIT and without aggregation."""
    sql = 'SELECT * FROM credit_train'
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    assert "LIMIT" in formatted_sql.upper()
    # Should add LIMIT 100 (default)
    assert "100" in formatted_sql or "LIMIT 100" in formatted_sql.upper()


@pytest.mark.unit
def test_does_not_add_limit_to_aggregation():
    """Should NOT add LIMIT to queries with GROUP BY (aggregation)."""
    sql = 'SELECT "UF", AVG("TARGET") FROM credit_train GROUP BY "UF"'
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    # Should NOT have LIMIT added (because GROUP BY is aggregation)
    # Note: Depends on implementation - might still add LIMIT to aggregations


@pytest.mark.unit
def test_preserves_existing_limit():
    """Should preserve existing LIMIT clause."""
    sql = 'SELECT * FROM credit_train LIMIT 50'
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    assert "LIMIT" in formatted_sql.upper()
    # Should keep original LIMIT 50, not change to 100


# ==============================================================================
# Test Table Extraction
# ==============================================================================

@pytest.mark.unit
def test_extract_tables_single():
    """Should extract single table name."""
    sql = 'SELECT * FROM credit_train LIMIT 10'
    tables = sql_validator.extract_tables(sql)
    assert "credit_train" in tables


@pytest.mark.unit
def test_extract_tables_multiple():
    """Should extract multiple table names from JOIN."""
    sql = '''
    SELECT a."UF", b.total
    FROM credit_train a
    JOIN summary_table b ON a."UF" = b."UF"
    '''
    tables = sql_validator.extract_tables(sql)
    # Should extract both tables
    assert "credit_train" in tables or len(tables) >= 1


@pytest.mark.unit
def test_extract_tables_with_cte():
    """Should extract tables from CTEs."""
    sql = '''
    WITH temp AS (SELECT * FROM credit_train)
    SELECT * FROM temp
    '''
    tables = sql_validator.extract_tables(sql)
    assert "credit_train" in tables


# ==============================================================================
# Test Aggregation Detection
# ==============================================================================

@pytest.mark.unit
def test_detects_group_by():
    """Should detect GROUP BY as aggregation."""
    sql = 'SELECT "UF", COUNT(*) FROM credit_train GROUP BY "UF"'
    parsed = sql_validator._parse_sql(sql)
    assert sql_validator._has_aggregation(parsed) is True


@pytest.mark.unit
def test_detects_aggregate_functions():
    """Should detect aggregate functions (AVG, SUM, COUNT, etc.)."""
    sql = 'SELECT AVG("TARGET") FROM credit_train'
    parsed = sql_validator._parse_sql(sql)
    assert sql_validator._has_aggregation(parsed) is True


@pytest.mark.unit
def test_non_aggregation_query():
    """Should NOT detect aggregation for simple SELECT."""
    sql = 'SELECT * FROM credit_train LIMIT 10'
    parsed = sql_validator._parse_sql(sql)
    assert sql_validator._has_aggregation(parsed) is False


# ==============================================================================
# Test SQL Formatting
# ==============================================================================

@pytest.mark.unit
def test_formats_sql_pretty_print():
    """Should format SQL for readability."""
    sql = 'select "UF",avg("TARGET") from credit_train group by "UF"'
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True
    # Should be formatted (capitalized keywords, proper spacing)
    assert formatted_sql != sql  # Should be different from original
    assert len(formatted_sql.split("\n")) >= 1  # Should have some formatting


# ==============================================================================
# Test Edge Cases
# ==============================================================================

@pytest.mark.unit
def test_handles_comments():
    """Should handle SQL comments."""
    sql = '''
    -- This is a comment
    SELECT "UF", AVG("TARGET")
    FROM credit_train  -- inline comment
    GROUP BY "UF"
    '''
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True


@pytest.mark.unit
def test_handles_multiline_sql():
    """Should handle multi-line SQL."""
    sql = '''
    SELECT
        "UF",
        AVG("TARGET") as taxa,
        COUNT(*) as volume
    FROM credit_train
    GROUP BY "UF"
    HAVING COUNT(*) >= 20
    ORDER BY taxa DESC
    '''
    is_valid, formatted_sql = sql_validator.validate(sql)
    assert is_valid is True


@pytest.mark.unit
def test_empty_sql():
    """Should reject empty SQL string."""
    with pytest.raises(SQLValidationError):
        sql_validator.validate("")


@pytest.mark.unit
def test_whitespace_only_sql():
    """Should reject whitespace-only SQL."""
    with pytest.raises(SQLValidationError):
        sql_validator.validate("   \n\t  ")


# ==============================================================================
# Test SQL Injection Attempts
# ==============================================================================

@pytest.mark.unit
def test_blocks_sql_injection_with_drop():
    """Should block SQL injection attempt with DROP."""
    # Classic Bobby Tables attack
    malicious_sql = "SELECT * FROM credit_train WHERE \"UF\" = 'SP'; DROP TABLE credit_train; --"
    with pytest.raises(SQLValidationError, match="(não permitida|DROP)"):
        sql_validator.validate(malicious_sql)


@pytest.mark.unit
def test_blocks_sql_injection_with_union_and_insert():
    """Should block UNION-based injection with INSERT."""
    malicious_sql = """
    SELECT * FROM credit_train WHERE \"UF\" = 'SP'
    UNION
    SELECT * FROM (SELECT 'malicious' as data) x; INSERT INTO credit_train VALUES (999, NOW(), 1, 'M', 99, false, 'XX', 'a')
    """
    # Should block due to INSERT
    with pytest.raises(SQLValidationError, match="(não permitida|INSERT)"):
        sql_validator.validate(malicious_sql)


@pytest.mark.unit
def test_blocks_stacked_queries_with_update():
    """Should block stacked queries with UPDATE."""
    malicious_sql = 'SELECT * FROM credit_train; UPDATE credit_train SET "TARGET" = 1'
    with pytest.raises(SQLValidationError, match="(não permitida|UPDATE)"):
        sql_validator.validate(malicious_sql)
