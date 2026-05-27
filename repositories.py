"""
Capa de acceso a datos.
Cada función encapsula una o más queries a Supabase.
Las rutas Flask deben llamar estas funciones en lugar de supabase_request directamente.
"""

from db import supabase_request, get_tipos_map, cache_invalidate


# ── Tipos de equipos ──────────────────────────────────────────────────────────

def get_all_tipos_equipos() -> list:
    result = supabase_request('GET', 'tipos_equipos', '?order=nombre.asc')
    return result if isinstance(result, list) else []


def create_tipo_equipo(nombre: str, descripcion: str = '', serial_prefix: str | None = None) -> dict:
    data: dict = {'nombre': nombre, 'descripcion': descripcion}
    if serial_prefix:
        data['serial_prefix'] = serial_prefix.upper()
    return supabase_request('POST', 'tipos_equipos', '', data)


def update_tipo_equipo(tipo_id: int, nombre: str, descripcion: str = '', serial_prefix: str | None = None) -> dict:
    data: dict = {'nombre': nombre, 'descripcion': descripcion, 'serial_prefix': serial_prefix.upper() if serial_prefix else None}
    return supabase_request('PATCH', 'tipos_equipos', f'?id=eq.{tipo_id}', data)


def delete_tipo_equipo(tipo_id: int):
    return supabase_request('DELETE', 'tipos_equipos', f'?id=eq.{tipo_id}')


def get_tipo_equipo(tipo_id: int) -> dict | None:
    result = supabase_request('GET', 'tipos_equipos', f'?id=eq.{tipo_id}')
    return result[0] if isinstance(result, list) and result else None


# ── Equipos ───────────────────────────────────────────────────────────────────

def get_all_equipos() -> list:
    """Lista completa de equipos con tipo_nombre resuelto."""
    result = supabase_request('GET', 'equipos', '?order=nombre.asc')
    if not isinstance(result, list):
        return []
    tipos_map = get_tipos_map()
    for eq in result:
        eq['tipo_nombre'] = tipos_map.get(eq.get('tipo_id'), eq.get('tipo', 'Sin tipo'))
    return result


def get_equipo(equipo_id: int) -> dict | None:
    result = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
    return result[0] if isinstance(result, list) and result else None


def create_equipo(data: dict) -> dict:
    return supabase_request('POST', 'equipos', '', data)


def update_equipo(equipo_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'equipos', f'?id=eq.{equipo_id}', data)


def delete_equipo(equipo_id: int):
    return supabase_request('DELETE', 'equipos', f'?id=eq.{equipo_id}')


# ── Usuarios ──────────────────────────────────────────────────────────────────

def get_all_usuarios() -> list:
    result = supabase_request('GET', 'usuarios', '?order=nombre.asc')
    return result if isinstance(result, list) else []


def get_usuario(usuario_id: int) -> dict | None:
    result = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
    return result[0] if isinstance(result, list) and result else None


def get_usuario_by_email(email: str) -> dict | None:
    result = supabase_request('GET', 'usuarios', f'?email=eq.{email}')
    return result[0] if isinstance(result, list) and result else None


def create_usuario(data: dict) -> dict:
    return supabase_request('POST', 'usuarios', '', data)


def update_usuario(usuario_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'usuarios', f'?id=eq.{usuario_id}', data)


def delete_usuario(usuario_id: int):
    return supabase_request('DELETE', 'usuarios', f'?id=eq.{usuario_id}')


# ── Préstamos ─────────────────────────────────────────────────────────────────

