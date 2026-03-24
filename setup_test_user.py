#!/usr/bin/env python3
"""
Script para configurar la BD e insertar usuario de prueba
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def setup_test_user():
    """Crear/actualizar usuario de prueba para login"""
    print("=" * 70)
    print("CONFIGURANDO USUARIO DE PRUEBA")
    print("=" * 70)
    
    # 1. Verificar si el usuario admin existe
    print("\n1. Buscando usuario admin existente...")
    try:
        resp = requests.get(
            f"{SUPABASE_API_URL}/usuarios?email=eq.admin@activoseq.com",
            headers=HEADERS
        )
        
        usuarios = resp.json() if resp.status_code == 200 else []
        
        if usuarios:
            print(f"   ✓ Usuario encontrado: {usuarios[0]['nombre']}")
            user_id = usuarios[0]['id']
            
            # Actualizar la contraseña
            print("\n2. Actualizando contraseña...")
            update_resp = requests.patch(
                f"{SUPABASE_API_URL}/usuarios?id=eq.{user_id}",
                json={'password': '123456'},
                headers=HEADERS
            )
            
            if update_resp.status_code in [200, 204]:
                print("   ✓ Contraseña actualizada")
            else:
                print(f"   ✗ Error al actualizar: {update_resp.text}")
                
        else:
            print("   ✗ Usuario no encontrado, creando...")
            
            # Crear nuevo usuario
            print("\n2. Creando usuario admin...")
            create_resp = requests.post(
                f"{SUPABASE_API_URL}/usuarios",
                json={
                    'nombre': 'Admin',
                    'email': 'admin@activoseq.com',
                    'password': '123456',
                    'departamento': 'Administración',
                    'estado': 'activo'
                },
                headers=HEADERS
            )
            
            if create_resp.status_code in [200, 201]:
                print("   ✓ Usuario creado exitosamente")
                user_data = create_resp.json()
                if isinstance(user_data, list):
                    print(f"   - ID: {user_data[0]['id']}")
                    print(f"   - Email: {user_data[0]['email']}")
            else:
                print(f"   ✗ Error al crear: {create_resp.text}")
                
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETADO")
    print("=" * 70)
    print("\nCredenciales para login:")
    print("  Usuario: admin")
    print("  Email: admin@activoseq.com")
    print("  Contraseña: 123456")
    print("\nAccede a: http://localhost:5000/login")
    print("=" * 70)
    
    return True

if __name__ == '__main__':
    setup_test_user()
