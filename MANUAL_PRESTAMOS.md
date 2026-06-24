# Manual de Usuario: Módulo de Préstamos y Devoluciones
## Sistema de Gestión de Activos Empresariales — ActivosLA

Este manual describe el funcionamiento, políticas y flujo operativo del módulo de **Préstamos** del sistema **ActivosLA**. Su objetivo es guiar tanto a administradores como a colaboradores en el uso correcto de la plataforma para garantizar el control y cuidado de los activos de la organización.

---

## 📌 1. Introducción al Módulo de Préstamos

El módulo de préstamos permite controlar la entrega de equipos (laptops, celulares, periféricos, licencias, etc.) de manera temporal o indefinida a los colaboradores de la empresa.

Para garantizar la transparencia y seguridad, el sistema exige:
1. **Firma Digital:** Firma electrónica manuscrita o archivo cargado del colaborador.
2. **Evidencia Fotográfica (PhotoDocs):** Dos fotografías obligatorias al recibir y al devolver el equipo.
3. **Responsabilidad Patrimonial:** Aceptación explícita de las políticas de la organización.

---

## 🏢 2. Roles en el Proceso

El sistema opera bajo dos roles principales:

| Rol | Responsabilidad en Préstamos |
| :--- | :--- |
| **Administrador** (Área de TI / Operaciones) | Crea los préstamos (individuales o masivos), monitorea retrasos en el Dashboard, revisa las hojas de vida y aprueba/recibe las devoluciones. |
| **Colaborador** (Usuario Final / Custodio) | Recibe el enlace, revisa el estado del equipo, firma digitalmente, adjunta las fotos de verificación y asume la responsabilidad patrimonial del activo. |

---

## 🚀 3. Flujo Paso a Paso para Administradores

### 3.1. Crear un Préstamo Individual
Para registrar un préstamo a un colaborador:
1. Vaya a la sección **Préstamos** en el menú lateral izquierdo.
2. Haga clic en el botón **"+ Nuevo préstamo"**.
3. Complete los campos del formulario:
   - **Equipo:** Seleccione el activo de la lista (sólo se muestran equipos en estado *Disponible*).
   - **Responsable:** Seleccione al colaborador que recibirá el equipo.
   - **Fecha Préstamo:** Fecha en la que se realiza la entrega física.
   - **Devolución Esperada:** Fecha pactada para retornar el equipo (opcional).
   - **Notas:** Registre cualquier observación relevante (ej. *"Se entrega con cargador original y estuche"*).
4. Presione **"Guardar"**. El préstamo quedará creado en estado **Solicitado**.

### 3.2. Crear un Préstamo Masivo (Varios Equipos)
Si necesita entregar varios activos al mismo tiempo a una sola persona (por ejemplo, un kit de bienvenida con laptop, mouse, pantalla y celular):
1. En la sección **Préstamos**, haga clic en **"+ Préstamo masivo"**.
2. Seleccione al colaborador responsable.
3. Seleccione la fecha de préstamo y devolución esperada.
4. En el listado de equipos, marque las casillas de todos los activos que va a entregar.
5. Haga clic en **"Crear Préstamo Masivo"**.
   - *Nota:* El sistema validará que ninguno de los equipos seleccionados tenga otro préstamo activo o esté en mantenimiento.

---

## ✍️ 4. Proceso de Firma y Verificación (Colaborador)

Una vez que el administrador crea el préstamo, el colaborador responsable debe firmarlo. Este proceso se realiza a través de un **enlace público único** enviado al colaborador (no requiere que el usuario inicie sesión).

Al abrir el enlace, el colaborador verá la siguiente interfaz:

```
[ Información del Préstamo ]
Equipo: Laptop Dell Latitude 5420  |  Código: PRE-0042
Responsable: Juan Pérez            |  Fecha Límite: 15/07/2026
-----------------------------------------------------------
[ Área de Firma ]
( ) Dibujar Firma   ( ) Subir Imagen
[_________________________________________________________] <- Canvas Táctil
[ Fotos de Evidencia ]
[ Tomar Foto 1: Estado Inicial ]   [ Tomar Foto 2: Verificación ]
-----------------------------------------------------------
[x] Acepto Términos y Condiciones de la Política LA-PL-008
-----------------------------------------------------------
                 [ CONFIRMAR FIRMA ]
```

