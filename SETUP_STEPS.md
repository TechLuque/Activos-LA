# 🚀 PASOS PARA ACTIVAR SISTEMA DE TIPOS Y ROLES

## ⏱️ Tiempo estimado: 5-10 minutos

---

## PASO 1: Crear las tablas en Supabase (3 minutos)

### 1.1 Abre Supabase Dashboard
- Ve a: https://app.supabase.com/
- Selecciona tu proyecto **ActivosEQ**

### 1.2 Abre SQL Editor
- En el menú izquierdo, haz clic en **SQL Editor**
- Haz clic en **+ New Query**

### 1.3 Copia el SQL
- Abre archivo: `SQL_CREATE_TYPES_AND_ROLES.md` (en esta carpeta)
- Verás 4 bloques SQL
- **Copia BLOQUE 1** completo (desde `CREATE TABLE tipos_equipos` hasta `WITH CHECK (true);`)

### 1.4 Ejecuta BLOQUE 1
- Pega en SQL Editor
- Haz clic en botón azul **RUN**
- Espera a que diga "✓ Success"

### 1.5 Repite para BLOQUE 2
- Copia **BLOQUE 2** (roles_empresa)
- Ejecuta igual que el BLOQUE 1

### 1.6 Ejecuta BLOQUE 3 (Insertar tipos)
- Copia **BLOQUE 3** (INSERT INTO tipos_equipos)
- Ejecuta

### 1.7 Ejecuta BLOQUE 4 (Insertar roles)
- Copia **BLOQUE 4** (INSERT INTO roles_empresa)
- Ejecuta

### ✅ Verificación:
- Ve a **Database** → **Tables** en menú izquierdo
- Deberías ver:
  - ✅ `tipos_equipos` (18 registros)
  - ✅ `roles_empresa` (4 registros)

---

## PASO 2: Hacer commit y push (2 minutos)

### 2.1 Abre Terminal en VS Code
- Presiona: `Ctrl + `` (backtick)
- O: Terminal → New Terminal

### 2.2 Verificar cambios
```bash
git status
```
Deberías ver:
- ✅ modified: app.py
- ✅ modified: templates/index.html
- ✅ new file: SQL_CREATE_TYPES_AND_ROLES.md
- ✅ new file: CHANGELOG_TIPOS_ROLES.md

### 2.3 Hacer commit
```bash
git add -A
git commit -m "Feature: Sistema de tipos de equipos y roles en base de datos

- Migrar tipos de hardcoded a tabla tipos_equipos
- Crear CRUD endpoints para tipos (/api/tipos-equipos)
- Crear CRUD endpoints para roles (/api/roles)
- Frontend carga tipos dinámicamente desde API
- Agregar modal para crear nuevos tipos sin código
- Tabla roles_empresa para gestión centralizada
- RLS policies configuradas en Supabase"
```

### 2.4 Push a GitHub
```bash
git push origin main
```

Espera 2-3 minutos. Vercel deploya automáticamente.

---

## PASO 3: Probar en la aplicación (2-5 minutos)

### 3.1 Esperar deployment
- Ve a: https://vercel.com/dashboard
- Selecciona proyecto **activoseq**
- Espera a que estado sea **Ready** (verde)

### 3.2 Probar tipos en producción
- Abre: https://activos-la-9ziz.vercel.app/
- Ve a: **Equipos** → **+ Nuevo equipo**
- En "Tipo", deberías ver dropdown con:
  - Computador
  - Laptop
  - Monitor
  - ... (18 tipos)

### 3.3 Crear nuevo tipo
1. Haz clic en botón **➕** (botón más junto a tipo)
2. Aparece modal "Agregar tipo de equipo"
3. Escribe: "Servidor Web"
4. Escribe descripción: "Computador para alojar aplicaciones"
5. Haz clic en **Agregar tipo**
6. Verás toast: "Tipo 'Servidor Web' agregado correctamente"
7. El tipo se selecciona automáticamente

### ✅ Verificación exitosa:
- Dropdown tiene 19 tipos (18 originales + 1 nuevo)
- Nuevo tipo persiste después de refrescar página
- Puedes crear otro equipo y "Servidor Web" disponible

---

## 🎉 ¡LISTO!

Tu sistema de tipos dinámicos está activo.

### Próximos pasos (Opcionales):
- [ ] Crear panel de administración de tipos (editar/eliminar)
- [ ] Crear panel de administración de roles
- [ ] Asignar permisos específicos a cada rol
- [ ] Validar que usuarios tengan roles asignados

---

## ⚠️ Solución de Problemas

### El dropdown de tipos está vacío
**Causa**: Tabla no existe o RLS está bloqueando lectura

**Solución**:
1. Abre Supabase Dashboard
2. Ve a **Database** → **Tables**
3. Verifica que `tipos_equipos` existe
4. Verifica que tiene datos (click en tabla, ver registros)
5. Abre consola navegador (F12 → Console)
6. Ejecuta:
```javascript
api('/api/tipos-equipos').then(r => console.log(r))
```
7. Deberías ver array de tipos

### Modal de "Agregar tipo" no abre
**Causa**: Botón no está visible o JavaScript error

**Solución**:
1. Abre Consola (F12 → Console)
2. Verifica que no hay errores rojos
3. Haz clic en botón ➕
4. Si sigue sin abrir, recarga página (Ctrl+R)

### Error: "El tipo ya existe"
**Causa**: Ya creaste ese tipo

**Solución**: Usa nombre diferente (ej: "Servidor Web 2")

### Tipos no se guardan después de refresh
**Causa**: Tabla no existe en Supabase

**Solución**: Ejecuta SQL de nuevo, verificando que no haya errores

---

## 📞 ¿Necesitas ayuda?

1. Revisa archivo: `CHANGELOG_TIPOS_ROLES.md` (más detallado)
2. Revisa archivo: `SQL_CREATE_TYPES_AND_ROLES.md` (SQL con documentación)
3. Abre Consola (F12) y busca errores rojos
4. Verifica que Supabase tenga las tablas (Database → Tables)

---

## 🔐 Verificación de seguridad

✅ RLS habilitado en Supabase (lectura pública, escritura controlada)
✅ Validación de duplicados en backend
✅ Validación de campos vacíos
✅ Manejo de errores en frontend
✅ CORS configurado para Vercel

---

**¡Éxito instalando! 🎊**
