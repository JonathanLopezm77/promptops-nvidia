-- Cambios del Parcial 1 sobre las tablas originales de backend/schema.sql.
--
-- Idempotente: backend/main.py lo aplica al arrancar (después de
-- schema_requirements.sql) para que las bases de datos ya creadas, como la
-- de Render, reciban los cambios sin ejecutar SQL a mano. Para una base
-- nueva, schema.sql ya incluye estos valores.

-- Punto 4: auditoría de línea base. Una iteración 'original' guarda el
-- prompt tal como lo escribió el humano, auditado ANTES de optimizarlo, para
-- tener las métricas iniciales y el delta que exige el enunciado (6.1).
-- ADD VALUE puede ir dentro de una transacción desde PostgreSQL 12.
ALTER TYPE iteration_source ADD VALUE IF NOT EXISTS 'original';

-- Punto 4: el Optimizer tiene modelo de respaldo (kimi-k3 degenera de forma
-- intermitente). Cada iteración registra qué modelo produjo su versión y,
-- si hubo respaldo, el modelo original, el motivo y su respuesta cruda.
ALTER TABLE iterations ADD COLUMN IF NOT EXISTS model TEXT;
ALTER TABLE iterations ADD COLUMN IF NOT EXISTS optimizer_fallback JSONB;
