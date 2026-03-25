# 🔄 Migración de Estructura de Usuarios - Eliminación de Cargo

## Cambios Principales
- ❌ Eliminar campo `cargo` (redundante con `rol_id`)
- ✅ Hacer `rol_id` el campo principal obligatorio  
- ✅ Convertir `departamento` a SELECT con 6 opciones validadas
- ✅ Agregar CHECK constraint para validar departamentos

## 📋 SQL de Migración

### 1. Agregar CHECK Constraint a departamento (si no existe)

```sql
-- Primero, asegurarse de que todos los usuarios tengan un departamento válido
UPDATE usuarios 
SET departamento = 'Gerencia' 
WHERE departamento IS NULL OR departamento = '';

-- Agregar la restricción CHECK (si la tabla ya tiene datos)
ALTER TABLE usuarios 
ADD CONSTRAINT check_departamento_valido 
CHECK (departamento IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia'));
```

### 2. Hacer rol_id NOT NULL (opcional - si los datos lo permiten)

```sql
-- Verificar que todos tengan rol_id
SELECT COUNT(*) FROM usuarios WHERE rol_id IS NULL;

-- Si el resultado es 0, hacer NOT NULL:
ALTER TABLE usuarios 
ALTER COLUMN rol_id SET NOT NULL;
```

### 3. Eliminar columna cargo (DESPUÉS de verificar que ya no se usa)

```sql
-- OPCIÓN A: Eliminar columna completamente
ALTER TABLE usuarios DROP COLUMN cargo;

-- OPCIÓN B: Renombrar como deprecated (más seguro)
-- ALTER TABLE usuarios RENAME COLUMN cargo TO cargo_deprecated;
```

### 4. Actualizar tabla si no existe la columna departamento

```sql
-- Si departamento no existe:
ALTER TABLE usuarios 
ADD COLUMN departamento VARCHAR(50);

-- Luego aplicar restricción:
ALTER TABLE usuarios 
ADD CONSTRAINT check_departamento_valido 
CHECK (departamento IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia'));
```

## 📊 Estrategia de Asignación de Departamentos

### Opción 1: Asignar por Rol (Automático)
```sql
-- Ejemplo: Los Administradores y Gerentes → Gerencia
UPDATE usuarios 
SET departamento = 'Gerencia'
WHERE rol_id IN (
  SELECT id FROM roles_empresa WHERE nombre LIKE '%Gerente%' OR nombre = 'Administrador'
);

-- Productores → Producción
UPDATE usuarios 
SET departamento = 'Producción'
WHERE rol_id IN (
  SELECT id FROM roles_empresa WHERE nombre LIKE '%Productor%'
);

-- Académicos → Academia
UPDATE usuarios 
SET departamento = 'Academia'
WHERE rol_id IN (
  SELECT id FROM roles_empresa WHERE nombre LIKE '%Academia%'
);

-- Resto: Asignar a Gerencia por defecto
UPDATE usuarios 
SET departamento = 'Gerencia'
WHERE departamento IS NULL OR departamento = '';
```

### Opción 2: Asignar Manual (más seguro)
```sql
-- Si prefieres hacerlo manualmente a través del UI, simplemente:
-- 1. Asegurar que todos los usuarios tengan al menos un departamento
UPDATE usuarios 
SET departamento = 'Gerencia' 
WHERE departamento IS NULL OR departamento = '';

-- 2. Luego, actualizar uno por uno a través de la interfaz
```

## 🔄 Orden de Ejecución

### PASO 1: Preparar datos existentes
```sql
-- Paso 1: Asignar departamento a usuarios sin departamento
UPDATE usuarios 
SET departamento = 'Gerencia'
WHERE departamento IS NULL OR departamento = '';
```

### PASO 2: Agregar restricción
```sql
-- Paso 2: Agregar CHECK constraint
ALTER TABLE usuarios 
ADD CONSTRAINT check_departamento_valido 
CHECK (departamento IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia'));
```

### PASO 3: Renombrar cargo a deprecated (opción segura)
```sql
-- Paso 3: Renombrar campo cargo como deprecated
ALTER TABLE usuarios RENAME COLUMN cargo TO cargo_deprecated;

-- Esto evita perder datos históricos y permite rollback si es necesario
```

### PASO 4: O eliminar directamente (opción agresiva)
```sql
-- O eliminar completamente si estás seguro
ALTER TABLE usuarios DROP COLUMN cargo;
```

## 📝 Verificación Post-Migración

```sql
-- Verificar estructura
\d usuarios;

-- Contar usuarios por departamento
SELECT departamento, COUNT(*) FROM usuarios GROUP BY departamento;

-- Verificar que todos tienen rol_id
SELECT COUNT(*) as sin_rol FROM usuarios WHERE rol_id IS NULL;

-- Ver usuarios con departamento inválido (no debería haber ninguno)
SELECT * FROM usuarios 
WHERE departamento NOT IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia');
```

## ⚠️ Rollback (si algo sale mal)

```sql
-- Restaurar columna cargo si fue renombrada
ALTER TABLE usuarios RENAME COLUMN cargo_deprecated TO cargo;

-- O recrearla si fue eliminada
ALTER TABLE usuarios ADD COLUMN cargo VARCHAR(100);

-- Eliminar constraint si fue agregado
ALTER TABLE usuarios DROP CONSTRAINT check_departamento_valido;
```

## 🚀 Script Final Simplificado (SIN COLUMNA CARGO)

**Estado:** El constraint ya fue creado exitosamente ✅

Solo verifica el estado actual:

```sql
-- Ver distribución de departamentos (33 usuarios esperados)
SELECT departamento, COUNT(*) as cantidad 
FROM usuarios 
GROUP BY departamento
ORDER BY cantidad DESC;

-- Verificar que todos tienen rol_id
SELECT COUNT(*) as sin_rol FROM usuarios WHERE rol_id IS NULL;

-- Ver estructura de la tabla
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;
```

**Si necesitas recrear el constraint (eliminar y crear de nuevo):**

```sql
-- Solo si quieres hacerlo de nuevo (no es necesario si ya funciona):
ALTER TABLE usuarios DROP CONSTRAINT check_departamento_valido;

ALTER TABLE usuarios 
ADD CONSTRAINT check_departamento_valido 
CHECK (departamento IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia'));
```

## 📌 Notas Importantes

- ✅ El frontend ya validará los departamentos en el formulario
- ✅ El backend validará al recibir POST/PUT
- ✅ La base de datos validará con CHECK constraint
- ⚠️ Ejecutar estas migraciones es **IRREVERSIBLE** (a menos que hagas backup)
- 💾 Se recomienda hacer backup de la base de datos antes
- 🔒 Si usas Supabase, estas operaciones requieren permisos de administrador
