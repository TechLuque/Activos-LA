-- migrations/add_direccion_correo_personal_usuarios.sql

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS direccion text,
    ADD COLUMN IF NOT EXISTS correo_personal text;
