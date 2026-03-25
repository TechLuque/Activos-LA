# 🎯 SQL COMPLETO FINAL - Ejecución única

Copia TODO el SQL de abajo y ejecuta en **Supabase → SQL Editor → New Query**.

```sql
-- ═══════════════════════════════════════════════════════════════════
-- ACTUALIZACIÓN COMPLETA DEL SISTEMA: TIPOS, ROLES Y USUARIOS
-- ═══════════════════════════════════════════════════════════════════

-- ========== 1. LIMPIAR ROLES ANTERIORES ==========
DELETE FROM roles_empresa WHERE nombre NOT IN (
  'Admin','Analista Administrativa','Aprendiz SENA','Asistente de Operaciones',
  'Atención y Servicio Al Cliente','Community Manager','Copy','Creador Audiovisual',
  'Diseñadora Gráfica','Editor de Video Corto','Finanzas','Gerente',
  'Lider de Academia','Lider de Contenido','Lider de Plataformas',
  'Líder de Finanzas','Media Buyer','Producción','Soporte Tecnológico','Video Maker Largo'
);

-- ========== 2. INSERTAR 20 ROLES COMPLETOS ==========
INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Admin', 'Gestión administrativa global y control de accesos al sistema.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Gestión administrativa global y control de accesos al sistema.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Analista Administrativa', 'Apoyo en procesos de oficina, gestión de documentos y flujos internos.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Apoyo en procesos de oficina, gestión de documentos y flujos internos.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Aprendiz SENA', 'Estudiante en etapa práctica apoyando áreas generales de la empresa.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Estudiante en etapa práctica apoyando áreas generales de la empresa.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Asistente de Operaciones', 'Soporte en la ejecución y seguimiento de procesos operativos diarios.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Soporte en la ejecución y seguimiento de procesos operativos diarios.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Atención y Servicio Al Cliente', 'Gestión de peticiones, quejas, reclamos y soporte directo a usuarios.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Gestión de peticiones, quejas, reclamos y soporte directo a usuarios.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Community Manager', 'Gestión de redes sociales, interacción con la comunidad y voz de marca.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Gestión de redes sociales, interacción con la comunidad y voz de marca.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Copy', 'Redacción creativa y estratégica de textos para campañas y contenido.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Redacción creativa y estratégica de textos para campañas y contenido.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Creador Audiovisual', 'Producción y realización de material de video y audio para la empresa.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Producción y realización de material de video y audio para la empresa.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Diseñadora Gráfica', 'Creación de conceptos visuales, piezas publicitarias e identidad de marca.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Creación de conceptos visuales, piezas publicitarias e identidad de marca.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Editor de Video Corto', 'Edición especializada en formatos rápidos (Reels, TikTok, Shorts).')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Edición especializada en formatos rápidos (Reels, TikTok, Shorts).';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Finanzas', 'Ejecución de procesos contables, pagos y conciliaciones.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Ejecución de procesos contables, pagos y conciliaciones.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Gerente', 'Dirección estratégica y toma de decisiones a nivel ejecutivo y operativo.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Dirección estratégica y toma de decisiones a nivel ejecutivo y operativo.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Lider de Academia', 'Supervisión de programas educativos y formación de usuarios/clientes.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Supervisión de programas educativos y formación de usuarios/clientes.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Lider de Contenido', 'Estrategia y supervisión de la línea editorial y creativa de la empresa.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Estrategia y supervisión de la línea editorial y creativa de la empresa.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Lider de Plataformas', 'Supervisión de infraestructura tecnológica y desarrollo de herramientas.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Supervisión de infraestructura tecnológica y desarrollo de herramientas.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Líder de Finanzas', 'Responsable de la salud financiera y planeación presupuestaria.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Responsable de la salud financiera y planeación presupuestaria.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Media Buyer', 'Compra de pauta publicitaria y optimización de presupuestos en ads.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Compra de pauta publicitaria y optimización de presupuestos en ads.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Producción', 'Ejecución técnica de proyectos audiovisuales y logísticos.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Ejecución técnica de proyectos audiovisuales y logísticos.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Soporte Tecnológico', 'Mantenimiento de sistemas, resolución de errores y ayuda técnica.')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Mantenimiento de sistemas, resolución de errores y ayuda técnica.';

INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Video Maker Largo', 'Producción y edición de contenidos de video de larga duración (YouTube/Cursos).')
ON CONFLICT (nombre) DO UPDATE SET descripcion='Producción y edición de contenidos de video de larga duración (YouTube/Cursos).';

-- ========== 3. MAPEAR USUARIOS A ROLES POR CARGO ==========

-- Admin
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Admin') 
WHERE email = 'admin@activoseq.com';

-- Analista Administrativa
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Analista Administrativa')
WHERE cargo = 'Analista Administrativa';

-- Aprendiz SENA
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Aprendiz SENA')
WHERE cargo = 'Aprendiz SENA';

-- Asistente de Operaciones
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Asistente de Operaciones')
WHERE cargo = 'Asistente de Operaciones';

-- Atención y Servicio Al Cliente
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Atención y Servicio Al Cliente')
WHERE cargo = 'Atención y Servicio Al Cliente';

-- Community Manager
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Community Manager')
WHERE cargo = 'Community Manager';

-- Copy
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Copy')
WHERE cargo = 'Copy';

-- Creador Audiovisual
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Creador Audiovisual')
WHERE cargo = 'Creador Audiovisual';

-- Diseñadora Gráfica
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Diseñadora Gráfica')
WHERE cargo LIKE '%Diseñadora Grafica%' OR cargo LIKE '%Diseñadora Gráfica%';

-- Editor de Video Corto
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Editor de Video Corto')
WHERE cargo = 'Editor de Video Corto';

-- Finanzas (pero NO los que tienen Líder)
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Finanzas')
WHERE cargo = 'Finanzas' AND cargo NOT LIKE '%Líder%';

-- Gerente / Gerente Operativa
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Gerente')
WHERE cargo = 'Gerente' OR cargo = 'Gerente Operativa';

-- Lider de Academia
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Lider de Academia')
WHERE cargo = 'Lider de Academia';

-- Lider de Contenido
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Lider de Contenido')
WHERE cargo = 'Lider de Contenido';

-- Lider de Plataformas (incluye variaciones)
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Lider de Plataformas')
WHERE cargo LIKE '%Lider de Plataformas%' OR cargo = 'Tecnología' OR cargo = 'Lider%Tecnología%';

-- Líder de Finanzas
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Líder de Finanzas')
WHERE cargo = 'Líder de Finanzas';

-- Media Buyer
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Media Buyer')
WHERE cargo = 'Media Buyer';

-- Producción / Team Producción (ambas variaciones)
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Producción')
WHERE cargo = 'Producción' OR cargo = 'Team Producción';

-- Soporte Tecnológico y Plataformas (variaciones)
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Soporte Tecnológico')
WHERE cargo LIKE '%Soporte Tecnologico%' OR cargo LIKE '%Soporte Tecnológico%';

-- Video Maker Largo (incluye variación sin tilde)
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Video Maker Largo')
WHERE cargo = 'Video Marker Largo' OR cargo = 'Video Maker Largo';

-- Rol por defecto para cualquiera que quedara sin asignar
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Asistente de Operaciones')
WHERE rol_id IS NULL;

-- ========== 4. VERIFICACIÓN FINAL ==========
-- Descomenta las siguientes líneas para verificar:

-- SELECT COUNT(*) as "Total usuarios con rol" FROM usuarios WHERE rol_id IS NOT NULL;
-- SELECT COUNT(*) as "Total usuarios sin rol" FROM usuarios WHERE rol_id IS NULL;

-- SELECT r.nombre, COUNT(u.id) as cantidad 
-- FROM usuarios u 
-- LEFT JOIN roles_empresa r ON u.rol_id = r.id 
-- GROUP BY r.nombre 
-- ORDER BY cantidad DESC;

-- SELECT id, nombre, cargo, rol_id FROM usuarios WHERE rol_id IS NULL;
```

