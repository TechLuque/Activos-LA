-- Agrega columnas para fotos adicionales de evidencia en préstamos (más allá de las 2 fijas)
-- Las 2 fotos originales (imagen1_url/imagen2_url y sus versiones de devolución) se mantienen igual.
-- Las columnas nuevas guardan un array de URLs (jsonb) con las fotos extra que el usuario añada.
-- Ejecutar en el SQL Editor de Supabase

ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS imagenes_extra_urls JSONB DEFAULT '[]'::jsonb;
ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS imagenes_extra_devolucion_urls JSONB DEFAULT '[]'::jsonb;

ALTER TABLE prestamos_masivos ADD COLUMN IF NOT EXISTS imagenes_extra_urls JSONB DEFAULT '[]'::jsonb;
ALTER TABLE prestamos_masivos ADD COLUMN IF NOT EXISTS imagenes_extra_devolucion_urls JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN prestamos.imagenes_extra_urls IS 'URLs adicionales de evidencia fotográfica inicial, más allá de las 2 fotos fijas (imagen1_url/imagen2_url).';
COMMENT ON COLUMN prestamos.imagenes_extra_devolucion_urls IS 'URLs adicionales de evidencia fotográfica de devolución, más allá de las 2 fotos fijas.';
COMMENT ON COLUMN prestamos_masivos.imagenes_extra_urls IS 'URLs adicionales de evidencia fotográfica inicial, más allá de las 2 fotos fijas (imagen1_url/imagen2_url).';
COMMENT ON COLUMN prestamos_masivos.imagenes_extra_devolucion_urls IS 'URLs adicionales de evidencia fotográfica de devolución, más allá de las 2 fotos fijas.';