def get_all_prestamos() -> list:
    """Lista de préstamos con equipo_nombre, equipo_tipo, usuario_nombre resueltos."""
    prestamos = supabase_request('GET', 'prestamos', '?order=creado_en.desc')
    if not isinstance(prestamos, list):
        return []

    tipos_map = get_tipos_map()
    equipos_data = supabase_request('GET', 'equipos')
    usuarios_data = supabase_request('GET', 'usuarios')

    equipos_map = {eq['id']: eq for eq in equipos_data} if isinstance(equipos_data, list) else {}
    usuarios_map = {u['id']: u for u in usuarios_data} if isinstance(usuarios_data, list) else {}

    for loan in prestamos:
        eq = equipos_map.get(loan.get('equipo_id'), {})
        loan['equipo_nombre'] = eq.get('nombre', 'Equipo desconocido')
        loan['equipo_tipo'] = tipos_map.get(eq.get('tipo_id'), 'Desconocido')

        usr = usuarios_map.get(loan.get('usuario_id'), {})
        loan['usuario_nombre'] = usr.get('nombre', 'Usuario desconocido')
        loan['departamento'] = usr.get('departamento', '')

    return prestamos


def get_prestamo(prestamo_id: int) -> dict | None:
    """Préstamo individual con datos de equipo y usuario enriquecidos."""
    prestamos = supabase_request('GET', 'prestamos', f'?id=eq.{prestamo_id}')
    if not isinstance(prestamos, list) or not prestamos:
        return None
    loan = prestamos[0]

    equipo_id = loan.get('equipo_id')
    equipos_raw = None
    if equipo_id:
        equipos_raw = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
        if isinstance(equipos_raw, list) and equipos_raw:
            eq = equipos_raw[0]
            loan['equipo_nombre'] = eq.get('nombre', 'Equipo desconocido')
            loan['equipo_codigo'] = eq.get('serial', 'N/A')
            loan['equipo_tipo'] = eq.get('tipo', 'N/A')
            loan['equipo_serialno'] = eq.get('serialno', 'N/A')
        else:
            loan['equipo_nombre'] = 'Equipo desconocido'
            loan['equipo_codigo'] = 'N/A'
    else:
        loan['equipo_nombre'] = 'Sin equipo'
        loan['equipo_codigo'] = 'N/A'

    usuario_id = loan.get('usuario_id')
    if usuario_id:
        usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
        if isinstance(usuarios, list) and usuarios:
            usr = usuarios[0]
            loan['usuario_nombre'] = usr.get('nombre', 'Usuario desconocido')
            loan['usuario_email'] = usr.get('email', '')
            loan['usuario_telefono'] = usr.get('telefono', '')
        else:
            loan['usuario_nombre'] = 'Usuario desconocido'
    else:
        loan['usuario_nombre'] = 'Sin responsable'

    # Combinar notas del préstamo con notas del equipo
    notas_parts = []
    if loan.get('notas'):
        notas_parts.append(f"📝 Observaciones del préstamo:\n{loan['notas']}")
    if equipo_id and isinstance(equipos_raw, list) and equipos_raw:
        desc_equipo = equipos_raw[0].get('descripcion') or equipos_raw[0].get('notas')
        if desc_equipo:
            notas_parts.append(f"💻 Notas del equipo:\n{desc_equipo}")
    loan['notas'] = '\n\n'.join(notas_parts) if notas_parts else 'Sin observaciones'

    return loan


def create_prestamo(data: dict) -> dict:
    return supabase_request('POST', 'prestamos', '', data)


def update_prestamo(prestamo_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'prestamos', f'?id=eq.{prestamo_id}', data)


def delete_prestamo(prestamo_id: int):
    return supabase_request('DELETE', 'prestamos', f'?id=eq.{prestamo_id}')


# ── Mantenimientos ────────────────────────────────────────────────────────────

def get_all_mantenimientos() -> list:
    """Lista de mantenimientos con equipo_nombre y equipo_tipo resueltos."""
    mants = supabase_request('GET', 'mantenimientos', '?order=fecha.desc')
    if not isinstance(mants, list):
        return []

    equipos = supabase_request('GET', 'equipos')
    tipos_map = get_tipos_map()

    eq_map = {}
    if isinstance(equipos, list):
        for eq in equipos:
            eq_map[eq['id']] = {'nombre': eq.get('nombre'), 'tipo_id': eq.get('tipo_id')}

    for m in mants:
        eq_id = m.get('equipo_id')
        eq_data = eq_map.get(eq_id, {})
        m['equipo_nombre'] = eq_data.get('nombre', 'Equipo desconocido')
        m['equipo_tipo'] = tipos_map.get(eq_data.get('tipo_id'), 'Desconocido')

    return mants


