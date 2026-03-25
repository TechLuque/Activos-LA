# 🎯 SQL - Roles Basados en Cargos Reales

Copia y ejecuta en Supabase SQL Editor.

```sql
-- ========== 1. LIMPIAR ROLES ANTERIORES (opcional) ==========
-- DELETE FROM roles_empresa;

-- ========== 2. INSERTAR LOS 20 ROLES EXACTOS ==========
INSERT INTO roles_empresa (nombre, descripcion) VALUES 
  ('Admin', 'Gestión administrativa global y control de accesos al sistema.'),
  ('Analista Administrativa', 'Apoyo en procesos de oficina, gestión de documentos y flujos internos.'),
  ('Aprendiz SENA', 'Estudiante en etapa práctica apoyando áreas generales de la empresa.'),
  ('Asistente de Operaciones', 'Soporte en la ejecución y seguimiento de procesos operativos diarios.'),
  ('Atención y Servicio Al Cliente', 'Gestión de peticiones, quejas, reclamos y soporte directo a usuarios.'),
  ('Community Manager', 'Gestión de redes sociales, interacción con la comunidad y voz de marca.'),
  ('Copy', 'Redacción creativa y estratégica de textos para campañas y contenido.'),
  ('Creador Audiovisual', 'Producción y realización de material de video y audio para la empresa.'),
  ('Diseñadora Gráfica', 'Creación de conceptos visuales, piezas publicitarias e identidad de marca.'),
  ('Editor de Video Corto', 'Edición especializada en formatos rápidos (Reels, TikTok, Shorts).'),
  ('Finanzas', 'Ejecución de procesos contables, pagos y conciliaciones.'),
  ('Gerente', 'Dirección estratégica y toma de decisiones a nivel ejecutivo y operativo.'),
  ('Lider de Academia', 'Supervisión de programas educativos y formación de usuarios/clientes.'),
  ('Lider de Contenido', 'Estrategia y supervisión de la línea editorial y creativa de la empresa.'),
  ('Lider de Plataformas', 'Supervisión de infraestructura tecnológica y desarrollo de herramientas.'),
  ('Líder de Finanzas', 'Responsable de la salud financiera y planeación presupuestaria.'),
  ('Media Buyer', 'Compra de pauta publicitaria y optimización de presupuestos en ads.'),
  ('Producción', 'Ejecución técnica de proyectos audiovisuales y logísticos.'),
  ('Soporte Tecnológico', 'Mantenimiento de sistemas, resolución de errores y ayuda técnica.'),
  ('Video Maker Largo', 'Producción y edición de contenidos de video de larga duración (YouTube/Cursos).')
ON CONFLICT (nombre) DO NOTHING;

-- ========== 3. MAPEAR USUARIOS A ROLES POR CARGO ==========
-- Admin
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Admin') 
WHERE email = 'admin@activoseq.com';

-- Analista Administrativa
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Analista Administrativa')
WHERE cargo LIKE '%Analista Administrativa%';

-- Aprendiz SENA
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Aprendiz SENA')
WHERE cargo LIKE '%Aprendiz SENA%';

-- Asistente de Operaciones
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Asistente de Operaciones')
WHERE cargo LIKE '%Asistente de Operaciones%';

-- Atención y Servicio Al Cliente
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Atención y Servicio Al Cliente')
WHERE cargo LIKE '%Atención%' OR cargo LIKE '%Servicio Al Cliente%';

-- Community Manager
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Community Manager')
WHERE cargo LIKE '%Community Manager%';

-- Copy
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Copy')
WHERE cargo LIKE '%Copy%';

-- Creador Audiovisual
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Creador Audiovisual')
WHERE cargo LIKE '%Creador Audiovisual%';

-- Diseñadora Gráfica
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Diseñadora Gráfica')
WHERE cargo LIKE '%Diseñadora Grafica%' OR cargo LIKE '%Diseñadora Gráfica%';

-- Editor de Video Corto
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Editor de Video Corto')
WHERE cargo LIKE '%Editor de Video Corto%';

-- Finanzas
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Finanzas')
WHERE cargo = 'Finanzas' OR cargo LIKE '%Finanzas%' AND cargo NOT LIKE '%Líder%';

-- Gerente / Gerente Operativa
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Gerente')
WHERE cargo = 'Gerente' OR cargo = 'Gerente Operativa';

-- Lider de Academia
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Lider de Academia')
WHERE cargo LIKE '%Lider de Academia%';

-- Lider de Contenido
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Lider de Contenido')
WHERE cargo LIKE '%Lider de Contenido%';

-- Lider de Plataformas / Tecnología
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Lider de Plataformas')
WHERE cargo LIKE '%Lider de Plataformas%' OR cargo LIKE '%Lider%Tecnología%' OR cargo = 'Tecnología';

-- Líder de Finanzas
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Líder de Finanzas')
WHERE cargo LIKE '%Líder de Finanzas%';

-- Media Buyer
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Media Buyer')
WHERE cargo LIKE '%Media Buyer%';

-- Producción / Team Producción
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Producción')
WHERE cargo = 'Producción' OR cargo = 'Team Producción';

-- Soporte Tecnológico y Plataformas
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Soporte Tecnológico')
WHERE cargo LIKE '%Soporte Tecnologico%' OR cargo LIKE '%Soporte Tecnológico%';

-- Video Maker Largo
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Video Maker Largo')
WHERE cargo LIKE '%Video Maker Largo%' OR cargo LIKE '%Video Marker Largo%';

-- Otros cargos generales
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'Asistente de Operaciones')
WHERE rol_id IS NULL AND (cargo LIKE '%Contenido%' OR cargo LIKE '%Producción%');

-- ========== 4. VERIFICACIÓN ==========
-- Ver cuántos usuarios tienen rol asignado
-- SELECT COUNT(*) as usuarios_con_rol FROM usuarios WHERE rol_id IS NOT NULL;
-- SELECT COUNT(*) as usuarios_sin_rol FROM usuarios WHERE rol_id IS NULL;

-- Ver distribución de usuarios por rol
-- SELECT r.nombre, COUNT(u.id) as cantidad 
-- FROM usuarios u 
-- LEFT JOIN roles_empresa r ON u.rol_id = r.id 
-- GROUP BY r.nombre 
-- ORDER BY cantidad DESC;

-- Ver usuarios sin rol asignado (para revisar manualmente si necesario)
-- SELECT id, nombre, cargo, rol_id FROM usuarios WHERE rol_id IS NULL;
```

