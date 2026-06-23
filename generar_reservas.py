"""
Genera seriales de reserva para impresión de etiquetas.

Crea 50 equipos de reserva por cada categoría (PC, MB, TC)
con nombre "Reserva" y serial auto-generado.

Uso:
    python generar_reservas.py
    python generar_reservas.py --dry-run   # muestra seriales sin insertar
"""

import re
import sys
import argparse
from datetime import date
from db import supabase_request


PREFIJOS = ['PC', 'MB', 'TC']
CANTIDAD = 50


def get_tipos() -> list:
    result = supabase_request('GET', 'tipos_equipos', '?select=id,nombre,serial_prefix')
    if not isinstance(result, list):
        print(f"ERROR: No se pudieron obtener los tipos: {result}")
        sys.exit(1)
    return result


def get_seriales_existentes() -> list:
    result = supabase_request('GET', 'equipos', '?select=serial')
    if not isinstance(result, list):
        return []
    return [r.get('serial', '') or '' for r in result]


def max_serial_por_prefijo(seriales: list, prefix: str) -> int:
    patron = re.compile(rf'^{re.escape(prefix)}(\d{{4}})$', re.IGNORECASE)
    nums = [int(m.group(1)) for s in seriales if (m := patron.match(s))]
    return max(nums) if nums else 0


def main():
    parser = argparse.ArgumentParser(description='Generar seriales de reserva')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar seriales sin insertar')
    args = parser.parse_args()

    tipos = get_tipos()
    tipos_por_prefijo = {}
    for t in tipos:
        prefijo = (t.get('serial_prefix') or '').upper().strip()
        if prefijo in PREFIJOS:
            if prefijo not in tipos_por_prefijo:
                tipos_por_prefijo[prefijo] = []
            tipos_por_prefijo[prefijo].append(t)

    seriales = get_seriales_existentes()

    total = 0
    for prefijo in PREFIJOS:
        tipos_prefijo = tipos_por_prefijo.get(prefijo, [])
        if not tipos_prefijo:
            print(f"  {prefijo}: no se encontraron tipos con ese prefijo")
            continue

        ultimo = max_serial_por_prefijo(seriales, prefijo)
        print(f"\n{prefijo} (ultimo: {prefijo}{ultimo:04d}) - {len(tipos_prefijo)} tipo(s):")
        for t in tipos_prefijo:
            print(f"    - {t['nombre']} (id={t['id']})")

        # Usar el primer tipo encontrado para este prefijo
        tipo = tipos_prefijo[0]

        for i in range(1, CANTIDAD + 1):
            num = ultimo + i
            serial = f"{prefijo}{num:04d}"

            if args.dry_run:
                print(f"  [DRY-RUN] {serial} -> nombre=Reserva, tipo_id={tipo['id']} ({tipo['nombre']})")
                total += 1
                continue

            equipo_data = {
                'nombre': 'Reserva',
                'tipo_id': tipo['id'],
                'serial': serial,
                'estado': 'bueno',
                'disponibilidad': 'Disponible',
            }

            result = supabase_request('POST', 'equipos', '', equipo_data)

            if not isinstance(result, list) or not result:
                print(f"  ERROR al insertar {serial}: {result}")
                continue

            equipo_id = result[0]['id']
            supabase_request('POST', 'hoja_vida', '', {
                'equipo_id': equipo_id,
                'tipo': 'adquisicion',
                'titulo': 'Registro inicial',
                'descripcion': 'Serial de reserva',
                'fecha': date.today().isoformat(),
                'responsable': 'Generación de reservas',
            })

            print(f"  {serial} -> id={equipo_id}")
            total += 1

    print(f"\nTotal: {total} seriales de reserva generados" + (" (dry-run)" if args.dry_run else ""))


if __name__ == '__main__':
    main()