### Pasos para el colaborador:
1. **Revisión de Datos:** Validar que los campos del equipo y observaciones coincidan con lo recibido.
2. **Registro de Firma:**
   - **Dibujar firma (Recomendado):** Puede firmar con el dedo en pantallas táctiles (móviles/tabletas) o con el mouse.
   - **Subir imagen:** Puede subir una fotografía de su firma escrita en papel.
3. **Fotografías de Respaldo:** El colaborador debe subir obligatoriamente dos imágenes del estado físico del activo:
   - *Foto 1 (Estado Inicial):* Foto general del equipo encendido o en su estado de entrega.
   - *Foto 2 (Verificación):* Foto de detalles específicos (teclado, pantalla, número de serie).
4. **Casilla de Política:** Aceptar la cláusula de **Responsabilidad Patrimonial**.
5. **Confirmación:** Hacer clic en **"Confirmar Firma"**.
   - El sistema almacena la firma y fotos en la nube.
   - El estado del préstamo se actualiza a **"Firmado"** y el activo queda asignado legalmente al usuario.

---

## ⏰ 5. Monitoreo y Alertas Automáticas

El sistema cuenta con un motor de notificaciones automatizado para evitar olvidos:

* **Alertas en el Dashboard:** En el panel de control del Administrador, se mostrarán en la sección **"Alertas de préstamos"** todos los equipos vencidos o próximos a vencer en los siguientes 7 días.
* **Calendario General:** La pestaña de **Calendario** agrupa visualmente las fechas límite:
  - 🟡 *Amarillo:* Préstamos activos en curso.
  - 🔴 *Rojo:* Préstamos vencidos pendientes de devolución.
* **Notificaciones por Correo Diario:**
  - **Aviso de Vencimiento:** 3 días antes de la fecha límite, el colaborador recibirá un correo recordando la entrega.
  - **Aviso de Retraso:** Si la fecha vence y no se ha devuelto, se enviarán correos diarios notificando la mora tanto al colaborador como al administrador de TI.

---

## 🔄 6. Flujo de Devolución de Activos

Cuando el colaborador entrega de vuelta el activo, se debe cerrar la custodia:

1. **Inspección Física:** El administrador de TI o supervisor inspecciona el equipo para validar que no tenga daños externos no reportados.
2. **Ingresar a Firma de Devolución:** El colaborador abre el enlace de devolución de su préstamo (`/firma/<id>?tipo=devolucion`).
3. **Registro de Entrega:**
   - Dibuja su firma de entrega en el canvas táctil.
   - Toma **2 fotografías** que muestren el estado en el que devuelve el activo (evidencia de que se entregó sin daños).
4. **Cerrar en Sistema:** Al guardar, el estado cambia a **"Devuelto"** y se libera el equipo.
   - El campo `usuario_id` del equipo se limpia automáticamente, haciéndolo disponible de inmediato para futuras asignaciones.

---

## ❓ 7. Preguntas Frecuentes y Políticas Organizacionales

#### ¿Qué ocurre si pierdo o daño accidentalmente el activo?
De acuerdo con la política **LA-PL-008**, el colaborador asume la custodia total del activo. Los daños causados por negligencia, descuido o pérdida del equipo serán evaluados por el departamento correspondiente, pudiendo aplicar cobros administrativos o descuentos vía nómina respaldados por la firma digital del préstamo.

#### ¿Cómo se reporta una falla técnica durante el préstamo?
Si el equipo presenta fallas de software o hardware, el colaborador no debe intentar repararlo. Debe reportarlo de inmediato al administrador para que este registre un evento de **Mantenimiento Correctivo** en la *Hoja de Vida* del equipo y, de ser necesario, se le asigne un equipo de reemplazo provisional.

#### ¿Se puede extender la fecha esperada de devolución?
Sí. El administrador puede editar el registro del préstamo desde el panel de control y modificar la **Fecha de Devolución Esperada** si el colaborador requiere el equipo por más tiempo, lo cual actualizará los recordatorios automáticos de correo.
