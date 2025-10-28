# 🧪 Test Suite - Credit Analytics Chatbot

Suite completa de testes para o agente LangChain de análise de crédito, implementada seguindo as melhores práticas do [guia oficial de testes do LangChain](https://python.langchain.com/docs/langchain/test/).

## 📊 Resultados Atuais

### Testes Unitários
- **104 testes PASSANDO** ✅
- **23 testes com ajustes necessários** ⚠️
- **Taxa de sucesso: ~82%**

### Coverage
```
Name                               Stmts   Miss   Cover
---------------------------------------------------------
src/config.py                         72      0 100.00%  ✅
src/utils/business_dictionary.py      56      2  96.43%  ✅
src/utils/sql_validator.py            82     14  82.93%  ✅
src/utils/db_connection.py            56     14  75.00%  🟡
src/utils/gcs_uploader.py             34     16  52.94%  🟡
src/tools/visualization_tool.py      135     97  28.15%  ⚠️
---------------------------------------------------------
TOTAL                                540    248  54.07%
```

## 🗂️ Estrutura de Testes

```
tests/
├── unit/                           # Testes unitários (rápidos, sem deps externas)
│   ├── test_sql_validator.py      # 34 testes - SEGURANÇA CRÍTICA ✅
│   ├── test_business_dictionary.py # 34 testes - Mapeamento NL-to-SQL ✅
│   ├── test_config.py             # 21 testes - Validação Pydantic ✅
│   ├── test_formatting.py         # 15 testes - Formatação PT-BR ✅
│   ├── test_chart_detection.py    # 6 testes - Auto-detecção gráficos ✅
│   ├── test_db_connection.py      # 10 testes - Pool de conexões ⚠️
│   └── test_gcs_uploader.py       # 7 testes - Upload GCS ⚠️
│
├── integration/                    # Testes de integração (com mocks)
│   ├── test_database_query_tool.py     # 8 testes - SQL generation + retry
│   ├── test_visualization_tool.py      # 6 testes - Geração de gráficos
│   ├── test_agent_trajectories.py      # 4 testes - AgentEvals (skipped)
│   └── test_retry_system.py            # 6 testes - Auto-correção SQL ✅
│
├── fixtures/                       # Dados de teste
│   ├── sample_credit_data.csv
│   └── mock_llm_responses.json
│
├── conftest.py                     # Fixtures compartilhadas
└── README.md                       # Este arquivo
```

## 🚀 Como Rodar os Testes

### Pré-requisitos

1. **Docker PostgreSQL rodando:**
   ```bash
   docker-compose up -d
   ```

2. **Dependências instaladas:**
   ```bash
   uv sync --dev
   ```

### Rodar Todos os Testes Unitários

```bash
# Testes unitários (rápidos, ~5s)
uv run pytest tests/unit -v

# Com coverage report
uv run pytest tests/unit --cov=src --cov-report=html

# Apenas testes de segurança SQL
uv run pytest tests/unit/test_sql_validator.py -v
```

### Rodar Testes de Integração

```bash
# Todos (alguns skipped por padrão)
uv run pytest tests/integration -v

# Apenas com Docker DB (remove --skip)
uv run pytest tests/integration -v --run-integration
```

### Rodar Testes por Marker

```bash
# Apenas unit tests
uv run pytest -m unit -v

# Apenas integration tests
uv run pytest -m integration -v

# Testes que logam no LangSmith
uv run pytest -m langsmith -v
```

### Ver Coverage Report HTML

```bash
uv run pytest tests/unit --cov=src --cov-report=html
open htmlcov/index.html  # ou xdg-open no Linux
```

## 📚 Bibliotecas Utilizadas

### Core Testing
- **pytest** - Framework de testes
- **pytest-cov** - Coverage reports
- **pytest-mock** - Mocking simplificado
- **pytest-asyncio** - Testes assíncronos

### LangChain Testing
- **agentevals** - Avaliação de trajetórias de agentes
  - Trajectory match (strict, unordered, subset, superset)
  - LLM-as-judge para qualidade de raciocínio
- **GenericFakeChatModel** - Mock de LLM determinístico

### Fixtures
- **Fake LLMs** - Respostas predefinidas para testes
- **Mock GCS** - Upload sem custos
- **Mock DB** - SQLAlchemy engine mockado
- **Sample Data** - Dados representativos do credit_train

## 🎯 Estratégia de Testes

### Tier 1: Unit Tests (Essencial) ✅
**Objetivo:** Testar lógica isolada, rápido, determinístico

- ✅ **test_sql_validator.py** - 34 testes de segurança SQL
  - Bloqueia todas operações perigosas (INSERT, DROP, DELETE, etc.)
  - Valida sintaxe com sqlglot
  - Testa SQL injection attempts
  - Auto-adiciona LIMIT para queries não-agregadas

- ✅ **test_business_dictionary.py** - 34 testes
  - Mapeamento NL-to-SQL (métricas, dimensões)
  - Busca por sinônimos (case-insensitive)
  - Few-shot examples válidos
  - Schema completo da tabela

- ✅ **test_formatting.py** - 15 testes PT-BR
  - Percentuais: `0.1525` → `"15,25%"`
  - Inteiros: `1234` → `"1.234"`
  - Decimais: `35.7` → `"35,7"`

- ✅ **test_chart_detection.py** - 6 testes
  - Datetime → line chart
  - Categórico → bar chart
  - Numérico >30 unique → histogram

### Tier 2: Integration Tests (Extra) 🟡
**Objetivo:** Testar interação entre componentes com mocks

- 🟡 **test_database_query_tool.py** - 8 testes
  - SQL generation com GenericFakeChatModel
  - Validação pipeline completo
  - Retry logic (até 3 tentativas)
  - Auto-correção de erros comuns

- 🟡 **test_visualization_tool.py** - 6 testes
  - Geração de gráficos (bar, line, pie, histogram)
  - Retorna content blocks com GCS URL
  - Mock completo de upload

- ⏸️ **test_agent_trajectories.py** - 4 testes (skipped)
  - Trajectory match (strict, unordered, superset)
  - LLM-as-judge para qualidade
  - **Nota:** Requer setup completo do agente

### Tier 3: E2E Tests (Opcional) ⏸️
**Objetivo:** Testes com LLM real usando VCR.py

- ⏸️ **Não implementado** - Conforme escolha do usuário
- Pode ser adicionado futuramente com `pytest-recording`

## 🔧 Configuração

### pytest.ini (via pyproject.toml)
```toml
[tool.pytest.ini_options]
markers = [
    "unit: fast unit tests without external dependencies",
    "integration: integration tests requiring external services",
    "langsmith: tests that log results to LangSmith",
]
addopts = ["-v", "--strict-markers", "--cov=src"]
```

### Fixtures Principais (conftest.py)

```python
# Fake LLMs
fake_llm_simple                     # Retorna SQL simples
fake_llm_with_tool_call            # Retorna tool call para agent
fake_llm_retry_scenario            # SQL com erro → corrigido

# Mock GCS
mock_gcs_client                    # Mock Google Cloud Storage
mock_gcs_uploader                  # Mock upload_image()

# Mock Database
mock_db_engine                     # SQLAlchemy engine mockado
mock_db_connection_manager         # DatabaseManager mockado

# Sample Data
sample_credit_data                 # 10 registros representativos
sample_aggregated_data             # Resultado de GROUP BY
sample_temporal_data               # Série temporal
```

## 🐛 Problemas Conhecidos e TODOs

### ⚠️ Ajustes Necessários

1. **test_config.py** (5 falhas)
   - Causa: `.env` carregado interfere com testes de defaults
   - Fix: Usar `patch.dict(os.environ, {}, clear=True)` em todos

2. **test_gcs_uploader.py** (7 falhas)
   - Causa: Interface `GCSUploader()` não aceita `project_id` como kwarg
   - Fix: Verificar assinatura correta do construtor

3. **test_db_connection.py** (6 falhas)
   - Causa: Métodos retornam tuplas `(bool, result)` em vez de valores diretos
   - Fix: Ajustar assertions para esperar tuplas

4. **test_sql_validator.py** (4 falhas)
   - Causa: Métodos privados `_parse_sql`, `_has_aggregation` não acessíveis
   - Fix: Remover testes de métodos privados ou torná-los públicos

### 🚀 Melhorias Futuras

- [ ] Aumentar coverage de `visualization_tool.py` (28% → 70%)
- [ ] Implementar testes E2E com VCR.py (Tier 3)
- [ ] Completar testes de `test_agent_trajectories.py`
- [ ] Adicionar testes de performance (query timeout, etc.)
- [ ] CI/CD: GitHub Actions workflow para rodar testes

## 📖 Referências

- [LangChain Testing Guide](https://python.langchain.com/docs/langchain/test/)
- [AgentEvals GitHub](https://github.com/langchain-ai/agentevals)
- [LangSmith Pytest Integration](https://docs.smith.langchain.com/pytest)
- [pytest Documentation](https://docs.pytest.org/)

## 💡 Dicas

### Debug de Testes Falhando
```bash
# Rodar apenas 1 teste com traceback completo
uv run pytest tests/unit/test_sql_validator.py::test_blocks_insert -vvs

# Parar no primeiro erro
uv run pytest tests/unit -x

# Ver print statements
uv run pytest tests/unit -s
```

### Atualizar Snapshots (se usar pytest-snapshot)
```bash
uv run pytest tests/unit --snapshot-update
```

### Profile de Performance
```bash
uv run pytest tests/unit --durations=10
```

---

**Criado por:** Claude Code
**Data:** 2025-10-27
**Versão:** 1.0.0
