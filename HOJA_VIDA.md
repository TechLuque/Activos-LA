# Hoja de Vida de los Activos (ActivosLA)

La **Hoja de Vida** es el módulo encargado de registrar y auditar el historial completo de eventos, mantenimientos, reparaciones, asignaciones y cambios de estado de cada activo (equipo) a lo largo de su ciclo de vida en la empresa.

---

## 🗄️ Estructura de Datos (Base de Datos)

En Supabase (PostgreSQL), la información de la hoja de vida se almacena en la tabla `hoja_vida`. Cada registro está asociado a un equipo individual.

### Tabla: `hoja_vida`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | `integer` (PK) | Identificador único del evento. |
| `equipo_id` | `integer` (FK) | ID del equipo al que pertenece el evento (relacionado con la tabla `equipos`). |
| `tipo` | `varchar` | Categoría o tipo de evento (ver listado de tipos). |
| `titulo` | `varchar` | Título descriptivo corto del evento. |
| `descripcion` | `text` | Detalles adicionales sobre lo ocurrido. |
| `fecha` | `date` | Fecha en la que ocurrió el evento (formato `YYYY-MM-DD`). |
| `responsable` | `varchar` | Persona o entidad que realiza o registra el evento (ej. "Sistema", nombre del técnico o del usuario). |
| `creado_en` | `timestamp` | Fecha y hora de creación del registro en la base de datos (por defecto `now()`). |

---

## 🏷️ Tipos de Eventos e Iconos Asociados

El sistema clasifica los eventos mediante la columna `tipo`. En la interfaz de usuario, cada tipo se representa con un icono visual en la línea de tiempo:

| Tipo (`tipo`) | Icono en UI | Uso |
| :--- | :---: | :--- |
| `adquisicion` | 🟢 | Registro inicial y compra del equipo. |
| `mantenimiento` | 🟡 | Labores de mantenimiento preventivo y correctivo. |
| `reparacion` | 🔴 | Reparaciones técnicas o de hardware. |
| `proceso` | 🔵 | Procesos internos del equipo. |
| `otro` | ⚪ | Eventos varios o personalizados creados manualmente. |
| `asignacion` | ⚪ / Personalizado | Asignación del equipo a un nuevo responsable. |
| `devolucion` | ⚪ / Personalizado | Retorno del equipo y liberación del responsable. |
| `reasignacion` | ⚪ / Personalizado | Transferencia directa del equipo a otro responsable. |
| `desasignacion` | ⚪ / Personalizado | Desvinculación de un responsable (mediante firma o proceso administrativo). |
| `cambio_responsable` | ⚪ / Personalizado | Cambio directo de dueño/responsable en la edición. |

---

## 🔗 Endpoints de la API REST (`app.py`)

El backend Flask expone los siguientes endpoints públicos y protegidos bajo la ruta base de la API:

### 1. Obtener la hoja de vida de un equipo
* **Ruta:** `GET /api/equipos/<int:id>/hoja_vida`
* **Descripción:** Obtiene todos los eventos de la hoja de vida asociados al equipo especificado, ordenados cronológicamente de forma descendente por fecha e ID.
* **Respuesta (200 OK):**
  ```json
  [
    {
      "id": 12,
      "equipo_id": 5,
      "tipo": "mantenimiento",
      "titulo": "Mant. preventivo: Limpieza interna y cambio de pasta térmica",
      "descripcion": "Se realiza mantenimiento preventivo semestral...",
      "fecha": "2026-06-16",
      "responsable": "Téc. Juan Pérez"
    },
    {
      "id": 1,
      "equipo_id": 5,
      "tipo": "adquisicion",
      "titulo": "Registro inicial",
      "descripcion": "Equipo registrado en sistema",
      "fecha": "2026-01-15",
      "responsable": "Sistema"
    }
  ]
  ```

### 2. Registrar un nuevo evento manualmente
* **Ruta:** `POST /api/equipos/<int:id>/hoja_vida`
* **Descripción:** Permite a un administrador añadir un evento personalizado a la hoja de vida del activo.
* **Payload (JSON):**
  ```json
  {
    "tipo": "reparacion",
    "titulo": "Cambio de pantalla",
    "descripcion": "Se reemplaza panel LCD dañado por uno nuevo de 14 pulgadas.",
    "fecha": "2026-06-16",
    "responsable": "Soporte TI"
  }
  ```
* **Respuesta (201 Created):** Retorna el registro insertado.

