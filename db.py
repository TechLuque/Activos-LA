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

def supabase_request(method: str, table: str, query: str = '', data=None):
    """Ejecuta una request a la Supabase REST API usando session persistente."""
    url = f"{SUPABASE_API_URL}/{table}{query}"
    kwargs: dict = {'timeout': 10}
    if method == 'POST':
        kwargs['headers'] = {'Prefer': 'return=representation'}
    if data is not None:
        kwargs['json'] = data
    for attempt in range(2):
        try:
            resp = _session.request(method, url, **kwargs)
            if resp.status_code in [200, 201]:
                try:
                    return resp.json()
                except Exception:
                    return {'ok': True}
            # Solo reintentar en errores de servidor transitorios (5xx), no en 4xx
            if attempt == 0 and resp.status_code >= 500:
                time.sleep(0.1)
                continue
            return {'error': resp.text, 'status': resp.status_code}
        except Exception as e:
            if attempt == 0:
                time.sleep(0.1)
                continue
            return {'error': str(e)}


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
