# Stack
Python · HTML · JavaScript · Supabase

# Prioridad absoluta
Mejorar velocidad en entorno de produccion

# Arquitectura
- Capas: domain / application / infrastructure / presentation
- Repository pattern para acceso a datos
- Sin lógica de negocio en controladores ni acceso directo a Supabase desde vistas/rutas
- Funciones pequeñas y reutilizables
- Claridad sobre abstracción; sin clases/interfaces sin necesidad real

# Performance
- Detectar cuellos de botella antes de refactorizar
- Sin SELECT *, queries repetitivas ni payloads innecesarios
- Sin operaciones bloqueantes ni imports pesados

# Convenciones
- Tipado cuando aporte claridad
- Nombres descriptivos, comentarios mínimos
- Sin duplicación, bajo acoplamiento

# Prohibido
Microservicios · CQRS · DDD extremo · abstracciones gratuitas · mover archivos sin justificación

# Flujo de cambios
Analizar impacto → detectar dependencias → proponer plan → ejecutar cambios pequeños