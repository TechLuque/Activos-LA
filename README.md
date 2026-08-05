# ActivosLA — Gestión de Activos Empresariales

Aplicación web completa para gestionar activos de tu empresa con **Supabase** como backend.

## 🚀 Inicio Rápido

### Requisitos
- Python 3.8+
- Cuenta en [Supabase](https://supabase.com) (gratis)

### Instalación Local

```bash
# 1. Clonar/descargar el proyecto
cd activoseq

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase

# 5. Crear tablas en Supabase
# - Ir a Dashboard → SQL Editor
# - Ejecutar el script de inicialización (ver app.py init_db)

# 6. Ejecutar la aplicación
python app.py

# 7. Abrir en navegador
# http://localhost:5000
```

## 📊 Modules

| Módulo | Descripción |
|--------|-------------|
| **Panel de Control** | Estadísticas, gráficos y alertas en tiempo real |
| **Equipos** | CRUD de activos (computadores, muebles, periféricos, etc.) |
| **Hoja de Vida** | Historial completo: eventos, mantenimientos, reparaciones |
| **Usuarios** | Gestión de personas que pueden recibir equipos |
| **Préstamos** | Asignar/devolver equipos con seguimiento de fechas |
| **Mantenimientos** | Registro preventivo y correctivo |
| **Calendario** | Próximas revisiones y devoluciones programadas |
| **Firma Digital** | Requiere firma y 2 fotos en cada préstamo (rastreable) |

### 📝 Firma Digital y Documentación

El sistema ahora incluye captura de firma digital y documentos de préstamos:

- ✅ **Firma Digital:** Canvas con capacidad de dibujo (requiere presión táctil)
- ✅ **FotoDocs:** Captura de 2 imágenes por préstamo (ID, documentos, etc)
- ✅ **Almacenamiento:** Guardadas en `/uploads/prestamos/` con timestampes
- ✅ **Visualización:** Modal para revisar histórico de documentos firmados
- ✅ **Base de Datos:** URLs almacenadas en `prestamos.firma_url`, `.imagen1_url`, `.imagen2_url`

Ver [DOCUMENT_STORAGE.md](DOCUMENT_STORAGE.md) para detalles de rutas, convenciones de nombres y acceso.

## 🗄️ Base de Datos

Usa **Supabase** (PostgreSQL en la nube). No requiere instalación local.

- **Ventajas**: 
  - Datos siempre sincronizados
  - Escalable y seguro
  - Gratis hasta 500MB
  - Compatible con Vercel

## 📁 Estructura

```
activoseq/
├── app.py                           # Backend Flask + 30 endpoints REST
├── requirements.txt                 # Dependencias Python
├── vercel.json                      # Configuración deployment Vercel
├── .env.example                     # Template de variables
├── DOCUMENT_STORAGE.md              # 📄 Documentación de almacenamiento
├── VERCEL_DEBUGGING.md              # Troubleshooting deployment
├── templates/
│   ├── index.html                   # Frontend SPA - Panel principal
│   └── firma.html                   # Página pública de firma digital
├── static/                          # Archivos CSS/JS (si aplica)
└── uploads/prestamos/               # 📁 Documentos de préstamos (firmas e imágenes)
```

## 🌐 Deployment en Vercel

El proyecto está listo para Vercel:

```bash
# 1. Instalar Vercel CLI
npm i -g vercel

# 2. Deploy
vercel

# 3. Configurar variables en Vercel Dashboard
# - SUPABASE_URL
# - SUPABASE_KEY
```

## 📝 Configuración Supabase

### Variables requeridas (.env)
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### Crear tablas
Copiar el script SQL de `app.py` (función `init_db()`) y ejecutar en SQL Editor de Supabase.

## 🔗 API Endpoints

- `GET /api/usuarios`
- `POST /api/usuarios`
- `GET /api/equipos`
- `POST /api/equipos`
- `GET /api/prestamos`
- `POST /api/prestamos` 
- `GET /api/mantenimientos`
- `POST /api/mantenimientos`
- Y más... (25 endpoints totales)

## 📄 Licencia

MIT


## 🔌 API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/init` · `/api/init/secondary` | Carga inicial (el dashboard se calcula en el cliente) |
| GET/POST | `/api/equipos` | Listar / crear equipos |
| GET/PUT/DELETE | `/api/equipos/:id` | Ver / editar / eliminar equipo |
| GET/POST | `/api/equipos/:id/hoja_vida` | Hoja de vida del equipo |
| GET/POST | `/api/equipos/:id/mantenimientos` | Mantenimientos del equipo |
| GET/POST | `/api/usuarios` | Listar / crear responsables |
| PUT | `/api/usuarios/:id` | Editar responsable (update parcial) |
| DELETE | `/api/usuarios/:id` | Eliminar responsable — 409 si tiene historial |
| GET/POST | `/api/prestamos` | Listar / crear préstamos |
| PUT | `/api/prestamos/:id/devolver` | Marcar devolución |
| DELETE | `/api/prestamos/:id` | Eliminar préstamo |
| GET | `/api/mantenimientos` | Todos los mantenimientos |
