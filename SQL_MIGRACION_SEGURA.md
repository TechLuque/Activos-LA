# 🔧 SQL SEGURO - Migración de Tipos y Roles (CON DATOS ACTUALES PROTEGIDOS)

## ⚠️ IMPORTANTE: LEE ANTES DE EJECUTAR

Este SQL está diseñado para:
- ✅ Crear nuevas tablas `tipos_equipos` y `roles_empresa`
- ✅ Migrar tus datos actuales de `equipos.tipo` (texto) a IDs
- ✅ Mantener TODAS las relaciones existentes intactas
- ✅ Preservar índices y constraints
- ✅ Sin pérdida de datos

---

## ✅ BLOQUE 1: Crear tabla `tipos_equipos` con todos tus tipos

```sql
CREATE TABLE IF NOT EXISTS tipos_equipos (
  id BIGSERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Insertar TODOS los tipos (18)
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
  ('Otros', 'Equipos varios')
ON CONFLICT (nombre) DO NOTHING;

-- Crear índice para búsquedas
CREATE INDEX IF NOT EXISTS idx_tipos_equipos_nombre ON tipos_equipos(nombre);

-- RLS Policies
ALTER TABLE tipos_equipos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir lectura de tipos_equipos" 
  ON tipos_equipos FOR SELECT 
  USING (true);

CREATE POLICY "Permitir escritura de tipos_equipos" 
  ON tipos_equipos FOR INSERT 
  WITH CHECK (true);

CREATE POLICY "Permitir actualización de tipos_equipos" 
  ON tipos_equipos FOR UPDATE 
  USING (true) WITH CHECK (true);

CREATE POLICY "Permitir eliminación de tipos_equipos" 
  ON tipos_equipos FOR DELETE 
  USING (true);
```

---

## ✅ BLOQUE 2: Crear tabla `roles_empresa`

```sql
CREATE TABLE IF NOT EXISTS roles_empresa (
  id BIGSERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  permisos TEXT DEFAULT '[]',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO roles_empresa (nombre, descripcion, permisos) VALUES 
  ('Administrador', 'Acceso completo al sistema', '["read","write","delete","admin"]'),
  ('Gerente', 'Gestión de equipos y préstamos', '["read","write","approve"]'),
  ('Técnico', 'Soporte y mantenimiento de activos', '["read","write","maintenance"]'),
  ('Usuario', 'Acceso básico a consulta de equipos', '["read"]')
ON CONFLICT (nombre) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_roles_empresa_nombre ON roles_empresa(nombre);

ALTER TABLE roles_empresa ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir lectura de roles_empresa" 
  ON roles_empresa FOR SELECT 
  USING (true);

CREATE POLICY "Permitir escritura de roles_empresa" 
  ON roles_empresa FOR INSERT 
  WITH CHECK (true);

CREATE POLICY "Permitir actualización de roles_empresa" 
  ON roles_empresa FOR UPDATE 
  USING (true) WITH CHECK (true);

CREATE POLICY "Permitir eliminación de roles_empresa" 
  ON roles_empresa FOR DELETE 
  USING (true);
```

---

## ✅ BLOQUE 3: Modificar tabla `equipos` para usar `tipo_id` en lugar de `tipo TEXT`

### 3.1 Agregar columna temporal para almacenar tipo antiguo
```sql
-- Agregar columna temporal para guardar el tipo antiguo
ALTER TABLE equipos 
ADD COLUMN tipo_nombre TEXT;

-- Copiar datos actuales
UPDATE equipos 
SET tipo_nombre = tipo;
```

### 3.2 Crear nueva columna `tipo_id` y llenarla
```sql
-- Agregar columna tipo_id
ALTER TABLE equipos 
ADD COLUMN tipo_id BIGINT;

-- Crear relación con tipos_equipos (llena los IDs basado en el nombre)
UPDATE equipos e
SET tipo_id = t.id
FROM tipos_equipos t
WHERE LOWER(e.tipo_nombre) = LOWER(t.nombre)
  OR (LOWER(e.tipo_nombre) IN ('pc', 'computadora', 'desktop') AND t.nombre = 'Computador')
  OR (LOWER(e.tipo_nombre) IN ('computadora portátil', 'portátil', 'notebook') AND t.nombre = 'Laptop');

-- Para los que no coincidieron, asignar a 'Otros'
UPDATE equipos 
SET tipo_id = (SELECT id FROM tipos_equipos WHERE nombre = 'Otros')
WHERE tipo_id IS NULL;

-- Agregar constraint de foreign key
ALTER TABLE equipos 
ADD CONSTRAINT fk_equipos_tipo FOREIGN KEY (tipo_id) REFERENCES tipos_equipos(id) ON DELETE SET NULL;

-- ⚠️ IMPORTANTE: NO ELIMINAR COLUMNA `tipo` AÚN
-- La aplicación sigue leyendo de ella. Se eliminará después de actualizar el código.
```

---

## ✅ BLOQUE 4: Agregar `rol_id` a tabla `usuarios`

