# Credit Analytics Chatbot

Chatbot inteligente para análise de dados de crédito usando LLM, capaz de interpretar perguntas em linguagem natural, gerar SQL seguro e retornar insights formatados.

## Características

- **Tool única auto-contida**: Query inteligente com validação, retry e auto-correção
- **Segurança**: Read-only, k-anonimato, validação SQL com sqlglot
- **LangChain 1.0**: Arquitetura moderna baseada em tools
- **Deploy no LangSmith**: Observabilidade completa com tracing
- **Agent Chat UI**: Interface web pronta para uso

## Quick Start (Desenvolvimento Local)

### 1. Pré-requisitos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (gerenciador de pacotes)
- Docker & Docker Compose

### 2. Setup do Ambiente

```bash
# Clonar o repositório
git clone <repo-url>
cd neuro-challange-chatbot

# Instalar dependências com uv
uv sync

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas API keys (OpenAI, LangSmith)
```

### 3. Iniciar Banco de Dados Local

```bash
# Subir Postgres em container
docker-compose up -d

# Verificar se está rodando
docker-compose ps

# Opcional: Subir também o pgAdmin
docker-compose --profile admin up -d
# Acesse: http://localhost:5050 (admin@credit.local / admin)
```

### 4. Carregar Dados

```bash
# Carregar dataset completo (~170k linhas)
uv run python scripts/load_data.py

# Ou carregar amostra para testes (1000 linhas)
uv run python scripts/load_data.py --sample 1000
```

### 5. Testar Conexão ao Banco

```bash
# Via psql
docker exec -it credit-analytics-db psql -U chatbot_reader -d credit_analytics

# Ou via Python
uv run python -c "from src.config import config; print(config.database.connection_string)"
```

## Estrutura do Projeto

```
neuro-challange-chatbot/
├── src/
│   ├── __init__.py
│   ├── agent.py                 # Agente LangChain principal
│   ├── config.py                # Configurações centralizadas
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── database_query_tool.py    # Tool SQL inteligente
│   │   └── visualization_tool.py     # Tool de gráficos matplotlib
│   └── utils/
│       ├── __init__.py
│       ├── sql_validator.py          # Validação com sqlglot
│       ├── business_dictionary.py    # Mapeamento NL→SQL
│       └── db_connection.py          # Pool de conexões
├── scripts/
│   ├── init_db.sql              # Schema inicial do banco
│   └── load_data.py             # Script de carga de dados
├── tests/
│   ├── __init__.py
│   ├── test_tools.py
│   └── test_agent.py
├── eval/
│   └── questions_dataset.json   # Dataset de avaliação
├── notebooks/
│   └── eda_credit_data.ipynb    # Análise exploratória
├── docker-compose.yml           # Postgres + pgAdmin
├── .env.example                 # Template de variáveis
├── .gitignore
├── pyproject.toml               # Dependências (gerenciado por uv)
├── langgraph.json               # Config para deploy LangSmith
└── README.md
```

## Comandos Úteis

### Docker Compose

```bash
# Iniciar serviços
docker-compose up -d

# Parar serviços
docker-compose down

# Ver logs
docker-compose logs -f postgres

# Resetar banco (apaga volumes)
docker-compose down -v
```

### Desenvolvimento

```bash
# Instalar nova dependência
uv add <package>

# Rodar testes
uv run pytest

# Formatar código
uv run ruff format .

# Lint
uv run ruff check .
```

### Banco de Dados

```bash
# Conectar ao Postgres (dentro do container)
docker exec -it credit-analytics-db psql -U postgres -d credit_analytics

# Backup do banco
docker exec credit-analytics-db pg_dump -U postgres credit_analytics > backup.sql

# Restore
docker exec -i credit-analytics-db psql -U postgres credit_analytics < backup.sql

# Ver tabelas e dados
docker exec -it credit-analytics-db psql -U chatbot_reader -d credit_analytics -c "\dt"
docker exec -it credit-analytics-db psql -U chatbot_reader -d credit_analytics -c "SELECT COUNT(*) FROM credit_train;"
```

## Testando o Agente

```python
from src.agent import agent

# Exemplo de uso
response = agent.invoke({
    "messages": [
        {"role": "user", "content": "Qual a taxa de inadimplência média por UF?"}
    ]
})

print(response["messages"][-1].content)
```

