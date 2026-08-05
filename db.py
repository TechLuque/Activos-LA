import os
import time
import requests
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"
SUPABASE_STORAGE_BUCKET = 'prestamos'

# service_role key para DB — bypasses RLS; la anon key queda bloqueada si RLS está activo
_DB_KEY = SUPABASE_SECRET_KEY or SUPABASE_KEY
HEADERS = {
    'apikey': _DB_KEY,
    'Authorization': f'Bearer {_DB_KEY}',
    'Content-Type': 'application/json'
}

# Persistent session — reutiliza conexiones TCP/TLS entre requests
_session = requests.Session()
_session.headers.update(HEADERS)
_session.mount('https://', HTTPAdapter(pool_connections=10, pool_maxsize=30))

# ── Caché en memoria ──────────────────────────────────────────────────────────

_cache: dict = {}
_cache_ttl: dict = {}
CACHE_TTL_SECONDS = 300  # 5 minutos


def cache_get(key):
    if key in _cache and time.time() < _cache_ttl.get(key, 0):
        return _cache[key]
    return None


def cache_set(key, value):
    _cache[key] = value
    _cache_ttl[key] = time.time() + CACHE_TTL_SECONDS


def cache_invalidate(key):
    _cache.pop(key, None)
    _cache_ttl.pop(key, None)


def get_tipos_map() -> dict:
    """Devuelve {id: nombre} de tipos_equipos con caché de 5 min."""
    cached = cache_get('tipos_equipos')
    if cached is not None:
        return cached
    tipos = supabase_request('GET', 'tipos_equipos')
    result = {t['id']: t['nombre'] for t in tipos} if isinstance(tipos, list) else {}
    cache_set('tipos_equipos', result)
    return result


# ── Cliente Supabase ──────────────────────────────────────────────────────────

def _parse_error(resp) -> dict:
    """Normaliza un error de PostgREST a {'error', 'code', 'status'}.

    `code` es el SQLSTATE de Postgres (p.ej. 23503 = foreign key violation),
    necesario para distinguir "no se puede borrar por dependencias" de un fallo real.
    """
    payload = {'error': (resp.text or '').strip() or f'HTTP {resp.status_code}', 'status': resp.status_code}
    try:
        body = resp.json()
    except Exception:
        return payload
    if isinstance(body, dict):
        payload['error'] = body.get('message') or body.get('msg') or payload['error']
        for key in ('code', 'details', 'hint'):
            if body.get(key):
                payload[key] = body[key]
    return payload


def supabase_request(method: str, table: str, query: str = '', data=None):
    """Ejecuta una request a la Supabase REST API usando session persistente.

    Éxito → cuerpo JSON (list/dict) o {'ok': True} si la respuesta no tiene cuerpo
    (204/205, que es lo que PostgREST devuelve en PATCH y DELETE).
    Error  → {'error': str, 'status': int, 'code': str|None}.
    """
    url = f"{SUPABASE_API_URL}/{table}{query}"
    kwargs: dict = {'timeout': 10}
    if method in ('POST', 'PATCH'):
        # PATCH devuelve la fila actualizada: evita un GET extra para refrescar
        # y permite detectar un update que no afectó a ninguna fila.
        kwargs['headers'] = {'Prefer': 'return=representation'}
    if data is not None:
        kwargs['json'] = data
    # Solo reintentamos GET: repetir un POST/PATCH/DELETE cuya respuesta se perdió
    # puede duplicar o repetir la escritura.
    attempts = 2 if method == 'GET' else 1
    for attempt in range(attempts):
        try:
            resp = _session.request(method, url, **kwargs)
            if 200 <= resp.status_code < 300:
                if resp.status_code in (204, 205) or not resp.content:
                    return {'ok': True}
                try:
                    return resp.json()
                except Exception:
                    return {'ok': True}
            if attempt + 1 < attempts and resp.status_code >= 500:
                time.sleep(0.1)
                continue
            return _parse_error(resp)
        except Exception as e:
            if attempt + 1 < attempts:
                time.sleep(0.1)
                continue
            return {'error': str(e), 'status': 0}


def supabase_storage_upload(file_content, file_path: str):
    """Sube un archivo al bucket de Storage y devuelve la URL pública."""
    try:
        if not isinstance(file_content, bytes):
            file_content = bytes(file_content)
        if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SECRET_KEY:
            return None
        storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{file_path}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_SECRET_KEY}',
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/octet-stream'
        }
        resp = requests.post(storage_url, headers=headers, data=file_content, timeout=10)
        if resp.status_code in [200, 201]:
            return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{file_path}"
        return None
    except Exception:
        return None


def supabase_storage_download(file_path: str) -> bytes | None:
    """Descarga un archivo del bucket de Storage. Acepta path relativo o URL pública completa."""
    try:
        url = file_path if file_path.startswith('http') else \
            f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{file_path}"
        resp = requests.get(url, timeout=10)
        return resp.content if resp.status_code == 200 else None
    except Exception:
        return None


def supabase_storage_delete(file_path: str) -> bool:
    """Elimina un archivo del bucket de Storage. Retorna True si fue exitoso."""
    try:
        if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
            return False
        delete_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_SECRET_KEY}',
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/json'
        }
        resp = requests.delete(delete_url, headers=headers, json={'prefixes': [file_path]}, timeout=10)
        return resp.status_code in [200, 201]
    except Exception:
        return False
