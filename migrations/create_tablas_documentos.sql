-- migrations/create_tablas_documentos.sql

CREATE TABLE tipos_documento (
    id serial PRIMARY KEY,
    nombre text NOT NULL,
    metodo_generacion text NOT NULL CHECK (metodo_generacion IN ('overlay_pdf', 'plantilla_docx')),
    plantilla_path text NOT NULL,
    campos_requeridos jsonb DEFAULT '[]',   -- ej: [{"key":"periodo","label":"Periodo","tipo":"text"}]
    aplica_a jsonb DEFAULT '["nomina","prestacion_servicios"]',
    coordenadas jsonb,                       -- posiciones x1/bottom para overlay_pdf
    activo boolean DEFAULT true,
    creado_en timestamptz DEFAULT now()
);

CREATE TABLE documentos_generados (
    id serial PRIMARY KEY,
    usuario_id int REFERENCES usuarios(id),
    tipo_documento_id int REFERENCES tipos_documento(id),
    datos_adicionales jsonb DEFAULT '{}',
    archivo_url text,
    generado_por text,
    generado_en timestamptz DEFAULT now()
);

CREATE INDEX idx_docgen_usuario ON documentos_generados (usuario_id);