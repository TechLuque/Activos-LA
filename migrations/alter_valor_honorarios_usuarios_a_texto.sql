-- migrations/alter_valor_honorarios_usuarios_a_texto.sql
-- El valor de honorarios en el contrato admite texto libre (ej. "$2.500.000 mensuales"),
-- por lo que la columna deja de ser numerica para guardar el valor tal cual se escribe.

ALTER TABLE usuarios
    ALTER COLUMN valor_honorarios TYPE text USING valor_honorarios::text;
