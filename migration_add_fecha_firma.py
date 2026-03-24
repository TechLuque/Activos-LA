"""
Migration: Add new columns for loan state tracking
- fecha_firma: When the loan was signed
"""

MIGRATION_SQL = """
-- Agregar columnas para tracking de estados
ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS fecha_firma TIMESTAMP;

-- Comentario para documentación
COMMENT ON COLUMN prestamos.fecha_firma IS 'Fecha y hora cuando se firmó el préstamo';
"""

def run_migration():
    """
    Executa la migración en Supabase usando SQL Editor
    """
    print("=" * 70)
    print("MIGRACIÓN: Agregar tracking de estados en préstamos")
    print("=" * 70)
    print()
    print("Copiar y pegar esto en Supabase Dashboard → SQL Editor:")
    print()
    print(MIGRATION_SQL)
    print()
    print("=" * 70)
    print("Cambios realizados:")
    print("- ✅ Agregar columna fecha_firma (timestamp)")
    print()
    print("Estados ahora soportados:")
    print("  • 'solicitado' - Cuando se crea el préstamo")
    print("  • 'firmado' - Cuando se firma con firma digital + fotos")
    print("  • 'devuelto' - Cuando se devuelve el equipo")
    print()
    print("IMPORTANTE:")
    print("- Ejecuta el SQL en tu Supabase Dashboard")
    print("- Si la columna ya existe, no pasará nada (por el IF NOT EXISTS)")
    print("=" * 70)

if __name__ == '__main__':
    run_migration()
