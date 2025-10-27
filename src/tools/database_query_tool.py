"""
Tool para executar queries SQL baseadas em perguntas em linguagem natural.

Implementa retry com auto-correção usando LLM.
"""

from typing import Any

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import config
from src.utils.business_dictionary import BusinessDictionary
from src.utils.db_connection import db_manager
from src.utils.sql_validator import SQLValidationError, sql_validator


class QueryDatabaseInput(BaseModel):
    """Schema de input para a tool query_database."""

    question_context: str = Field(
        description="Pergunta do usuário em linguagem natural sobre dados de crédito"
    )


def _generate_sql_with_llm(question: str) -> str:
    """
    Gera SQL a partir de uma pergunta em linguagem natural.

    Args:
        question: Pergunta do usuário

    Returns:
        Query SQL gerada
    """
    # Inicializar modelo
    llm = ChatOpenAI(
        model=config.llm.model,
        temperature=0.0,  # Determinístico para SQL
        api_key=config.llm.api_key,
    )

    # Criar prompt com contexto
    system_prompt = f"""Você é um especialista em SQL para PostgreSQL.

{BusinessDictionary.get_table_description()}

**Exemplos de perguntas e queries:**
"""

    # Adicionar exemplos few-shot
    for exemplo in BusinessDictionary.EXEMPLOS:
        system_prompt += f"\nPergunta: {exemplo['nl']}\n"
        system_prompt += f"SQL: {exemplo['sql']}\n"
        system_prompt += f"Explicação: {exemplo['explicacao']}\n"

    system_prompt += """

**Regras importantes:**
1. Use SEMPRE aspas duplas nas colunas (ex: "UF", "TARGET")
2. Aplique k-anonimato: HAVING COUNT(*) >= 20 em agregações
3. Apenas queries SELECT (read-only)
4. Use DATE_TRUNC para agregações temporais
5. Normalize strings com UPPER/LOWER/TRIM quando apropriado
6. Retorne APENAS o SQL, sem explicações ou markdown

**Sua tarefa:**
Gere um SQL válido para responder à pergunta abaixo.
"""

    user_prompt = f"Pergunta: {question}"

    # Gerar SQL
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.invoke(messages)
    sql = response.content.strip()

    # Limpar markdown se presente
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    elif sql.startswith("```"):
        sql = sql.replace("```", "").strip()

    return sql


def _execute_with_retry(sql: str, question: str, max_retries: int = 3) -> list[dict[str, Any]]:
    """
    Executa SQL com retry e auto-correção.

    Args:
        sql: Query SQL para executar
        question: Pergunta original (para contexto na correção)
        max_retries: Número máximo de tentativas

    Returns:
        Lista de dicts com resultados

    Raises:
        Exception: Se todas as tentativas falharem
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Validar SQL
            is_valid, validated_sql = sql_validator.validate(sql)

            # Executar
            result = db_manager.execute_query(validated_sql)
            return result

        except (SQLValidationError, Exception) as e:
            last_error = e
            error_msg = str(e)

            # Se é a última tentativa, lançar exceção
            if attempt == max_retries - 1:
                break

            # Tentar corrigir com LLM
            print(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou: {error_msg}")
            print("   Tentando corrigir SQL...")

            llm = ChatOpenAI(
                model=config.llm.model,
                temperature=0.0,
                api_key=config.llm.api_key,
            )

            correction_prompt = f"""Você é um especialista em SQL para PostgreSQL.

{BusinessDictionary.get_table_description()}

**SQL que falhou:**
{sql}

**Erro recebido:**
{error_msg}

**Pergunta original:**
{question}

**Sua tarefa:**
Corrija o SQL para resolver o erro. Retorne APENAS o SQL corrigido, sem explicações.

**Regras:**
- Use aspas duplas nas colunas
- Aplique k-anonimato: HAVING COUNT(*) >= 20
- Apenas queries SELECT
"""

            response = llm.invoke([{"role": "user", "content": correction_prompt}])
            sql = response.content.strip()

            # Limpar markdown
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()

    # Se chegou aqui, todas as tentativas falharam
    raise Exception(
        f"Falha após {max_retries} tentativas. Último erro: {last_error}"
    )


def _format_response_natural_language(
    question: str, data: list[dict[str, Any]], sql: str
) -> str:
    """
    Formata resultados em linguagem natural PT-BR.

    Args:
        question: Pergunta original
        data: Dados retornados pela query
        sql: SQL executado

    Returns:
        Resposta formatada em linguagem natural
    """
    if not data:
        return "Não encontrei resultados para essa consulta. Tente reformular a pergunta."

    # Usar LLM para gerar resposta natural
    llm = ChatOpenAI(
        model=config.llm.model,
        temperature=0.3,  # Um pouco de criatividade na formatação
        api_key=config.llm.api_key,
    )

    # Limitar dados para não estourar context window
    data_sample = data[:100]  # Primeiras 100 linhas
    total_rows = len(data)

    prompt = f"""Você é um assistente de análise de dados especializado em crédito.

**Pergunta do usuário:**
{question}

**Dados retornados (primeiras {len(data_sample)} de {total_rows} linhas):**
{data_sample}

**SQL executado:**
{sql}

**Sua tarefa:**
Responda à pergunta do usuário de forma clara e objetiva em português brasileiro,
usando os dados retornados. Formate números adequadamente:
- Percentuais: use vírgula decimal e 2 casas (ex: 24,50%)
- Idades: use vírgula decimal e 1 casa (ex: 35,4 anos)
- Quantidades: use ponto como separador de milhar (ex: 1.234)

Seja conciso mas informativo. Se houver insights relevantes, mencione-os.
"""

    response = llm.invoke([{"role": "user", "content": prompt}])
    return response.content.strip()


@tool(response_format="content_and_artifact")
def query_database(question_context: str) -> tuple[str, dict]:
    """
    Executa análise de dados SQL baseada em pergunta do usuário.

    Esta tool:
    1. Interpreta a pergunta e gera SQL
    2. Valida sintaxe e aplicardarails
    3. Executa com retry e auto-correção
    4. Formata resposta em linguagem natural PT-BR

    Args:
        question_context: Pergunta do usuário em linguagem natural

    Returns:
        Tupla (resposta_formatada, metadata)
        - resposta_formatada: Resposta em PT-BR para o modelo
        - metadata: Dict com {"sql": "...", "data": [...], "row_count": N}
    """
    try:
        # 1. Gerar SQL
        print(f"\n🤔 Interpretando pergunta: {question_context[:100]}...")
        sql = _generate_sql_with_llm(question_context)
        print(f"📝 SQL gerado:\n{sql}\n")

        # 2. Executar com retry
        print("⚙️ Executando query...")
        result_data = _execute_with_retry(sql, question_context)
        print(f"✅ Query executada: {len(result_data)} linhas retornadas\n")

        # 3. Formatar resposta
        print("💬 Formatando resposta...")
        formatted_response = _format_response_natural_language(
            question_context, result_data, sql
        )

        # 4. Preparar metadata (artifact)
        metadata = {
            "sql": sql,
            "data": result_data[:100],  # Limitar a 100 linhas no artifact
            "row_count": len(result_data),
            "truncated": len(result_data) > 100,
        }

        return formatted_response, metadata

    except Exception as e:
        error_msg = f"Erro ao processar consulta: {str(e)}"
        print(f"❌ {error_msg}")

        # Retornar erro como resposta
        return error_msg, {"error": str(e), "sql": sql if "sql" in locals() else None}
