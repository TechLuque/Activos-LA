import requests
import os
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

print("=" * 70)
print("VERIFICANDO USUARIO ADMIN")
print("=" * 70)

# Buscar por email
print("\n1. Buscando por email 'admin@activoseq.com'...")
url = f"{SUPABASE_API_URL}/usuarios?email=eq.admin@activoseq.com"
resp = requests.get(url, headers=HEADERS)
print(f"   Status: {resp.status_code}")
data = resp.json() if resp.status_code == 200 else {}
print(f"   Respuesta: {data}")

if isinstance(data, list) and len(data) > 0:
    user = data[0]
    print(f"\n2. Usuario encontrado:")
    print(f"   ID: {user.get('id')}")
    print(f"   Nombre: {user.get('nombre')}")
    print(f"   Email: {user.get('email')}")
    print(f"   Password: '{user.get('password')}'")
    print(f"   Estado: {user.get('estado')}")
    print(f"\n3. Verificación:")
    if user.get('password') == '123456':
        print("   ✅ Contraseña coincide con '123456'")
    else:
        print(f"   ❌ Contraseña NO coincide. Es: '{user.get('password')}'")
    if user.get('estado') == 'activo':
        print("   ✅ Usuario está activo")
    else:
        print(f"   ❌ Usuario NO está activo. Estado: {user.get('estado')}")
else:
    print("   ❌ No se encontró usuario")

# Buscar por nombre
print("\n4. Buscando por nombre 'admin'...")
url = f"{SUPABASE_API_URL}/usuarios?nombre=eq.admin"
resp = requests.get(url, headers=HEADERS)
print(f"   Status: {resp.status_code}")
data = resp.json() if resp.status_code == 200 else {}
if isinstance(data, list) and len(data) > 0:
    print(f"   Encontrado: {data}")
else:
    print("   ❌ No encontrado por nombre 'admin'")

# Buscar por nombre 'Admin'
print("\n5. Buscando por nombre 'Admin' (con mayúscula)...")
url = f"{SUPABASE_API_URL}/usuarios?nombre=eq.Admin"
resp = requests.get(url, headers=HEADERS)
print(f"   Status: {resp.status_code}")
data = resp.json() if resp.status_code == 200 else {}
if isinstance(data, list) and len(data) > 0:
    print(f"   Encontrado: {data[0].get('nombre')}")
else:
    print("   ❌ No encontrado")

print("\n" + "=" * 70)
