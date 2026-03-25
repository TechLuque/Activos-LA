# 🚀 EJECUTAR AHORA - Migración Segura en Producción

## ⏰ Tiempo total: 10-15 minutos

Este es el plan FINAL para migrar tu BD sin perder nada.

---

## PASO 1: Ejecutar SQL en Supabase (5 minutos)

### 1.1 Abre Supabase
- Ve a: https://app.supabase.com/
- Selecciona tu proyecto
- Ve a: **SQL Editor** → **New Query**

### 1.2 Copia este SQL COMPLETO y ejecuta TODO de una vez

```sql
-- ========== CREAR TABLA TIPOS_EQUIPOS ==========
CREATE TABLE IF NOT EXISTS tipos_equipos (
  id BIGSERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

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

CREATE INDEX IF NOT EXISTS idx_tipos_equipos_nombre ON tipos_equipos(nombre);
ALTER TABLE tipos_equipos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Permitir lectura de tipos_equipos" ON tipos_equipos FOR SELECT USING (true);
CREATE POLICY "Permitir escritura de tipos_equipos" ON tipos_equipos FOR INSERT WITH CHECK (true);
CREATE POLICY "Permitir actualización de tipos_equipos" ON tipos_equipos FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "Permitir eliminación de tipos_equipos" ON tipos_equipos FOR DELETE USING (true);

-- ========== CREAR TABLA ROLES_EMPRESA ==========
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
CREATE POLICY "Permitir lectura de roles_empresa" ON roles_empresa FOR SELECT USING (true);
CREATE POLICY "Permitir escritura de roles_empresa" ON roles_empresa FOR INSERT WITH CHECK (true);
CREATE POLICY "Permitir actualización de roles_empresa" ON roles_empresa FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "Permitir eliminación de roles_empresa" ON roles_empresa FOR DELETE USING (true);

-- ========== AGREGAR COLUMNAS A EQUIPOS ==========
ALTER TABLE equipos 
ADD COLUMN IF NOT EXISTS tipo_nombre TEXT,
ADD COLUMN IF NOT EXISTS tipo_id BIGINT;

UPDATE equipos SET tipo_nombre = tipo WHERE tipo_nombre IS NULL;

UPDATE equipos e
SET tipo_id = t.id
FROM tipos_equipos t
WHERE LOWER(COALESCE(e.tipo_nombre, '')) = LOWER(t.nombre)
   OR (LOWER(COALESCE(e.tipo_nombre, '')) IN ('pc', 'computadora', 'desktop') AND t.nombre = 'Computador')
   OR (LOWER(COALESCE(e.tipo_nombre, '')) IN ('computadora portátil', 'portátil', 'notebook') AND t.nombre = 'Laptop');

UPDATE equipos SET tipo_id = (SELECT id FROM tipos_equipos WHERE nombre = 'Otros') WHERE tipo_id IS NULL;

ALTER TABLE equipos 
ADD CONSTRAINT fk_equipos_tipo FOREIGN KEY (tipo_id) REFERENCES tipos_equipos(id) ON DELETE SET NULL;

-- ========== AGREGAR COLUMNA A USUARIOS ==========
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS rol_id BIGINT;

ALTER TABLE usuarios 
ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles_empresa(id) ON DELETE SET NULL;

UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Usuario') WHERE rol_id IS NULL;

-- ========== CREAR ÍNDICES ==========
CREATE INDEX IF NOT EXISTS idx_equipos_tipo_id ON equipos(tipo_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol_id ON usuarios(rol_id);
```

✅ **Haz click en RUN y espera a que diga "Success"**

---

## PASO 2: Verificar en Supabase (2 minutos)

Ve a **Database** → **Tables** y verifica:

- ✅ `tipos_equipos` existe y tiene 18 registros
- ✅ `roles_empresa` existe y tiene 4 registros  
- ✅ `equipos` tiene columnas: `tipo_id` (nueva), `tipo_nombre` (nueva), `tipo` (original)
- ✅ `usuarios` tiene columna: `rol_id` (nueva)

Si ves esto, ¡listo! La BD está actualizada.

---

## PASO 3: Hacer Commit y Push (2 minutos)

Abre Terminal en VS Code:

```bash
cd "c:\Users\Usuario Normal\Documents\activoseq"
git add -A
git commit -m "Feat: Migración a tipos_equipos y roles_empresa con relaciones ForeignKey

- Crear tabla tipos_equipos con 18 tipos predefinidos
- Crear tabla roles_empresa con 4 roles
- Agregar tipo_id en equipos con FK a tipos_equipos
- Agregar rol_id en usuarios con FK a roles_empresa
- Actualizar endpoints POST/PUT para escribir ambas columnas
- Migración segura: mantener columna tipo (texto) durante transición"

git push origin main
```

✅ Vercel despliega automáticamente en 2-3 minutos

---

## PASO 4: Verificar en Producción (3 minutos)

### 4.1 Espera que Vercel despliegue
- Ve a: https://vercel.com/dashboard
- Proyecto: activoseq
- Espera estado **Ready** (verde)

### 4.2 Prueba en la app
Abre: https://activos-la-9ziz.vercel.app/

1. **Crea nuevo equipo**
   - Equipos → + Nuevo equipo
   - Ves dropdown con: Computador, Laptop, Monitor, etc. ✅

2. **Crea nuevo tipo**
   - Click botón ➕ junto a tipo
   - Modal "Agregar tipo de equipo"
   - Escribe: "Servidor Web"
   - Click **Agregar tipo** ✅
   - Aparece en dropdown (tipo 19) ✅

3. **Verifica en BD**
   - Supabase → Database → Tables → `tipos_equipos`
   - "Servidor Web" debe existir ahí ✅

---

## ✨ ¡LISTO!

Tu sistema ahora tiene:
- ✅ Tipos dinámicos (18 predefinidos + los que crees)
- ✅ Roles centralizados (Administrador, Gerente, Técnico, Usuario)
- ✅ Sincronización automática con BD
- ✅ Compatibilidad con datos antiguos (columna `tipo` sigue ahí)

---

## 🔒 ¿Por qué es seguro?

1. **No eliminamos datos históricos**
   - Columna `tipo` sigue existiendo con todos tus datos
   - Nueva columna `tipo_id` apunta a tipos_equipos
   - Ambas sincronizadas automáticamente

2. **Las relaciones se mantienen**
   - `prestamos` sigue apuntando a `equipos` ✅
   - `equipos` ahora apunta a `tipos_equipos` ✅
   - `usuarios` ahora apunta a `roles_empresa` ✅

3. **Rollback fácil**
   ```sql
   -- Si algo falla, ejecuta esto:
   ALTER TABLE equipos DROP CONSTRAINT fk_equipos_tipo;
   ALTER TABLE usuarios DROP CONSTRAINT fk_usuarios_rol;
   ALTER TABLE equipos DROP COLUMN tipo_id;
   ALTER TABLE usuarios DROP COLUMN rol_id;
   DROP TABLE roles_empresa;
   DROP TABLE tipos_equipos;
   ```

---

## 📞 Soporte

Si ves error:

**"Relation tipos_equipos no existe"**
→ Espera 5 segundos, recarga página

**"Foreign key constraint"**  
→ Verifica que todas las tablas tengan RLS habilitado

**Dropdown vacío de tipos**
→ Abre Console (F12) y verifica `/api/tipos-equipos` retorna datos

---

**¡Ahora sí, adelante! 🎉**
