-- Esquema PostgreSQL del Laboratorio de PromptOps.
-- Fuente de verdad del esquema (sin Alembic, ver anti-objetivos en CLAUDE.md).
-- Aplicar con: psql promptops -f backend/schema.sql

CREATE TYPE run_status AS ENUM (
    'CREATED', 'OPTIMIZING', 'AUDITING', 'GATING', 'WAITING_HUMAN',
    'ITERATING', 'APPROVED', 'EXECUTING', 'COMPLETED', 'REJECTED', 'ERROR'
);

CREATE TYPE iteration_source AS ENUM ('optimizer', 'human_edit');

CREATE TYPE human_decision_type AS ENUM ('approve', 'iterate', 'edit', 'reject');

-- ---------------------------------------------------------------------------
-- runs: una ejecución completa del pipeline, desde el prompt original
-- hasta el resultado final (o el rechazo/error).
-- ---------------------------------------------------------------------------
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status run_status NOT NULL DEFAULT 'CREATED',
    original_prompt TEXT NOT NULL,
    optimizer_model TEXT NOT NULL,
    auditor_model TEXT NOT NULL,
    executor_model TEXT NOT NULL,
    error_message TEXT
);

CREATE INDEX idx_runs_status ON runs(status);

-- ---------------------------------------------------------------------------
-- iterations: cada versión del prompt dentro de un run (generada por el
-- Optimizer o por edición humana directa).
-- ---------------------------------------------------------------------------
CREATE TABLE iterations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL CHECK (iteration_number > 0),
    input_prompt TEXT NOT NULL,
    -- NULL cuando el Optimizer devolvió JSON inválido tras el reintento:
    -- la iteración queda "fallida" pero optimizer_raw conserva la evidencia.
    output_prompt TEXT,
    source iteration_source NOT NULL,
    optimizer_raw JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, iteration_number)
);

CREATE INDEX idx_iterations_run_id ON iterations(run_id);

-- ---------------------------------------------------------------------------
-- audits: resultado del Auditor sobre una iteración concreta.
-- Los 4 Gates son PASS / FAIL / NO_APLICA; el score y el detalle de cada
-- Gate quedan en JSONB para no perder nada de la respuesta cruda.
-- ---------------------------------------------------------------------------
CREATE TABLE audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iteration_id UUID NOT NULL REFERENCES iterations(id) ON DELETE CASCADE,
    -- FALSE cuando el JSON del Auditor no pudo parsearse ni tras el
    -- reintento: en ese caso solo raw_response queda garantizado.
    parse_ok BOOLEAN NOT NULL,
    audited_prompt TEXT,
    total_score INTEGER CHECK (total_score IS NULL OR total_score BETWEEN 0 AND 100),
    gates_passed INTEGER NOT NULL DEFAULT 0,
    gates_failed INTEGER NOT NULL DEFAULT 0,
    gates_not_applicable INTEGER NOT NULL DEFAULT 0,
    gates_score NUMERIC(5, 4) CHECK (gates_score IS NULL OR gates_score BETWEEN 0 AND 1),
    properties JSONB,
    gates JSONB,
    recommendations JSONB,
    raw_response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        parse_ok = FALSE
        OR (gates_passed + gates_failed + gates_not_applicable = 4)
    )
);

CREATE INDEX idx_audits_iteration_id ON audits(iteration_id);

-- ---------------------------------------------------------------------------
-- human_decisions: la intervención humana obligatoria tras cada auditoría.
-- ---------------------------------------------------------------------------
CREATE TABLE human_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iteration_id UUID NOT NULL REFERENCES iterations(id) ON DELETE CASCADE,
    decision human_decision_type NOT NULL,
    feedback TEXT,
    -- solo se rellena cuando decision = 'edit'
    edited_prompt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_human_decisions_iteration_id ON human_decisions(iteration_id);

-- ---------------------------------------------------------------------------
-- results: la respuesta final del Executor, tras la aprobación humana.
-- Un run aprobado se ejecuta una sola vez (lo garantiza la máquina de
-- estados: APPROVED -> EXECUTING -> COMPLETED no tiene ciclo de vuelta).
-- ---------------------------------------------------------------------------
CREATE TABLE results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE REFERENCES runs(id) ON DELETE CASCADE,
    approved_prompt TEXT NOT NULL,
    final_response TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
