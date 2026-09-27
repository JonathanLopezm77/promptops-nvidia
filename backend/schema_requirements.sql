-- Esquema de la capa de Ingeniería de Requisitos (Parcial 1, Componente 1).
-- Complementa backend/schema.sql sin tocar sus cinco tablas.
--
-- Es idempotente (IF NOT EXISTS): se puede aplicar a mano con
--   psql promptops -f backend/schema_requirements.sql
-- y además backend/main.py lo aplica al arrancar, para que las bases de
-- datos ya desplegadas (p. ej. la de Render) reciban las tablas nuevas sin
-- que nadie tenga que entrar a ejecutar SQL. Los estados se guardan como
-- TEXT + CHECK en vez de ENUM porque CREATE TYPE no admite IF NOT EXISTS.

-- ---------------------------------------------------------------------------
-- requirement_analyses: un análisis completo de un requisito, desde el
-- texto (o la transcripción de voz) hasta el requisito mejorado.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requirement_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Cuando el usuario responde las preguntas de aclaración se crea un
    -- análisis nuevo ligado al anterior, que queda intacto para auditoría.
    parent_id UUID REFERENCES requirement_analyses(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'CREATED' CHECK (
        status IN ('CREATED', 'EVALUATING', 'IMPROVING', 'REEVALUATING', 'COMPLETED', 'ERROR')
    ),
    input_mode TEXT NOT NULL DEFAULT 'text' CHECK (input_mode IN ('text', 'voice')),
    -- Motor de STT, idioma, duración, etc. Solo cuando input_mode = 'voice'.
    stt_metadata JSONB,
    original_requirement TEXT NOT NULL,
    project_context TEXT,
    clarifications TEXT,
    evaluator_model TEXT NOT NULL,
    improver_model TEXT NOT NULL,
    -- TRUE cuando el requisito original ya era de alta calidad y no se
    -- modificó (caso A del parcial: evitar modificaciones innecesarias).
    improvement_skipped BOOLEAN NOT NULL DEFAULT FALSE,
    improved_requirement TEXT,
    -- changes, acceptance_criteria, pending_items, intent_preservation,
    -- unsupported_values (números sin respaldo en las fuentes) y
    -- unsupported_retry (si hubo que pedir corregirlos)
    improvement JSONB,
    -- Respuesta cruda del Mejorador; se guarda aunque el parseo falle.
    improvement_raw JSONB,
    improvement_tokens INTEGER,
    improvement_latency_ms INTEGER,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_requirement_analyses_created_at
    ON requirement_analyses(created_at DESC);

-- Cada vez que el resultado se lee en voz alta (TTS) se registra motor,
-- voz, si es local o remota, el texto leído y la hora: es la evidencia de
-- la retroalimentación hablada (caso D). Se agrega con ALTER ... IF NOT
-- EXISTS para que también llegue a las bases de datos ya creadas.
ALTER TABLE requirement_analyses
    ADD COLUMN IF NOT EXISTS tts_log JSONB NOT NULL DEFAULT '[]'::jsonb;

-- ---------------------------------------------------------------------------
-- requirement_evaluations: la evaluación de los 10 criterios de calidad,
-- una para el requisito original y (si hubo mejora) otra para el mejorado.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requirement_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES requirement_analyses(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN ('original', 'improved')),
    -- Texto exacto que recibió el Evaluador (requisito + criterios de
    -- aceptación en el caso del mejorado).
    evaluated_text TEXT NOT NULL,
    parse_ok BOOLEAN NOT NULL,
    -- Calculado en código (no por el LLM): promedio de los 10 criterios x 10.
    global_score INTEGER CHECK (global_score IS NULL OR global_score BETWEEN 0 AND 100),
    is_high_quality BOOLEAN,
    criteria JSONB,
    ambiguous_terms JSONB,
    clarification_questions JSONB,
    missing_information JSONB,
    is_compound BOOLEAN,
    summary TEXT,
    raw_response JSONB NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (analysis_id, stage),
    CHECK (parse_ok = FALSE OR (global_score IS NOT NULL AND criteria IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_requirement_evaluations_analysis_id
    ON requirement_evaluations(analysis_id);
