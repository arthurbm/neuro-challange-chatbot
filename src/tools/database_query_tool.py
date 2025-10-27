"""
Tool para executar queries SQL baseadas em perguntas em linguagem natural.

Implementa retry com auto-correção usando LLM.
"""

import logging
from typing import Any

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langsmith import traceable
from pydantic import BaseModel, Field

from src.config import config
from src.utils.business_dictionary import BusinessDictionary
from src.utils.db_connection import db_manager
from src.utils.sql_validator import SQLValidationError, sql_validator

# Configurar logger
logger = logging.getLogger(__name__)


class QueryDatabaseInput(BaseModel):
    """Schema de input para a tool query_database."""

    question_context: str = Field(
        description="Pergunta do usuário em linguagem natural sobre dados de crédito"
    )


@traceable(name="generate_sql", metadata={"component": "sql_generation"})
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
2. Apenas queries SELECT (read-only) - nunca INSERT, UPDATE, DELETE, DROP
3. Use DATE_TRUNC para agregações temporais
4. Normalize strings com UPPER/LOWER/TRIM quando apropriado
5. Retorne APENAS o SQL, sem explicações ou markdown

**K-anonimato (privacidade):**
- Em queries com GROUP BY: adicione HAVING COUNT(*) >= 20
- Em queries SEM GROUP BY (filtros simples): NÃO use HAVING
- Exemplos:
  ✅ CORRETO: SELECT "UF", AVG("TARGET") FROM ... GROUP BY "UF" HAVING COUNT(*) >= 20
  ✅ CORRETO: SELECT AVG("TARGET") FROM ... WHERE "SEXO" = 'F' AND "CLASSE_SOCIAL" IN ('c','d','e')
  ❌ ERRADO: SELECT AVG("TARGET") FROM ... WHERE ... HAVING COUNT(*) >= 20 (sem GROUP BY)

**Valores válidos para filtros:**
- CLASSE_SOCIAL: 'a' (alta), 'b' (média-alta), 'c', 'd', 'e' (baixa)
- Para "classe baixa": use IN ('c', 'd', 'e')
- SEXO: 'M' ou 'F'

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


@traceable(name="correct_sql", metadata={"component": "sql_correction"})
def _correct_sql_with_llm(failed_sql: str, error_msg: str, question: str) -> str:
    """
    Corrige SQL usando LLM com contexto completo.

    Args:
        failed_sql: SQL que falhou
        error_msg: Mensagem de erro do Postgres/validator
        question: Pergunta original do usuário

    Returns:
        SQL corrigido
    """
    llm = ChatOpenAI(
        model=config.llm.model,
        temperature=0.0,
        api_key=config.llm.api_key,
    )

    # Incluir MESMOS exemplos do prompt original
    examples_str = "\n\n".join([
        f"Pergunta: {ex['nl']}\nSQL: {ex['sql']}\nExplicação: {ex['explicacao']}"
        for ex in BusinessDictionary.EXEMPLOS
    ])

    correction_prompt = f"""Você é um especialista em SQL para PostgreSQL.

{BusinessDictionary.get_table_description()}

**Exemplos de SQL correto:**
{examples_str}

**SQL que FALHOU:**
{failed_sql}

**ERRO recebido do banco/validador:**
{error_msg}

**Pergunta original do usuário:**
{question}

**Sua tarefa:**
Analise o erro SQL e corrija-o. Retorne APENAS o SQL corrigido, sem explicações ou markdown.

**Regras importantes:**
- Use aspas duplas nas colunas (ex: "UF", "TARGET")
- HAVING apenas com GROUP BY (nunca sem GROUP BY)
- Classe baixa = IN ('c', 'd', 'e')
- SEXO: 'M' ou 'F'
- Nome correto da tabela: credit_train
- Apenas queries SELECT (read-only)

**Erros comuns a corrigir:**
- Falta de aspas duplas: UF → "UF"
- HAVING sem GROUP BY: remover HAVING ou adicionar GROUP BY
- Tabela errada: credit_data → credit_train
- Sintaxe incorreta de agregação
"""

    response = llm.invoke([{"role": "user", "content": correction_prompt}])
    sql = response.content.strip()

    # Limpar markdown se presente
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    elif sql.startswith("```"):
        sql = sql.replace("```", "").strip()

    return sql


