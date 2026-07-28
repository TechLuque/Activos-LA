-- migrations/add_nacionalidad_usuarios.sql

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS nacionalidad text;