```sql
-- Agregar columna rol_id
ALTER TABLE usuarios 
ADD COLUMN rol_id BIGINT,
ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles_empresa(id) ON DELETE SET NULL;

-- Asignar rol por defecto "Usuario" a todos los existentes
UPDATE usuarios 
SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Usuario')
WHERE rol_id IS NULL;

-- Opcional: si tienes usuarios "admin" en tu aplicación, puedes actualizar:
-- UPDATE usuarios 
-- SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Administrador')
-- WHERE email = 'admin@example.com';  -- CAMBIAR ESTO
```

---

## ✅ BLOQUE 5: Crear índices adicionales

```sql
-- Índices para relaciones
CREATE INDEX IF NOT EXISTS idx_equipos_tipo_id ON equipos(tipo_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol_id ON usuarios(rol_id);
```

---

## 🔍 VERIFICAR QUE TODO ESTÁ BIEN

```sql
-- Ver tipos creados
SELECT COUNT(*) as total_tipos FROM tipos_equipos;
-- Deberías ver: 18

-- Ver roles creados
SELECT COUNT(*) as total_roles FROM roles_empresa;
-- Deberías ver: 4

-- Ver equipos con sus tipos migrados
SELECT e.id, e.nombre, e.tipo, t.nombre as tipo_nuevo
FROM equipos e
LEFT JOIN tipos_equipos t ON e.tipo_id = t.id
LIMIT 10;

-- Ver usuarios con sus roles
SELECT u.id, u.nombre, u.email, r.nombre as rol
FROM usuarios u
LEFT JOIN roles_empresa r ON u.rol_id = r.id
LIMIT 10;
```

---

## 🚀 ORDEN DE EJECUCIÓN (CRÍTICO)

1. **PRIMERO**: BLOQUE 1 (crear tipos_equipos)
2. **SEGUNDO**: BLOQUE 2 (crear roles_empresa)
3. **TERCERO**: BLOQUE 3.1 (agregar tipo_nombre temporal)
4. **CUARTO**: BLOQUE 3.2 (agregar tipo_id y llenar datos)
5. **QUINTO**: BLOQUE 4 (agregar rol_id a usuarios)
6. **SEXTO**: BLOQUE 5 (índices)
7. **SÉPTIMO**: EJECUTAR VERIFICACIÓN

---

## ⚠️ IMPORTANTE: Después de ejecutar el SQL

Tu código en `app.py` sigue funcionando porque:
- ✅ La columna `tipo TEXT` sigue existiendo en equipos (NO la eliminamos)
- ✅ La nueva columna `tipo_id` está ahí pero la app la ignora por ahora
- ✅ Los datos están duplicados (tipo y tipo_id) pero sincronizados

**Próximo paso**: Actualizar `app.py` para usar `tipo_id` en lugar de `tipo` (se hace en código, no en BD)

---

## 📋 RESUMEN DE CAMBIOS EN BD

| Tabla | Cambio | Seguro? |
|-------|--------|---------|
| `equipos` | Agregó `tipo_id` (FK) | ✅ Sí, `tipo` sigue igual |
| `usuarios` | Agregó `rol_id` (FK) | ✅ Sí, sin datos perdidos |
| Nueva: `tipos_equipos` | 18 registros | ✅ Sí, nueva tabla |
| Nueva: `roles_empresa` | 4 registros | ✅ Sí, nueva tabla |
| `prestamos` | Sin cambios | ✅ Sí, intacta |
| `mantenimientos` | Sin cambios | ✅ Sí, intacta |
| `hoja_vida` | Sin cambios | ✅ Sí, intacta |

---

## 🆘 Si algo sale mal

Si después de ejecutar algo te dice error, puedes hacer rollback:

```sql
-- Deshacer TODO (en orden inverso)
ALTER TABLE usuarios DROP CONSTRAINT fk_usuarios_rol;
ALTER TABLE usuarios DROP COLUMN rol_id;

ALTER TABLE equipos DROP CONSTRAINT fk_equipos_tipo;
ALTER TABLE equipos DROP COLUMN tipo_id;
ALTER TABLE equipos DROP COLUMN tipo_nombre;

DROP TABLE roles_empresa;
DROP TABLE tipos_equipos;
```

---

## ✨ Ahora sí, ¡a ejecutar!

1. Abre Supabase Dashboard → SQL Editor
2. Copia y ejecuta BLOQUE 1
3. Espera OK ✓
4. Copia y ejecuta BLOQUE 2
5. Espera OK ✓
6. Copia y ejecuta BLOQUE 3.1
7. Espera OK ✓
8. Copia y ejecuta BLOQUE 3.2
9. Espera OK ✓
10. Copia y ejecuta BLOQUE 4
11. Espera OK ✓
12. Copia y ejecuta BLOQUE 5
13. Espera OK ✓
14. Copia y ejecuta VERIFICACIÓN para confirmar

Cuando todo esté OK, avísame para actualizar `app.py` para usar las nuevas columnas.

