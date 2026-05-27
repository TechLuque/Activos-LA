import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"
SUPABASE_STORAGE_BUCKET = 'prestamos'

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

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
    """Ejecuta una request a la Supabase REST API."""
    url = f"{SUPABASE_API_URL}/{table}{query}"
    headers = HEADERS.copy()
    if method == 'POST':
        headers['Prefer'] = 'return=representation'
    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers)
        elif method == 'POST':
            resp = requests.post(url, headers=headers, json=data)
        elif method == 'PATCH':
            resp = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers)
        else:
            return None

        if resp.status_code in [200, 201]:
            try:
                return resp.json()
            except Exception:
                return {'ok': True}
        return {'error': resp.text, 'status': resp.status_code}
    except Exception as e:
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