def get_mantenimientos_by_equipo(equipo_id: int) -> list:
    result = supabase_request('GET', 'mantenimientos', f'?equipo_id=eq.{equipo_id}&order=fecha.desc')
    if not isinstance(result, list):
        return []

    eq = get_equipo(equipo_id)
    tipos_map = get_tipos_map()
    eq_nombre = eq.get('nombre', 'Equipo desconocido') if eq else 'Equipo desconocido'
    eq_tipo = tipos_map.get(eq.get('tipo_id'), 'Desconocido') if eq else 'Desconocido'

    for m in result:
        m['equipo_nombre'] = eq_nombre
        m['equipo_tipo'] = eq_tipo

    return result


def create_mantenimiento(data: dict) -> dict:
    return supabase_request('POST', 'mantenimientos', '', data)


def update_mantenimiento(mant_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'mantenimientos', f'?id=eq.{mant_id}', data)


def delete_mantenimiento(mant_id: int):
    return supabase_request('DELETE', 'mantenimientos', f'?id=eq.{mant_id}')


def get_mantenimiento(mant_id: int) -> dict | None:
    result = supabase_request('GET', 'mantenimientos', f'?id=eq.{mant_id}')
    return result[0] if isinstance(result, list) and result else None


# ── Roles ─────────────────────────────────────────────────────────────────────

def get_all_roles() -> list:
    from db import cache_get, cache_set
    cached = cache_get('roles_empresa')
    if cached is not None:
        return cached
    result = supabase_request('GET', 'roles_empresa', '?order=nombre.asc')
    data = result if isinstance(result, list) else []
    cache_set('roles_empresa', data)
    return data


def get_rol(rol_id: int) -> dict | None:
    result = supabase_request('GET', 'roles_empresa', f'?id=eq.{rol_id}')
    return result[0] if isinstance(result, list) and result else None


# ── Asignaciones de equipos ───────────────────────────────────────────────────

def get_all_asignaciones() -> list:
    """Lista de asignaciones con datos de equipo y usuario embebidos."""
    result = supabase_request('GET', 'asignaciones_equipos', '?order=fecha_asignacion.desc')
    if not isinstance(result, list):
        return []

    equipos_data = supabase_request('GET', 'equipos')
    usuarios_data = supabase_request('GET', 'usuarios')

    eq_map = {e['id']: e for e in equipos_data} if isinstance(equipos_data, list) else {}
    usr_map = {u['id']: u for u in usuarios_data} if isinstance(usuarios_data, list) else {}

    for asig in result:
        asig['equipo'] = eq_map.get(asig.get('equipo_id'), {})
        asig['usuario'] = usr_map.get(asig.get('usuario_id'), {})

    return result


def get_asignacion(asig_id: int) -> dict | None:
    result = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{asig_id}')
    if not isinstance(result, list) or not result:
        return None
    asig = result[0]
    eq = supabase_request('GET', 'equipos', f'?id=eq.{asig.get("equipo_id")}')
    usr = supabase_request('GET', 'usuarios', f'?id=eq.{asig.get("usuario_id")}')
    asig['equipo'] = eq[0] if isinstance(eq, list) and eq else {}
    asig['usuario'] = usr[0] if isinstance(usr, list) and usr else {}
    return asig


# ── Usuarios (extras) ─────────────────────────────────────────────────────────

def get_usuario_by_nombre_ilike(nombre: str) -> dict | None:
    result = supabase_request('GET', 'usuarios', f'?nombre=ilike.{nombre}')
    return result[0] if isinstance(result, list) and result else None


# ── Roles (writes) ────────────────────────────────────────────────────────────