@traceable(name="execute_sql_with_retry", metadata={"component": "sql_execution"})
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
            # Log da tentativa
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Validating and executing SQL")
            logger.debug(f"SQL to execute: {sql[:200]}...")

            # Validar SQL (retorna (True, sql_formatado) ou levanta exceção)
            _, validated_sql = sql_validator.validate(sql)

            # Executar
            result = db_manager.execute_query(validated_sql)

            # Sucesso!
            if attempt > 0:
                logger.info(f"✅ SQL auto-corrected successfully after {attempt + 1} attempts")
            else:
                logger.info("✅ SQL executed successfully on first attempt")

            return result

        except (SQLValidationError, Exception) as e:
            last_error = e
            error_msg = str(e)

            # Log do erro
            logger.warning(
                f"❌ Attempt {attempt + 1}/{max_retries} failed: {error_msg[:200]}"
            )

            # Se é a última tentativa, lançar exceção
            if attempt == max_retries - 1:
                logger.error(
                    f"All {max_retries} attempts failed. Last error: {error_msg}"
                )
                break

            # Tentar corrigir com LLM usando função dedicada
            logger.info("🔧 Attempting to auto-correct SQL...")
            sql = _correct_sql_with_llm(sql, error_msg, question)
            logger.info(f"🆕 Corrected SQL: {sql[:150]}...")

    # Se chegou aqui, todas as tentativas falharam
    raise Exception(
        f"Falha após {max_retries} tentativas. Último erro: {last_error}"
    )


def _convert_decimals_to_float(data: Any) -> Any:
    """
    Converte objetos Decimal para float recursivamente.

    PostgreSQL retorna Decimal que não é JSON-serializável.
    Esta função converte recursivamente para float preservando estrutura.

    Args:
        data: Estrutura de dados (dict, list, ou valor primitivo)

    Returns:
        Mesma estrutura com Decimals convertidos para float
    """
    from decimal import Decimal

    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: _convert_decimals_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_decimals_to_float(item) for item in data]
    else:
        return data


@tool(response_format="content_and_artifact")
def query_database(question_context: str) -> tuple[str, dict]:
    """
    Executa análise de dados SQL baseada em pergunta do usuário.

    Esta tool:
    1. Interpreta a pergunta e gera SQL
    2. Valida sintaxe e aplica guardrails
    3. Executa com retry e auto-correção
    4. Retorna SQL e dados brutos para o agente formatar

    Args:
        question_context: Pergunta do usuário em linguagem natural

    Returns:
        Tupla (mensagem_com_dados, metadata)
        - mensagem_com_dados: Contém SQL executado + dados brutos (Decimals convertidos para float)
                             O agente deve ler os dados da mensagem e formatá-los
        - metadata: Dict com {"sql": "...", "data": [...], "row_count": N, "truncated": bool}
                   (Mantido para compatibilidade, mas create_agent não acessa)
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

        # 3. Converter Decimals para float (serialização)
        converted_data = _convert_decimals_to_float(result_data)

        # 4. Preparar metadata (artifact)
        metadata = {
            "sql": sql,
            "data": converted_data[:100],  # Limitar a 100 linhas no artifact
            "row_count": len(result_data),
            "truncated": len(result_data) > 100,
        }

        # 5. Criar mensagem com dados incluídos para o agente processar
        # (create_agent não passa artifact, então incluímos dados na mensagem)
        data_preview = converted_data[:10] if len(converted_data) > 10 else converted_data

        message = f"""Query executada com sucesso.

SQL executado:
{sql}

Resultados ({len(result_data)} linha{'s' if len(result_data) != 1 else ''}):
{data_preview}"""

        if len(converted_data) > 10:
            message += f"\n\n(Mostrando primeiras 10 de {len(result_data)} linhas. Use os dados para formatar sua resposta.)"

        return message, metadata

    except Exception as e:
        error_msg = f"Erro ao processar consulta: {str(e)}"
        print(f"❌ {error_msg}")

        # Retornar erro como resposta
        return error_msg, {"error": str(e), "sql": sql if "sql" in locals() else None}
