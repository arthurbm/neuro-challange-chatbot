"""
Configurações do projeto Credit Analytics Chatbot.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Carregar variáveis de ambiente
load_dotenv()


class DatabaseConfig(BaseSettings):
    """Configurações do banco de dados Postgres."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    database: str = Field(default="credit_analytics", alias="DB_NAME")
    user: str = Field(default="chatbot_reader", alias="DB_USER")
    password: str = Field(default="", alias="DB_PASSWORD")

    # Configurações de conexão
    pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    statement_timeout: int = Field(default=10000, alias="DB_STATEMENT_TIMEOUT")  # 10s em ms

    @property
    def connection_string(self) -> str:
        """Retorna string de conexão PostgreSQL."""
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class LLMConfig(BaseSettings):
    """Configurações do modelo LLM."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    provider: str = Field(default="openai", alias="LLM_PROVIDER")
    model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    max_tokens: Optional[int] = Field(default=2000, alias="LLM_MAX_TOKENS")
    api_key: str = Field(default="", alias="OPENAI_API_KEY")


class LangSmithConfig(BaseSettings):
    """Configurações do LangSmith."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    tracing_enabled: bool = Field(default=True, alias="LANGSMITH_TRACING")
    api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    # Default "default" - no deployment, será sobrescrito pelo nome do deployment automaticamente
    project: str = Field(default="default", alias="LANGSMITH_PROJECT")
    endpoint: str = Field(default="https://api.smith.langchain.com", alias="LANGSMITH_ENDPOINT")


class GuardrailsConfig(BaseSettings):
    """Guardrails e políticas de segurança."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # K-anonimato
    k_anonymity: int = Field(default=20, alias="K_ANONYMITY")

    # Limites de queries
    default_limit: int = Field(default=100, alias="DEFAULT_QUERY_LIMIT")
    max_rows_return: int = Field(default=10000, alias="MAX_ROWS_RETURN")

    # Timeout
    query_timeout_seconds: int = Field(default=10, alias="QUERY_TIMEOUT_SECONDS")

    # Operações bloqueadas
    blocked_operations: list[str] = Field(
        default_factory=lambda: [
            "DROP", "DELETE", "UPDATE", "INSERT",
            "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"
        ]
    )

    # Retry
    max_retry_attempts: int = Field(default=3, alias="MAX_RETRY_ATTEMPTS")


class FormattingConfig(BaseSettings):
    """Configurações de formatação de respostas."""

    decimal_separator: str = ","
    thousand_separator: str = "."
    decimal_places_percentage: int = 2
    decimal_places_age: int = 1
    date_format: str = "%d/%m/%Y"
    language: str = "pt-BR"


class GCSConfig(BaseSettings):
    """Configurações do Google Cloud Storage."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    project_id: str = Field(default="neuro-test-476419", alias="GCS_PROJECT_ID")
    bucket_name: str = Field(default="neuro-test", alias="GCS_BUCKET_NAME")

    # Prioridade: JSON_CONTENT > JSON (path) > ADC
    service_account_json: Optional[str] = Field(default=None, alias="GCS_SERVICE_ACCOUNT_JSON")
    service_account_json_content: Optional[str] = Field(default=None, alias="GCS_SERVICE_ACCOUNT_JSON_CONTENT")


class Config:
    """Configuração centralizada da aplicação."""

    def __init__(self):
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.langsmith = LangSmithConfig()
        self.guardrails = GuardrailsConfig()
        self.formatting = FormattingConfig()
        self.gcs = GCSConfig()

        # Paths
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.eval_dir = self.project_root / "eval"

    def setup_langsmith(self):
        """Configura variáveis de ambiente para LangSmith.

        Usa setdefault() para preservar variáveis automáticas do deployment.
        No LangSmith Studio, o control plane define essas variáveis automaticamente,
        então não devemos sobrescrevê-las.
        """
        if self.langsmith.tracing_enabled:
            os.environ.setdefault("LANGSMITH_TRACING", "true")
            os.environ.setdefault("LANGSMITH_API_KEY", self.langsmith.api_key)
            os.environ.setdefault("LANGSMITH_PROJECT", self.langsmith.project)
            os.environ.setdefault("LANGSMITH_ENDPOINT", self.langsmith.endpoint)


# Instância global
config = Config()
