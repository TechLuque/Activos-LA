"""
Script de importación masiva de activos desde CSV.

Uso:
    python importar_activos.py activos_template.csv
    python importar_activos.py mi_lista.csv --dry-run   # valida sin insertar

El CSV solo necesita dos columnas: nombre, tipo
El serial se genera automáticamente con el prefijo del tipo (ej: LAP0001, MON0002).
"""

import csv
import re
import sys
import argparse
from datetime import date
from db import supabase_request


def get_tipos() -> list:
    """Devuelve todos los tipos con id, nombre y serial_prefix."""
    result = supabase_request('GET', 'tipos_equipos', '?select=id,nombre,serial_prefix&order=nombre.asc')
    if not isinstance(result, list):
        print(f"ERROR: No se pudieron obtener los tipos de equipos: {result}")
        sys.exit(1)
    return result


def get_seriales_existentes() -> list:
    """Devuelve todos los seriales actuales de la tabla equipos."""
    result = supabase_request('GET', 'equipos', '?select=serial')
    if not isinstance(result, list):
        return []
    return [r.get('serial', '') or '' for r in result]


def build_serial_counters(seriales: list, tipos: list) -> dict:
    """
    Precalcula el máximo número usado por cada prefix.
    Devuelve {prefix_upper: max_num} para poder incrementar durante la importación.
    """
    counters: dict = {}
    for tipo in tipos:
        prefix = (tipo.get('serial_prefix') or '').upper().strip()
        if not prefix:
            continue
        patron = re.compile(rf'^{re.escape(prefix)}(\d{{4}})$', re.IGNORECASE)
        nums = [int(m.group(1)) for s in seriales if (m := patron.match(s))]
        counters[prefix] = max(nums) if nums else 0
    return counters


def next_serial(prefix: str, counters: dict) -> str:
    """Genera el siguiente serial para un prefix y actualiza el contador en memoria."""
    prefix = prefix.upper()
    counters[prefix] = counters.get(prefix, 0) + 1
    return f"{prefix}{str(counters[prefix]).zfill(4)}"


def main():
    parser = argparse.ArgumentParser(description='Importar activos desde CSV a Supabase')
    parser.add_argument('csv_file', help='Ruta al archivo CSV')
    parser.add_argument('--dry-run', action='store_true', help='Validar y mostrar seriales sin insertar')
    args = parser.parse_args()

    # Cargar datos de referencia desde Supabase
    tipos = get_tipos()
    tipos_por_nombre = {t['nombre'].lower().strip(): t for t in tipos}

    print("Tipos disponibles:")
    for t in tipos:
        prefix = t.get('serial_prefix') or '(sin prefijo)'
        print(f"  - {t['nombre']}  →  prefijo: {prefix}")
    print()

    seriales_existentes = get_seriales_existentes()
    counters = build_serial_counters(seriales_existentes, tipos)

    # Leer CSV
    with open(args.csv_file, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    print(f"Procesando {total} activos de '{args.csv_file}'...\n")

    ok = 0
    errores = 0

    for i, row in enumerate(rows, start=2):
        nombre = row.get('nombre', '').strip()
        tipo_raw = row.get('tipo', '').strip()

        if not nombre:
            print(f"  Fila {i}: IGNORADA — falta 'nombre'")
            errores += 1
            continue
        if not tipo_raw:
            print(f"  Fila {i}: IGNORADA — falta 'tipo'")
            errores += 1
            continue

        tipo = tipos_por_nombre.get(tipo_raw.lower())
        if tipo is None:
            disponibles = ', '.join(t['nombre'] for t in tipos)
            print(f"  Fila {i}: ERROR — tipo '{tipo_raw}' no existe. Disponibles: {disponibles}")
            errores += 1
            continue

        prefix = (tipo.get('serial_prefix') or '').upper().strip()
        if not prefix:
            print(f"  Fila {i}: ERROR — el tipo '{tipo['nombre']}' no tiene prefijo serial configurado. "
                  f"Configúralo en la app antes de importar.")
            errores += 1
            continue

        serial = next_serial(prefix, counters)

        if args.dry_run:
            print(f"  Fila {i}: [DRY-RUN] '{nombre}' → serial: {serial}")
            ok += 1
            continue

        equipo_data = {
            'nombre': nombre,
            'tipo_id': tipo['id'],
            'serial': serial,
            'estado': 'bueno',
            'disponibilidad': 'Disponible',
        }

        result = supabase_request('POST', 'equipos', '', equipo_data)

        if not isinstance(result, list) or not result:
            print(f"  Fila {i}: ERROR al insertar '{nombre}' — {result}")
            errores += 1
            # Revertir el contador para no dejar un hueco en la secuencia
            counters[prefix] -= 1
            continue

        equipo_id = result[0]['id']
        supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': equipo_id,
            'tipo': 'adquisicion',
            'titulo': 'Registro inicial',
            'descripcion': 'Equipo registrado en sistema',
            'fecha': date.today().isoformat(),
            'responsable': 'Importación masiva',
        })

        print(f"  Fila {i}: OK — '{nombre}' → serial: {serial}  (id={equipo_id})")
        ok += 1

    print(f"\nResultado: {ok} insertados, {errores} errores de {total} filas")
    if args.dry_run:
        print("(modo dry-run: no se insertó nada)")


if __name__ == '__main__':
    main()
