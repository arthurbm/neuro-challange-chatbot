"""
Unit tests for chart type auto-detection

Tests chart type detection logic from visualization_tool.py
"""
import pytest
import pandas as pd
from src.tools.visualization_tool import _detect_chart_type


# ==============================================================================
# Test Chart Type Detection
# ==============================================================================

@pytest.mark.unit
def test_detect_datetime_column_returns_line():
    """Should detect line chart for datetime column."""
    df = pd.DataFrame({
        "mes": pd.to_datetime(["2017-01", "2017-02", "2017-03"]),
        "taxa": [0.08, 0.09, 0.10],
    })
    chart_type = _detect_chart_type(df, "mes", "taxa")
    assert chart_type == "line"


@pytest.mark.unit
def test_detect_categorical_returns_bar():
    """Should detect bar chart for categorical data."""
    df = pd.DataFrame({
        "UF": ["SP", "RJ", "MG", "PR", "BA"],
        "taxa": [0.08, 0.12, 0.09, 0.07, 0.11],
    })
    chart_type = _detect_chart_type(df, "UF", "taxa")
    assert chart_type == "bar"


@pytest.mark.unit
def test_detect_few_unique_values_returns_bar():
    """Should detect bar chart for numeric column with few unique values."""
    df = pd.DataFrame({
        "classe_id": [1, 2, 3, 4, 5],
        "volume": [1000, 2000, 1500, 1800, 900],
    })
    chart_type = _detect_chart_type(df, "classe_id", "volume")
    assert chart_type == "bar"


@pytest.mark.unit
def test_detect_numeric_many_unique_returns_histogram():
    """Should detect histogram for numeric column with many unique values (>30)."""
    df = pd.DataFrame({
        "idade": list(range(18, 80)),  # 62 unique values
        "count": [10] * 62,
    })
    chart_type = _detect_chart_type(df, "idade", "count")
    assert chart_type == "histogram"


@pytest.mark.unit
def test_detect_edge_case_exactly_30_unique():
    """Should detect bar chart for exactly 30 unique values (not >30)."""
    df = pd.DataFrame({
        "category": [f"cat_{i}" for i in range(30)],
        "value": range(30),
    })
    # nunique() == 30, not > 30, so should be bar
    chart_type = _detect_chart_type(df, "category", "value")
    assert chart_type == "bar"


@pytest.mark.unit
def test_detect_single_value_returns_bar():
    """Should return bar chart for single value."""
    df = pd.DataFrame({
        "name": ["Total"],
        "value": [100],
    })
    chart_type = _detect_chart_type(df, "name", "value")
    assert chart_type == "bar"
