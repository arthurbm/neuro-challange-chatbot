"""
Integration tests for visualization tool.

Tests chart generation with mocked GCS upload.
"""
import pytest
from unittest.mock import patch
from src.tools.visualization_tool import generate_chart


# ==============================================================================
# Test Chart Generation with Mocked GCS
# ==============================================================================

@pytest.mark.integration
def test_generate_bar_chart(mock_gcs_uploader):
    """Should generate bar chart and return content blocks with GCS URL."""
    data = [
        {"uf": "SP", "taxa_inadimplencia": 0.15, "n": 1000},
        {"uf": "RJ", "taxa_inadimplencia": 0.12, "n": 800},
        {"uf": "MG", "taxa_inadimplencia": 0.18, "n": 600},
    ]

    result = generate_chart(
        data=data, chart_type="bar", title="Taxa de Inadimplência por UF"
    )

    # Should return list of content blocks
    assert isinstance(result, list)
    assert len(result) == 2  # Text block + image block

    # First block: text description
    assert result[0]["type"] == "text"
    assert "Gráfico gerado" in result[0]["text"] or "Taxa de Inadimplência" in result[0]["text"]

    # Second block: image with GCS URL
    assert result[1]["type"] == "image"
    assert result[1]["source_type"] == "url"
    assert result[1]["url"].startswith("https://storage.googleapis.com")
    assert result[1]["mime_type"] == "image/png"


@pytest.mark.integration
def test_generate_line_chart(mock_gcs_uploader):
    """Should generate line chart."""
    data = [
        {"mes": "2017-01", "taxa": 0.14},
        {"mes": "2017-02", "taxa": 0.16},
        {"mes": "2017-03", "taxa": 0.15},
    ]

    result = generate_chart(data=data, chart_type="line", title="Evolução Mensal")

    # Should return content blocks
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[1]["type"] == "image"


@pytest.mark.integration
def test_auto_detect_chart_type(mock_gcs_uploader):
    """Should auto-detect bar chart for categorical data."""
    data = [
        {"categoria": "A", "valor": 10},
        {"categoria": "B", "valor": 20},
    ]

    result = generate_chart(data=data, chart_type="auto")

    # Should auto-detect and generate chart
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[1]["url"].startswith("https://storage.googleapis.com")


@pytest.mark.integration
def test_empty_data():
    """Should handle empty data gracefully."""
    result = generate_chart(data=[], chart_type="bar")

    # Should return error message (either as string or in content blocks)
    if isinstance(result, str):
        assert "Erro" in result or "erro" in result.lower()
    elif isinstance(result, list):
        assert any("erro" in str(block).lower() for block in result)


@pytest.mark.integration
def test_invalid_column():
    """Should handle invalid column names."""
    data = [{"a": 1, "b": 2}]

    result = generate_chart(
        data=data, chart_type="bar", x_column="nao_existe", y_column="b"
    )

    # Should return error message
    if isinstance(result, str):
        assert "Erro" in result or "erro" in result.lower()
    elif isinstance(result, list):
        assert any("erro" in str(block).lower() for block in result)


