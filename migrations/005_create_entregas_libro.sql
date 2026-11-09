-- Registro de entrega de libro: datos de la persona + firma + foto de evidencia.
-- Ejecutar en el SQL Editor de Supabase

CREATE TABLE IF NOT EXISTS entregas_libro (
    id serial PRIMARY KEY,
    nombres text NOT NULL,
    apellidos text NOT NULL,
    correo text NOT NULL,
    telefono text NOT NULL,
    identificacion text NOT NULL,
    firma_url text NOT NULL,
    foto_url text NOT NULL,
    registrado_por int REFERENCES usuarios(id),
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_entregas_libro_identificacion ON entregas_libro (identificacion);
