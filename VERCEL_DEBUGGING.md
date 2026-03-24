# Guía de Debugging - ActivosEQ en Vercel

## Cambios Realizados

### 1. ✅ Scrollbar Habilitado en Tablas
- **Problema**: Las tablas mostraban todos los datos pero no eran scrolleables (`overflow:hidden`)
- **Solución**: Cambié `.tbl-wrap` a `overflow-y:auto` con `max-height:calc(100vh - 200px)`
- **Archivo**: `templates/index.html` línea ~220

### 2. ✅ Botones de Cerrar Modales Reparados
- **Problema**: Los botones X y Cancelar en los modales no cerraban los popups
- **Solución**: 
  - Agregué event listeners JavaScript explícitos a todos los pulsadores `.m-close`
  - Estos listeners usan `e.preventDefault()` y `e.stopPropagation()` para garantizar ejecución
  - Removemos la clase 'open' del overlay padre
- **Archivo**: `templates/index.html` línea ~1489

### 3. ✅ Logging y Diagnóstico Mejorado
- **Dashboard**: Agregué función `/api/health` en Flask para verificar conectividad a Supabase
- **Frontend**: 
  - Función `api()` mejorada con logging de errores
  - `loadAll()` ahora valida respuestas y registra el estado de datos
  - `init()` comprueba `/api/health` al arrancar
  - Consola del navegador mostrará detalles de todas las peticiones

---

## Pasos para Diagnosticar el Problema de Datos en Vercel

### Paso 1: Verificar Consola del Navegador
1. Abre tu app en Vercel
2. Presiona `F12` o `Ctrl+Shift+I` para abrir DevTools
3. Ve a la pestaña **Console**
4. Busca estos mensajes:
   - ✓ `🚀 Initializing app...` - App iniciando
   - ✓ `✓ Backend healthy` - Servidor Flask corriendo
   - ✓ `✓ API GET /api/equipos: XX items` - Datos cargados

**Si ves errores aquí, copia el mensaje completo**.

### Paso 2: Verificar Health Check
1. Abre tu navegador en: `https://tu-vercel-app.vercel.app/api/health`
2. Deberías ver una respuesta JSON como:
```json
{
  "status": "ok",
  "message": "Backend and Supabase connected",
  "supabase_url": "https"
}
```

Si ves `"status": "error"`, el problema está en la conexión a Supabase.

### Paso 3: Verificar Vercel Environment Variables
1. Ve a tu proyecto en [Vercel Dashboard](https://vercel.com)
2. Click en **Settings** → **Environment Variables**
3. Verifica que existen:
   - `SUPABASE_URL` = `https://xxxxx.supabase.co`
   - `SUPABASE_KEY` = Tu clave anon key (comienza con `eyJ...`)

**Importante**: Después de agregar/cambiar variables, redeploy el proyecto.

### Paso 4: Redeploy en Vercel
```bash
git add .
git commit -m "Fix scrollbar, modals, and add debugging"
git push origin main
```

Luego en [Vercel Dashboard](https://vercel.com):
1. Click en tu proyecto
2. Verás automáticamente el nuevo deploy
3. Espera a que finalice (status = "Ready")

### Paso 5: Verificar Logs de Vercel
1. En el dashboard de Vercel, abre el deploy más reciente
2. Ve a **Logs**
3. Busca errores de Python o en la conexión a Supabase

---

## Posibles Causas y Soluciones

### ❌ Problema: `/api/health` devuelve error
**Causa**: Supabase no está accesible desde Vercel
**Soluciones**:
- Verifica que SUPABASE_KEY sea la clave **anon** (no admin)
- Verifica que SUPABASE_URL sea correcto y público
- En Supabase: Settings → API → revisa que RLS esté bien configurado

### ❌ Problema: Console muestra "Network Error"
**Causa**: El backend Flask no está respondiendo
**Soluciones**:
- Verifica que vercel.json está correcto:
  ```json
  {
    "version": 2,
    "builds": [{"src": "app.py", "use": "@vercel/python"}],
    "routes": [{"src": "/(.*)", "dest": "app.py"}]
  }
  ```
- Elimina y reinstala `requirements.txt` en local
- Asegurate que no hay `instance/` o `.db` files no necesarios

### ❌ Problema: Consola muestra "API Error [400]" o [500]
**Causa**: Error en la petición a Supabase desde Flask
**Soluciones**:
- Los logs de Vercel mostrarán el error exacto - cúralos
- Verifica que las tablas existan en Supabase:
  - usuarios, equipos, prestamos, mantenimientos, hoja_vida
- Verifica que los campos existan (nombres exactos: id, nombre, tipo, etc.)

---

## Testing Local Antes de Hacer Deploy

```bash
# 1. Crear .env con valores correctos
echo "SUPABASE_URL=https://xxxxx.supabase.co" > .env
echo "SUPABASE_KEY=xxxxxx" >> .env

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar Flask
python app.py

# 4. Ir a http://localhost:5000
# 5. Abrir console (F12) y verificar logs
# 6. Si todo funciona, hacer push a GitHub
```

---

## Comandos Útiles para Debugging

**Verificar si Flask corre sin errores**:
```bash
python -c "import app; print(f'Routes: {len(app.app.url_map._rules_by_endpoint)}')"
```

**Listar archivos que van a Vercel**:
```bash
git ls-files
```

**Simular instalación de Vercel**:
```bash
pip install -r requirements.txt
python app.py
```

---

## Contacto / Próximos Pasos

- Si los logs de Vercel muestran un error específico, muéstramelo
- Si la consola del navegador tiene error, cópialo completo
- Una vez que `/api/health` devuelve OK, los datos deberían cargar

¡Los cambios principales ya se hicieron! Solo necesitas verificar las variables de entorno en Vercel. 🚀
