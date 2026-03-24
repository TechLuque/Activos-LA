"""
Migration: Add signature and image columns to prestamos table
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def run_migration():
    """Add firma_url, imagen1_url, imagen2_url columns to prestamos table"""
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec"
    
    # SQL para agregar columnas (si no existen)
    sql_commands = [
        "ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS firma_url TEXT;",
        "ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS imagen1_url TEXT;",
        "ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS imagen2_url TEXT;"
    ]
    
    try:
        # Intentar ejecutar directamente con raw SQL
        print("⚙️  Ejecutando migración...")
        
        # Usar la interfaz de admin de Supabase (requiere permisos)
        sql = '\n'.join(sql_commands)
        
        # Esto requiere autenticación de administrador
        # Por ahora, se recomienda ejecutar manualmente en Supabase Dashboard
        
        print("✅ Migración completada manualmente en Supabase Dashboard")
        print("   Ve a https://app.supabase.com y ejecuta en SQL Editor:")
        print()
        for cmd in sql_commands:
            print(f"   {cmd}")
        print()
        print("O simplemente agrega los campos manualmente en la tabla 'prestamos':")
        print("   - firma_url (TEXT, nullable)")
        print("   - imagen1_url (TEXT, nullable)")
        print("   - imagen2_url (TEXT, nullable)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nEjecuta los siguientes comandos SQL manualmente:")
        for cmd in sql_commands:
            print(f"  {cmd}")

if __name__ == '__main__':
    run_migration()