## Dados

- **Dataset**: train.gz (~170k registros)
- **Período**: 2017-01 a 2017-08
- **Colunas**:
  - `ref_date`: Data de referência
  - `target`: Inadimplência (0=bom, 1=mau pagador)
  - `sexo`: M/F
  - `idade`: Idade em anos
  - `obito`: Indicador de óbito (boolean)
  - `uf`: Estado brasileiro (27 UFs)
  - `classe_social`: alta/média/baixa

## Segurança

- **Read-only**: Usuário do chatbot só tem SELECT
- **K-anonimato**: k=20 (grupos pequenos são filtrados)
- **SQL Validation**: sqlglot bloqueia DDL/DML
- **Timeout**: Queries limitadas a 10s
- **Guardrails**: LIMIT padrão de 100 linhas

## Deploy

### Deploy no LangSmith

```bash
# Testar localmente
langgraph dev

# Deploy para LangSmith Cloud
langgraph push

# Ver status
langgraph deployments list
```

### Agent Chat UI

```bash
# Clonar e configurar
git clone https://github.com/langchain-ai/agent-chat-ui
cd agent-chat-ui

# Configurar .env
echo "LANGSMITH_URL=<sua-url>" > .env
echo "LANGSMITH_DEPLOYMENT_NAME=credit_agent" >> .env

# Rodar
npm install
npm run dev
```

## Documentação

