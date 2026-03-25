# SQL para crear tablas de Tipos de Equipos y Roles

## 🚨 INSTRUCCIONES CRÍTICAS

1. Abre el **Supabase Dashboard**: https://app.supabase.com/
2. Selecciona tu proyecto **ActivosEQ**
3. Ve a **SQL Editor** en el menú izquierdo
4. Copia y ejecuta CADA bloque de SQL abajo
5. Ejecuta en este orden:
   - Bloque 1: Crear tabla `tipos_equipos`
   - Bloque 2: Crear tabla `roles_empresa` 
   - Bloque 3: Insertar datos de tipos
   - Bloque 4: Insertar datos de roles

---

## ✅ BLOQUE 1: Crear tabla `tipos_equipos`

```sql
CREATE TABLE tipos_equipos (
  id BIGSERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índice para búsquedas rápidas
CREATE INDEX idx_tipos_equipos_nombre ON tipos_equipos(nombre);

-- Habilitar RLS (Row Level Security)
ALTER TABLE tipos_equipos ENABLE ROW LEVEL SECURITY;

-- Crear política para permitir lectura a todos
CREATE POLICY "Permitir lectura de tipos_equipos" 
  ON tipos_equipos FOR SELECT 
  USING (true);

-- Crear política para permitir escritura a usuarios autenticados
CREATE POLICY "Permitir escritura de tipos_equipos" 
  ON tipos_equipos FOR INSERT 
  WITH CHECK (true);

-- Crear política para permitir actualización
CREATE POLICY "Permitir actualización de tipos_equipos" 
  ON tipos_equipos FOR UPDATE 
  USING (true) 
  WITH CHECK (true);

-- Crear política para permitir eliminación
CREATE POLICY "Permitir eliminación de tipos_equipos" 
  ON tipos_equipos FOR DELETE 
  USING (true);
```

---

## ✅ BLOQUE 2: Crear tabla `roles_empresa`

```sql
CREATE TABLE roles_empresa (
  id BIGSERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  permisos TEXT DEFAULT '[]',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índice
CREATE INDEX idx_roles_empresa_nombre ON roles_empresa(nombre);

-- Habilitar RLS
ALTER TABLE roles_empresa ENABLE ROW LEVEL SECURITY;

-- Políticas
CREATE POLICY "Permitir lectura de roles_empresa" 
  ON roles_empresa FOR SELECT 
  USING (true);

CREATE POLICY "Permitir escritura de roles_empresa" 
  ON roles_empresa FOR INSERT 
  WITH CHECK (true);

CREATE POLICY "Permitir actualización de roles_empresa" 
  ON roles_empresa FOR UPDATE 
  USING (true) 
  WITH CHECK (true);

CREATE POLICY "Permitir eliminación de roles_empresa" 
  ON roles_empresa FOR DELETE 
  USING (true);
```

---

## ✅ BLOQUE 3: Insertar Tipos de Equipos

```sql
INSERT INTO tipos_equipos (nombre, descripcion) VALUES 
  ('Computador', 'PC de escritorio'),
  ('Laptop', 'Computadora portátil'),
  ('Monitor', 'Pantalla de monitor'),
  ('Teclado', 'Teclado estándar'),
  ('Ratón', 'Ratón de computadora'),
  ('Servidor', 'Servidor web/datos'),
  ('Router', 'Equipo de red'),
  ('Switch', 'Switch de red'),
  ('Impresora', 'Impresora de red'),
  ('Proyector', 'Proyector multimedia'),
  ('Cámara', 'Cámara digital'),
  ('Escáner', 'Escáner de documentos'),
  ('Parlante', 'Sistema de audio'),
  ('Micrófono', 'Micrófono'),
  ('Webcam', 'Cámara web'),
  ('Tableta', 'Tablet o iPad'),
  ('Teléfono', 'Telefóno celular'),
  ('Otros', 'Equipos varios');
```

---

## ✅ BLOQUE 4: Insertar Roles de Empresa

```sql
INSERT INTO roles_empresa (nombre, descripcion, permisos) VALUES 
  ('Administrador', 'Acceso completo al sistema', '["read","write","delete","admin"]'),
  ('Gerente', 'Gestión de equipos y préstamos', '["read","write","approve"]'),
  ('Técnico', 'Soporte y mantenimiento de activos', '["read","write","maintenance"]'),
  ('Usuario', 'Acceso básico a consulta de equipos', '["read"]');
```

---

## 🔍 Verificar que se creó correctamente

Después de ejecutar el SQL, verifica en Supabase que las tablas existan:

1. Ve a **Database** → **Tables** en el menú izquierdo
2. Deberías ver:
   - ✅ `tipos_equipos` (con 18 registros)
   - ✅ `roles_empresa` (con 4 registros)

---

## 🧪 Test de API (opcional)

Una vez creadas las tablas, prueba estos endpoints:

```bash
# Obtener todos los tipos de equipos
curl https://tu-vercel-domain.vercel.app/api/tipos-equipos

# Obtener todos los roles
curl https://tu-vercel-domain.vercel.app/api/roles
```

---

## ⚠️ Solución de problemas

**Si ves error: "Relation ... does not exist"**
- Confirma que ejecutaste el BLOQUE 1 y BLOQUE 2 exitosamente
- Recarga la página si trabajas desde el frontend

**Si ves error: "Permission denied"**
- Asegúrate de que las políticas RLS se crearon (BLOQUE 1, BLOQUE 2 incluyen esto)
- Verifica que el `SUPABASE_KEY` esté configurado en Vercel Environment Variables

**Si las tablas no aparecen en UI**
- Espera 5-10 segundos (a veces Supabase tarda en sincronizar)
- Recarga el dashboard de Supabase
- Revisa la consola del navegador para errores

---

## ✨ Después de crear las tablas

1. Navega a la sección **Equipos** en la aplicación
2. Haz clic en **+ Nuevo equipo**
3. En el dropdown de "Tipo" deberías ver los 18 tipos listados
4. Puedes agregar nuevos tipos haciendo clic en el botón **➕**

¡Listo! 🎉