---

## 🎯 ¿Qué hace este SQL?

1. ✅ **Inserta 20 roles** exactamente como los pusiste
2. ✅ **Mapea automáticamente usuarios** a roles según su CARGO
3. ✅ **Si hay cargos que no coinciden**, quedan SIN rol (para revisión)
4. ✅ **No elimina datos existentes**

---

## 📊 Ejemplos de mapeo:

| Cargo en BD | → Rol asignado |
|---|---|
| Soporte Tecnologico y Plataformas | → Soporte Tecnológico |
| Lider de Academia | → Lider de Academia |
| Gerente | → Gerente |
| Gerente Operativa | → Gerente |
| Finanzas | → Finanzas |
| admin@activoseq.com | → Admin |

---

## ✅ Pasos:

1. Copia **TODO el SQL** del bloque de arriba
2. Ve a **Supabase → SQL Editor → New Query**
3. **Pega** y click **RUN**
4. Ejecuta las queries de "VERIFICACIÓN" para confirmar

---

## ⚠️ Si quedan usuarios SIN rol:

Edita manualmente esta línea en el SQL para cada cargo especial:
```sql
UPDATE usuarios SET rol_id = (SELECT id FROM roles_empresa WHERE nombre = 'NOMBRE_DEL_ROL')
WHERE cargo = 'CARGO_EXACTO';
```

Después, avísame qué cargos no se mapearon y los agrego.