- [LangChain 1.0 Docs](https://docs.langchain.com/)
- [LangSmith](https://docs.smith.langchain.com/)
- [Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui)

## Contribuindo

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -m 'Add nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Abra um Pull Request

## Licença

MIT

---

## Decisões Técnicas e Arquiteturais

Esta seção documenta as principais decisões tomadas durante o desenvolvimento do chatbot de análise de dados, justificativas e trade-offs considerados.

### 1. Contexto do Desafio

O objetivo era criar um chatbot capaz de:
- Interpretar perguntas em linguagem natural sobre dados de crédito
- Converter perguntas em queries SQL válidas
- Executar queries em banco de dados na cloud
- Retornar insights formatados e visualizações

**Requisitos principais:**
- Interface amigável e intuitiva
- Integração robusta entre LLM e ferramentas (tools)
- Tratamento eficiente de erros
- Segurança e privacidade dos dados
- Análises estatísticas e visualizações

### 2. Decisões de Arquitetura

#### 2.1 Migração de LangGraph para LangChain 1.0

**Decisão:** Após uma implementação inicial em LangGraph com múltiplos nós (router query, nós conversacionais, nós de validação), optei por migrar para a arquitetura mais simples do LangChain 1.0.

**Motivação:**
- A implementação original em LangGraph, apesar de interessante tecnicamente, se mostrou **limitante para queries complexas**
- Em casos de uso reais, analistas de dados frequentemente precisam de queries muito complexas que não cabem em um workflow pré-definido
- A complexidade do grafo estava crescendo e tornando o código **difícil de manter**
- O LangChain 1.0, lançado recentemente, é **construído em cima do LangGraph**, aproveitando suas vantagens sem a complexidade excessiva

**Vantagens da arquitetura atual:**
- **Simplicidade**: Agente único com tools auto-contidas
- **Flexibilidade**: Suporta queries arbitrariamente complexas
- **Manutenibilidade**: Menos código, mais fácil de debugar
- **Evolução natural**: Alinhado com a direção da plataforma LangChain

**Trade-offs:**
- Menos controle granular sobre o fluxo (aceitável dado o objetivo)
- Menor previsibilidade da sequência de ações (compensado por tracing robusto)

#### 2.2 Design de Tools

**Decisão:** Implementar **duas tools principais auto-contidas** ao invés de múltiplos nós especializados.

**Tools implementadas:**

1. **`query_database`**: Tool inteligente para executar análises SQL
   - Geração automática de SQL a partir de linguagem natural
   - Validação sintática e semântica com `sqlglot`
   - **Sistema de retry com auto-correção** (até 3 tentativas)
   - Conversão automática de Decimals para float (JSON-serializável)
   - Few-shot learning com exemplos no Business Dictionary

2. **`generate_chart`**: Criação de visualizações matplotlib
   - Detecção automática do melhor tipo de gráfico
   - Formatação PT-BR (vírgula decimal, ponto separador de milhar)
   - Suporte a múltiplos tipos: barras, linha, histograma, pizza
   - Upload automático para GCS com URLs públicas

**Justificativa:**
- Tools auto-contidas são mais **reutilizáveis e testáveis**
- Permitem **composição flexível** pelo agente
- Suportam **multi-step tool calls** naturalmente
- Facilitam observabilidade via tracing do LangSmith

### 3. Decisões de Infraestrutura

#### 3.1 Deploy no LangSmith

**Decisão:** Utilizar o ecossistema LangSmith para deploy e observabilidade.

**Vantagens:**
- **Tracing completo** de todas as execuções do agente
- Visualização de cada tool call, inputs/outputs, latências
- Logs estruturados em todos os níveis (@traceable decorators)
- Deploy simplificado (`langgraph push`)
- Integração nativa com Agent Chat UI

**Implementação:**
- Adicionei decorators `@traceable` nas funções críticas:
  - `generate_sql` (geração de SQL)
  - `correct_sql` (auto-correção)
  - `execute_sql_with_retry` (execução com retry)
- Configuração via `config.py` com suporte a variáveis automáticas do control plane

#### 3.2 Interface: Fork do Agent Chat UI

**Decisão:** Usar fork do repositório oficial `langchain-ai/agent-chat-ui`.

**Justificativa:**
- **Integração out-of-the-box** com agentes deployados no LangSmith
- **Suporte nativo a content blocks multimodais** (texto + imagem)
- Renderização automática de imagens inline
- Interface profissional e responsiva
- Menos esforço de desenvolvimento em UI

**Modificações no fork:**
- Configuração para apontar para deployment do LangSmith
- Ajustes para renderizar imagens do GCS corretamente

#### 3.3 Google Cloud Storage para Imagens

**Decisão:** Armazenar gráficos gerados em bucket GCS público.

**Motivação:**
- Base64 em mensagens aumenta muito o payload
- URLs públicas são mais eficientes para UI
- GCS é escalável e confiável
- Integração simples via `google-cloud-storage`

**Implementação:**
- Classe `GCSUploader` em `src/utils/gcs_uploader.py`
- Nomes únicos com UUID para evitar colisões
- Suporte a autenticação via Service Account JSON ou ADC
- Upload com tipo MIME correto (`image/png`)

#### 3.4 Banco de Dados PostgreSQL

**Decisão:** PostgreSQL via Docker Compose (desenvolvimento) ou cloud (produção).

**Vantagens do PostgreSQL:**
- Suporte robusto a tipos de dados (timestamp, numeric)
- Funções agregadas e window functions
- Excelente performance para analytics
- `psycopg` driver moderno e eficiente

**Segurança:**
- Usuário `chatbot_reader` com permissões **apenas de leitura (SELECT)**
- Statement timeout configurável (10s padrão)
- Pool de conexões com `SQLAlchemy`

### 4. Decisões de Segurança e Guardrails

#### 4.1 K-anonimato (k=20)

**Decisão:** Filtrar automaticamente grupos com menos de 20 observações.

**Motivação:**
- Prevenir identificação de indivíduos em grupos pequenos
- Compliance com boas práticas de privacidade
- Balancear utilidade dos dados vs. proteção de privacidade

**Implementação:**
- Adicionado automaticamente em queries com `GROUP BY`: `HAVING COUNT(*) >= 20`
- Configurável via `.env` (`K_ANONYMITY=20`)

#### 4.2 Validação SQL com sqlglot

**Decisão:** Validar todas as queries antes de executar usando biblioteca `sqlglot`.

**O que é validado:**
- **Sintaxe SQL**: previne erros básicos
- **Operações bloqueadas**: DROP, DELETE, UPDATE, INSERT, CREATE, ALTER, TRUNCATE, GRANT, REVOKE
- **Estrutura da query**: verifica se é SELECT válido
- **Parsing**: garante que SQL é parseável antes de enviar ao banco

**Benefícios:**
- Previne SQL injection
- Bloqueia operações destrutivas
- Feedback rápido de erros sem sobrecarregar o banco

#### 4.3 Outras Proteções

- **Read-only user**: Usuário do banco não tem permissões de escrita
- **Statement timeout**: Queries canceladas após 10s
- **Limite de resultados**: Máximo de 10.000 linhas por query
- **Default LIMIT**: 100 linhas se não especificado

### 5. Decisões de UX e Produto

#### 5.1 Não usar Human-in-the-Loop

**Decisão:** Após testar, optei por **não** implementar human-in-the-loop.

**Justificativa:**
- O perfil do usuário (analista de dados) valoriza **velocidade e fluidez**
- Guardrails técnicos (read-only, validação SQL) já garantem segurança
- Sistema de retry transparente corrige a maioria dos erros automaticamente
- Interromper o fluxo para aprovação prejudicaria a experiência

**Alternativa implementada:**
- Logging detalhado no LangSmith para auditoria posterior
- Mensagens claras de erro quando algo falha
- Sistema de retry automático com até 3 tentativas

#### 5.2 Formatação PT-BR

**Decisão:** Todas as respostas e visualizações seguem padrões brasileiros.

**Padrões implementados:**
- **Percentuais**: `24,50%` (vírgula decimal, 2 casas)
- **Idades**: `35,7 anos` (vírgula decimal, 1 casa)
- **Números grandes**: `123.456` (ponto separador de milhar)
- **Datas**: `01/06/2017` (formato %d/%m/%Y)

**Implementação:**
- Funções helper em `_format_number_ptbr()`
- Configuração centralizada em `FormattingConfig`

#### 5.3 Sistema de Retry com Auto-correção

**Decisão:** Implementar retry inteligente com correção automática via LLM.

**Como funciona:**
1. Gera SQL inicial com LLM + few-shot examples
2. Valida sintaxe com `sqlglot`
3. Se falhar, usa **LLM para corrigir** com contexto completo:
   - SQL que falhou
   - Mensagem de erro
   - Pergunta original do usuário
   - Mesmos exemplos do prompt inicial
4. Repete até 3 vezes ou sucesso

**Benefícios:**
- **Auto-recuperação** de erros comuns (aspas, HAVING sem GROUP BY, tabela errada)
- Menor frustração do usuário
- Melhoria contínua via few-shot learning

### 6. Qualidade e Testes

#### 6.1 Testes Automatizados

**Implementação:** 15 arquivos de teste cobrindo:

**Testes Unitários:**
- `test_config.py`: Validação de configurações
- `test_sql_validator.py`: Validação SQL
- `test_business_dictionary.py`: Mapeamento NL→SQL
- `test_formatting.py`: Formatação PT-BR
- `test_chart_detection.py`: Detecção de tipo de gráfico
- `test_gcs_uploader.py`: Upload para GCS
- `test_db_connection.py`: Pool de conexões

**Testes de Integração:**
- `test_database_query_tool.py`: Execução completa de queries
- `test_visualization_tool.py`: Geração de gráficos
- `test_agent_trajectories.py`: Fluxos completos do agente

**Testes de Sistema:**
- `test_retry_system.py`: Sistema de retry e auto-correção

**Cobertura:**
- Tools principais
- Validação e segurança
- Formatação e visualização
- Trajetórias end-to-end do agente

#### 6.2 Observabilidade via LangSmith

**Implementação:**
- Decorators `@traceable` em funções críticas
- Metadata customizada para filtrar traces
- Logs estruturados em todos os níveis

**Benefícios:**
- **Debugging facilitado**: Ver exatamente onde algo falhou
- **Performance monitoring**: Identificar gargalos
- **Análise de comportamento**: Entender padrões de uso
- **Multi-step tool calls**: Rastreamento de chamadas encadeadas

### 7. Insights da Análise Exploratória

Durante a análise exploratória (notebook `analyzis.ipynb`), identifiquei insights importantes que influenciaram o design:

#### 7.1 Tratamento de Dados

**Descobertas:**
- **OBITO**: Quando vivo, retorna `NaN` ao invés de "Não" → Tool preparada para interpretar corretamente
- **Nulos informativos**: Ausência de informação é uma informação → Mantidos como "Não informado"
- **Sem outliers significativos**: Idade entre 18-105 anos (conforme LGPD)
- **Desbalanceamento**: 24,50% inadimplentes → Mantido (objetivo é análise, não modelagem)

#### 7.2 Estatísticas da Base

- **Volume**: 120.750 registros
- **Período**: Janeiro a Agosto de 2017 (8 meses)
- **Taxa de Inadimplência Global**: 24,50%
- **Idade Média**: 42,1 anos (mediana: 39,9 anos)
- **Cobertura geográfica**: 27 UFs
- **Classes sociais**: A-E presentes

#### 7.3 Perfis de Inadimplência

**Variações por dimensão:**
- **Por UF**: Amplitude de 12,5 p.p. (AP: 32,12% vs SC: 19,62%)
- **Por Sexo**: Homens (26,81%) vs Mulheres (21,24%)
- **Por Classe Social**: Classe A com maior taxa (32,92%)

**Insights acionáveis:**
- Homens da Classe B têm maior propensão à inadimplência
- Visualizações são **essenciais** (gráficos complementam tabelas)
- K-anonimato necessário para proteger grupos pequenos

#### 7.4 Melhorias Identificadas

- Comparar tabelas e gráficos mostrou que **informações são complementares**
- Suporte a visualização é **feature essencial**, não adicional
- Possibilidade de análises estatísticas avançadas (ex: teste KS) em versões futuras

### 8. Próximos Passos e Melhorias Futuras

#### 8.1 Avaliação Sistemática

**Objetivo:** Criar dataset fixo de avaliação para medir performance.

**Proposta:**
- Dataset de perguntas com respostas esperadas
- Métricas em múltiplas dimensões:
  - Precisão do SQL gerado
  - Correção das respostas
  - Latência end-to-end
  - Taxa de sucesso em multi-step queries
- Avaliação automatizada via `pytest`

#### 8.2 Testes com Múltiplos Modelos

**Modelos candidatos:**
- **GPT-4.1**: Modelo principal atual (ótimo para tool calls)
- **GPT-4.1 mini**: Modelo menor, menor custo, latência reduzida
- **Claude 3.5 Sonnet**: Alternativa competitiva
- **Llama 3.1 70B**: Opção open-source

**Critérios de comparação:**
- Precisão das queries SQL
- Taxa de auto-correção bem-sucedida
- Custo por consulta
- Latência média
- Qualidade das respostas em linguagem natural

#### 8.3 Abordagens Determinísticas

**Consideração:** Para cenários específicos e queries muito frequentes, uma abordagem mais determinística (similar ao LangGraph inicial) pode ser mais eficiente.

**Possibilidade:**
- **Híbrido**: Router inicial que direciona queries simples/comuns para fluxo determinístico
- Queries complexas/novas continuam com agente LLM-based
- Redução de custo e latência para casos comuns

**Trade-off:** Complexidade adicional vs. ganhos de performance

#### 8.4 Análises Estatísticas Avançadas

**Propostas:**
- Teste de Kolmogorov-Smirnov (KS) para comparar distribuições
- Testes de hipótese (t-test, chi-quadrado)
- Análises de correlação
- Séries temporais com decomposição sazonal

**Implementação:** Nova tool `statistical_analysis` ou extensão da `query_database`

#### 8.5 Melhorias de UX

- **Sugestões contextuais**: Perguntas de follow-up baseadas na análise atual
- **Histórico de conversação**: Persistência entre sessões
- **Export de resultados**: Download de CSVs, gráficos em alta resolução
- **Compartilhamento**: URLs permanentes para análises

---

### Conclusão

Este projeto representa uma implementação **pragmática e escalável** de um chatbot de análise de dados com LLMs. As decisões tomadas priorizaram:

1. **Simplicidade**: Arquitetura enxuta baseada em LangChain 1.0
2. **Segurança**: Múltiplas camadas de proteção (read-only, validação, k-anonimato)
3. **Confiabilidade**: Sistema de retry com auto-correção
4. **Observabilidade**: Tracing completo via LangSmith
5. **Experiência do Usuário**: Respostas rápidas, formatação PT-BR, visualizações automáticas

A migração de LangGraph para LangChain 1.0, embora contraintuitiva inicialmente, se provou a **decisão arquitetural mais importante**, permitindo flexibilidade para queries complexas sem sacrificar manutenibilidade.

O sistema está pronto para uso em produção, com caminhos claros de evolução identificados para futuras iterações.

---

**Desenvolvido usando LangChain 1.0**
