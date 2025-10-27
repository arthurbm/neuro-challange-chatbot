"""
SQL Validator - Validação e sanitização de queries SQL usando sqlglot.
"""

import re
from typing import Literal

import sqlglot
from sqlglot import ParseError

from src.config import config


class SQLValidationError(Exception):
    """Exceção customizada para erros de validação SQL."""

    pass


class SQLValidator:
    """Validador de queries SQL com foco em segurança e guardrails."""

    def __init__(self):
        self.guardrails = config.guardrails
        self.blocked_ops = [op.upper() for op in self.guardrails.blocked_operations]

    def validate(self, sql: str) -> tuple[Literal[True], str]:
        """
        Valida uma query SQL.

        Args:
            sql: Query SQL para validar

        Returns:
            Tuple (True, sql_formatado) se válido

        Raises:
            SQLValidationError: Se a query for inválida
        """
        # 1. Validar sintaxe
        self._validate_syntax(sql)

        # 2. Bloquear operações perigosas
        self._check_blocked_operations(sql)

        # 3. Garantir read-only (apenas SELECT)
        self._ensure_read_only(sql)

        # 4. Formatar SQL
        formatted_sql = self._format_sql(sql)

        # 5. Aplicar guardrails (LIMIT se necessário)
        final_sql = self._apply_guardrails(formatted_sql)

        return True, final_sql

    def _validate_syntax(self, sql: str):
        """Valida sintaxe SQL usando sqlglot."""
        try:
            # Parse SQL (dialect Postgres)
            parsed = sqlglot.parse_one(sql, dialect="postgres")

            if parsed is None:
                raise SQLValidationError("Query SQL vazia ou inválida")

        except ParseError as e:
            raise SQLValidationError(f"Erro de sintaxe SQL: {str(e)}")
        except Exception as e:
            raise SQLValidationError(f"Erro ao validar SQL: {str(e)}")

    def _check_blocked_operations(self, sql: str):
        """Verifica se a query contém operações bloqueadas."""
        sql_upper = sql.upper()

        for blocked_op in self.blocked_ops:
            # Busca por palavra completa (não parte de outra palavra)
            pattern = r"\b" + re.escape(blocked_op) + r"\b"
            if re.search(pattern, sql_upper):
                raise SQLValidationError(
                    f"Operação bloqueada detectada: {blocked_op}. "
                    f"Apenas queries SELECT (read-only) são permitidas."
                )

    def _ensure_read_only(self, sql: str):
        """Garante que a query é read-only (SELECT)."""
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")

            # Tipos permitidos: SELECT, WITH (CTE), UNION
            allowed_types = {"select", "union", "with"}

            exp_type = parsed.key.lower()

            if exp_type not in allowed_types:
                raise SQLValidationError(
                    f"Apenas queries SELECT são permitidas. Tipo detectado: {exp_type.upper()}"
                )

        except ParseError:
            # Já validado em _validate_syntax
            pass

    def _format_sql(self, sql: str) -> str:
        """Formata SQL para melhor legibilidade."""
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")
            formatted = parsed.sql(dialect="postgres", pretty=True)
            return formatted
        except Exception:
            # Se falhar formatação, retorna original
            return sql

    def _apply_guardrails(self, sql: str) -> str:
        """Aplica guardrails (ex: LIMIT padrão se não especificado)."""
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")

            # Se não tem LIMIT e não é agregação, adicionar LIMIT padrão
            has_limit = self._has_limit(parsed)
            has_aggregation = self._has_aggregation(parsed)

            if not has_limit and not has_aggregation:
                # Adicionar LIMIT padrão
                sql_with_limit = f"{sql.rstrip(';')} LIMIT {self.guardrails.default_limit}"
                return sql_with_limit

            return sql

        except Exception:
            # Se falhar, retorna SQL original (já validado antes)
            return sql

    def _has_limit(self, parsed) -> bool:
        """Verifica se a query tem LIMIT."""
        try:
            # sqlglot: parsed.args.get('limit')
            return parsed.args.get("limit") is not None
        except Exception:
            return False

    def _has_aggregation(self, parsed) -> bool:
        """Verifica se a query tem funções de agregação."""
        sql_str = parsed.sql().upper()

        # Funções de agregação comuns
        agg_functions = ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX(", "GROUP BY"]

        return any(func in sql_str for func in agg_functions)

    def extract_tables(self, sql: str) -> list[str]:
        """Extrai nomes de tabelas da query."""
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")

            tables = []
            for table in parsed.find_all(sqlglot.exp.Table):
                tables.append(table.name)

            return list(set(tables))  # Remove duplicatas

        except Exception:
            return []

    def add_timeout(self, sql: str) -> str:
        """
        Adiciona timeout statement ao SQL (Postgres specific).
        Nota: Isso deve ser executado na sessão, não na query.
        Mantido aqui para referência.
        """
        timeout_ms = self.guardrails.query_timeout_seconds * 1000
        return f"SET LOCAL statement_timeout = {timeout_ms}; {sql}"


# Instância global
sql_validator = SQLValidator()
