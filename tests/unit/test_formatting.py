"""
Unit tests for PT-BR number formatting

Tests number formatting functions from visualization_tool.py
"""
import pytest
from src.tools.visualization_tool import _format_number_ptbr


# ==============================================================================
# Test Percentage Formatting
# ==============================================================================

@pytest.mark.unit
def test_format_percentage_basic():
    """Should format percentage with 2 decimals and comma separator."""
    result = _format_number_ptbr(0.1525, "percentage")
    assert result == "15,25%"


@pytest.mark.unit
def test_format_percentage_zero():
    """Should format zero percentage."""
    result = _format_number_ptbr(0.0, "percentage")
    assert result == "0,00%"


@pytest.mark.unit
def test_format_percentage_high_value():
    """Should format high percentage (>100%)."""
    result = _format_number_ptbr(1.5, "percentage")
    assert result == "150,00%"


@pytest.mark.unit
def test_format_percentage_low_value():
    """Should format very low percentage."""
    result = _format_number_ptbr(0.0001, "percentage")
    assert result == "0,01%"


# ==============================================================================
# Test Integer Formatting
# ==============================================================================

@pytest.mark.unit
def test_format_integer_with_thousands():
    """Should format integer with dot as thousand separator."""
    result = _format_number_ptbr(1234, "integer")
    assert result == "1.234"


@pytest.mark.unit
def test_format_integer_millions():
    """Should format millions with dots."""
    result = _format_number_ptbr(1234567, "integer")
    assert result == "1.234.567"


@pytest.mark.unit
def test_format_integer_small_number():
    """Should format small integer without separator."""
    result = _format_number_ptbr(123, "integer")
    assert result == "123"


@pytest.mark.unit
def test_format_integer_zero():
    """Should format zero."""
    result = _format_number_ptbr(0, "integer")
    assert result == "0"


# ==============================================================================
# Test Decimal Formatting
# ==============================================================================

@pytest.mark.unit
def test_format_decimal_basic():
    """Should format decimal with 1 decimal place and comma."""
    result = _format_number_ptbr(35.7, "decimal")
    assert result == "35,7"


@pytest.mark.unit
def test_format_decimal_rounds():
    """Should round to 1 decimal place."""
    result = _format_number_ptbr(35.75, "decimal")
    assert result == "35,8"


@pytest.mark.unit
def test_format_decimal_zero():
    """Should format zero decimal."""
    result = _format_number_ptbr(0.0, "decimal")
    assert result == "0,0"


@pytest.mark.unit
def test_format_decimal_integer_value():
    """Should format integer value as decimal with ,0."""
    result = _format_number_ptbr(42.0, "decimal")
    assert result == "42,0"


# ==============================================================================
# Test Edge Cases
# ==============================================================================

@pytest.mark.unit
def test_format_negative_percentage():
    """Should format negative percentage."""
    result = _format_number_ptbr(-0.15, "percentage")
    assert result == "-15,00%"


@pytest.mark.unit
def test_format_negative_decimal():
    """Should format negative decimal."""
    result = _format_number_ptbr(-25.5, "decimal")
    assert result == "-25,5"


@pytest.mark.unit
def test_format_very_large_number():
    """Should format very large number."""
    result = _format_number_ptbr(1_000_000_000, "integer")
    assert result == "1.000.000.000"
