-- Agrega columna notification_email a la tabla usuarios
-- Permite enviar notificaciones a un correo distinto del email de login
-- Ejecutar en el SQL Editor de Supabase

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS notification_email TEXT;

-- Índice opcional para búsquedas por notification_email
CREATE INDEX IF NOT EXISTS idx_usuarios_notification_email ON usuarios (notification_email);

-- Comentario para documentar la columna
COMMENT ON COLUMN usuarios.notification_email IS 'Correo alternativo para notificaciones. Si es NULL, se usa el email del usuario.';
