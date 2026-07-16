# Documento de Requerimientos del Proyecto — ActivosLA
## Sistema de Gestión de Activos Empresariales (Luque Academy)

Este documento detalla los requerimientos funcionales y técnicos identificados e implementados en la plataforma **ActivosLA**, cuyo objetivo principal es la gestión integral de activos tecnológicos (computadores, periféricos, teléfonos, SIM cards), la trazabilidad histórica de los equipos (Hoja de Vida), la programación de mantenimientos, y el control estricto de préstamos mediante firma digital y evidencias fotográficas.

---

## 📋 1. Requerimientos Funcionales

Los requerimientos funcionales describen los módulos y flujos operativos que el sistema debe proveer para satisfacer las necesidades del Área Tech y los colaboradores de Luque Academy.

### 1.1. Módulo de Inventario de Equipos y SIM Cards
- **CRUD de Activos:** Registro de equipos tecnológicos incluyendo nombre, número de serie, marca, modelo, tipo de equipo, estado físico y operativo, valor de adquisición, fecha de compra, ubicación física y responsable asignado.
- **Identificación Visual:** Capacidad de asociar una fotografía física del equipo (avatar de equipo) almacenada en Supabase Storage, que sirva de encabezado visual en la Hoja de Vida.
- **Galería de Adjuntos Múltiples:** Reemplazo del campo único de factura para habilitar una galería de archivos adjuntos por equipo. El sistema debe clasificar cada archivo según su tipo:
  - Factura de compra.
  - Garantía del fabricante o distribuidor.
  - Foto del estado del equipo.
  - Informe técnico de mantenimiento.
  - Otros documentos de soporte.
- **Visor de Imágenes (Lightbox):** Capacidad de ampliar imágenes de la galería o de firmas a pantalla completa para validación detallada.
- **Gestión de SIM Cards y Celulares:** Control específico de dispositivos móviles y sus respectivas tarjetas SIM, permitiendo registrar la vinculación y los estados de red y del servicio (`activo`, `reserva`, `bloqueado`, `desactivado`).

### 1.2. Módulo de Hoja de Vida (HV) e Historial del Activo
- **Línea de Tiempo Cronológica:** Visualización interactiva y vertical de todos los eventos del equipo ordenados de forma descendente (del más reciente al más antiguo).
- **Auditoría Automática de Eventos:** El sistema debe registrar hitos automáticamente en la hoja de vida al realizar las siguientes acciones en la aplicación:
  - **Adquisición:** Generado en el registro inicial del equipo.
  - **Mantenimiento:** Generado al programar o completar una orden de mantenimiento preventivo o correctivo (incluye descripción y técnico).
  - **Asignación:** Generado al entregar el equipo y completarse la firma de préstamo.
  - **Devolución:** Generado al registrarse el retorno y firma de entrega del activo.
  - **Reasignación / Desasignación:** Generado al liberar de custodia o transferir el equipo entre colaboradores.
  - **Cambio de Responsable:** Generado al editar manualmente el campo responsable en el formulario de edición.
- **Gestión Manual de Eventos:** Los administradores deben poder agregar hitos manuales de tipo `reparacion`, `proceso` u `otro` con su respectivo título, descripción, fecha e ingeniero a cargo, así como eliminar registros erróneos del historial.
- **Exportación e Impresión:** Vista optimizada e independiente para imprimir o guardar como PDF la hoja de vida completa de cada activo (metadatos generales, histórico de mantenimientos y la línea de tiempo detallada).

### 1.3. Módulo de Usuarios y Colaboradores
- **CRUD de Colaboradores:** Administración del personal apto para recibir activos, registrando su nombre, departamento (Finanzas, Plataformas, Producción, Academia, Contenido, Gerencia), teléfono y estado (`activo`, `inactivo`).
- **Canal Alternativo de Notificaciones:** Columna `notification_email` en la base de datos de usuarios para definir una cuenta de correo alternativa. Si está configurada, las alertas del sistema se envían a este correo en lugar del email principal de acceso.

### 1.4. Flujo de Préstamos y Devoluciones con Firma Digital (PhotoDocs)
Para formalizar la entrega de activos y deslindar responsabilidades patrimoniales (Política **LA-PL-008**), se implementa el siguiente flujo estandarizado:

#### 1.4.1. Prerrequisito: Solicitud por Correo Electrónico
- Todo préstamo requiere una solicitud previa al correo `tech@luqueacademy.com` con el motivo y la fecha estimada de devolución.
- **Regla del Horario Límite (5:00 PM):** Toda solicitud recibida después de las 5:00 PM en día hábil requiere de forma obligatoria la autorización por escrito de la COO (**Paola Luque** - `paola@luqueacademy.com`) en copia o adjunta para que el Área Tech pueda proceder con el registro en la plataforma.

