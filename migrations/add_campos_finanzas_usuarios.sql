-- migrations/add_campos_finanzas_usuarios.sql

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS cedula text,
    ADD COLUMN IF NOT EXISTS cargo text,
    ADD COLUMN IF NOT EXISTS tipo_vinculacion text
        CHECK (tipo_vinculacion IN ('nomina', 'prestacion_servicios')),
    ADD COLUMN IF NOT EXISTS fecha_ingreso date,
    ADD COLUMN IF NOT EXISTS fecha_retiro date,

    -- Solo nómina
    ADD COLUMN IF NOT EXISTS salario numeric(12,2),
    ADD COLUMN IF NOT EXISTS tipo_contrato text,
    ADD COLUMN IF NOT EXISTS eps text,
    ADD COLUMN IF NOT EXISTS fondo_pension text,

    -- Solo prestación de servicios
    ADD COLUMN IF NOT EXISTS valor_honorarios numeric(12,2),
    ADD COLUMN IF NOT EXISTS objeto_contrato text,
    ADD COLUMN IF NOT EXISTS fecha_fin_contrato date;

CREATE INDEX IF NOT EXISTS idx_usuarios_cedula ON usuarios (cedula);