# Configuración Make.com — Notificaciones de Activos

## Conexión a Supabase

Headers que van en **cada** módulo HTTP:

| Header | Valor |
|---|---|
| `apikey` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJkcnFpem1nY3d2dnJ6bmpocmt3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDAzMTQyNSwiZXhwIjoyMDg5NjA3NDI1fQ.7wp4-nVpDrl-wUt5b87LNwZ75PhgeUmMjQwAxSsv-QE` |
| `Authorization` | `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJkcnFpem1nY3d2dnJ6bmpocmt3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDAzMTQyNSwiZXhwIjoyMDg5NjA3NDI1fQ.7wp4-nVpDrl-wUt5b87LNwZ75PhgeUmMjQwAxSsv-QE` |
| `Content-Type` | `application/json` |
| `Prefer` | `count=exact` |

**Nota:** Usamos la `service_role` key para evitar RLS y traer datos limpios.

---

## Paso 1 — Trigger: Schedule

- **Schedule:** Every day
- **Time:** `08:00` (8 AM)
- **Timezone:** `America/Bogota`

---

## Paso 2 — HTTP GET: Préstamos próximos a vencer (≤3 días)

**URL:**
```
https://rdrqizmgcwvvrznjhrkw.supabase.co/rest/v1/prestamos
```

**Method:** `GET`

**Query string:**
```
select=id,fecha_prestamo,fecha_devolucion_esperada,estado,equipos(nombre,serial,marca,modelo,ubicacion),usuarios(nombre,email,departamento)
estado=neq.devuelto
fecha_devolucion_esperada=lte.{{formatDate (addDays now 3) "YYYY-MM-DD"}}
fecha_devolucion_esperada=gte.{{formatDate now "YYYY-MM-DD"}}
order=fecha_devolucion_esperada.asc
```

En Make, ponlo como:
```
?select=id,fecha_prestamo,fecha_devolucion_esperada,estado,equipos(nombre,serial,marca,modelo,ubicacion),usuarios(nombre,email,departamento)&estado=neq.devuelto&fecha_devolucion_esperada=lte.{{formatDate (addDays now 3) "YYYY-MM-DD"}}&fecha_devolucion_esperada=gte.{{formatDate now "YYYY-MM-DD"}}&order=fecha_devolucion_esperada.asc
```

**Parse response:** `Data` → `data[]`

---

## Paso 3 — HTTP GET: Mantenimientos preventivos próximos (≤3 días)

**URL:**
```
https://rdrqizmgcwvvrznjhrkw.supabase.co/rest/v1/mantenimientos
```

**Method:** `GET`

**Query string:**
```
select=id,equipo_id,tipo,estado,fecha,proxima_revision,descripcion,costo,tecnico,equipos(nombre,serial,marca,modelo,ubicacion)
tipo=eq.preventivo
estado=neq.completado
proxima_revision=lte.{{formatDate (addDays now 3) "YYYY-MM-DD"}}
order=proxima_revision.asc
```

En Make:
```
?select=id,equipo_id,tipo,estado,fecha,proxima_revision,descripcion,costo,tecnico,equipos(nombre,serial,marca,modelo,ubicacion)&tipo=eq.preventivo&estado=neq.completado&proxima_revision=lte.{{formatDate (addDays now 3) "YYYY-MM-DD"}}&order=proxima_revision.asc
```

**Parse response:** `Data` → `data[]`

---

## Paso 4 — Text Aggregator ×2

### Aggregator 1: Préstamos

| Campo | Valor |
|---|---|
| **Source** | Array del paso 2 |
| **Aggregate by** | `all` (un solo bloque) |

**Template:**
```
📋 PRÉSTAMOS PRÓXIMOS A VENCER
{{#if (empty data)}}
✅ No hay préstamos próximos a vencer
{{else}}
{{#forEach data}}
────────────────────────
• Equipo: {{this.equipos.nombre}}
  Serial: {{this.equipos.serial}}
  Modelo: {{this.equipos.marca}} {{this.equipos.modelo}}
  Ubicación: {{this.equipos.ubicacion}}
  Responsable: {{this.usuarios.nombre}} ({{this.usuarios.departamento}})
  Vence: {{formatDate this.fecha_devolucion_esperada "DD/MM/YYYY"}}
  Estado: {{this.estado}}

{{/forEach}}
{{/if}}
```

### Aggregator 2: Mantenimientos

| Campo | Valor |
|---|---|
| **Source** | Array del paso 3 |
| **Aggregate by** | `all` |

**Template:**
```
🔧 MANTENIMIENTOS PREVENTIVOS PRÓXIMOS
{{#if (empty data)}}
✅ No hay mantenimientos preventivos pendientes
{{else}}
{{#forEach data}}
────────────────────────
• Equipo: {{this.equipos.nombre}}
  Serial: {{this.equipos.serial}}
  Modelo: {{this.equipos.marca}} {{this.equipos.modelo}}
  Ubicación: {{this.equipos.ubicacion}}
  Técnico: {{this.tecnico}}
  Próxima revisión: {{formatDate this.proxima_revision "DD/MM/YYYY"}}
  Descripción: {{this.descripcion}}

{{/forEach}}
{{/if}}
```

---

## Paso 5 — Gmail: Enviar resumen

| Campo | Valor |
|---|---|
| **To** | `santiagolazaro649@gmail.com` |
| **Subject** | `📌 Resumen de Activos — {{formatDate now "DD/MM/YYYY"}}` |
| **Content** | `{{aggregator1.text}}\n\n{{aggregator2.text}}` |

---

## Resumen del escenario

```
[Schedule 8AM] → [HTTP: Préstamos] → [Aggregator 1] → [Gmail]
                                      ↘
[                ] → [HTTP: Manttos] → [Aggregator 2]
```

Los dos HTTP se ejecutan en paralelo, luego cada uno alimenta su aggregator, y el Gmail recibe el texto combinado de ambos.
