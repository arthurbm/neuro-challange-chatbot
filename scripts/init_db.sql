-- Script de inicialização do banco de dados
-- Executado automaticamente quando o container Postgres é criado

-- Criar schema principal
CREATE SCHEMA IF NOT EXISTS public;

-- Criar tabela credit_train (com colunas em MAIÚSCULA)
CREATE TABLE IF NOT EXISTS public.credit_train (
    "ID" SERIAL PRIMARY KEY,
    "REF_DATE" TIMESTAMPTZ NOT NULL,
    "TARGET" SMALLINT NOT NULL CHECK ("TARGET" IN (0, 1)),
    "SEXO" VARCHAR(1) CHECK ("SEXO" IN ('M', 'F') OR "SEXO" IS NULL),
    "IDADE" NUMERIC,
    "OBITO" BOOLEAN,
    "UF" VARCHAR(2),
    "CLASSE_SOCIAL" VARCHAR(20)
);

-- Criar índices recomendados pela EDA
CREATE INDEX IF NOT EXISTS idx_uf_refdate ON public.credit_train("UF", "REF_DATE");
CREATE INDEX IF NOT EXISTS idx_classe_social ON public.credit_train("CLASSE_SOCIAL");
CREATE INDEX IF NOT EXISTS idx_sexo ON public.credit_train("SEXO");
CREATE INDEX IF NOT EXISTS idx_refdate ON public.credit_train("REF_DATE");
CREATE INDEX IF NOT EXISTS idx_target ON public.credit_train("TARGET");

-- Criar usuário read-only para o chatbot
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatbot_reader') THEN
        CREATE ROLE chatbot_reader WITH LOGIN PASSWORD 'chatbot_pass_dev';
    END IF;
END
$$;

-- Conceder permissões read-only
GRANT CONNECT ON DATABASE credit_analytics TO chatbot_reader;
GRANT USAGE ON SCHEMA public TO chatbot_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_reader;

-- Garantir que novas tabelas também terão permissão SELECT
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chatbot_reader;

-- Remover explicitamente permissões de escrita (garantia)
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM chatbot_reader;

-- Comentários nas tabelas
COMMENT ON TABLE public.credit_train IS 'Base de treino de concessão de crédito com 170k registros';
COMMENT ON COLUMN public.credit_train."REF_DATE" IS 'Data de referência do registro';
COMMENT ON COLUMN public.credit_train."TARGET" IS 'Alvo binário de inadimplência (0=bom, 1=mau pagador)';
COMMENT ON COLUMN public.credit_train."SEXO" IS 'Sexo do indivíduo (M/F)';
COMMENT ON COLUMN public.credit_train."IDADE" IS 'Idade do indivíduo em anos';
COMMENT ON COLUMN public.credit_train."OBITO" IS 'Indicador de óbito (true=sim, false/null=não)';
COMMENT ON COLUMN public.credit_train."UF" IS 'Unidade Federativa (estado brasileiro)';
COMMENT ON COLUMN public.credit_train."CLASSE_SOCIAL" IS 'Classe social estimada (alta, média, baixa)';

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully!';
    RAISE NOTICE 'Read-only user "chatbot_reader" created with password "chatbot_pass_dev"';
    RAISE NOTICE 'Table "credit_train" created with indexes';
END $$;
