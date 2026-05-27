# Contexto del proyecto

Aplicación web basada en:
- Python
- HTML
- JavaScript
- Supabase

# Objetivos prioritarios

1. Mejorar rendimiento local
2. Reducir acoplamiento
3. Migrar progresivamente a arquitectura por capas
4. Mantener simplicidad
5. Evitar sobreingeniería

# Reglas de arquitectura

- No colocar lógica de negocio en controladores
- No acceder a Supabase directamente desde vistas o rutas
- Usar repository pattern para acceso a datos
- Separar domain, application, infrastructure y presentation
- Mantener funciones pequeñas y reutilizables
- Evitar dependencias innecesarias
- Priorizar claridad sobre abstracción
- No crear clases/interfaces sin necesidad real

# Reglas de performance

- Detectar consultas lentas
- Evitar SELECT *
- Evitar queries repetitivas
- Reducir payloads
- Evitar operaciones bloqueantes
- Minimizar imports pesados
- Detectar cuellos de botella antes de refactorizar

# Convenciones

- Código limpio y tipado cuando tenga sentido
- Nombres descriptivos
- Comentarios mínimos y útiles
- Evitar duplicación
- Mantener bajo acoplamiento

# Qué NO hacer

- No implementar microservicios
- No usar CQRS
- No usar DDD extremo
- No crear abstracciones innecesarias
- No mover archivos masivamente sin justificarlo

# Flujo esperado

Antes de modificar:
1. Analizar impacto
2. Detectar dependencias
3. Proponer plan corto
4. Ejecutar cambios pequeños y seguros

# Prioridad absoluta

La aplicación actualmente es lenta en entorno local.
Toda decisión técnica debe priorizar mejorar velocidad de desarrollo y ejecución local.