def get_rol_by_nombre(nombre: str) -> dict | None:
    result = supabase_request('GET', 'roles_empresa', f'?nombre=eq.{nombre}')
    return result[0] if isinstance(result, list) and result else None


def create_rol(data: dict) -> dict:
    result = supabase_request('POST', 'roles_empresa', '', data)
    cache_invalidate('roles_empresa')
    return result


def update_rol(rol_id: int, data: dict) -> dict:
    result = supabase_request('PATCH', 'roles_empresa', f'?id=eq.{rol_id}', data)
    cache_invalidate('roles_empresa')
    return result


def delete_rol(rol_id: int):
    supabase_request('DELETE', 'roles_empresa', f'?id=eq.{rol_id}')
    cache_invalidate('roles_empresa')


# ── Tipos de equipos (extras) ─────────────────────────────────────────────────

def get_tipo_by_nombre(nombre: str) -> dict | None:
    result = supabase_request('GET', 'tipos_equipos', f'?nombre=eq.{nombre}')
    return result[0] if isinstance(result, list) and result else None


# ── Hoja de vida ──────────────────────────────────────────────────────────────

def get_hoja_vida_by_equipo(equipo_id: int) -> list:
    result = supabase_request('GET', 'hoja_vida', f'?equipo_id=eq.{equipo_id}&order=fecha.desc,id.desc')
    return result if isinstance(result, list) else []


def create_hoja_vida(data: dict) -> dict:
    return supabase_request('POST', 'hoja_vida', '', data)


def delete_hoja_vida(hv_id: int):
    supabase_request('DELETE', 'hoja_vida', f'?id=eq.{hv_id}')


# ── Préstamos (extras) ────────────────────────────────────────────────────────

def get_prestamos_raw() -> list:
    """Préstamos sin enriquecer — útil para dashboard y calendario."""
    result = supabase_request('GET', 'prestamos')
    return result if isinstance(result, list) else []


def get_prestamos_activos_by_equipo(equipo_id: int, exclude_id: int = None) -> list:
    query = f'?equipo_id=eq.{equipo_id}&estado=neq.devuelto'
    if exclude_id is not None:
        query += f'&id=neq.{exclude_id}'
    result = supabase_request('GET', 'prestamos', query)
    return result if isinstance(result, list) else []


# ── Mantenimientos (extras) ───────────────────────────────────────────────────

def get_mantenimientos_raw() -> list:
    """Mantenimientos sin enriquecer — útil para dashboard y calendario."""
    result = supabase_request('GET', 'mantenimientos')
    return result if isinstance(result, list) else []


def get_mantenimientos_proxima_revision() -> list:
    result = supabase_request('GET', 'mantenimientos', '?order=proxima_revision.asc')
    return result if isinstance(result, list) else []


# ── Licencias ─────────────────────────────────────────────────────────────────

def get_all_licencias() -> list:
    result = supabase_request('GET', 'licencias', '?order=fecha_caducidad.asc')
    return result if isinstance(result, list) else []


def get_licencia(licencia_id: int) -> dict | None:
    result = supabase_request('GET', 'licencias', f'?id=eq.{licencia_id}')
    return result[0] if isinstance(result, list) and result else None


def create_licencia(data: dict) -> dict:
    return supabase_request('POST', 'licencias', '', data)


def update_licencia(licencia_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'licencias', f'?id=eq.{licencia_id}', data)


def delete_licencia(licencia_id: int):
    supabase_request('DELETE', 'licencias', f'?id=eq.{licencia_id}')


# ── Equipos-Licencias ─────────────────────────────────────────────────────────

def get_licencias_by_equipo(equipo_id: int) -> list:
    """Licencias asignadas a un equipo con datos completos de la licencia."""
    items = supabase_request('GET', 'equipos_licencias', f'?equipo_id=eq.{equipo_id}&order=fecha_asignacion.desc')
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        lic = get_licencia(item.get('licencia_id'))
        if lic:
            lic['asignacion_id'] = item['id']
            lic['fecha_asignacion'] = item.get('fecha_asignacion')
            lic['notas_asignacion'] = item.get('notas', '')
            result.append(lic)
    return result


