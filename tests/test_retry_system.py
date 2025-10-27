"""
Testes do sistema de retry com auto-correção de SQL.

Testa casos onde o SQL inicial está errado e deve ser corrigido automaticamente.
"""

import logging

from src.tools.database_query_tool import (
    _correct_sql_with_llm,
    _execute_with_retry,
    _generate_sql_with_llm,
)

# Configurar logging para ver output detalhado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_case_1_correct_sql_first_attempt():
    """
    Teste 1: SQL correto na primeira tentativa (baseline).

    Deve executar com sucesso sem precisar de retry.
    """
    print("\n" + "=" * 80)
    print("TESTE 1: SQL correto na primeira tentativa")
    print("=" * 80)

    question = "Quantas pessoas têm mais de 60 anos?"

    try:
        # Gerar SQL (deve estar correto)
        sql = _generate_sql_with_llm(question)
        print(f"\n📝 SQL gerado:\n{sql}\n")

        # Executar (deve funcionar na primeira tentativa)
        result = _execute_with_retry(sql, question, max_retries=3)

        print(f"✅ SUCESSO: {len(result)} resultados retornados")
        print(f"   Dados: {result}")
        return True

    except Exception as e:
        print(f"❌ FALHA: {e}")
        return False


def test_case_2_missing_quotes():
    """
    Teste 2: SQL sem aspas duplas nas colunas.

    Erro comum: UF ao invés de "UF"
    Deve auto-corrigir adicionando aspas.
    """
    print("\n" + "=" * 80)
    print("TESTE 2: SQL sem aspas duplas (deve auto-corrigir)")
    print("=" * 80)

    # SQL intencionalmente errado (sem aspas duplas)
    broken_sql = "SELECT UF, AVG(TARGET) as taxa FROM credit_train GROUP BY UF HAVING COUNT(*) >= 20"
    question = "Qual a taxa de inadimplência por UF?"

    print(f"\n🔧 SQL intencionalmente quebrado:\n{broken_sql}\n")
    print("   (falta aspas duplas em UF e TARGET)")

    try:
        result = _execute_with_retry(broken_sql, question, max_retries=3)

        print(f"\n✅ SUCESSO após auto-correção: {len(result)} resultados")
        print(f"   Primeiros 3 resultados: {result[:3]}")
        return True

    except Exception as e:
        print(f"\n❌ FALHA: Sistema não conseguiu corrigir")
        print(f"   Erro final: {e}")
        return False


def test_case_3_wrong_table_name():
    """
    Teste 3: SQL com nome de tabela errado.

    Erro comum: credit_data ao invés de credit_train
    Deve auto-corrigir o nome da tabela.
    """
    print("\n" + "=" * 80)
    print("TESTE 3: Nome de tabela errado (deve auto-corrigir)")
    print("=" * 80)

    # SQL com nome de tabela errado
    broken_sql = 'SELECT COUNT(*) as total FROM credit_data WHERE "IDADE" >= 60'
    question = "Quantas pessoas têm mais de 60 anos?"

    print(f"\n🔧 SQL intencionalmente quebrado:\n{broken_sql}\n")
    print("   (tabela 'credit_data' não existe, deveria ser 'credit_train')")

    try:
        result = _execute_with_retry(broken_sql, question, max_retries=3)

        print(f"\n✅ SUCESSO após auto-correção: {result}")
        return True

    except Exception as e:
        print(f"\n❌ FALHA: Sistema não conseguiu corrigir")
        print(f"   Erro final: {e}")
        return False


def test_case_4_having_without_group_by():
    """
    Teste 4: HAVING sem GROUP BY (erro de sintaxe SQL).

    Erro comum: usar HAVING COUNT(*) >= 20 em query sem GROUP BY
    Deve auto-corrigir removendo HAVING ou adicionando GROUP BY.
    """
    print("\n" + "=" * 80)
    print("TESTE 4: HAVING sem GROUP BY (deve auto-corrigir)")
    print("=" * 80)

    # SQL com HAVING mas sem GROUP BY (invalido)
    broken_sql = 'SELECT AVG("TARGET") as taxa FROM credit_train WHERE "SEXO" = \'F\' HAVING COUNT(*) >= 20'
    question = "Qual a taxa de inadimplência de mulheres?"

    print(f"\n🔧 SQL intencionalmente quebrado:\n{broken_sql}\n")
    print("   (HAVING sem GROUP BY é inválido)")

    try:
        result = _execute_with_retry(broken_sql, question, max_retries=3)

        print(f"\n✅ SUCESSO após auto-correção: {result}")
        return True

    except Exception as e:
        print(f"\n❌ FALHA: Sistema não conseguiu corrigir")
        print(f"   Erro final: {e}")
        return False


