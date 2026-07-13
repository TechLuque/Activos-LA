"""
Migración: renombrar seriales PT* → TC*

Reglas:
- pt0012 → tc0012 si tc0012 no existe
- pt0012 → siguiente TC disponible si tc0012 ya existe
- Los seriales TC existentes no se tocan
- dry_run=True imprime el plan sin ejecutar nada
"""

import re
import sys
from db import supabase_request

DRY_RUN = '--execute' not in sys.argv


def fetch_all_serials() -> dict[str, int]:
    """Devuelve {serial_upper: equipo_id} para todos los equipos."""
    result = supabase_request('GET', 'equipos', '?select=id,serial')
    if not isinstance(result, list):
        raise RuntimeError(f"Error al obtener equipos: {result}")
    return {row['serial'].upper(): row['id'] for row in result if row.get('serial')}


def next_available_tc(taken: set[str], start: int = 1) -> str:
    n = start
    while True:
        candidate = f"TC{n:04d}"
        if candidate not in taken:
            return candidate
        n += 1


def build_plan(serial_map: dict[str, int]) -> list[tuple[int, str, str]]:
    """Retorna lista de (equipo_id, serial_actual, serial_nuevo)."""
    pt_entries = {s: eid for s, eid in serial_map.items() if s.startswith('PT')}
    taken = set(serial_map.keys())
    plan = []

    for serial, eid in sorted(pt_entries.items()):
        num_match = re.search(r'\d+', serial[2:])  # extrae número después de PT
        if num_match:
            same_num = f"TC{num_match.group().zfill(4)}"
        else:
            same_num = None

        if same_num and same_num not in taken:
            new_serial = same_num
        else:
            # busca desde 1 el primer TC libre
            new_serial = next_available_tc(taken)

        plan.append((eid, serial, new_serial))
        taken.add(new_serial)  # reservar para siguientes iteraciones

    return plan


def run():
    print("=== Migracion PT -> TC ===")
    print(f"Modo: {'DRY RUN (solo lectura)' if DRY_RUN else 'EJECUCION REAL'}\n")

    serial_map = fetch_all_serials()
    plan = build_plan(serial_map)

    if not plan:
        print("No se encontraron seriales con prefijo PT. Nada que hacer.")
        return

    print(f"{'EQUIPO_ID':<12} {'SERIAL ACTUAL':<14} {'SERIAL NUEVO':<14} {'ESTADO'}")
    print("-" * 58)

    errors = []
    for eid, old, new in plan:
        if DRY_RUN:
            print(f"{eid:<12} {old:<14} {new:<14} [pendiente]")
        else:
            result = supabase_request('PATCH', 'equipos', f'?id=eq.{eid}', {'serial': new})
            if isinstance(result, list) or (isinstance(result, dict) and 'error' not in result):
                print(f"{eid:<12} {old:<14} {new:<14} OK")
            else:
                print(f"{eid:<12} {old:<14} {new:<14} ERROR: {result}")
                errors.append((eid, old, new, result))

    print(f"\nTotal: {len(plan)} seriales a renombrar.")
    if not DRY_RUN:
        if errors:
            print(f"ERRORES: {len(errors)}")
        else:
            print("Migración completada sin errores.")
    else:
        print("\nPara ejecutar: python migrate_pt_to_tc.py --execute")


if __name__ == '__main__':
    run()
