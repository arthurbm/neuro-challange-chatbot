"""
Tool para gerar visualizações matplotlib e retornar como base64.

Suporta múltiplos tipos de gráficos com formatação PT-BR.
"""

import base64
import io
import logging
from typing import Any, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from langchain.tools import tool
from pydantic import BaseModel, Field

from src.utils.gcs_uploader import gcs_uploader

# Configurar matplotlib para não usar GUI (necessário para ambientes headless)
matplotlib.use("Agg")

# Configurar logger
logger = logging.getLogger(__name__)


class GenerateChartInput(BaseModel):
    """Schema de input para a tool generate_chart."""

    data: list[dict[str, Any]] = Field(
        description="Dados para plotar no formato lista de dicionários. "
        "Exemplo: [{'uf': 'SP', 'taxa_inadimplencia': 0.15, 'n': 1000}]"
    )
    chart_type: str = Field(
        default="auto",
        description="Tipo de gráfico: 'bar' (barras), 'line' (linha), 'pie' (pizza), "
        "'histogram' (histograma), 'auto' (detecta automaticamente)",
    )
    title: Optional[str] = Field(
        default=None, description="Título do gráfico (gera automaticamente se omitido)"
    )
    x_column: Optional[str] = Field(
        default=None, description="Nome da coluna para eixo X (detecta automaticamente)"
    )
    y_column: Optional[str] = Field(
        default=None, description="Nome da coluna para eixo Y (detecta automaticamente)"
    )


def _format_number_ptbr(value: float, format_type: str = "decimal") -> str:
    """
    Formata número no padrão PT-BR.

    Args:
        value: Valor numérico
        format_type: 'decimal', 'percentage', 'integer'

    Returns:
        String formatada
    """
    if format_type == "percentage":
        # Percentual: 15,25%
        return f"{value * 100:.2f}%".replace(".", ",")
    elif format_type == "integer":
        # Inteiro com separador de milhar: 1.234
        return f"{int(value):,}".replace(",", ".")
    else:
        # Decimal: 35,7
        return f"{value:.1f}".replace(".", ",")


def _detect_chart_type(df: pd.DataFrame, x_col: str, y_col: str) -> str:
    """
    Detecta automaticamente o melhor tipo de gráfico baseado nos dados.

    Args:
        df: DataFrame com os dados
        x_col: Nome da coluna X
        y_col: Nome da coluna Y

    Returns:
        Tipo de gráfico: 'bar', 'line', 'histogram'
    """
    # Se X é temporal, usar linha
    if pd.api.types.is_datetime64_any_dtype(df[x_col]):
        return "line"

    # Se X é categórica com poucas categorias, usar barras
    if df[x_col].dtype == "object" or df[x_col].nunique() < 30:
        return "bar"

    # Se X é numérica contínua, usar histograma
    if pd.api.types.is_numeric_dtype(df[x_col]) and df[x_col].nunique() > 30:
        return "histogram"

    # Padrão: barras
    return "bar"


def _detect_columns(df: pd.DataFrame) -> tuple[str, str]:
    """
    Detecta automaticamente as colunas X e Y baseado nos dados.

    Args:
        df: DataFrame com os dados

    Returns:
        Tupla (x_column, y_column)
    """
    columns = df.columns.tolist()

    # Se há apenas 2 colunas, usar elas
    if len(columns) == 2:
        return columns[0], columns[1]

    # Procurar por colunas de identificação (primeira coluna geralmente é X)
    # e colunas numéricas (geralmente Y)
    x_candidates = [
        col
        for col in columns
        if df[col].dtype == "object"
        or col.lower() in ["uf", "sexo", "classe", "mes", "date", "data"]
    ]
    y_candidates = [
        col
        for col in columns
        if pd.api.types.is_numeric_dtype(df[col])
        and col.lower() not in ["n", "count", "total"]
    ]

    if x_candidates and y_candidates:
        return x_candidates[0], y_candidates[0]

    # Fallback: primeira e segunda coluna
    return columns[0], columns[1] if len(columns) > 1 else columns[0]