#### 1.4.2. Registro Administrativo y Enlace Único
- El administrador crea préstamos individuales o préstamos masivos (múltiples equipos en un solo lote para un colaborador).
- Al guardar el préstamo en estado **Solicitado**, el sistema genera un **enlace público único** (`/firma/<id>`) para que el colaborador firme la entrega. Este enlace no requiere inicio de sesión en la plataforma.

#### 1.4.3. Firma de Entrega y Carga de Evidencias (PhotoDocs)
Al abrir el enlace, el colaborador debe:
1. **Verificar los Datos:** Visualizar el equipo, seriales y notas de entrega.
2. **Firmar:** Dibujar su firma directamente en pantalla utilizando el canvas táctil (compatible con móviles, tablets y ratón) o subir un archivo de su firma digitalizada.
3. **Cargar PhotoDocs (2 Fotos Obligatorias):**
   - **Foto 1 (Estado Inicial):** Vista general del equipo encendido o del empaque de entrega.
   - **Foto 2 (Detalles / Verificación):** Imagen detallada de etiquetas de serie, teclado, pantalla o áreas críticas para constatar el estado físico de entrega.
4. **Aceptar Políticas:** Marcar la aceptación expresa de las políticas de custodia y responsabilidad patrimonial (**LA-PL-008**).
5. **Confirmar:** Al confirmar la firma, el estado cambia a **"Firmado"** y el activo se vincula automáticamente en custodia del colaborador en la base de datos.

#### 1.4.4. Proceso de Devolución
- Al retornar el equipo, el personal del Área Tech realiza una inspección física del activo.
- El colaborador accede al enlace de devolución (`/firma/<id>?tipo=devolucion`).
- Dibuja su firma de entrega en pantalla.
- Toma y carga **2 fotografías de evidencia de devolución** que acrediten que el activo retorna sin daños físicos.
- Al guardar, el préstamo se actualiza a **"Devuelto"** y el sistema desvincula automáticamente el equipo liberando su `usuario_id` para dejarlo en estado "Disponible".

---

## 🛠️ 2. Requerimientos Técnicos y de Arquitectura

Los requerimientos técnicos detallan el stack de tecnologías, los patrones de diseño, el almacenamiento de datos, el flujo de desarrollo y las optimizaciones del sistema.

### 2.1. Arquitectura de Software y Código Limpio
- **Backend:** Desarrollado bajo el framework micro-web **Flask (Python 3.8+)**.
- **Arquitectura en Capas:** Migración progresiva y estricta hacia una arquitectura desacoplada para evitar sobreingeniería y acoplamiento en Flask:
  - **Presentación:** Rutas web y controladores API REST (`app.py`).
  - **Aplicación / Dominio:** Reglas de negocio y constantes de dominio definidos en funciones utilitarias y servicios.
  - **Infraestructura / Datos:** Aislamiento de llamadas a base de datos en un archivo especializado de repositorio (`repositories.py`) y manejo de conexiones en `db.py`.
- **Patrón Repositorio:** Toda interacción de consulta, inserción, actualización o borrado contra Supabase debe ser encapsulada en funciones de `repositories.py`. Queda **estrictamente prohibido** que las rutas Flask invoquen llamadas API directas de Supabase o requests HTTP raw hacia Supabase REST.
- **Frontend:** Estructura tipo **Single Page Application (SPA)** implementada en una plantilla HTML dinámica (`templates/index.html`) que consume endpoints del backend mediante llamadas asíncronas de JavaScript (`fetch` API) y renderiza componentes dinámicamente con estilos nativos **CSS Vanilla**.

### 2.2. Base de Datos (Supabase - PostgreSQL Cloud)
- **Supabase REST API:** Consumo de la base de datos cloud PostgreSQL provista por Supabase a través del cliente REST.
- **Modelado Relacional de Tablas:**
  - `equipos`: Registro de activos físicos.
  - `usuarios`: Catálogo de personas habilitadas en la organización.
  - `prestamos` y `prestamos_items`: Gestión de asignaciones y préstamos individuales/masivos.
  - `mantenimientos`: Bitácora de mantenimiento técnico.
  - `hoja_vida`: Registro cronológico e histórico de hitos del activo.
  - `equipo_adjuntos`: Nueva tabla relacional para administrar adjuntos múltiples por equipo.
  - `tipos_equipos`: Clasificación tipológica de activos con prefijos de serie.
- **Integridad y Restricciones:** Configuración de llaves foráneas y eliminación en cascada (`ON DELETE CASCADE`) en relaciones subordinadas (como `equipo_adjuntos` vinculada a `equipos`).
- **Indexación:** Creación y mantenimiento de índices en columnas clave de búsqueda y filtros frecuentes para maximizar el rendimiento:
  - `idx_usuarios_notification_email` en la tabla `usuarios`.
  - `idx_equipo_adjuntos_equipo_id` en la tabla `equipo_adjuntos`.

