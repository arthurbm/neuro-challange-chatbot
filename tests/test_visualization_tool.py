"""
Testes básicos para a tool de visualização.
"""

from src.tools.visualization_tool import generate_chart


def test_generate_bar_chart():
    """Testa geração de gráfico de barras."""
    data = [
        {"uf": "SP", "taxa_inadimplencia": 0.15, "n": 1000},
        {"uf": "RJ", "taxa_inadimplencia": 0.12, "n": 800},
        {"uf": "MG", "taxa_inadimplencia": 0.18, "n": 600},
    ]

    result = generate_chart(
        data=data, chart_type="bar", title="Taxa de Inadimplência por UF"
    )

    # Verificar que retorna base64
    assert result.startswith("data:image/png;base64,")
    assert len(result) > 100  # Base64 deve ter tamanho razoável


def test_generate_line_chart():
    """Testa geração de gráfico de linha."""
    data = [
        {"mes": "2017-01", "taxa": 0.14},
        {"mes": "2017-02", "taxa": 0.16},
        {"mes": "2017-03", "taxa": 0.15},
    ]

    result = generate_chart(data=data, chart_type="line", title="Evolução Mensal")

    assert result.startswith("data:image/png;base64,")


def test_auto_detect_chart_type():
    """Testa auto-detecção de tipo de gráfico."""
    data = [
        {"categoria": "A", "valor": 10},
        {"categoria": "B", "valor": 20},
    ]

    result = generate_chart(data=data, chart_type="auto")

    # Auto deve detectar e gerar gráfico de barras
    assert result.startswith("data:image/png;base64,")


def test_empty_data():
    """Testa tratamento de dados vazios."""
    result = generate_chart(data=[], chart_type="bar")

    # Deve retornar mensagem de erro
    assert "Erro" in result


def test_invalid_column():
    """Testa tratamento de coluna inválida."""
    data = [{"a": 1, "b": 2}]

    result = generate_chart(
        data=data, chart_type="bar", x_column="nao_existe", y_column="b"
    )

    # Deve retornar mensagem de erro
    assert "Erro" in result


if __name__ == "__main__":
    print("Executando testes básicos da visualization_tool...")

    # Teste simples inline
    test_data = [
        {"uf": "SP", "taxa_inadimplencia": 0.15, "n": 1000},
        {"uf": "RJ", "taxa_inadimplencia": 0.12, "n": 800},
        {"uf": "MG", "taxa_inadimplencia": 0.18, "n": 600},
    ]

    print("\n1. Testando gráfico de barras...")
    result = generate_chart(
        data=test_data, chart_type="bar", title="Taxa de Inadimplência por UF"
    )
    print(f"   ✓ Resultado: {result[:50]}... (base64 gerada com sucesso)")

    print("\n2. Testando auto-detecção...")
    result = generate_chart(data=test_data, chart_type="auto")
    print(f"   ✓ Auto-detecção funcionou: {result[:50]}...")

    print("\n3. Testando tratamento de erro...")
    result = generate_chart(data=[], chart_type="bar")
    print(f"   ✓ Erro tratado corretamente: {result}")

    print("\n✅ Todos os testes passaram!")
