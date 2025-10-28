"""
Unit tests for Business Dictionary

Tests NL-to-SQL mapping, synonym matching, and metadata retrieval.
"""
import pytest
from src.utils.business_dictionary import BusinessDictionary
from src.utils.sql_validator import sql_validator


# ==============================================================================
# Test Metric SQL Retrieval
# ==============================================================================

@pytest.mark.unit
def test_get_metric_sql_taxa_inadimplencia():
    """Should return correct SQL for taxa_inadimplencia metric."""
    sql = BusinessDictionary.get_metric_sql("taxa_inadimplencia")
    assert sql == 'AVG("TARGET")'


@pytest.mark.unit
def test_get_metric_sql_volume():
    """Should return correct SQL for volume metric."""
    sql = BusinessDictionary.get_metric_sql("volume")
    assert sql == "COUNT(*)"


@pytest.mark.unit
def test_get_metric_sql_idade_media():
    """Should return correct SQL for idade_media metric."""
    sql = BusinessDictionary.get_metric_sql("idade_media")
    assert sql == 'AVG("IDADE")'


@pytest.mark.unit
def test_get_metric_sql_nonexistent():
    """Should return None for non-existent metric."""
    sql = BusinessDictionary.get_metric_sql("nonexistent_metric")
    assert sql is None


# ==============================================================================
# Test Dimension Column Retrieval
# ==============================================================================

@pytest.mark.unit
def test_get_dimension_column_uf():
    """Should return correct column for UF dimension."""
    col = BusinessDictionary.get_dimension_column("uf")
    assert col == "UF"


@pytest.mark.unit
def test_get_dimension_column_sexo():
    """Should return correct column for sexo dimension."""
    col = BusinessDictionary.get_dimension_column("sexo")
    assert col == "SEXO"


@pytest.mark.unit
def test_get_dimension_column_classe_social():
    """Should return correct column for classe_social dimension."""
    col = BusinessDictionary.get_dimension_column("classe_social")
    assert col == "CLASSE_SOCIAL"


# ==============================================================================
# Test Synonym Matching for Metrics
# ==============================================================================

@pytest.mark.unit
def test_find_metric_by_synonym_inadimplencia():
    """Should find taxa_inadimplencia by synonym 'inadimplência'."""
    metric = BusinessDictionary.find_metric_by_synonym("Qual a inadimplência?")
    assert metric == "taxa_inadimplencia"


@pytest.mark.unit
def test_find_metric_by_synonym_default_rate():
    """Should find taxa_inadimplencia by synonym 'default rate'."""
    metric = BusinessDictionary.find_metric_by_synonym("What is the default rate?")
    assert metric == "taxa_inadimplencia"


@pytest.mark.unit
def test_find_metric_by_synonym_quantidade():
    """Should find volume by synonym 'quantidade'."""
    metric = BusinessDictionary.find_metric_by_synonym("Qual a quantidade total?")
    assert metric == "volume"


@pytest.mark.unit
def test_find_metric_by_synonym_idade_media():
    """Should find idade_media by synonym 'média de idade'."""
    metric = BusinessDictionary.find_metric_by_synonym("Qual a média de idade?")
    assert metric == "idade_media"


@pytest.mark.unit
def test_find_metric_by_synonym_case_insensitive():
    """Synonym matching should be case-insensitive."""
    metric_upper = BusinessDictionary.find_metric_by_synonym("INADIMPLÊNCIA")
    metric_lower = BusinessDictionary.find_metric_by_synonym("inadimplência")
    assert metric_upper == metric_lower == "taxa_inadimplencia"


@pytest.mark.unit
def test_find_metric_by_synonym_not_found():
    """Should return None for text with no matching synonym."""
    metric = BusinessDictionary.find_metric_by_synonym("palavras aleatórias sem sentido")
    assert metric is None


# ==============================================================================
# Test Synonym Matching for Dimensions
# ==============================================================================

@pytest.mark.unit
def test_find_dimension_by_synonym_estado():
    """Should find uf dimension by synonym 'estado'."""
    dim = BusinessDictionary.find_dimension_by_synonym("Por estado")
    assert dim == "uf"


@pytest.mark.unit
def test_find_dimension_by_synonym_genero():
    """Should find sexo dimension by synonym 'gênero'."""
    dim = BusinessDictionary.find_dimension_by_synonym("Por gênero")
    assert dim == "sexo"


@pytest.mark.unit
def test_find_dimension_by_synonym_classe():
    """Should find classe_social by synonym 'classe'."""
    dim = BusinessDictionary.find_dimension_by_synonym("Por classe social")
    assert dim == "classe_social"


@pytest.mark.unit
def test_find_dimension_by_synonym_periodo():
    """Should find data_referencia by synonym 'período'."""
    dim = BusinessDictionary.find_dimension_by_synonym("Evolução no período")
    assert dim == "data_referencia"


# ==============================================================================
# Test Few-Shot Examples
# ==============================================================================

@pytest.mark.unit
def test_get_few_shot_examples_default():
    """Should return 3 examples by default."""
    examples = BusinessDictionary.get_few_shot_examples()
    assert len(examples) == 3
    assert all("nl" in ex and "sql" in ex for ex in examples)