def _create_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    ax: plt.Axes,
    show_values: bool = True,
) -> None:
    """
    Cria gráfico de barras horizontais.

    Args:
        df: DataFrame
        x_col: Coluna X (categorias)
        y_col: Coluna Y (valores)
        title: Título
        ax: Axes do matplotlib
        show_values: Se deve mostrar valores nas barras
    """
    # Ordenar por valor
    df_sorted = df.sort_values(y_col, ascending=True)

    # Criar barras horizontais
    bars = ax.barh(range(len(df_sorted)), df_sorted[y_col], color="#2E86AB")
    ax.set_yticks(range(len(df_sorted)))
    ax.set_yticklabels(df_sorted[x_col])

    # Labels
    ax.set_xlabel(y_col.replace("_", " ").title())
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3, axis="x")

    # Adicionar valores nas barras
    if show_values:
        for i, (idx, row) in enumerate(df_sorted.iterrows()):
            value = row[y_col]

            # Detectar se é percentual (valor entre 0 e 1 ou nome da coluna indica taxa)
            is_percentage = (
                0 <= value <= 1 and "taxa" in y_col.lower()
            ) or "percentual" in y_col.lower()

            if is_percentage:
                label = _format_number_ptbr(value, "percentage")
            else:
                label = _format_number_ptbr(value, "decimal")

            # Adicionar n se existir
            if "n" in df.columns:
                n_val = row["n"]
                label += f" (n={_format_number_ptbr(n_val, 'integer')})"

            ax.text(value, i, f"  {label}", va="center", ha="left", fontsize=9)


def _create_line_chart(
    df: pd.DataFrame, x_col: str, y_col: str, title: str, ax: plt.Axes
) -> None:
    """
    Cria gráfico de linha (temporal).

    Args:
        df: DataFrame
        x_col: Coluna X (temporal)
        y_col: Coluna Y (valores)
        title: Título
        ax: Axes do matplotlib
    """
    # Ordenar por X
    df_sorted = df.sort_values(x_col)

    # Plotar linha
    ax.plot(
        df_sorted[x_col],
        df_sorted[y_col],
        marker="o",
        linewidth=2,
        markersize=6,
        color="#2E86AB",
    )

    # Labels
    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel(y_col.replace("_", " ").title())
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3)

    # Rotacionar labels do eixo X se necessário
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    # Adicionar valores nos pontos (apenas se não houver muitos pontos)
    if len(df_sorted) <= 15:
        for idx, row in df_sorted.iterrows():
            value = row[y_col]
            is_percentage = (0 <= value <= 1 and "taxa" in y_col.lower()) or "percentual" in y_col.lower()

            if is_percentage:
                label = _format_number_ptbr(value, "percentage")
            else:
                label = _format_number_ptbr(value, "decimal")

            ax.annotate(
                label,
                (row[x_col], value),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=8,
            )


def _create_histogram(
    df: pd.DataFrame, x_col: str, title: str, ax: plt.Axes, bins: int = 30
) -> None:
    """
    Cria histograma.

    Args:
        df: DataFrame
        x_col: Coluna para histograma
        title: Título
        ax: Axes do matplotlib
        bins: Número de bins
    """
    ax.hist(df[x_col].dropna(), bins=bins, edgecolor="black", color="#2E86AB", alpha=0.7)

    # Labels
    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel("Frequência")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3, axis="y")

    # Adicionar linha de mediana
    median = df[x_col].median()
    ax.axvline(
        median, color="red", linestyle="--", linewidth=2, label=f"Mediana: {median:.1f}"
    )
    ax.legend()


def _create_pie_chart(
    df: pd.DataFrame, x_col: str, y_col: str, title: str, ax: plt.Axes
) -> None:
    """
    Cria gráfico de pizza.

    Args:
        df: DataFrame
        x_col: Coluna de categorias
        y_col: Coluna de valores
        title: Título
        ax: Axes do matplotlib
    """
    # Criar pizza
    wedges, texts, autotexts = ax.pie(
        df[y_col],
        labels=df[x_col],
        autopct=lambda pct: f"{pct:.1f}%".replace(".", ","),
        startangle=90,
        colors=plt.cm.Set3.colors,
    )

    # Melhorar formatação dos textos
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)


