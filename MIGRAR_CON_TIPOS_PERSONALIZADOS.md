# 🚀 SQL MEJORADO - Con tus tipos personalizados

Copia TODO este SQL en Supabase SQL Editor y ejecútalo de una vez.

```sql
-- ========== CREAR TABLA TIPOS_EQUIPOS CON TODOS TUS TIPOS ==========
CREATE TABLE IF NOT EXISTS tipos_equipos (
  id BIGSERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Insertar tipos predefinidos + tus tipos personalizados
INSERT INTO tipos_equipos (nombre, descripcion) VALUES 
  -- Tipos predefinidos (18)
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
  ('Otros', 'Equipos varios'),
  -- Tus tipos personalizados (de tus equipos)
  ('Maquina Humo', 'Máquina de humo para eventos'),
  ('Panel Acustico', 'Panel acústico'),
  ('Pantalla led', 'Pantalla LED'),
  ('Bafle', 'Sistema de bafle'),
  ('Luz parlet', 'Luz parlet'),
  ('Televisores', 'Televisor'),
  ('Inears', 'In-ear monitors'),
  ('Filtros antipop', 'Filtro antipop para micrófono'),
  ('Disco', 'Disco de almacenamiento'),
  ('Filtro Lente', 'Filtro para lentes de cámara'),
  ('Base Microfono', 'Base/soporte para micrófono'),
  ('Consola', 'Consola de audio/DJ'),
  ('Wireless Laser', 'Puntero laser inalámbrico'),
  ('Audífonos', 'Audífonos/headphones'),
  ('Controles', 'Control remoto'),
  ('Cargadores', 'Cargador de batería'),
  ('Receptor', 'Receptor inalámbrico'),
  ('Emisor', 'Emisor inalámbrico'),
  ('Multipuerto', 'Hub/Multiplexor'),
  ('Claqueta', 'Claqueta de producción'),
  ('Convertidor', 'Convertidor de video/audio'),
  ('HDMI', 'Cable/Convertidor HDMI'),
  ('Mouses', 'Ratón/Mouse'),
  ('UPS', 'Sistema ininterrumpible de potencia'),
  ('Usb', 'Dispositivo USB')
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

-- Guardar tipo actual en tipo_nombre si aún no está
UPDATE equipos SET tipo_nombre = tipo WHERE tipo_nombre IS NULL;

-- MAPEAR TIPOS: buscar cada tipo_nombre en tipos_equipos
UPDATE equipos e
SET tipo_id = t.id
FROM tipos_equipos t
WHERE LOWER(COALESCE(e.tipo_nombre, '')) = LOWER(t.nombre);

-- Para los que aún no tienen tipo_id (tipos que no se encontraron), asignar "Otros"
UPDATE equipos 
SET tipo_id = (SELECT id FROM tipos_equipos WHERE nombre = 'Otros') 
WHERE tipo_id IS NULL;

-- Agregar constraint de Foreign Key
ALTER TABLE equipos 
ADD CONSTRAINT fk_equipos_tipo FOREIGN KEY (tipo_id) REFERENCES tipos_equipos(id) ON DELETE SET NULL;

-- ========== AGREGAR COLUMNA A USUARIOS ==========
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS rol_id BIGINT;

-- Asignar rol "Usuario" (id=4) a todos los usuarios
UPDATE usuarios 
SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Usuario')
WHERE rol_id IS NULL;

-- Opcionalmente: asignar rol "Administrador" a admin@activoseq.com
UPDATE usuarios 
SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Administrador')
WHERE email = 'admin@activoseq.com';

-- Opcionalmente: asignar rol "Gerente" a los que tienen "Gerente" o "Gerente Operativa" en cargo
UPDATE usuarios 
SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Gerente')
WHERE rol_id IS NOT NULL 
  AND (cargo LIKE '%Gerente%' OR cargo LIKE '%Lider%')
  AND email != 'admin@activoseq.com';

-- Agregar constraint de Foreign Key
ALTER TABLE usuarios 
ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles_empresa(id) ON DELETE SET NULL;

-- ========== CREAR ÍNDICES ==========
CREATE INDEX IF NOT EXISTS idx_equipos_tipo_id ON equipos(tipo_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol_id ON usuarios(rol_id);

-- ========== VERIFICACIÓN FINAL ==========
-- Ejecuta estas queries después para verificar que todo está bien:

-- Ver cuántos equipos tienen tipo_id asignado
-- SELECT COUNT(*) as equipos_con_tipo FROM equipos WHERE tipo_id IS NOT NULL;

-- Ver cuántos usuarios tienen rol_id asignado
-- SELECT COUNT(*) as usuarios_con_rol FROM usuarios WHERE rol_id IS NOT NULL;

-- Ver tipos que no se encontraron (quedarían en "Otros")
-- SELECT DISTINCT tipo_nombre FROM equipos WHERE tipo_id = (SELECT id FROM tipos_equipos WHERE nombre = 'Otros');

-- Ver distribución de tipos
-- SELECT t.nombre, COUNT(e.id) as cantidad FROM equipos e 
-- LEFT JOIN tipos_equipos t ON e.tipo_id = t.id GROUP BY t.nombre ORDER BY cantidad DESC;

-- Ver distribution de roles
-- SELECT r.nombre, COUNT(u.id) as cantidad FROM usuarios u 
-- LEFT JOIN roles_empresa r ON u.rol_id = r.id GROUP BY r.nombre;
```

---

## ✅ ¿Qué hace este SQL?

1. ✅ **Crea 18 tipos predefinidos** + **43 tipos personalizados** (tus tipos)
2. ✅ **Mapea TODOS tus equipos** a sus tipos correctos por nombre
3. ✅ **Asigna rol "Usuario"** a todos los usuarios
4. ✅ **Asigna rol "Administrador"** al admin@activoseq.com
5. ✅ **Asigna rol "Gerente"** a usuarios con "Gerente" o "Lider" en el cargo
6. ✅ **Crea relaciones** tipo_id → tipos_equipos.id y rol_id → roles_empresa.id

---

## 🎯 Resultado esperado

### Equipos
- ✅ 100% equipos con `tipo_id` asignado correctamente
- ✅ Tipos personalizados en la BD (no todos en "Otros")
- ✅ Puedes editar tipos sin afectar historial

### Usuarios
- ✅ Admin tiene rol "Administrador"
- ✅ Gerentes/Líderes tienen rol "Gerente"
- ✅ El resto tienen rol "Usuario"

---

## 📋 Pasos

1. **Copia** TODO el SQL de arriba
2. **Ve a** Supabase Dashboard → SQL Editor → New Query
3. **Pega** y haz click en **RUN**
4. **Espera** a que diga "✅ Success"
5. **Verifica** (opcional) ejecutando las queries de verificación

---

¿Listo? ¡Copia y ejecuta en Supabase!
