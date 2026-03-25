# 🔄 Actualización de Roles con Departamentos

## Estructura de Relación Roles → Departamentos

```
Academia
- Lider de Academia
- Atención y Servicio Al Cliente

Contenido
- Lider de Contenido
- Diseñadora Grafica
- Community Manager
- Editor de Video Corto
- Video Marker Largo
- Contenido (General)

Finanzas
- Líder de Finanzas
- Finanzas
- Analista Administrativa

Gerencia
- Gerente
- Gerente Operativa

Plataformas
- Lider de Plataformas
- Soporte Tecnologico y Plataformas
- Tecnología

Producción
- Media Buyer
- Creador Audiovisual
- Producción
- Team Producción
- Copy
- Diseñadora Grafica (Producción)
```

## 📋 SQL de Migración

### 1. Agregar columna departamento a roles_empresa

```sql
-- Agregar columna si no existe
ALTER TABLE roles_empresa 
ADD COLUMN departamento VARCHAR(50);

-- Agregar CHECK constraint
ALTER TABLE roles_empresa 
ADD CONSTRAINT check_rol_departamento 
CHECK (departamento IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia'));
```

### 2. Actualizar roles con departamentos correspondientes

```sql
-- ACADEMIA
UPDATE roles_empresa 
SET departamento = 'Academia'
WHERE nombre IN ('Lider de Academia', 'Atención y Servicio Al Cliente');

-- CONTENIDO
UPDATE roles_empresa 
SET departamento = 'Contenido'
WHERE nombre IN ('Lider de Contenido', 'Diseñadora Grafica', 'Community Manager', 'Editor de Video Corto', 'Video Marker Largo', 'Contenido (General)', 'Contenido');

-- FINANZAS
UPDATE roles_empresa 
SET departamento = 'Finanzas'
WHERE nombre IN ('Líder de Finanzas', 'Finanzas', 'Analista Administrativa');

-- GERENCIA
UPDATE roles_empresa 
SET departamento = 'Gerencia'
WHERE nombre IN ('Gerente', 'Gerente Operativa', 'Administrador');

-- PLATAFORMAS
UPDATE roles_empresa 
SET departamento = 'Plataformas'
WHERE nombre IN ('Lider de Plataformas', 'Soporte Tecnologico y Plataformas', 'Tecnología');

-- PRODUCCIÓN
UPDATE roles_empresa 
SET departamento = 'Producción'
WHERE nombre IN ('Media Buyer', 'Creador Audiovisual', 'Producción', 'Team Producción', 'Copy', 'Diseñadora Grafica (Producción)');

-- Roles generales sin departamento específico (asignar Gerencia)
UPDATE roles_empresa 
SET departamento = 'Gerencia'
WHERE departamento IS NULL;
```

### 3. Verificar actualización

```sql
-- Ver distribución de roles por departamento
SELECT departamento, COUNT(*) as cantidad, STRING_AGG(nombre, ', ' ORDER BY nombre)
FROM roles_empresa
GROUP BY departamento
ORDER BY departamento;

-- Ver roles sin departamento (no debería haber)
SELECT * FROM roles_empresa WHERE departamento IS NULL;
```

### 4. Sincronizar usuarios con sus departamentos basados en rol

```sql
-- Academia
UPDATE usuarios 
SET departamento = 'Academia'
WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Academia');

-- Contenido
UPDATE usuarios 
SET departamento = 'Contenido'
WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Contenido');

-- Finanzas
UPDATE usuarios 
SET departamento = 'Finanzas'
WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Finanzas');

-- Gerencia
UPDATE usuarios 
SET departamento = 'Gerencia'
WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Gerencia');

-- Plataformas
UPDATE usuarios 
SET departamento = 'Plataformas'
WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Plataformas');

-- Producción
UPDATE usuarios 
SET departamento = 'Producción'
WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Producción');

-- Verificar resultado
SELECT departamento, COUNT(*) FROM usuarios GROUP BY departamento;
```

## 🚀 Script Completo para Ejecutar en Orden

```sql
-- 1. Agregar columna departamento a roles
ALTER TABLE roles_empresa 
ADD COLUMN departamento VARCHAR(50);

-- 2. Actualizar todos los roles
UPDATE roles_empresa SET departamento = 'Academia' WHERE nombre IN ('Lider de Academia', 'Atención y Servicio Al Cliente');
UPDATE roles_empresa SET departamento = 'Contenido' WHERE nombre IN ('Lider de Contenido', 'Diseñadora Grafica', 'Community Manager', 'Editor de Video Corto', 'Video Marker Largo', 'Contenido (General)', 'Contenido');
UPDATE roles_empresa SET departamento = 'Finanzas' WHERE nombre IN ('Líder de Finanzas', 'Finanzas', 'Analista Administrativa');
UPDATE roles_empresa SET departamento = 'Gerencia' WHERE nombre IN ('Gerente', 'Gerente Operativa', 'Administrador');
UPDATE roles_empresa SET departamento = 'Plataformas' WHERE nombre IN ('Lider de Plataformas', 'Soporte Tecnologico y Plataformas', 'Tecnología');
UPDATE roles_empresa SET departamento = 'Producción' WHERE nombre IN ('Media Buyer', 'Creador Audiovisual', 'Producción', 'Team Producción', 'Copy', 'Diseñadora Grafica (Producción)');
UPDATE roles_empresa SET departamento = 'Gerencia' WHERE departamento IS NULL;

-- 3. Agregar constraint
ALTER TABLE roles_empresa 
ADD CONSTRAINT check_rol_departamento 
CHECK (departamento IN ('Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia'));

-- 4. Sincronizar usuarios con departamentos de sus roles
UPDATE usuarios SET departamento = 'Academia' WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Academia');
UPDATE usuarios SET departamento = 'Contenido' WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Contenido');
UPDATE usuarios SET departamento = 'Finanzas' WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Finanzas');
UPDATE usuarios SET departamento = 'Gerencia' WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Gerencia');
UPDATE usuarios SET departamento = 'Plataformas' WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Plataformas');
UPDATE usuarios SET departamento = 'Producción' WHERE rol_id IN (SELECT id FROM roles_empresa WHERE departamento = 'Producción');

-- 5. Verificar
SELECT 'Roles por Departamento' as tipo, departamento, COUNT(*) as cantidad FROM roles_empresa GROUP BY departamento
UNION ALL
SELECT 'Usuarios por Departamento' as tipo, departamento, COUNT(*) FROM usuarios GROUP BY departamento;
```

## 📌 Cambios en Frontend

Cuando el usuario selecciona un rol en el formulario:
1. El rol viene con su `departamento` 
2. El campo `departamento` se llena **automáticamente**
3. El usuario **no puede cambiarlo** (solo lectura o hidden)

Esto asegura que:
✅ El departamento siempre coincida con el rol
✅ No hay inconsistencias
✅ Simplifica la UI (menos campos para llenar)