@tool
def generate_chart(
    data: list[dict[str, Any]],
    chart_type: str = "auto",
    title: Optional[str] = None,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Gera visualização matplotlib e retorna como array de content blocks.

    Esta tool cria gráficos profissionais com formatação PT-BR (vírgula decimal,
    separador de milhar) e retorna como array de content blocks (texto + imagem).

    O Agent Chat UI renderiza imagens Base64ContentBlock automaticamente inline.

    Args:
        data: Lista de dicionários com os dados. Exemplo:
              [{"uf": "SP", "taxa_inadimplencia": 0.15, "n": 1000}]
        chart_type: Tipo de gráfico ('bar', 'line', 'pie', 'histogram', 'auto').
                   'auto' detecta automaticamente o melhor tipo.
        title: Título do gráfico. Se None, gera automaticamente.
        x_column: Nome da coluna para eixo X. Se None, detecta automaticamente.
        y_column: Nome da coluna para eixo Y. Se None, detecta automaticamente.

    Returns:
        Array de content blocks (similar a HumanMessage multimodal):
        [
            {"type": "text", "text": "Descrição do gráfico"},
            {"type": "image", "source_type": "base64", "data": str, "mime_type": "image/png"}
        ]

        O Agent Chat UI itera pelo array e renderiza cada block automaticamente.

    Exemplos de uso:
        # Gráfico de barras por UF
        generate_chart(
            data=[{"uf": "SP", "taxa": 0.15}, {"uf": "RJ", "taxa": 0.12}],
            chart_type="bar",
            title="Taxa de Inadimplência por UF"
        )
        # Retorna: [{"type": "text", ...}, {"type": "image", ...}]

        # Gráfico temporal (auto-detecta tipo linha)
        generate_chart(
            data=[{"mes": "2017-01", "taxa": 0.14}, {"mes": "2017-02", "taxa": 0.16}],
            chart_type="auto"
        )
        # Agent Chat UI renderiza automaticamente a imagem inline
    """
    try:
        # Validar dados
        if not data or len(data) == 0:
            return [{"type": "text", "text": "Erro: Nenhum dado fornecido para gerar gráfico."}]

        # Converter para DataFrame
        df = pd.DataFrame(data)

        # Detectar colunas X e Y automaticamente se não fornecidas
        if x_column is None or y_column is None:
            detected_x, detected_y = _detect_columns(df)
            x_column = x_column or detected_x
            y_column = y_column or detected_y

        # Validar colunas
        if x_column not in df.columns:
            return [{"type": "text", "text": f"Erro: Coluna '{x_column}' não encontrada nos dados. Colunas disponíveis: {list(df.columns)}"}]
        if y_column not in df.columns:
            return [{"type": "text", "text": f"Erro: Coluna '{y_column}' não encontrada nos dados. Colunas disponíveis: {list(df.columns)}"}]

        # Detectar tipo de gráfico automaticamente
        if chart_type == "auto":
            chart_type = _detect_chart_type(df, x_column, y_column)
            logger.info(f"Auto-detected chart type: {chart_type}")

        # Gerar título automaticamente se não fornecido
        if title is None:
            title = f"{y_column.replace('_', ' ').title()} por {x_column.replace('_', ' ').title()}"

        # Criar figura
        fig, ax = plt.subplots(figsize=(10, 6))

        # Criar gráfico baseado no tipo
        if chart_type == "bar":
            _create_bar_chart(df, x_column, y_column, title, ax)
        elif chart_type == "line":
            _create_line_chart(df, x_column, y_column, title, ax)
        elif chart_type == "histogram":
            _create_histogram(df, x_column, title, ax)
        elif chart_type == "pie":
            _create_pie_chart(df, x_column, y_column, title, ax)
        else:
            plt.close()
            return [{"type": "text", "text": f"Erro: Tipo de gráfico '{chart_type}' não suportado. Use: bar, line, pie, histogram, ou auto."}]

        # Ajustar layout
        plt.tight_layout()

        # Salvar imagem em buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        buffer.seek(0)
        plt.close(fig)

        # Upload para Google Cloud Storage
        try:
            image_url = gcs_uploader.upload_image(
                image_buffer=buffer,
                content_type="image/png",
                filename=None,  # Auto-gera UUID
                public=True
            )
        except Exception as e:
            logger.error(f"Erro ao fazer upload: {e}")
            return [{"type": "text", "text": f"Erro ao fazer upload da imagem: {str(e)}"}]

        # Retornar array de content blocks com URL pública
        # O Agent Chat UI renderiza URLs automaticamente
        return [
            {
                "type": "text",
                "text": f"Visualização gerada: {title}"
            },
            {
                "type": "image",
                "source_type": "url",
                "url": image_url,
                "mime_type": "image/png"
            }
        ]

    except Exception as e:
        logger.error(f"Erro ao gerar gráfico: {e}", exc_info=True)
        return [{"type": "text", "text": f"Erro ao gerar visualização: {str(e)}"}]
