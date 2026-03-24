#!/usr/bin/env python3
"""
Migration: Add devolucion fields and ensure all required columns exist

This migration adds fields to support capturing signatures and images
both when the loan is created AND when it's returned.

New columns:
- fecha_firma: Timestamp when initial signature is captured
- firma_devolucion_url: Path to return signature image
- imagen1_devolucion_url: Path to first return photo
- imagen2_devolucion_url: Path to second return photo

State flow:
1. solicitado → (create_prestamo)
2. firmado → (submit initial signature + images)
3. devuelto → (submit return signature + images)

Database changes needed:
"""

SQL_MIGRATIONS = [
    # Ensure fecha_firma exists
    """ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS fecha_firma TIMESTAMP;""",
    
    # Add devolution signature and images columns
    """ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS firma_devolucion_url VARCHAR(255);""",
    """ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS imagen1_devolucion_url VARCHAR(255);""",
    """ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS imagen2_devolucion_url VARCHAR(255);""",
]

print("=" * 70)
print("MIGRACIÓN: Agregar campos para devolución de préstamos")
print("=" * 70)
print()
print("Ejecuta estas comandos en Supabase SQL Editor:")
print()
for i, sql in enumerate(SQL_MIGRATIONS, 1):
    print(f"{i}. {sql}")
print()
print("=" * 70)
print("ESTADO DEL PRÉSTAMO:")
print("=" * 70)
print("""
1. SOLICITADO (inicial)
   - fecha_prestamo: set
   - estado: solicitado
   
2. FIRMADO (después de firmar)
   - firma_url: set (PNG signature)
   - imagen1_url: set (JPG)
   - imagen2_url: set (JPG)
   - fecha_firma: set
   - estado: firmado
   
3. DEVUELTO (después de devolver)
   - firma_devolucion_url: set (PNG return signature)
   - imagen1_devolucion_url: set (JPG return)
   - imagen2_devolucion_url: set (JPG return)
   - fecha_devolucion_real: set
   - estado: devuelto
""")
print("=" * 70)