def assign_licencia_to_equipo(data: dict) -> dict:
    return supabase_request('POST', 'equipos_licencias', '', data)


def remove_licencia_from_equipo(equipo_id: int, licencia_id: int):
    supabase_request('DELETE', 'equipos_licencias', f'?equipo_id=eq.{equipo_id}&licencia_id=eq.{licencia_id}')


def delete_equipo_licencia(asignacion_id: int):
    supabase_request('DELETE', 'equipos_licencias', f'?id=eq.{asignacion_id}')


# ── Préstamos ordenados por devolución (calendario) ───────────────────────────

def get_prestamos_por_devolucion() -> list:
    result = supabase_request('GET', 'prestamos', '?order=fecha_devolucion_esperada.asc')
    return result if isinstance(result, list) else []


# ── Aplicativos ───────────────────────────────────────────────────────────────

def get_all_aplicativos() -> list:
    result = supabase_request('GET', 'aplicativos', '?order=nombre.asc')
    return result if isinstance(result, list) else []


def get_aplicativo(aplicativo_id: int) -> dict | None:
    result = supabase_request('GET', 'aplicativos', f'?id=eq.{aplicativo_id}')
    return result[0] if isinstance(result, list) and result else None


def create_aplicativo(data: dict) -> dict:
    return supabase_request('POST', 'aplicativos', '', data)


def update_aplicativo(aplicativo_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'aplicativos', f'?id=eq.{aplicativo_id}', data)


def delete_aplicativo(aplicativo_id: int):
    supabase_request('DELETE', 'aplicativos', f'?id=eq.{aplicativo_id}')


# ── Pagos de aplicativos ──────────────────────────────────────────────────────

def get_pagos_by_aplicativo(aplicativo_id: int) -> list:
    result = supabase_request('GET', 'pagos_aplicativos', f'?aplicativo_id=eq.{aplicativo_id}&order=fecha_pago.desc')
    return result if isinstance(result, list) else []


def create_pago_aplicativo(data: dict) -> dict:
    return supabase_request('POST', 'pagos_aplicativos', '', data)


def delete_pago_aplicativo(pago_id: int):
    supabase_request('DELETE', 'pagos_aplicativos', f'?id=eq.{pago_id}')


# ── Celulares ─────────────────────────────────────────────────────────────────

def get_all_celulares() -> list:
    result = supabase_request('GET', 'celulares', '?order=nombre.asc')
    return result if isinstance(result, list) else []


def get_celular(celular_id: int) -> dict | None:
    result = supabase_request('GET', 'celulares', f'?id=eq.{celular_id}')
    return result[0] if isinstance(result, list) and result else None


def create_celular(data: dict) -> dict:
    return supabase_request('POST', 'celulares', '', data)


def update_celular(celular_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'celulares', f'?id=eq.{celular_id}', data)


def delete_celular(celular_id: int):
    supabase_request('DELETE', 'celulares', f'?id=eq.{celular_id}')


# ── SIM cards ─────────────────────────────────────────────────────────────────

def get_all_simcards() -> list:
    result = supabase_request('GET', 'simcards', '?order=numero.asc')
    return result if isinstance(result, list) else []


def get_all_simcards_raw() -> list:
    result = supabase_request('GET', 'simcards', '')
    return result if isinstance(result, list) else []


def get_simcard(simcard_id: int) -> dict | None:
    result = supabase_request('GET', 'simcards', f'?id=eq.{simcard_id}')
    return result[0] if isinstance(result, list) and result else None


def get_simcard_by_numero(numero: str) -> dict | None:
    result = supabase_request('GET', 'simcards', f'?numero=eq.{numero}')
    return result[0] if isinstance(result, list) and result else None