### 3. Eliminar un evento de la hoja de vida
* **Ruta:** `DELETE /api/hoja_vida/<int:id>`
* **Descripción:** Elimina un evento de la hoja de vida utilizando su ID único.
* **Respuesta (200 OK):**
  ```json
  {
    "ok": true
  }
  ```

---

## ⚡ Registro Automático de Eventos

Para garantizar la trazabilidad total del activo, el sistema registra eventos automáticamente en la hoja de vida cuando se realizan las siguientes acciones en la aplicación:

### A. Registro Inicial (Creación del Equipo)
Al crear un equipo nuevo en la base de datos, el sistema genera automáticamente el primer hito en su hoja de vida:
* **Tipo:** `adquisicion`
* **Título:** `"Registro inicial"`
* **Descripción:** La descripción ingresada para el equipo (o `"Equipo registrado en sistema"` por defecto).
* **Responsable:** `"Sistema"`

### B. Creación de un Mantenimiento
Cuando se registra un nuevo mantenimiento preventivo o correctivo en el módulo de mantenimientos:
* **Tipo:** `mantenimiento`
* **Título:** `"Mant. {tipo}: {primeros 60 caracteres de la descripción}"`
* **Descripción:** Descripción completa del mantenimiento.
* **Responsable:** Nombre del técnico a cargo (`tecnico`).

### C. Asignación del Equipo
Al entregar y firmar la asignación de un equipo a un colaborador:
* **Tipo:** `asignacion`
* **Título:** `"Asignado a {nombre_usuario}"`
* **Descripción:** `"Equipo asignado en entrada con estado: {estado_equipo}"`
* **Responsable:** Usuario logueado en la sesión (o `"Sistema"` si se hace de forma automatizada).

### D. Devolución del Equipo
Al retornar el equipo (cierre de asignación o préstamo):
* **Tipo:** `devolucion`
* **Título:** `"Devuelto por {nombre_usuario}"`
* **Descripción:** `"Equipo devuelto con estado: {estado_equipo}. Notas: {notas}"` (o `"Equipo devuelto mediante firma pública de devolución."` en firmas públicas).
* **Responsable:** Usuario de sesión (o `"Sistema (Firma Pública)"`).

### E. Reasignación de Responsable
Al transferir el equipo directamente a otro colaborador desde una asignación abierta:
* **Tipo:** `reasignacion`
* **Título:** `"Reasignado a {nombre_nuevo_usuario}"`
* **Descripción:** `"Equipo reasignado a {nombre_nuevo_usuario}."`
* **Responsable:** Usuario de sesión.

### F. Desasignación o Liberación
Al desvincular un equipo de su responsable para dejarlo nuevamente "Disponible" sin registrar retorno físico inmediato:
* **Tipo:** `desasignacion`
* **Título:** `"Desasignado de {nombre_usuario}"`
* **Descripción:** `"Equipo desasignado del responsable {nombre_usuario}."` (o `"Equipo desasignado del responsable {nombre_usuario} mediante firma de desasignación."` en flujos públicos).
* **Responsable:** Usuario de sesión (o `"Sistema (Firma Pública)"`).

### G. Cambio de Responsable Manual (Edición de Equipo)
Cuando se cambia el campo de responsable de forma manual en el formulario de edición de equipo:
* **Tipo:** `cambio_responsable`
* **Título:** `"Cambio de responsable: {usuario_anterior} → {usuario_nuevo}"`
* **Descripción:** Motivo especificado para el cambio.
* **Responsable:** Usuario de sesión.

---

## 🖥️ Integración en la Interfaz de Usuario (UI)

La Hoja de Vida se visualiza en la aplicación web mediante un modal interactivo (`ovHV`) que se abre al hacer clic en el botón `📋` de la fila de un equipo:

1. **Metadatos Generales:** En la parte superior del modal se muestran tarjetas con datos actuales del equipo: *Estado*, *Valor*, *Fecha de Adquisición* y *Ubicación*.
2. **Pestaña de Mantenimientos:** Lista todos los mantenimientos asociados (obtenidos de `/api/equipos/<id>/mantenimientos`), detallando si es preventivo/correctivo, costo, técnico y fechas de revisión. Permite añadir nuevos mantenimientos o borrarlos desde allí.
3. **Pestaña de Línea de Tiempo (Eventos):** Dibuja una línea de tiempo vertical con todos los registros devueltos por `/api/equipos/<id>/hoja_vida`. Permite a los administradores registrar eventos manuales (mediante el botón de "Agregar evento" que abre el modal `ovAddHV`) y eliminar eventos del historial.
