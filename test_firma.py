#!/usr/bin/env python3
"""
Script para testear el sistema de firmas
Ejecutar con: python test_firma.py
"""
import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_get_loan(loan_id=1):
    """Test: Obtener datos del prestamo"""
    print("\n" + "="*60)
    print(f"TEST 1: Obtener prestamo #{loan_id}")
    print("="*60)
    
    url = f"{BASE_URL}/api/prestamos/{loan_id}"
    print(f"GET {url}")
    
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        print(f"Response:")
        print(json.dumps(res.json(), indent=2, ensure_ascii=False))
        
        data = res.json()
        if data.get('id'):
            print(f"\n✅ Prestamo encontrado:")
            print(f"   - Equipo: {data.get('equipo_nombre', 'N/A')}")
            print(f"   - Responsable: {data.get('usuario_nombre', 'N/A')}")
            print(f"   - Fecha: {data.get('fecha_prestamo', 'N/A')}")
            return True
        else:
            print(f"\n❌ Error: {data.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_list_prestamos():
    """Test: Listar prestamos"""
    print("\n" + "="*60)
    print("TEST 0: Listar todos los prestamos")
    print("="*60)
    
    url = f"{BASE_URL}/api/prestamos"
    print(f"GET {url}")
    
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        
        data = res.json()
        if isinstance(data, list):
            print(f"\nTotal prestamos: {len(data)}")
            for p in data[:5]:  # Mostrar primeros 5
                print(f"  - ID {p.get('id')}: {p.get('equipo_nombre', 'Sin equipo')} - {p.get('usuario_nombre', 'Sin usuario')}")
            
            # Retornar el primer ID para test siguiente
            if len(data) > 0:
                return data[0]['id']
        else:
            print(f"Error: {data.get('error')}")
        return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_uploads_endpoint():
    """Test: Verificar que endpoint /uploads esta activo"""
    print("\n" + "="*60)
    print("TEST: Verificar endpoint /uploads")
    print("="*60)
    
    # Ver si existe algun archivo de prueba
    uploads_dir = "uploads/prestamos"
    if os.path.exists(uploads_dir):
        files = os.listdir(uploads_dir)
        print(f"Directorio {uploads_dir} existe")
        print(f"Archivos: {len(files)}")
        for f in files[:5]:
            print(f"  - {f}")
        
        # Intentar acceder a uno
        if files:
            test_file = files[0]
            url = f"{BASE_URL}/uploads/prestamos/{test_file}"
            print(f"\nIntentando acceder a: {url}")
            try:
                res = requests.head(url, timeout=2)
                if res.status_code == 200:
                    print(f"✅ Archivo accesible (status {res.status_code})")
                else:
                    print(f"❌ Archivo no accesible (status {res.status_code})")
            except Exception as e:
                print(f"❌ Error accediendo a archivo: {e}")
    else:
        print(f"⚠️ Directorio {uploads_dir} no existe (normal si es primera vez)")

def test_health():
    """Test: Health check"""
    print("\n" + "="*60)
    print("TEST: Health check del API")
    print("="*60)
    
    url = f"{BASE_URL}/api/health"
    print(f"GET {url}")
    
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        data = res.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get('status') == 'ok':
            print("\n✅ API esta funcionando correctamente")
            return True
        else:
            print("\n⚠️ API respondio pero con warning")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("\n" + "="*60)
    print(" PRUEBAS DEL SISTEMA DE FIRMAS")
    print("="*60)
    
    # 1. Health check
    test_health()
    
    # 2. Listar prestamos
    loan_id = test_list_prestamos()
    
    # 3. Verificar uploads
    test_uploads_endpoint()
    
    # 4. Obtener prestamo especifico
    if loan_id:
        test_get_loan(loan_id)
    else:
        print("\n⚠️ No hay prestamos para testear. Crea uno primero.")
    
    print("\n" + "="*60)
    print(" FIN DE PRUEBAS")
    print("="*60)