### 2.3. Rendimiento, Caché y Optimización Local
Dado que el entorno de desarrollo local experimentaba latencias elevadas, se definieron los siguientes requerimientos de performance:
- **Reducción de Payloads y Consultas:**
  - Evitar el uso indiscriminado de `SELECT *` en las consultas API de Supabase, solicitando únicamente las columnas requeridas por el frontend.
  - Reducir las consultas anidadas y repetitivas, implementando búsquedas basadas en lotes de IDs (`id=in.(...)`) para resolver asociaciones en lugar de joins SQL masivos.
- **Control de Caché y Assets Estáticos (Cache Busting):**
  - Configuración de cabeceras HTTP de respuesta: `Cache-Control: no-cache, no-store, must-revalidate` para todas las respuestas HTML dinámicas (evitando renderizado de datos desactualizados).
  - Configuración de caché a largo plazo (`public, max-age=31536000, immutable`) para archivos estáticos (`.js`, `.css`, imágenes).
  - Implementación de control de versiones por hash MD5 (`_CSS_V`, `_JS_V`) en el backend Flask, recalculando el hash en base al contenido de los archivos `static/css/app.css` y `static/js/app.js` en el arranque.
- **Compresión de Respuesta:** Uso de `Flask-Compress` para empaquetar con Gzip las respuestas HTML y JSON salientes.

### 2.4. Servicio de Notificaciones y Tareas Programadas (Cron Jobs)
El motor de notificaciones automatizado (`notification_service.py`) opera bajo las siguientes pautas técnicas:
- **Canal de Envío:** SMTP Gmail utilizando contraseñas de aplicación de Google (`GMAIL_APP_PASSWORD`) para autenticación segura.
- **GitHub Actions (Cron):** Programación semanal del script mediante el flujo de trabajo de GitHub Actions `.github/workflows/notificaciones.yml`, ejecutándose a las **8:00 AM hora de Colombia (13:00 UTC) de lunes a viernes**, con opción de ejecución manual por demanda (`workflow_dispatch`).
- **Reglas de Alerta por Correo:**
  - **Próximos a Vencer (3 días):** Filtrado de préstamos activos cuya fecha de devolución esperada se cumpla en un plazo menor o igual a 3 días. El correo se envía al responsable (utilizando la lógica de `notification_email` alternativo o `email` de login).
  - **Mora / Retrasos (Diario):** Filtrado de préstamos cuya fecha esperada es menor a la actual y permanecen activos. El sistema envía una notificación diaria al responsable moroso y copia al administrador del Área Tech (`NOTIFICATION_ADMIN_EMAIL`).
  - **Mantenimientos Vencidos o Próximos:** Envío de reportes de mantenimientos agendados sin filtro de estado técnico directo al correo del administrador de mantenimientos (`MAINTENANCE_ADMIN_EMAIL`).
- **Entorno de Pruebas (Override):** Variable de entorno `NOTIFICATION_RECIPIENT_OVERRIDE` para interceptar todas las salidas de correo y redireccionarlas a un único buzón durante pruebas y desarrollo local.
- **Extensibilidad de Canales:** Estructura modular preparada para implementar Meta Cloud API (WhatsApp) mediante tokens y IDs de teléfono parametrizados (`META_WHATSAPP_PHONE_NUMBER_ID`, `META_WHATSAPP_ACCESS_TOKEN`).

### 2.5. Seguridad y Almacenamiento
- **Políticas de Seguridad en Cabeceras:** Inyección automática de cabeceras HTTP de seguridad: `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY` para evitar ataques de clickjacking y spoofing.
- **Autenticación Basada en Sesión:** Decoradores `require_login` y `require_api_login` que encriptan y guardan el ID de usuario autenticado en la cookie de sesión cifrada de Flask.
- **Gestión de Archivos Físicos:**
  - Carga segura de adjuntos y firmas a través del servicio de almacenamiento de Supabase (buckets dedicados) utilizando nombres estructurados con timestamps para evitar colisiones.
  - Implementación local de carga a disco (`/uploads/`) como respaldo y fallback.
  - Establecimiento de un límite máximo de carga por archivo de 20 MB (`MAX_CONTENT_LENGTH = 20 * 1024 * 1024`).

### 2.6. Infraestructura y Despliegue (Deployment)
- **Deployment Platform:** Listo para su ejecución en **Vercel** usando el archivo de configuración `vercel.json` con constructor de Python de Vercel y ruteo optimizado para los assets estáticos del frontend.
- **Gestión de Entorno (.env):** Control estricto de secretos y parámetros de conexión (URLs de API de Supabase, API keys de roles de servicio, contraseñas de correos) aislados del repositorio Git principal.
