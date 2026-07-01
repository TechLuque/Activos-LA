-- Crea tabla equipo_adjuntos: galería de archivos por equipo (factura, garantía, foto, informe, otro)
-- Reemplaza el uso del campo equipos.factura_url
-- Ejecutar en el SQL Editor de Supabase

CREATE TABLE IF NOT EXISTS equipo_adjuntos (
  id BIGSERIAL PRIMARY KEY,
  equipo_id BIGINT NOT NULL REFERENCES equipos(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL CHECK (tipo IN ('factura', 'garantia', 'foto', 'informe', 'otro')),
  nombre_archivo TEXT,
  url TEXT NOT NULL,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_equipo_adjuntos_equipo_id ON equipo_adjuntos (equipo_id);

COMMENT ON TABLE equipo_adjuntos IS 'Galería de archivos adjuntos por equipo: factura, garantía, fotos, informes de mantenimiento, otros.';

-- Migra la factura existente (si la hay) de equipos.factura_url a la nueva tabla
INSERT INTO equipo_adjuntos (equipo_id, tipo, nombre_archivo, url, creado_en)
SELECT id, 'factura', NULL, factura_url, now()
FROM equipos
WHERE factura_url IS NOT NULL AND factura_url <> '';

-- Nota: la columna equipos.factura_url queda sin usarse tras este cambio.
-- Una vez verificada la migración de datos, puede eliminarse manualmente con:
-- ALTER TABLE equipos DROP COLUMN factura_url;
