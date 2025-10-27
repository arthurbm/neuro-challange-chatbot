"""
Dicionário de Negócio - Mapeamento de termos em linguagem natural para SQL.

Baseado na análise exploratória de dados (EDA).
"""

from typing import TypedDict


class MetricDefinition(TypedDict):
    """Definição de uma métrica de negócio."""

    sql: str
    formato: str
    descricao: str
    sinonimos: list[str]


class DimensionDefinition(TypedDict):
    """Definição de uma dimensão de negócio."""

    coluna: str
    tipo: str
    descricao: str
    sinonimos: list[str]
    normalizacao: str | None
    valores_validos: list[str] | None


class BusinessDictionary:
    """Dicionário de termos de negócio para geração de SQL."""

    # UFs válidas do Brasil
    VALID_UFS = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    ]

    VALID_SEXO = ["M", "F"]

    # Métricas canônicas
    METRICAS: dict[str, MetricDefinition] = {
        "taxa_inadimplencia": {
            "sql": 'AVG("TARGET")',
            "formato": "percentual",
            "descricao": "Proporção de inadimplentes (TARGET=1)",
            "sinonimos": [
                "inadimplência",
                "inadimplencia",
                "mau pagador",
                "default rate",
                "taxa de default",
                "percentual de inadimplentes",
                "proporção de inadimplentes",
                "taxa de mau pagador",
            ],
        },
        "volume": {
            "sql": "COUNT(*)",
            "formato": "inteiro",
            "descricao": "Número total de registros",
            "sinonimos": [
                "quantidade",
                "total",
                "contagem",
                "número de registros",
                "número de casos",
                "qtd",
                "n",
            ],
        },
        "idade_media": {
            "sql": 'AVG("IDADE")',
            "formato": "decimal_1",
            "descricao": "Idade média em anos",
            "sinonimos": ["média de idade", "idade média", "média etária", "idade media"],
        },
        "idade_min": {
            "sql": 'MIN("IDADE")',
            "formato": "decimal_1",
            "descricao": "Idade mínima",
            "sinonimos": ["menor idade", "idade mínima", "idade minima"],
        },
        "idade_max": {
            "sql": 'MAX("IDADE")',
            "formato": "decimal_1",
            "descricao": "Idade máxima",
            "sinonimos": ["maior idade", "idade máxima", "idade maxima"],
        },
    }

    # Dimensões de negócio
    DIMENSOES: dict[str, DimensionDefinition] = {
        "uf": {
            "coluna": "UF",
            "tipo": "categorica",
            "descricao": "Unidade Federativa (estado brasileiro)",
            "sinonimos": ["estado", "UF", "uf", "unidade federativa", "região", "estados"],
            "normalizacao": 'UPPER(TRIM("UF"))',
            "valores_validos": VALID_UFS,
        },
        "sexo": {
            "coluna": "SEXO",
            "tipo": "categorica",
            "descricao": "Sexo do indivíduo",
            "sinonimos": ["gênero", "genero", "sexo"],
            "normalizacao": 'UPPER(TRIM("SEXO"))',
            "valores_validos": VALID_SEXO,
        },
        "classe_social": {
            "coluna": "CLASSE_SOCIAL",
            "tipo": "categorica",
            "descricao": "Classe social estimada",
            "sinonimos": ["classe", "classe social", "categoria social", "classe economica"],
            "normalizacao": 'LOWER(TRIM("CLASSE_SOCIAL"))',
            "valores_validos": None,  # Variável (alta, média, baixa, etc.)
        },
        "idade": {
            "coluna": "IDADE",
            "tipo": "numerica",
            "descricao": "Idade do indivíduo em anos",
            "sinonimos": ["idade", "anos", "faixa etária", "faixa etaria"],
            "normalizacao": None,
            "valores_validos": None,
        },
        "obito": {
            "coluna": "OBITO",
            "tipo": "booleana",
            "descricao": "Indicador de óbito",
            "sinonimos": ["óbito", "obito", "falecimento", "morreu", "falecido"],
            "normalizacao": None,
            "valores_validos": None,
        },
        "data_referencia": {
            "coluna": "REF_DATE",
            "tipo": "temporal",
            "descricao": "Data de referência do registro",
            "sinonimos": ["data", "período", "periodo", "mês", "mes", "ano", "quando", "data referencia"],
            "normalizacao": None,
            "valores_validos": None,
        },
    }

    # Agregações temporais
    AGREGACOES_TEMPORAIS = {
        "mensal": {
            "sql": 'DATE_TRUNC(\'month\', "REF_DATE")',
            "sinonimos": ["por mês", "por mes", "mensal", "mensalmente", "a cada mês", "a cada mes", "evolução mensal"],
        },
        "anual": {
            "sql": 'DATE_TRUNC(\'year\', "REF_DATE")',
            "sinonimos": ["por ano", "anual", "anualmente", "a cada ano", "evolução anual"],
        },
    }

    # Faixas etárias pré-definidas
    FAIXAS_ETARIAS = [
        {"nome": "<18", "condicao": '"IDADE" < 18'},
        {"nome": "18-24", "condicao": '"IDADE" >= 18 AND "IDADE" < 25'},
        {"nome": "25-34", "condicao": '"IDADE" >= 25 AND "IDADE" < 35'},
        {"nome": "35-44", "condicao": '"IDADE" >= 35 AND "IDADE" < 45'},
        {"nome": "45-59", "condicao": '"IDADE" >= 45 AND "IDADE" < 60'},
        {"nome": "60+", "condicao": '"IDADE" >= 60'},
    ]

    # Exemplos de mapeamento NL → SQL (para few-shot learning)
    EXEMPLOS = [
        {
            "nl": "Qual a taxa de inadimplência média por UF?",
            "sql": 'SELECT "UF", AVG("TARGET") as taxa_inadimplencia FROM credit_train GROUP BY "UF" HAVING COUNT(*) >= 20 ORDER BY taxa_inadimplencia DESC',
            "explicacao": "Agrupa por UF, calcula média do TARGET, aplica k-anonimato (>=20)",
        },
        {
            "nl": "Quantas pessoas têm mais de 60 anos?",
            "sql": 'SELECT COUNT(*) as volume FROM credit_train WHERE "IDADE" >= 60',
            "explicacao": "Filtra por idade e conta registros",
        },
        {
            "nl": "Taxa de inadimplência por sexo e classe social",
            "sql": 'SELECT "SEXO", LOWER(TRIM("CLASSE_SOCIAL")) as classe, AVG("TARGET") as taxa FROM credit_train GROUP BY "SEXO", "CLASSE_SOCIAL" HAVING COUNT(*) >= 20',
            "explicacao": "Agrupa por duas dimensões, normaliza classe social",
        },
        {
            "nl": "Evolução mensal da inadimplência",
            "sql": 'SELECT DATE_TRUNC(\'month\', "REF_DATE") as mes, AVG("TARGET") as taxa FROM credit_train GROUP BY 1 ORDER BY 1',
            "explicacao": "Agrupa por mês usando DATE_TRUNC",
        },
        {
            "nl": "Compare inadimplência entre homens e mulheres",
            "sql": 'SELECT "SEXO", COUNT(*) as n, AVG("TARGET") as taxa_inadimplencia FROM credit_train WHERE "SEXO" IS NOT NULL GROUP BY "SEXO" HAVING COUNT(*) >= 20',
            "explicacao": "Compara taxas entre sexos, filtra nulos",
        },
    ]

    # Schema da tabela
    TABLE_SCHEMA = {
        "nome": "credit_train",
        "descricao": "Base de treino de concessão de crédito com ~170k registros",
        "periodo": "2017-01 a 2017-08",
        "colunas": {
            "REF_DATE": "TIMESTAMPTZ - Data de referência do registro",
            "TARGET": "SMALLINT - Alvo binário (0=bom pagador, 1=mau pagador)",
            "SEXO": "VARCHAR(1) - Sexo (M/F)",
            "IDADE": "NUMERIC - Idade em anos",
            "OBITO": "BOOLEAN - Indicador de óbito (TRUE=sim, FALSE/NULL=não)",
            "UF": "VARCHAR(2) - Unidade Federativa (estado)",
            "CLASSE_SOCIAL": "VARCHAR(20) - Classe social (alta, média, baixa)",
        },
    }

    @classmethod
    def get_metric_sql(cls, metric_name: str) -> str | None:
        """Retorna SQL para uma métrica, se encontrada."""
        return cls.METRICAS.get(metric_name, {}).get("sql")

    @classmethod
    def get_dimension_column(cls, dimension_name: str) -> str | None:
        """Retorna nome da coluna para uma dimensão."""
        return cls.DIMENSOES.get(dimension_name, {}).get("coluna")

    @classmethod
    def find_metric_by_synonym(cls, text: str) -> str | None:
        """Procura métrica por sinônimo no texto."""
        text_lower = text.lower()

        for metric_key, metric_data in cls.METRICAS.items():
            for sinonimo in metric_data["sinonimos"]:
                if sinonimo.lower() in text_lower:
                    return metric_key

        return None

    @classmethod
    def find_dimension_by_synonym(cls, text: str) -> str | None:
        """Procura dimensão por sinônimo no texto."""
        text_lower = text.lower()

        for dim_key, dim_data in cls.DIMENSOES.items():
            for sinonimo in dim_data["sinonimos"]:
                if sinonimo.lower() in text_lower:
                    return dim_key

        return None

    @classmethod
    def get_few_shot_examples(cls, n: int = 3) -> list[dict]:
        """Retorna N exemplos para few-shot learning."""
        return cls.EXEMPLOS[:n]

    @classmethod
    def get_table_description(cls) -> str:
        """Retorna descrição completa da tabela para o LLM."""
        desc = [
            f"Tabela: {cls.TABLE_SCHEMA['nome']}",
            f"Descrição: {cls.TABLE_SCHEMA['descricao']}",
            f"Período: {cls.TABLE_SCHEMA['periodo']}",
            "\nColunas:",
        ]

        for col, col_desc in cls.TABLE_SCHEMA["colunas"].items():
            desc.append(f"  • {col}: {col_desc}")

        desc.append("\n⚠️ IMPORTANTE: Use aspas duplas nas colunas (ex: \"UF\", \"TARGET\")")
        desc.append(f"⚠️ Aplique k-anonimato: HAVING COUNT(*) >= 20")

        return "\n".join(desc)


# Instância global (não necessária, mas mantida por consistência)
business_dict = BusinessDictionary()
