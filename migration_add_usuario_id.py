#!/usr/bin/env python3
"""
Script de migración: Agregar usuario_id a equipos
Ejecuta las queries SQL en Supabase para relacionar equipos con usuarios
"""

import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL y SUPABASE_KEY no están configuradas en .env")
    exit(1)

# Headers para Supabase
HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def run_sql(query):
    """Ejecuta una query SQL directamente en Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/sql_exec"
    
    # Alternativamente, usar el endpoint de SQL que Supabase proporciona
    # Este script asume que puedes ejecutar SQL a través de Supabase
    payload = {
        'query': query
    }
    
    try:
        print(f"Ejecutando: {query[:60]}...")
        # Este método puede no funcionar directamente. Alternativa: usar Supabase CLI
        print("⚠️  Este script requiere acceso directo a SQL en Supabase.")
        print("Por favor, ejecuta las queries manualmente en Supabase Dashboard.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("=" * 60)
    print("MIGRACIÓN: Agregar usuario_id a equipos")
    print("=" * 60)
    
    # Las queries que necesitan ejecutarse
    queries = [
        # 1. Agregar columna
        """ALTER TABLE equipos 
ADD COLUMN usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL;""",
        
        # 2. Vincular equipos con usuarios
        """UPDATE equipos
SET usuario_id = usuarios.id
FROM usuarios
WHERE equipos.ubicacion = usuarios.nombre;""",
        
        # 3. Crear índice
        """CREATE INDEX IF NOT EXISTS idx_equipos_usuario_id ON equipos(usuario_id);"""
    ]
    
    print("\n⚠️  NOTAS IMPORTANTES:")
    print("1. Este script NO puede ejecutar SQL directamente vía REST API")
    print("2. Debes ejecutar las queries en Supabase Dashboard")
    print("3. Las queries son:")
    print()
    
    for i, query in enumerate(queries, 1):
        print(f"--- QUERY {i} ---")
        print(query)
        print()
    
    print("\n📋 INSTRUCCIONES:")
    print("1. Ve a https://app.supabase.com → Tu proyecto")
    print("2. Click en 'SQL Editor' en el sidebar izquierdo")
    print("3. Click en 'New Query'")
    print("4. Copia y pega CADA query abajo UNA POR UNA")
    print("5. Presiona 'RUN' para ejecutar cada una")
    print()
    print("Después, ejecuta: python -c \"print('Migración completada')\"")

if __name__ == '__main__':
    main()