def get_simcards_by_celular(celular_id: int) -> list:
    result = supabase_request('GET', 'simcards', f'?celular_id=eq.{celular_id}&order=numero.asc')
    return result if isinstance(result, list) else []


def get_simcard_count_by_celular(celular_id: int) -> int:
    result = supabase_request('GET', 'simcards', f'?celular_id=eq.{celular_id}')
    return len(result) if isinstance(result, list) else 0


def create_simcard(data: dict) -> dict:
    return supabase_request('POST', 'simcards', '', data)


def update_simcard(simcard_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'simcards', f'?id=eq.{simcard_id}', data)


def delete_simcard(simcard_id: int):
    supabase_request('DELETE', 'simcards', f'?id=eq.{simcard_id}')


def get_bloqueos_by_simcard(simcard_id: int) -> list:
    result = supabase_request('GET', 'historial_bloqueos_sim', f'?simcard_id=eq.{simcard_id}&order=fecha_bloqueo.desc')
    return result if isinstance(result, list) else []


def get_bloqueo(bloqueo_id: int) -> dict | None:
    result = supabase_request('GET', 'historial_bloqueos_sim', f'?id=eq.{bloqueo_id}')
    return result[0] if isinstance(result, list) and result else None


def create_bloqueo_simcard(data: dict) -> dict:
    return supabase_request('POST', 'historial_bloqueos_sim', '', data)


def update_bloqueo_simcard(bloqueo_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'historial_bloqueos_sim', f'?id=eq.{bloqueo_id}', data)


def delete_bloqueo_simcard(bloqueo_id: int):
    supabase_request('DELETE', 'historial_bloqueos_sim', f'?id=eq.{bloqueo_id}')


def get_historial_acciones_simcard(simcard_id: int) -> list:
    result = supabase_request('GET', 'historial_acciones_simcard', f'?simcard_id=eq.{simcard_id}&order=fecha_hora.desc')
    return result if isinstance(result, list) else []


def create_historial_accion_simcard(data: dict) -> dict:
    return supabase_request('POST', 'historial_acciones_simcard', '', data)


def get_historial_sims_celular(celular_id: int) -> list:
    result = supabase_request('GET', 'historial_simcards_celular', f'?celular_id=eq.{celular_id}&order=fecha_asignacion.desc')
    return result if isinstance(result, list) else []


def create_historial_sim_celular(data: dict) -> dict:
    return supabase_request('POST', 'historial_simcards_celular', '', data)


def update_historial_sim_celular_by_sim(simcard_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'historial_simcards_celular', f'?simcard_id=eq.{simcard_id}&fecha_removida=is.null', data)


# ── Asignaciones de equipos (writes) ─────────────────────────────────────────

def create_asignacion(data: dict) -> dict:
    return supabase_request('POST', 'asignaciones_equipos', '', data)


def update_asignacion(asig_id: int, data: dict) -> dict:
    return supabase_request('PATCH', 'asignaciones_equipos', f'?id=eq.{asig_id}', data)


def delete_asignacion(asig_id: int):
    supabase_request('DELETE', 'asignaciones_equipos', f'?id=eq.{asig_id}')


def get_asignaciones_activas_by_equipo(equipo_id: int) -> list:
    result = supabase_request('GET', 'asignaciones_equipos', f'?equipo_id=eq.{equipo_id}&estado=eq.abierta')
    return result if isinstance(result, list) else []


def get_asignacion_raw(asig_id: int) -> dict | None:
    """Asignación sin enriquecer — útil para operaciones internas."""
    result = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{asig_id}')
    return result[0] if isinstance(result, list) and result else None


def get_ultima_asignacion_abierta_by_equipo_usuario(equipo_id: int, usuario_id: int) -> dict | None:
    result = supabase_request('GET', 'asignaciones_equipos',
        f'?equipo_id=eq.{equipo_id}&usuario_id=eq.{usuario_id}&estado=eq.abierta&order=id.desc&limit=1')
    return result[0] if isinstance(result, list) and result else None
