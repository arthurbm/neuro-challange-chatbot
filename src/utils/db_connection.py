"""
Database Connection Manager - Gerenciamento de conexões com Postgres.
"""

from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from src.config import config


class DatabaseManager:
    """Gerenciador de conexões com banco de dados Postgres."""

    def __init__(self):
        self._engine: Engine | None = None
        self._init_engine()

    def _init_engine(self):
        """Inicializa engine SQLAlchemy com pool de conexões."""
        db_config = config.database

        self._engine = create_engine(
            db_config.connection_string,
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_pre_ping=True,  # Verifica conexão antes de usar
            echo=False,  # Set True para debug SQL
            connect_args={
                "options": f"-c statement_timeout={db_config.statement_timeout}",
                "connect_timeout": 10,
            },
        )

    @property
    def engine(self) -> Engine:
        """Retorna engine SQLAlchemy."""
        if self._engine is None:
            self._init_engine()
        return self._engine

    @contextmanager
    def get_connection(self):
        """
        Context manager para obter conexão do pool.

        Usage:
            with db_manager.get_connection() as conn:
                result = conn.execute(text("SELECT ..."))
        """
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
        """
        Executa query SQL e retorna resultados como lista de dicts.

        Args:
            sql: Query SQL
            params: Parâmetros para query (opcional)

        Returns:
            Lista de dicionários com resultados

        Raises:
            Exception: Se houver erro na execução
        """
        with self.get_connection() as conn:
            result = conn.execute(text(sql), params or {})

            # Converter para lista de dicts
            rows = []
            if result.returns_rows:
                columns = result.keys()
                for row in result:
                    rows.append(dict(zip(columns, row)))

            return rows

    def test_connection(self) -> tuple[bool, str]:
        """
        Testa conexão com o banco.

        Returns:
            Tuple (success, message)
        """
        try:
            with self.get_connection() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                return True, f"Conectado: {version.split(',')[0]}"
        except Exception as e:
            return False, f"Erro: {str(e)}"

    def get_table_info(self, table_name: str = "credit_train") -> dict:
        """
        Retorna informações sobre uma tabela.

        Args:
            table_name: Nome da tabela

        Returns:
            Dict com informações da tabela
        """
        try:
            # Query para informações das colunas
            sql = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            ORDER BY ordinal_position
            """

            columns_info = self.execute_query(sql, {"table_name": table_name})

            # Query para contagem de registros
            count_sql = f'SELECT COUNT(*) as total FROM {table_name}'
            count_result = self.execute_query(count_sql)
            total_rows = count_result[0]["total"] if count_result else 0

            return {
                "table_name": table_name,
                "columns": columns_info,
                "total_rows": total_rows,
            }

        except Exception as e:
            return {
                "error": str(e),
                "table_name": table_name,
            }

    def close(self):
        """Fecha todas as conexões do pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# Instância global
db_manager = DatabaseManager()