---

## ✅ Pasos para ejecutar:

1. **Abre Supabase Dashboard** → SQL Editor
2. **Click "New Query"**
3. **Copia TODO el SQL** de arriba
4. **Pega** en el editor
5. **Click RUN**
6. **Espera** a que termine (5-10 segundos)

---

## 🎯 ¿Qué hace?

✅ **Inserta/actualiza 20 roles** exactamente como los necesitas  
✅ **Mapea automáticamente TODOS los usuarios** a su rol según su CARGO  
✅ **Si un usuario no tiene coincidencia**, se asigna a "Asistente de Operaciones" (fallback)  
✅ **No elimina ni modifica datos** de usuarios, solo asigna rol_id  

---

## 📊 Resultado esperado:

Después de ejecutarlo, deberías ver:
- ✅ 34 usuarios con `rol_id` asignado
- ✅ Cada uno mapeado a su rol correcto
- 0 usuarios sin rol (todos tienen el rol por defecto)

---

## 🔍 Para verificar manualmente:

Descomenta las últimas 4 líneas en el SQL para ver:
```sql
-- Ver distribución de roles
SELECT r.nombre, COUNT(u.id) as cantidad 
FROM usuarios u 
LEFT JOIN roles_empresa r ON u.rol_id = r.id 
GROUP BY r.nombre 
ORDER BY cantidad DESC;
```

---

## ⚠️ Si ves error:

- **"duplicate key"** → Normal, significa que el rol ya existe (se actualiza)
- **"column does not exist"** → Verifica que ejecutaste primero el SQL de migración de tipos
- Cualquier otro → Avísame el error exacto
