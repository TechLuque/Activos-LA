-- migrations/add_ciudad_usuarios.sql

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS ciudad text;