def test_case_5_classe_baixa_edge_case():
    """
    Teste 5: Edge case reportado - "classe baixa" com filtro de sexo.

    Testa o caso específico que estava falhando:
    - Deve usar IN ('c', 'd', 'e') para classe baixa
    - Não deve usar HAVING sem GROUP BY
    """
    print("\n" + "=" * 80)
    print("TESTE 5: Edge case - classe baixa + sexo feminino")
    print("=" * 80)

    question = "Qual a taxa de inadimplência de pessoas de classe baixa do sexo feminino?"

    try:
        # Gerar SQL (deve estar correto agora com os exemplos adicionados)
        sql = _generate_sql_with_llm(question)
        print(f"\n📝 SQL gerado:\n{sql}\n")

        # Verificar se está usando IN ('c', 'd', 'e')
        if "IN (" not in sql.upper() and ("'c'" not in sql.lower() or "'d'" not in sql.lower()):
            print("⚠️  AVISO: SQL pode não estar filtrando classe baixa corretamente")

        # Executar
        result = _execute_with_retry(sql, question, max_retries=3)

        print(f"\n✅ SUCESSO: {result}")

        # Validar que retornou dados
        if not result or (isinstance(result, list) and len(result) == 0):
            print("⚠️  AVISO: Nenhum resultado retornado (pode ser problema no filtro)")
            return False

        return True

    except Exception as e:
        print(f"\n❌ FALHA: {e}")
        return False


def test_case_6_correction_function_direct():
    """
    Teste 6: Testar função de correção diretamente.

    Testa se _correct_sql_with_llm consegue corrigir um SQL específico.
    """
    print("\n" + "=" * 80)
    print("TESTE 6: Função de correção diretamente")
    print("=" * 80)

    broken_sql = "SELECT UF, COUNT(*) FROM credit_data GROUP BY UF"
    error_msg = 'relation "credit_data" does not exist'
    question = "Quantos registros por UF?"

    print(f"\n🔧 SQL quebrado:\n{broken_sql}")
    print(f"\n❌ Erro simulado:\n{error_msg}\n")

    try:
        corrected_sql = _correct_sql_with_llm(broken_sql, error_msg, question)

        print(f"\n🆕 SQL corrigido:\n{corrected_sql}\n")

        # Verificar se corrigiu o nome da tabela
        if "credit_train" in corrected_sql:
            print("✅ SUCESSO: Tabela corrigida para 'credit_train'")
            return True
        else:
            print("❌ FALHA: Não corrigiu o nome da tabela")
            return False

    except Exception as e:
        print(f"\n❌ FALHA: {e}")
        return False


def run_all_tests():
    """Executa todos os testes e reporta resultados."""
    print("\n" + "=" * 80)
    print("INICIANDO BATERIA DE TESTES DO SISTEMA DE RETRY")
    print("=" * 80)

    tests = [
        ("SQL correto (baseline)", test_case_1_correct_sql_first_attempt),
        ("SQL sem aspas duplas", test_case_2_missing_quotes),
        ("Nome de tabela errado", test_case_3_wrong_table_name),
        ("HAVING sem GROUP BY", test_case_4_having_without_group_by),
        ("Edge case: classe baixa + sexo", test_case_5_classe_baixa_edge_case),
        ("Função de correção direta", test_case_6_correction_function_direct),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ ERRO INESPERADO em '{test_name}': {e}")
            results.append((test_name, False))

        # Pausa entre testes
        print("\n" + "-" * 80)

    # Relatório final
    print("\n" + "=" * 80)
    print("RELATÓRIO FINAL")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nResultados: {passed}/{total} testes passaram\n")

    for test_name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"  {status}: {test_name}")

    print("\n" + "=" * 80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()

    if success:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema de retry funcionando corretamente.\n")
        exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM. Verificar logs acima para detalhes.\n")
        exit(1)
