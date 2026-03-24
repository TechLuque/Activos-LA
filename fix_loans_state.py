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

print("=" * 80)
print("ACTUALIZANDO PRÉSTAMOS DE 'activo' A 'solicitado'")
print("=" * 80)

# Actualizar todos los préstamos en estado 'activo' a 'solicitado'
url = f"{SUPABASE_API_URL}/prestamos?estado=eq.activo"
resp = requests.patch(url, headers=HEADERS, json={'estado': 'solicitado'})

print(f"\nStatus: {resp.status_code}")
if resp.status_code in [200, 201, 204]:
    if resp.status_code == 204:
        print(f"✅ Se actualizaron los préstamos a estado 'solicitado'")
    else:
        data = resp.json()
        if isinstance(data, list):
            print(f"✅ Se actualizaron {len(data)} préstamo(s) a estado 'solicitado'")
            for p in data:
                print(f"   - ID {p['id']}: {p['estado']}")
        else:
            print(f"✅ Actualización completada")
else:
    print(f"❌ Error: {resp.text}")

print("\n" + "=" * 80)
