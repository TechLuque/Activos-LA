-- migrations/add_area_acceso_usuarios.sql

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS area_acceso text NOT NULL DEFAULT 'admin';