@pytest.mark.unit
def test_get_few_shot_examples_custom_n():
    """Should return N examples when specified."""
    examples = BusinessDictionary.get_few_shot_examples(n=5)
    assert len(examples) == 5


@pytest.mark.unit
def test_few_shot_examples_have_valid_sql():
    """All few-shot examples should have valid SQL."""
    examples = BusinessDictionary.EXEMPLOS

    for example in examples:
        sql = example["sql"]
        # Validate SQL syntax and security
        is_valid, formatted = sql_validator.validate(sql)
        assert is_valid is True, f"Invalid SQL in example: {example['nl']}"


# ==============================================================================
# Test Table Description
# ==============================================================================

@pytest.mark.unit
def test_get_table_description_contains_table_name():
    """Table description should contain table name."""
    desc = BusinessDictionary.get_table_description()
    assert "credit_train" in desc


@pytest.mark.unit
def test_get_table_description_contains_columns():
    """Table description should list all columns."""
    desc = BusinessDictionary.get_table_description()
    for col in BusinessDictionary.TABLE_SCHEMA["colunas"].keys():
        assert col in desc


@pytest.mark.unit
def test_get_table_description_contains_k_anonymity_warning():
    """Table description should warn about k-anonymity."""
    desc = BusinessDictionary.get_table_description()
    assert "k-anonimato" in desc or "HAVING COUNT(*) >= 20" in desc


@pytest.mark.unit
def test_get_table_description_contains_double_quotes_warning():
    """Table description should warn about using double quotes."""
    desc = BusinessDictionary.get_table_description()
    assert "aspas duplas" in desc or '"UF"' in desc


# ==============================================================================
# Test Valid Values
# ==============================================================================

@pytest.mark.unit
def test_valid_ufs_has_27_states():
    """Brazil has 27 states (26 + Federal District)."""
    assert len(BusinessDictionary.VALID_UFS) == 27


@pytest.mark.unit
def test_valid_ufs_contains_sp_rj_mg():
    """Valid UFs should contain major states."""
    assert "SP" in BusinessDictionary.VALID_UFS
    assert "RJ" in BusinessDictionary.VALID_UFS
    assert "MG" in BusinessDictionary.VALID_UFS


@pytest.mark.unit
def test_valid_sexo_has_two_values():
    """Valid sexo should have M and F."""
    assert BusinessDictionary.VALID_SEXO == ["M", "F"]


# ==============================================================================
# Test Temporal Aggregations
# ==============================================================================

@pytest.mark.unit
def test_temporal_aggregation_mensal():
    """Monthly aggregation should use DATE_TRUNC month."""
    mensal = BusinessDictionary.AGREGACOES_TEMPORAIS["mensal"]
    assert "DATE_TRUNC" in mensal["sql"]
    assert "month" in mensal["sql"]
    assert "REF_DATE" in mensal["sql"]


@pytest.mark.unit
def test_temporal_aggregation_anual():
    """Annual aggregation should use DATE_TRUNC year."""
    anual = BusinessDictionary.AGREGACOES_TEMPORAIS["anual"]
    assert "DATE_TRUNC" in anual["sql"]
    assert "year" in anual["sql"]


# ==============================================================================
# Test Age Ranges
# ==============================================================================

@pytest.mark.unit
def test_faixas_etarias_cover_all_ages():
    """Age ranges should cover all possible ages."""
    faixas = BusinessDictionary.FAIXAS_ETARIAS

    # Should have range for <18, 18-24, 25-34, 35-44, 45-59, 60+
    assert len(faixas) >= 6

    # Check specific ranges
    faixa_names = [f["nome"] for f in faixas]
    assert "<18" in faixa_names
    assert "18-24" in faixa_names
    assert "60+" in faixa_names


@pytest.mark.unit
def test_faixas_etarias_have_conditions():
    """Each age range should have a SQL condition."""
    faixas = BusinessDictionary.FAIXAS_ETARIAS

    for faixa in faixas:
        assert "nome" in faixa
        assert "condicao" in faixa
        assert "IDADE" in faixa["condicao"]


# ==============================================================================
# Test Metric Formats
# ==============================================================================

@pytest.mark.unit
def test_metric_formats_defined():
    """All metrics should have a defined format."""
    for metric_name, metric_data in BusinessDictionary.METRICAS.items():
        assert "formato" in metric_data
        assert metric_data["formato"] in ["percentual", "inteiro", "decimal_1"]


# ==============================================================================
# Test Dimension Normalizations
# ==============================================================================

@pytest.mark.unit
def test_dimension_uf_normalizes_to_upper():
    """UF dimension should normalize to uppercase."""
    uf_dim = BusinessDictionary.DIMENSOES["uf"]
    assert "UPPER" in uf_dim["normalizacao"]
    assert "TRIM" in uf_dim["normalizacao"]


@pytest.mark.unit
def test_dimension_classe_social_normalizes_to_lower():
    """Classe social should normalize to lowercase."""
    classe_dim = BusinessDictionary.DIMENSOES["classe_social"]
    assert "LOWER" in classe_dim["normalizacao"]
    assert "TRIM" in classe_dim["normalizacao"]
