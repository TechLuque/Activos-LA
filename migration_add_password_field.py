#!/usr/bin/env python3
"""
Migration: Add password field to usuarios table for login system

This migration adds a password column to support the new login authentication system.
"""

SQL_MIGRATIONS = [
    # Add password column if it doesn't exist
    """ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password VARCHAR(255);""",
]

print("=" * 70)
print("MIGRACIÓN: Agregar campo de contraseña a tabla usuarios")
print("=" * 70)
print()
print("Ejecuta este comando en Supabase SQL Editor:")
print()
for i, sql in enumerate(SQL_MIGRATIONS, 1):
    print(f"{i}. {sql}")
print()
print("=" * 70)
print("DATOS DE PRUEBA (LOGIN):")
print("=" * 70)
print("""
Usuario: admin
Contraseña: 123456

Para probar el login, asegúrate de que exista un usuario en la tabla usuarios
con:
- nombre o email = 'admin'
- password = '123456'
- estado = 'activo'

Ejemplo SQL para insertar usuario de prueba:
INSERT INTO usuarios (nombre, email, password, departamento, estado)
VALUES ('Admin', 'admin@activoseq.com', '123456', 'Administración', 'activo')
ON CONFLICT DO NOTHING;

NOTA IMPORTANTE: En producción, usar bcrypt o similar para hashear contraseñas.
""")
print("=" * 70)
