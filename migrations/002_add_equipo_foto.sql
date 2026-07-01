-- Agrega columna foto_url a la tabla equipos
-- Foto del equipo físico, se muestra como avatar en el encabezado de la Hoja de Vida
-- Ejecutar en el SQL Editor de Supabase

ALTER TABLE equipos ADD COLUMN IF NOT EXISTS foto_url TEXT;

COMMENT ON COLUMN equipos.foto_url IS 'URL pública de la foto del equipo físico (Supabase Storage). Se muestra como avatar en la Hoja de Vida.';
