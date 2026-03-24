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
print("LISTANDO TODOS LOS PRÉSTAMOS")
print("=" * 80)

# Obtener todos los préstamos
url = f"{SUPABASE_API_URL}/prestamos?order=id.desc"
resp = requests.get(url, headers=HEADERS)
print(f"\nStatus: {resp.status_code}")

if resp.status_code == 200:
    prestamos = resp.json()
    print(f"\nTotal: {len(prestamos)} préstamos\n")
    
    if len(prestamos) > 0:
        for i, p in enumerate(prestamos[:5]):  # Mostrar max 5
            print(f"{i+1}. ID: {p.get('id')}")
            print(f"   Equipo ID: {p.get('equipo_id')}")
            print(f"   Usuario ID: {p.get('usuario_id')}")
            print(f"   Estado: {p.get('estado')}")
            print(f"   Fecha Préstamo: {p.get('fecha_prestamo')}")
            print(f"   Fecha Devolución Esperada: {p.get('fecha_devolucion_esperada')}")
            print(f"   Firma URL: {p.get('firma_url')}")
            print(f"   Notas: {p.get('notas')}")
            print()
    else:
        print("❌ NO hay préstamos en la base de datos")
else:
    print(f"❌ Error: {resp.text}")

print("=" * 80)
