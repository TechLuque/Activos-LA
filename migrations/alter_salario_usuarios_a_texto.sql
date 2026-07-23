-- migrations/alter_salario_usuarios_a_texto.sql
-- El salario en el contrato admite texto libre (ej. "$2.500.000 + prestaciones de ley"),
-- por lo que la columna deja de ser numerica para guardar el valor tal cual se escribe.

ALTER TABLE usuarios
    ALTER COLUMN salario TYPE text USING salario::text;
