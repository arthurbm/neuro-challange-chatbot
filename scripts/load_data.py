"""
Script para carregar dados do arquivo train.gz para o banco Postgres.

Uso:
    python scripts/load_data.py [--sample N]

Exemplos:
    python scripts/load_data.py                 # Carrega todos os dados
    python scripts/load_data.py --sample 1000   # Carrega apenas 1000 linhas (para testes)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config


def download_data_if_needed(data_path: Path) -> Path:
    """Baixa o dataset do GitHub se não existir localmente."""
    if data_path.exists():
        print(f"✓ Dataset já existe em: {data_path}")
        return data_path

    print("Dataset não encontrado localmente. Baixando do GitHub...")
    import urllib.request

    url = "https://github.com/Neurolake/challenge-data-scientist/raw/main/datasets/credit_01/train.gz"
    data_path.parent.mkdir(parents=True, exist_ok=True)

    urllib.request.urlretrieve(url, data_path)
    print(f"✓ Dataset baixado em: {data_path}")

    return data_path


def load_and_transform_data(file_path: Path, sample: int | None = None) -> pd.DataFrame:
    """Carrega e transforma o dataset."""
    print(f"\n📂 Carregando dados de {file_path}...")

    # Colunas a serem carregadas
    columns = ["REF_DATE", "TARGET", "VAR2", "IDADE", "VAR4", "VAR5", "VAR8"]

    # Ler CSV comprimido
    df = pd.read_csv(file_path, compression="gzip", usecols=columns)

    if sample:
        print(f"⚠️  Usando apenas {sample} linhas (modo amostra)")
        df = df.sample(n=min(sample, len(df)), random_state=42)

    print(f"✓ Carregadas {len(df):,} linhas")

    # Renomear colunas (manter em MAIÚSCULA)
    rename_map = {
        "VAR2": "SEXO",
        "VAR4": "OBITO",
        "VAR5": "UF",
        "VAR8": "CLASSE_SOCIAL",
    }
    df = df.rename(columns=rename_map)

    # Converter tipos
    print("🔄 Transformando dados...")
    df["REF_DATE"] = pd.to_datetime(df["REF_DATE"], utc=True)
    df["TARGET"] = df["TARGET"].astype("int8")
    df["IDADE"] = pd.to_numeric(df["IDADE"], errors="coerce")

    # Transformar OBITO para boolean
    # 'S' = True (houve óbito), NaN = False/None (não houve óbito)
    df["OBITO"] = df["OBITO"].apply(lambda x: True if pd.notna(x) and x in ["S", "s"] else None)

    # Normalizar CLASSE_SOCIAL (lowercase e trim)
    df["CLASSE_SOCIAL"] = df["CLASSE_SOCIAL"].apply(
        lambda x: x.lower().strip() if pd.notna(x) else None
    )

    # Normalizar UF e SEXO (uppercase)
    df["UF"] = df["UF"].apply(lambda x: x.upper().strip() if pd.notna(x) else None)
    df["SEXO"] = df["SEXO"].apply(lambda x: x.upper().strip() if pd.notna(x) else None)

    print("✓ Dados transformados")

    # Estatísticas
    print("\n📊 Estatísticas:")
    print(f"   • Período: {df['REF_DATE'].min()} a {df['REF_DATE'].max()}")
    print(f"   • Taxa de inadimplência: {df['TARGET'].mean()*100:.2f}%")
    print(f"   • UFs únicas: {df['UF'].nunique()}")
    print("   • Valores nulos por coluna:")
    for col in df.columns:
        n_null = df[col].isna().sum()
        if n_null > 0:
            print(f"      - {col}: {n_null:,} ({n_null/len(df)*100:.1f}%)")

    return df


def load_to_database(df: pd.DataFrame, connection_string: str):
    """Carrega dados no banco Postgres."""
    print("\n💾 Conectando ao banco de dados...")

    # Criar engine (usando credenciais de admin para carga, não o read-only)
    # Nota: ajuste se necessário para usar usuário postgres com permissões de escrita
    admin_connection = connection_string.replace("chatbot_reader", "postgres").replace(
        "chatbot_pass_dev", "postgres"
    )

    engine = create_engine(admin_connection, echo=False)

    try:
        # Testar conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ Conectado ao PostgreSQL: {version.split(',')[0]}")

        # Limpar tabela se já existir dados
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM credit_train"))
            count = result.fetchone()[0]
            if count > 0:
                print(f"⚠️  Tabela credit_train já contém {count:,} registros")
                response = input("Deseja apagar e recarregar? (s/N): ").strip().lower()
                if response == "s":
                    conn.execute(text("TRUNCATE TABLE credit_train RESTART IDENTITY CASCADE"))
                    conn.commit()
                    print("✓ Tabela limpa")
                else:
                    print("❌ Operação cancelada")
                    return

        # Carregar dados em lotes
        print(f"\n⬆️  Carregando {len(df):,} linhas para o banco...")

        batch_size = 5000  # Reduzido para evitar limite de 65535 parâmetros do Postgres

        with tqdm(total=len(df), desc="Carregando", unit="linhas") as pbar:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i : i + batch_size]
                batch.to_sql(
                    "credit_train",
                    engine,
                    if_exists="append",
                    index=False,
                    method="multi",
                )
                pbar.update(len(batch))

        print("\n✅ Dados carregados com sucesso!")

        # Verificar carga
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM credit_train"))
            count = result.fetchone()[0]
            print(f"✓ Total de registros na tabela: {count:,}")

            # Estatísticas básicas
            result = conn.execute(
                text(
                    """
                SELECT
                    COUNT(*) as total,
                    AVG("TARGET"::float) as taxa_inad,
                    MIN("REF_DATE") as min_date,
                    MAX("REF_DATE") as max_date
                FROM credit_train
            """
                )
            )
            stats = result.fetchone()
            print(f"\n📈 Estatísticas do banco:")
            print(f"   • Total: {stats[0]:,}")
            print(f"   • Taxa inadimplência: {stats[1]*100:.2f}%")
            print(f"   • Período: {stats[2]} a {stats[3]}")

    except Exception as e:
        print(f"\n❌ Erro ao carregar dados: {e}")
        raise
    finally:
        engine.dispose()


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Carrega dados para o banco Postgres")
    parser.add_argument(
        "--sample", type=int, default=None, help="Número de linhas para carregar (para testes)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("  CARGA DE DADOS - CREDIT ANALYTICS CHATBOT")
    print("=" * 80)

    # Path do dataset
    data_path = config.data_dir / "train.gz"

    # Baixar se necessário
    data_path = download_data_if_needed(data_path)

    # Carregar e transformar
    df = load_and_transform_data(data_path, sample=args.sample)

    # Carregar no banco
    load_to_database(df, config.database.connection_string)

    print("\n" + "=" * 80)
    print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    print("=" * 80)
    print("\nPróximos passos:")
    print("  1. Testar conexão read-only: psql -h localhost -U chatbot_reader -d credit_analytics")
    print("  2. Iniciar desenvolvimento do chatbot")
    print("  3. Testar queries no banco")


if __name__ == "__main__":
    main()
