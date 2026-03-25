from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect, url_for
import os
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import json
import base64
from functools import wraps
from io import BytesIO

# Cargar variables de entorno
load_dotenv()

import sys
import platform

# Detectar si estamos en Vercel (read-only filesystem)
IS_VERCEL = 'VERCEL' in os.environ or os.getenv('VERCEL_ENV') == 'production'

# Debug logging function
def debug_log(msg):
    """Write debug message to console/stdout (works on Vercel)"""
    timestamp = datetime.now().isoformat()
    formatted_msg = f"[{timestamp}] {msg}"
    
    # Output to stdout (visible in Vercel logs)
    print(formatted_msg, file=sys.stdout)
    sys.stdout.flush()
    
    # Try to write to file for local development (Vercel will fail, but that's OK)
    if not IS_VERCEL:
        try:
            with open('debug.log', 'a', encoding='utf-8') as f:
                f.write(formatted_msg + "\n")
                f.flush()
        except:
            # Silently fail on read-only systems (Vercel)
            pass

# Verificar que las variables se cargaron
import dotenv
debug_log(f"\n[INIT] Current working directory: {os.getcwd()}")
debug_log(f"[INIT] load_dotenv returned: {load_dotenv()}")
debug_log(f"[INIT] SUPABASE_URL from env: {os.getenv('SUPABASE_URL')}")
debug_log(f"[INIT] SUPABASE_KEY from env: {os.getenv('SUPABASE_KEY')[:50] if os.getenv('SUPABASE_KEY') else 'NOT SET'}...")
debug_log(f"[INIT] SUPABASE_SECRET_KEY from env: {os.getenv('SUPABASE_SECRET_KEY')[:50] if os.getenv('SUPABASE_SECRET_KEY') else 'NOT SET'}...")

app = Flask(
    __name__,
    static_folder='static' if not IS_VERCEL else None,
    template_folder='templates'
)
app.secret_key = os.getenv('SECRET_KEY', 'tu-clave-secreta-super-segura-24-de-marzo-2026')

# Credenciales de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')  # Service Role Key para Storage
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"
SUPABASE_STORAGE_BUCKET = 'prestamos'  # Nombre del bucket de Storage
HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def supabase_storage_upload(file_content, file_path):
    """Upload file to Supabase Storage bucket and return public URL
    Uses Service Role Key to bypass Row-Level Security
    
    Args:
        file_content: bytes content of the file
        file_path: path within bucket (e.g., 'loan_22/firma.png')
    
    Returns:
        public_url: string URL to access the file publicly
    """
    try:
        debug_log(f"\n[STORAGE] ═════════════════════════════════════")
        debug_log(f"[STORAGE] Uploading file: {file_path}")
        debug_log(f"[STORAGE] Content size: {len(file_content)} bytes")
        
        # Ensure file_content is bytes
        if not isinstance(file_content, bytes):
            file_content = bytes(file_content)
        
        storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{file_path}"
        
        # Validate credentials are loaded
        if not SUPABASE_URL:
            debug_log(f"[ERROR] SUPABASE_URL is not set!")
            return None
        if not SUPABASE_KEY:
            debug_log(f"[ERROR] SUPABASE_KEY is not set!")
            return None
        if not SUPABASE_SECRET_KEY:
            debug_log(f"[ERROR] SUPABASE_SECRET_KEY is not set!")
            return None
        
        debug_log(f"[STORAGE] SUPABASE_URL: {SUPABASE_URL[:50]}...")
        debug_log(f"[STORAGE] SUPABASE_KEY len: {len(SUPABASE_KEY)}")
        debug_log(f"[STORAGE] SUPABASE_SECRET_KEY len: {len(SUPABASE_SECRET_KEY)}")
        
        # Headers with Authorization using Service Role Key
        headers = {
            'Authorization': f'Bearer {SUPABASE_SECRET_KEY}',
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/octet-stream'
        }
        
        debug_log(f"[STORAGE] Storage URL: {storage_url}")
        debug_log(f"[STORAGE] Making POST request...")
        
        resp = requests.post(storage_url, headers=headers, data=file_content, timeout=10)
        
        debug_log(f"[STORAGE] Response status: {resp.status_code}")
        debug_log(f"[STORAGE] Response body: {resp.text[:500]}")
        
        if resp.status_code in [200, 201]:
            # Generar URL pública
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{file_path}"
            debug_log(f"[STORAGE] SUCCESS - File uploaded: {file_path}")
            return public_url
        else:
            debug_log(f"[STORAGE] FAILED - Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        debug_log(f"[STORAGE] EXCEPTION: {e}")
        debug_log(f"[STORAGE] Exception type: {type(e).__name__}")
        import traceback
        debug_log(traceback.format_exc())
        return None

def supabase_request(method, table, query='', data=None):
    """Helper para hacer requests a Supabase REST API"""
    url = f"{SUPABASE_API_URL}/{table}{query}"
    headers = HEADERS.copy()
    
    # Para POST, agregar prefer=return=representation para que retorne los datos
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
            except:
                return {'ok': True}
        else:
            return {'error': resp.text, 'status': resp.status_code}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════
# AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════════

def require_login(f):
    """Decorador para proteger rutas - requiere login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def require_api_login(f):
    """Decorador para proteger API - requiere login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET'])
def login_page():
    """Página de login"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """Endpoint para autenticarse"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"[AUTH] Intento login - usuario: '{username}', password: '{password}'")
        
        if not username or not password:
            print(f"[AUTH] Error: campos vacíos")
            return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
        
        # Buscar usuario en BD por email (primero)
        print(f"[AUTH] Buscando por email: {username}")
        usuarios = supabase_request('GET', 'usuarios', f'?email=eq.{username}')
        print(f"[AUTH] Respuesta email: {type(usuarios)} - {str(usuarios)[:100]}")
        
        if not isinstance(usuarios, list) or len(usuarios) == 0:
            # Si no existe por email, buscar por nombre (case-insensitive)
            # Supabase soporta ilike para case-insensitive
            print(f"[AUTH] No encontrado por email, buscando por nombre: {username}")
            usuarios = supabase_request('GET', 'usuarios', f'?nombre=ilike.{username}')
            print(f"[AUTH] Respuesta nombre: {type(usuarios)} - {str(usuarios)[:100]}")
        
        if not isinstance(usuarios, list) or len(usuarios) == 0:
            print(f"[AUTH] Usuario no encontrado")
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
        
        user = usuarios[0]
        print(f"[AUTH] Usuario encontrado: {user.get('nombre')} (ID: {user.get('id')})")
        print(f"[AUTH] Password: '{user.get('password')}' vs '{password}'")
        print(f"[AUTH] Estado: {user.get('estado')}")
        
        # Verificar contraseña
        if user.get('password') != password:
            print(f"[AUTH] Contraseña incorrecta")
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
        
        # Verificar que el usuario esté activo
        if user.get('estado') != 'activo':
            print(f"[AUTH] Usuario no está activo")
            return jsonify({'error': 'Usuario inactivo'}), 403
        
        # Crear sesión
        session['user_id'] = user.get('id')
        session['username'] = user.get('nombre')
        session['email'] = user.get('email')
        
        print(f"[AUTH] ✅ Usuario {user.get('nombre')} (ID: {user.get('id')}) autenticado exitosamente")
        
        return jsonify({
            'ok': True,
            'message': 'Autenticado correctamente',
            'user': {
                'id': user.get('id'),
                'nombre': user.get('nombre'),
                'email': user.get('email')
            }
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Error en login: {str(e)}")
        return jsonify({'error': f'Error al autenticar: {str(e)}'}), 500

@app.route('/logout', methods=['GET'])
def logout():
    """Cerrar sesión"""
    username = session.get('username', 'Usuario')
    session.clear()
    print(f"[AUTH] {username} cerró sesión")
    return redirect(url_for('login_page'))

@app.route('/api/user', methods=['GET'])
@require_api_login
def get_current_user():
    """Obtener información del usuario actual desde la sesión"""
    return jsonify({
        'id': session.get('user_id'),
        'nombre': session.get('username'),
        'email': session.get('email')
    }), 200

@app.route('/firma/<int:id>')
def firma_page(id):
    """Página de firma digital - PÚBLICA (sin login requerido)"""
    return render_template('firma.html')

@app.route('/')
@require_login
def index():
    """Página principal - requiere login"""
    return render_template('index.html')

@app.route('/api/dashboard')
@require_api_login
def dashboard():
    try:
        today = date.today().isoformat()
        in7 = (date.today() + timedelta(days=7)).isoformat()
        
        # Total equipos
        equipos = supabase_request('GET', 'equipos')
        total_equipos = len(equipos) if isinstance(equipos, list) else 0
        
        # Total usuarios activos
        usuarios = supabase_request('GET', 'usuarios', '?estado=eq.activo')
        total_usuarios = len(usuarios) if isinstance(usuarios, list) else 0
        
        # Préstamos activos
        prestamos_act = supabase_request('GET', 'prestamos', '?estado=eq.activo')
        prestamos_activos = len(prestamos_act) if isinstance(prestamos_act, list) else 0
        
        # Mantenimientos en proceso
        mant_proc = supabase_request('GET', 'mantenimientos', '?estado=eq.en_proceso')
        mant_en_proceso = len(mant_proc) if isinstance(mant_proc, list) else 0
        
        # Estados de equipos
        equipos_data = supabase_request('GET', 'equipos')
        estados = {}
        if isinstance(equipos_data, list):
            for eq in equipos_data:
                estado = eq.get('estado', 'desconocido')
                estados[estado] = estados.get(estado, 0) + 1
        
        # Tipos de equipos
        tipos_count = {}
        if isinstance(equipos_data, list):
            for eq in equipos_data:
                # Usar tipo_nombre si existe, si no usar tipo
                tipo = eq.get('tipo_nombre') or eq.get('tipo', 'Sin tipo')
                tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
        tipos_equipos = [{'tipo_nombre': k, 'tipo': k, 'count': v} for k, v in sorted(tipos_count.items(), key=lambda x: x[1], reverse=True)[:7]]
        
        # Valor total
        valor_total = 0
        if isinstance(equipos_data, list):
            valor_total = sum(int(eq.get('valor', 0) or 0) for eq in equipos_data)
        
        # Préstamos vencidos
        todos_prestamos = supabase_request('GET', 'prestamos')
        prestamos_vencidos = []
        proximos_vencer = []
        if isinstance(todos_prestamos, list):
            for p in todos_prestamos:
                if p.get('estado') == 'activo' and p.get('fecha_devolucion_esperada'):
                    fecha_dev = p['fecha_devolucion_esperada']
                    if fecha_dev < today:
                        prestamos_vencidos.append(p)
                    elif fecha_dev <= in7:
                        proximos_vencer.append(p)
        
        # Mantenimientos vencidos
        todos_mants = supabase_request('GET', 'mantenimientos')
        preventivos_vencidos = 0
        if isinstance(todos_mants, list):
            for m in todos_mants:
                if m.get('tipo') == 'preventivo' and m.get('proxima_revision') and m.get('proxima_revision') < today:
                    preventivos_vencidos += 1
        
        return jsonify({
            'total_equipos': total_equipos,
            'total_usuarios': total_usuarios,
            'prestamos_activos': prestamos_activos,
            'mant_en_proceso': mant_en_proceso,
            'estados': estados,
            'tipos_equipos': tipos_equipos,
            'preventivos_vencidos': preventivos_vencidos,
            'valor_total': valor_total,
            'proximos_vencer': proximos_vencer,
            'prestamos_vencidos': prestamos_vencidos,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== USUARIOS ==========
@app.route('/api/usuarios', methods=['GET'])
@require_api_login
def get_usuarios():
    try:
        result = supabase_request('GET', 'usuarios', '?order=nombre.asc')
        if isinstance(result, list):
            return jsonify(result)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios', methods=['POST'])
def create_usuario():
    try:
        d = request.json
        
        # Departamentos permitidos
        DEPARTAMENTOS_VALIDOS = ['Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia']
        
        # Validaciones
        if not d.get('departamento') or d.get('departamento') not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400
        
        # Resolver rol_id
        rol_id = d.get('rol_id', None)
        if not rol_id and d.get('rol_nombre'):
            # Buscar rol por nombre
            roles_result = supabase_request('GET', 'roles_empresa', f'?nombre=eq.{d["rol_nombre"]}')
            if isinstance(roles_result, list) and len(roles_result) > 0:
                rol_id = roles_result[0]['id']
        
        if not rol_id:
            return jsonify({'error': 'Rol es requerido'}), 400
        
        usuario_data = {
            'nombre': d['nombre'],
            'email': d['email'],
            'departamento': d.get('departamento', ''),
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo'),
            'rol_id': rol_id
        }
        
        result = supabase_request('POST', 'usuarios', '', usuario_data)
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'email' in str(e).lower():
            return jsonify({'error': 'El email ya existe'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<int:id>', methods=['PUT'])
def update_usuario(id):
    try:
        d = request.json
        
        # Departamentos permitidos
        DEPARTAMENTOS_VALIDOS = ['Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia']
        
        # Validar departamento si fue proporcionado
        if d.get('departamento') and d.get('departamento') not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400
        
        # Resolver rol_id
        rol_id = d.get('rol_id', None)
        if not rol_id and d.get('rol_nombre'):
            # Buscar rol por nombre
            roles_result = supabase_request('GET', 'roles_empresa', f'?nombre=eq.{d["rol_nombre"]}')
            if isinstance(roles_result, list) and len(roles_result) > 0:
                rol_id = roles_result[0]['id']
        
        update_data = {
            'nombre': d['nombre'],
            'email': d['email'],
            'departamento': d.get('departamento', ''),
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo')
        }
        
        # Solo actualizar rol_id si fue proporcionado
        if rol_id:
            update_data['rol_id'] = rol_id
        
        result = supabase_request('PATCH', 'usuarios', f'?id=eq.{id}', update_data)
        return jsonify(result if isinstance(result, dict) else (result[0] if result else {}))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
def delete_usuario(id):
    try:
        supabase_request('DELETE', 'usuarios', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Tipos de equipos ahora se cargan desde BD (tipos_equipos)
# Ver endpoints /api/tipos-equipos para CRUD

@app.route('/api/equipos', methods=['GET'])
def get_equipos():
    try:
        result = supabase_request('GET', 'equipos', '?order=nombre.asc')
        if isinstance(result, list):
            # Obtener todos los tipos para mapearlos
            tipos_result = supabase_request('GET', 'tipos_equipos')
            tipos_map = {t['id']: t['nombre'] for t in tipos_result} if isinstance(tipos_result, list) else {}
            
            # Agregar tipo_nombre a cada equipo
            for eq in result:
                eq['tipo_nombre'] = tipos_map.get(eq.get('tipo_id'), eq.get('tipo', 'Sin tipo'))
            
            return jsonify(result)
        return jsonify([])
    except Exception as e:
        debug_log(f"[ERROR] Error getting equipos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tipos-equipos', methods=['GET'])
def get_tipos_equipos():
    """Obtener lista de tipos de equipos desde BD"""
    try:
        result = supabase_request('GET', 'tipos_equipos', '?order=nombre.asc')
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        debug_log(f"[ERROR] Error getting tipos_equipos: {e}")
        return jsonify([]), 200

@app.route('/api/tipos-equipos', methods=['POST'])
def create_tipo_equipo():
    """Crear nuevo tipo de equipo"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        result = supabase_request('POST', 'tipos_equipos', '', {
            'nombre': nombre,
            'descripcion': descripcion
        })
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': 'Este tipo de equipo ya existe'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/tipos-equipos/<int:id>', methods=['PUT'])
def update_tipo_equipo(id):
    """Actualizar tipo de equipo"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        result = supabase_request('PATCH', 'tipos_equipos', f'?id=eq.{id}', {
            'nombre': nombre,
            'descripcion': descripcion
        })
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 200
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tipos-equipos/<int:id>', methods=['DELETE'])
def delete_tipo_equipo(id):
    """Eliminar tipo de equipo"""
    try:
        supabase_request('DELETE', 'tipos_equipos', f'?id=eq.{id}')
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:id>', methods=['GET'])
def get_equipo(id):
    try:
        result = supabase_request('GET', 'equipos', f'?id=eq.{id}')
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0])
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos', methods=['POST'])
def create_equipo():
    try:
        d = request.json
        tipo_nombre = d['tipo']
        
        # Buscar ID del tipo en tipos_equipos
        tipos_result = supabase_request('GET', 'tipos_equipos', f'?nombre=eq.{tipo_nombre}')
        tipo_id = None
        if isinstance(tipos_result, list) and len(tipos_result) > 0:
            tipo_id = tipos_result[0]['id']
        
        # Escribir solo tipo_id (la columna tipo no existe)
        equipo_data = {
            'nombre': d['nombre'],
            'tipo_id': tipo_id,
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'usuario_id': d.get('usuario_id', None),
            'fecha_adquisicion': d.get('fecha_adquisicion', ''),
            'valor': d.get('valor', 0),
            'descripcion': d.get('descripcion', '')
        }
        
        equipo_result = supabase_request('POST', 'equipos', '', equipo_data)
        
        if isinstance(equipo_result, list) and len(equipo_result) > 0:
            equipo_id = equipo_result[0]['id']
            # Crear entrada en hoja_vida
            supabase_request('POST', 'hoja_vida', '', {
                'equipo_id': equipo_id,
                'tipo': 'adquisicion',
                'titulo': 'Registro inicial',
                'descripcion': d.get('descripcion', 'Equipo registrado en sistema'),
                'fecha': date.today().isoformat(),
                'responsable': 'Sistema'
            })
            return jsonify(equipo_result[0]), 201
        
        return jsonify(equipo_result), 201
    except Exception as e:
        if 'serial' in str(e).lower():
            return jsonify({'error': 'El serial ya existe'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:id>', methods=['PUT'])
def update_equipo(id):
    try:
        d = request.json
        tipo_nombre = d['tipo']
        
        # Buscar ID del tipo en tipos_equipos
        tipos_result = supabase_request('GET', 'tipos_equipos', f'?nombre=eq.{tipo_nombre}')
        tipo_id = None
        if isinstance(tipos_result, list) and len(tipos_result) > 0:
            tipo_id = tipos_result[0]['id']
        
        # Actualizar solo tipo_id (la columna tipo no existe)
        update_data = {
            'nombre': d['nombre'],
            'tipo_id': tipo_id,
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'usuario_id': d.get('usuario_id', None),
            'fecha_adquisicion': d.get('fecha_adquisicion', ''),
            'valor': d.get('valor', 0),
            'descripcion': d.get('descripcion', '')
        }
        
        result = supabase_request('PATCH', 'equipos', f'?id=eq.{id}', update_data)
        return jsonify(result if isinstance(result, dict) else (result[0] if result else {}))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:id>', methods=['DELETE'])
def delete_equipo(id):
    try:
        supabase_request('DELETE', 'equipos', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== ROLES DE EMPRESA ==========
@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Obtener lista de roles"""
    try:
        result = supabase_request('GET', 'roles_empresa', '?order=nombre.asc')
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        debug_log(f"[ERROR] Error getting roles: {e}")
        return jsonify([]), 200

@app.route('/api/roles', methods=['POST'])
def create_rol():
    """Crear nuevo rol"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        departamento = data.get('departamento', '')
        
        DEPARTAMENTOS_VALIDOS = ['Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia']
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        if not departamento or departamento not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400
        
        result = supabase_request('POST', 'roles_empresa', '', {
            'nombre': nombre,
            'descripcion': descripcion,
            'departamento': departamento,
            'permisos': '[]'
        })
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': 'Este rol ya existe'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/roles/<int:id>', methods=['PUT'])
def update_rol(id):
    """Actualizar rol"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        departamento = data.get('departamento', '')
        
        DEPARTAMENTOS_VALIDOS = ['Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia']
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        if departamento and departamento not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400
        
        update_data = {
            'nombre': nombre,
            'descripcion': descripcion
        }
        
        if departamento:
            update_data['departamento'] = departamento
        
        result = supabase_request('PATCH', 'roles_empresa', f'?id=eq.{id}', update_data)
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 200
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/roles/<int:id>', methods=['DELETE'])
def delete_rol(id):
    """Eliminar rol"""
    try:
        supabase_request('DELETE', 'roles_empresa', f'?id=eq.{id}')
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== MANTENIMIENTOS ==========
@app.route('/api/mantenimientos', methods=['GET'])
def get_all_mantenimientos():
    try:
        mants = supabase_request('GET', 'mantenimientos', '?order=fecha.desc')
        
        if isinstance(mants, list):
            # Fetch equipos and tipos to resolve names
            equipos = supabase_request('GET', 'equipos')
            tipos = supabase_request('GET', 'tipos_equipos')
            
            # Build maps
            eq_map = {}
            if isinstance(equipos, list):
                for eq in equipos:
                    eq_map[eq['id']] = {'nombre': eq.get('nombre'), 'tipo_id': eq.get('tipo_id')}
            
            tipos_map = {}
            if isinstance(tipos, list):
                for tipo in tipos:
                    tipos_map[tipo['id']] = tipo.get('nombre')
            
            # Enrich mantenimientos with resolved names
            for m in mants:
                eq_id = m.get('equipo_id')
                if eq_id in eq_map:
                    m['equipo_nombre'] = eq_map[eq_id].get('nombre', 'Equipo desconocido')
                    tipo_id = eq_map[eq_id].get('tipo_id')
                    m['equipo_tipo'] = tipos_map.get(tipo_id, 'Desconocido')
                else:
                    m['equipo_nombre'] = 'Equipo desconocido'
                    m['equipo_tipo'] = 'Desconocido'
            
            return jsonify(mants)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:id>/mantenimientos', methods=['GET'])
def get_mants_equipo(id):
    try:
        result = supabase_request('GET', 'mantenimientos', f'?equipo_id=eq.{id}&order=fecha.desc')
        if isinstance(result, list):
            # Fetch equipo and tipos to resolve names
            eq = supabase_request('GET', 'equipos', f'?id=eq.{id}')
            tipos = supabase_request('GET', 'tipos_equipos')
            
            eq_nombre = 'Equipo desconocido'
            eq_tipo = 'Desconocido'
            
            if isinstance(eq, list) and len(eq) > 0:
                eq_nombre = eq[0].get('nombre', 'Equipo desconocido')
                tipo_id = eq[0].get('tipo_id')
                
                if isinstance(tipos, list):
                    for tipo in tipos:
                        if tipo['id'] == tipo_id:
                            eq_tipo = tipo.get('nombre', 'Desconocido')
                            break
            
            # Enrich mantenimientos with resolved names
            for m in result:
                m['equipo_nombre'] = eq_nombre
                m['equipo_tipo'] = eq_tipo
            
            return jsonify(result)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mantenimientos', methods=['POST'])
def create_mantenimiento():
    try:
        d = request.json
        
        mant_result = supabase_request('POST', 'mantenimientos', '', {
            'equipo_id': d['equipo_id'],
            'tipo': d['tipo'],
            'descripcion': d['descripcion'],
            'fecha': d['fecha'],
            'tecnico': d.get('tecnico', ''),
            'costo': d.get('costo', 0),
            'estado': d.get('estado', 'completado'),
            'proxima_revision': d.get('proxima_revision') or None
        })
        
        # Crear entrada en hoja_vida
        supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': d['equipo_id'],
            'tipo': 'mantenimiento',
            'titulo': f"Mant. {d['tipo']}: {d['descripcion'][:60]}",
            'descripcion': d.get('descripcion', ''),
            'fecha': d['fecha'],
            'responsable': d.get('tecnico', '')
        })
        
        return jsonify({'ok': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mantenimientos/<int:id>', methods=['PUT'])
def update_mantenimiento(id):
    try:
        d = request.json
        supabase_request('PATCH', 'mantenimientos', f'?id=eq.{id}', {
            'tipo': d['tipo'],
            'descripcion': d['descripcion'],
            'fecha': d['fecha'],
            'tecnico': d.get('tecnico', ''),
            'costo': d.get('costo', 0),
            'estado': d.get('estado', 'completado'),
            'proxima_revision': d.get('proxima_revision') or None
        })
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mantenimientos/<int:id>', methods=['DELETE'])
def delete_mantenimiento(id):
    try:
        supabase_request('DELETE', 'mantenimientos', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== HOJA DE VIDA ==========
@app.route('/api/equipos/<int:id>/hoja_vida', methods=['GET'])
def get_hoja_vida(id):
    try:
        result = supabase_request('GET', 'hoja_vida', f'?equipo_id=eq.{id}&order=fecha.desc,id.desc')
        if isinstance(result, list):
            return jsonify(result)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:id>/hoja_vida', methods=['POST'])
def add_hoja_vida(id):
    try:
        d = request.json
        result = supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': id,
            'tipo': d['tipo'],
            'titulo': d['titulo'],
            'descripcion': d.get('descripcion', ''),
            'fecha': d['fecha'],
            'responsable': d.get('responsable', '')
        })
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hoja_vida/<int:id>', methods=['DELETE'])
def delete_hoja_vida(id):
    try:
        supabase_request('DELETE', 'hoja_vida', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== PRÉSTAMOS ==========
@app.route('/api/prestamos', methods=['GET'])
@require_api_login
def get_prestamos():
    try:
        prestamos = supabase_request('GET', 'prestamos', '?order=creado_en.desc')
        if isinstance(prestamos, list):
            # Fetch tipos para mapeo
            tipos = supabase_request('GET', 'tipos_equipos')
            tipos_map = {t['id']: t['nombre'] for t in tipos} if isinstance(tipos, list) else {}
            
            # Enriquecer con nombres de equipo y usuario
            for loan in prestamos:
                # Obtener nombre del equipo
                if 'equipo_id' in loan:
                    equipos = supabase_request('GET', 'equipos', f'?id=eq.{loan["equipo_id"]}')
                    if isinstance(equipos, list) and len(equipos) > 0:
                        eq = equipos[0]
                        loan['equipo_nombre'] = eq.get('nombre', 'Equipo desconocido')
                        tipo_id = eq.get('tipo_id')
                        loan['equipo_tipo'] = tipos_map.get(tipo_id, 'Desconocido')
                    else:
                        loan['equipo_nombre'] = 'Equipo desconocido'
                        loan['equipo_tipo'] = 'Desconocido'
                
                # Obtener nombre del usuario
                if 'usuario_id' in loan:
                    usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{loan["usuario_id"]}')
                    if isinstance(usuarios, list) and len(usuarios) > 0:
                        loan['usuario_nombre'] = usuarios[0].get('nombre', 'Usuario desconocido')
                        loan['departamento'] = usuarios[0].get('departamento', '')
                    else:
                        loan['usuario_nombre'] = 'Usuario desconocido'
            
            return jsonify(prestamos)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos/<int:id>', methods=['GET'])
def get_prestamo(id):
    """Get a specific loan by ID for the public signature page"""
    try:
        print(f"\n[LOAN_FETCH] Obteniendo préstamo ID {id}...")
        
        # ═══════════════════════════════════════════════════════════════
        # 1. OBTENER PRÉSTAMO
        # ═══════════════════════════════════════════════════════════════
        prestamos = supabase_request('GET', 'prestamos', f'?id=eq.{id}')
        print(f"[LOAN_FETCH] Respuesta de prestamos: {type(prestamos)} - {str(prestamos)[:200]}")
        
        if isinstance(prestamos, dict) and prestamos.get('error'):
            print(f"[ERROR] Error en query prestamos: {prestamos.get('error')}")
            return jsonify({'error': f"Error al obtener préstamo: {prestamos.get('error')}"}), 500
        
        if not isinstance(prestamos, list) or len(prestamos) == 0:
            print(f"[WARN] Préstamo ID {id} no encontrado")
            return jsonify({'error': 'Préstamo no encontrado'}), 404
        
        loan = prestamos[0]
        print(f"[LOAN_FETCH] Préstamo encontrado: {loan.get('id')} - equipo_id: {loan.get('equipo_id')} - usuario_id: {loan.get('usuario_id')}")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. OBTENER NOMBRE DEL EQUIPO
        # ═══════════════════════════════════════════════════════════════
        equipo_id = loan.get('equipo_id')
        if equipo_id:
            print(f"[LOAN_FETCH] Buscando equipo ID {equipo_id}...")
            equipos = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
            print(f"[LOAN_FETCH] Respuesta de equipos: {type(equipos)} - {str(equipos)[:200]}")
            
            if isinstance(equipos, list) and len(equipos) > 0:
                loan['equipo_nombre'] = equipos[0].get('nombre', 'Equipo desconocido')
                loan['equipo_tipo'] = equipos[0].get('tipo', 'N/A')
                loan['equipo_serialno'] = equipos[0].get('serialno', 'N/A')
                print(f"[LOAN_FETCH] ✅ Equipo encontrado: {loan['equipo_nombre']}")
            else:
                loan['equipo_nombre'] = 'Equipo desconocido'
                print(f"[WARN] Equipo no encontrado, usando default")
        else:
            loan['equipo_nombre'] = 'Sin equipo'
            print(f"[WARN] No hay equipo_id en préstamo")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. OBTENER NOMBRE DEL USUARIO
        # ═══════════════════════════════════════════════════════════════
        usuario_id = loan.get('usuario_id')
        if usuario_id:
            print(f"[LOAN_FETCH] Buscando usuario ID {usuario_id}...")
            usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
            print(f"[LOAN_FETCH] Respuesta de usuarios: {type(usuarios)} - {str(usuarios)[:200]}")
            
            if isinstance(usuarios, list) and len(usuarios) > 0:
                loan['usuario_nombre'] = usuarios[0].get('nombre', 'Usuario desconocido')
                loan['usuario_email'] = usuarios[0].get('email', '')
                loan['usuario_telefono'] = usuarios[0].get('telefono', '')
                print(f"[LOAN_FETCH] ✅ Usuario encontrado: {loan['usuario_nombre']}")
            else:
                loan['usuario_nombre'] = 'Usuario desconocido'
                print(f"[WARN] Usuario no encontrado, usando default")
        else:
            loan['usuario_nombre'] = 'Sin responsable'
            print(f"[WARN] No hay usuario_id en préstamo")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. RETORNAR RESPUESTA COMPLETA
        # ═══════════════════════════════════════════════════════════════
        print(f"[LOAN_FETCH] ✅ Respuesta final completa:")
        print(f"  - ID: {loan.get('id')}")
        print(f"  - Equipo: {loan.get('equipo_nombre')}")
        print(f"  - Usuario: {loan.get('usuario_nombre')}")
        print(f"  - Estado: {loan.get('estado')}")
        
        return jsonify(loan)
        
    except Exception as e:
        print(f"[ERROR] Exception en get_prestamo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error al obtener préstamo: {str(e)}"}), 500


@app.route('/api/prestamos/<int:id>/detalle', methods=['GET'])
def get_prestamo_detalle(id):
    """Get detailed loan information including timeline"""
    try:
        # Obtener préstamo
        prestamos = supabase_request('GET', 'prestamos', f'?id=eq.{id}')
        
        if not isinstance(prestamos, list) or len(prestamos) == 0:
            return jsonify({'error': 'Préstamo no encontrado'}), 404
        
        loan = prestamos[0]
        
        # Enriquecer con datos del equipo
        if loan.get('equipo_id'):
            equipos = supabase_request('GET', 'equipos', f'?id=eq.{loan["equipo_id"]}')
            if isinstance(equipos, list) and len(equipos) > 0:
                eq = equipos[0]
                loan['equipo'] = {
                    'id': eq.get('id'),
                    'nombre': eq.get('nombre'),
                    'tipo': eq.get('tipo'),
                    'serialno': eq.get('serialno'),
                    'valor': eq.get('valor')
                }
        
        # Enriquecer con datos del usuario
        if loan.get('usuario_id'):
            usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{loan["usuario_id"]}')
            if isinstance(usuarios, list) and len(usuarios) > 0:
                usr = usuarios[0]
                loan['usuario'] = {
                    'id': usr.get('id'),
                    'nombre': usr.get('nombre'),
                    'email': usr.get('email'),
                    'telefono': usr.get('telefono'),
                    'departamento': usr.get('departamento')
                }
        
        # Construir timeline de estados
        timeline = []
        
        # Estado: Solicitado
        if loan.get('fecha_prestamo'):
            timeline.append({
                'estado': 'solicitado',
                'fecha': loan.get('fecha_prestamo'),
                'icono': '📋',
                'titulo': 'Préstamo Solicitado',
                'completado': True
            })
        
        # Estado: Firmado
        if loan.get('fecha_firma'):
            timeline.append({
                'estado': 'firmado',
                'fecha': loan.get('fecha_firma'),
                'icono': '✍️',
                'titulo': 'Documento Firmado',
                'completado': True
            })
        elif loan.get('firma_url'):
            timeline.append({
                'estado': 'firmado',
                'fecha': 'Pendiente de firmar',
                'icono': '⏳',
                'titulo': 'Pendiente de Firma',
                'completado': False
            })
        else:
            timeline.append({
                'estado': 'firmado',
                'fecha': 'No iniciado',
                'icono': '⏳',
                'titulo': 'Pendiente de Firma',
                'completado': False
            })
        
        # Estado: Devolución esperada
        if loan.get('fecha_devolucion_esperada'):
            timeline.append({
                'estado': 'vencimiento',
                'fecha': loan.get('fecha_devolucion_esperada'),
                'icono': '📅',
                'titulo': 'Fecha Esperada de Devolución',
                'completado': loan.get('estado') == 'devuelto'
            })
        
        # Estado: Devuelto
        if loan.get('fecha_devolucion_real'):
            timeline.append({
                'estado': 'devuelto',
                'fecha': loan.get('fecha_devolucion_real'),
                'icono': '✅',
                'titulo': 'Equipo Devuelto',
                'completado': True
            })
        elif loan.get('estado') == 'devuelto':
            timeline.append({
                'estado': 'devuelto',
                'fecha': 'Completado',
                'icono': '✅',
                'titulo': 'Equipo Devuelto',
                'completado': True
            })
        else:
            timeline.append({
                'estado': 'devuelto',
                'fecha': 'Pendiente',
                'icono': '⏳',
                'titulo': 'Pendiente de Devolución',
                'completado': False
            })
        
        loan['timeline'] = timeline
        return jsonify(loan)
        
    except Exception as e:
        print(f"[ERROR] get_prestamo_detalle: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos', methods=['POST'])
@require_api_login
def create_prestamo():
    try:
        d = request.json
        
        # Verificar si el equipo ya tiene un préstamo no devuelto (solicitado, firmado o activo)
        existing = supabase_request('GET', 'prestamos', f'?equipo_id=eq.{d["equipo_id"]}&estado=ne.devuelto')
        if isinstance(existing, list) and len(existing) > 0:
            return jsonify({'error': 'El equipo ya tiene un prestamo no devuelto'}), 400
        
        result = supabase_request('POST', 'prestamos', '', {
            'equipo_id': d['equipo_id'],
            'usuario_id': d['usuario_id'],
            'fecha_prestamo': d['fecha_prestamo'],
            'fecha_devolucion_esperada': d.get('fecha_devolucion_esperada') or None,
            'estado': 'solicitado',
            'notas': d.get('notas', '')
        })
        
        # Retornar el ID del nuevo préstamo
        # Con prefer=return=representation, Supabase retorna un array con el registro creado
        if isinstance(result, list) and len(result) > 0:
            new_loan = result[0]
            return jsonify({
                'id': new_loan.get('id'),
                'ok': True
            }), 201
        elif isinstance(result, dict) and 'id' in result:
            return jsonify({
                'id': result.get('id'),
                'ok': True
            }), 201
        else:
            print(f"Unexpected result format: {result}")
            return jsonify({'error': 'Error al crear préstamo', 'result': result}), 500
            
    except Exception as e:
        print(f"Create prestamo error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos/<int:id>/firma', methods=['POST'])
def save_loan_signature(id):
    """Save signature and images for a loan to Supabase Storage - supports 'inicial' or 'devolucion'"""
    try:
        debug_log("\n" + "="*70)
        debug_log(f"[ENDPOINT] /api/prestamos/{id}/firma called")
        debug_log(f"[ENVIRONMENT] IS_VERCEL={IS_VERCEL}")
        debug_log("="*70)
        
        # Obtener archivos y parámetro de tipo
        imagen1 = request.files.get('imagen1')
        imagen2 = request.files.get('imagen2')
        firma_data = request.form.get('firma_data', '')
        tipo_firma = request.form.get('tipo', 'inicial')  # 'inicial' o 'devolucion'
        
        debug_log(f"[DEBUG] imagen1: {imagen1.filename if imagen1 else 'None'}")
        debug_log(f"[DEBUG] imagen2: {imagen2.filename if imagen2 else 'None'}")
        
        # Read files in memory only (no disk I/O)
        try:
            img1_content_test = imagen1.read() if imagen1 else b''
            if imagen1:
                imagen1.seek(0)  # Reset file pointer after reading size
            if imagen2:
                img2_content_test = imagen2.read()
                imagen2.seek(0)  # Reset file pointer
            else:
                img2_content_test = b''
        except Exception as e:
            debug_log(f"[ERROR] Error reading files from request: {e}")
            return jsonify({'error': f'Error al leer archivos: {str(e)}'}), 400
        
        debug_log(f"[DEBUG] imagen1 size: {len(img1_content_test)} bytes")
        debug_log(f"[DEBUG] imagen2 size: {len(img2_content_test)} bytes")
        debug_log(f"[DEBUG] firma_data length: {len(firma_data)}")
        debug_log(f"[DEBUG] tipo_firma: {tipo_firma}")
        debug_log(f"[DEBUG] SUPABASE_URL: {SUPABASE_URL[:50] if SUPABASE_URL else 'NOT SET'}...")
        debug_log(f"[DEBUG] SUPABASE_KEY: {'SET' if SUPABASE_KEY else 'NOT SET'}")
        debug_log(f"[DEBUG] SUPABASE_SECRET_KEY: {'SET' if SUPABASE_SECRET_KEY else 'NOT SET'}")
        
        if not imagen1 or not imagen2:
            debug_log(f"[ERROR] Missing files: imagen1={bool(imagen1)}, imagen2={bool(imagen2)}")
            return jsonify({'error': 'Se requieren 2 imágenes'}), 400
        
        # Validar que los archivos no estén vacíos
        if not img1_content_test:
            debug_log(f"[ERROR] imagen1 is empty!")
            return jsonify({'error': 'La imagen 1 está vacía'}), 400
        
        if not img2_content_test:
            debug_log(f"[ERROR] imagen2 is empty!")
            return jsonify({'error': 'La imagen 2 está vacía'}), 400
        
        if not firma_data:
            debug_log(f"[ERROR] Missing firma_data")
            return jsonify({'error': 'Se requiere la firma digital'}), 400
        
        # Generar timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Crear carpeta dentro del bucket para este préstamo
        loan_folder = f"loan_{id}"
        
        # ═══════════════════════════════════════════════════════════════
        # GUARDAR FIRMA a Supabase Storage como PNG
        # ═══════════════════════════════════════════════════════════════
        prefix = 'firma' if tipo_firma == 'inicial' else 'firma_devolucion'
        firma_filename = f"{prefix}_{timestamp}.png"
        firma_path = f"{loan_folder}/{firma_filename}"
        
        try:
            # Extraer datos base64 del dataURL
            if firma_data.startswith('data:image'):
                # formato: data:image/png;base64,iVBORw0KGgo...
                header, encoded = firma_data.split(',', 1)
                img_data = base64.b64decode(encoded)
                
                debug_log(f"[DEBUG] Firma base64 decoded: {len(img_data)} bytes")
                debug_log(f"[DEBUG] Uploading firma to path: {firma_path}")
                
                # Subir a Supabase Storage
                debug_log(f"[DEBUG] Calling supabase_storage_upload()...")
                firma_url = supabase_storage_upload(img_data, firma_path)
                
                debug_log(f"[DEBUG] supabase_storage_upload() returned: {firma_url is not None}")
                
                if not firma_url:
                    debug_log(f"[ERROR] supabase_storage_upload returned None for firmware {tipo_firma}")
                    return jsonify({'error': 'Error al guardar firma en Storage'}), 500
                
                debug_log(f"[SUCCESS] Firma URL: {firma_url}")
            else:
                return jsonify({'error': 'Firma no es un dataURL válido'}), 400
        except Exception as e:
            debug_log(f"[ERROR] Error procesando firma: {e}")
            import traceback
            debug_log(traceback.format_exc())
            return jsonify({'error': f'Error al procesar firma: {str(e)}'}), 500
        
        # ═══════════════════════════════════════════════════════════════
        # GUARDAR IMÁGENES a Supabase Storage
        # ═══════════════════════════════════════════════════════════════
        prefix_img = 'imagen1' if tipo_firma == 'inicial' else 'imagen1_dev'
        prefix_img2 = 'imagen2' if tipo_firma == 'inicial' else 'imagen2_dev'
        
        img1_filename = f"{prefix_img}_{timestamp}.jpg"
        img2_filename = f"{prefix_img2}_{timestamp}.jpg"
        
        img1_path = f"{loan_folder}/{img1_filename}"
        img2_path = f"{loan_folder}/{img2_filename}"
        
        # Leer contenido de archivos y subir a Storage
        try:
            img1_content = imagen1.read()
            img2_content = imagen2.read()
            
            debug_log(f"[DEBUG] imagen1 size: {len(img1_content)} bytes")
            debug_log(f"[DEBUG] imagen2 size: {len(img2_content)} bytes")
            
            img1_url = supabase_storage_upload(img1_content, img1_path)
            img2_url = supabase_storage_upload(img2_content, img2_path)
            
            if not img1_url or not img2_url:
                debug_log(f"[ERROR] One of images upload failed: img1={img1_url is not None}, img2={img2_url is not None}")
                return jsonify({'error': 'Error al guardar imágenes en Storage'}), 500
            
            debug_log(f"[SUCCESS] Imagen1 ({tipo_firma}) guardada: {img1_path}")
            debug_log(f"[SUCCESS] Imagen2 ({tipo_firma}) guardada: {img2_path}")
        except Exception as e:
            debug_log(f"[ERROR] Error guardando imágenes: {e}")
            import traceback
            debug_log(traceback.format_exc())
            return jsonify({'error': f'Error al guardar imágenes: {str(e)}'}), 500
        
        # ═══════════════════════════════════════════════════════════════
        # ACTUALIZAR PRÉSTAMO EN BD según tipo de firma
        # ═══════════════════════════════════════════════════════════════
        if tipo_firma == 'inicial':
            # Primera firma: cambiar a 'firmado' y guardar datos iniciales
            update_data = {
                'firma_url': firma_url,
                'imagen1_url': img1_url,
                'imagen2_url': img2_url,
                'estado': 'firmado',
                'fecha_firma': datetime.now().isoformat()
            }
        else:  # 'devolucion'
            # Firma de devolución: cambiar a 'devuelto' y guardar en campos de devolución
            update_data = {
                'firma_devolucion_url': firma_url,
                'imagen1_devolucion_url': img1_url,
                'imagen2_devolucion_url': img2_url,
                'estado': 'devuelto',
                'fecha_devolucion_real': datetime.now().isoformat()
            }
        
        result = supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', update_data)
        debug_log(f"[DEBUG] Supabase update result: {result}")
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f'Error al guardar en BD: {result.get("error")}'}), 500
        
        debug_log("\n[SUCCESS] ==================== FIRMA COMPLETADA ====================")
        return jsonify({
            'ok': True,
            'firma_url': firma_url,
            'img1_url': img1_url,
            'img2_url': img2_url,
            'tipo': tipo_firma,
            'message': f'Firma de {tipo_firma} y documentos guardados correctamente en Supabase Storage'
        }), 201
        
    except Exception as e:
        debug_log(f"\n[ERROR] save_loan_signature exception: {e}")
        import traceback
        debug_log(traceback.format_exc())
        return jsonify({'error': f'Error al procesar firma: {str(e)}'}), 500

@app.route('/api/prestamos/<int:id>/devolver', methods=['PUT'])
def devolver_prestamo(id):
    """Marcar prestamo como devuelto (después de que firma la devolución)"""
    try:
        supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', {
            'estado': 'devuelto',
            'fecha_devolucion_real': date.today().isoformat()
        })
        return jsonify({'ok': True, 'message': 'Prestamo marcado como devuelto'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== DEBUG ENDPOINT ==========
@app.route('/api/debug/storage-test', methods=['POST'])
def debug_storage_test():
    """Test endpoint to debug Storage uploads"""
    try:
        print("\n" + "="*70)
        print("DEBUG: Storage Upload Test")
        print("="*70)
        
        # Create test data
        test_content = b"TEST FILE CONTENT - " + bytes(str(datetime.now()), 'utf-8')
        test_path = f"debug/test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        print(f"\n[DEBUG] Testing upload to: {test_path}")
        print(f"[DEBUG] Content size: {len(test_content)} bytes")
        print(f"[DEBUG] SUPABASE_URL: {SUPABASE_URL}")
        print(f"[DEBUG] SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")
        print(f"[DEBUG] SUPABASE_SECRET_KEY exists: {bool(SUPABASE_SECRET_KEY)}")
        
        # Call storage upload
        result_url = supabase_storage_upload(test_content, test_path)
        
        print(f"\n[DEBUG] Upload result: {result_url}")
        
        if result_url:
            return jsonify({
                'ok': True,
                'message': 'Storage upload successful',
                'url': result_url
            }), 200
        else:
            return jsonify({
                'ok': False,
                'message': 'Storage upload failed - check server logs'
            }), 500
            
    except Exception as e:
        print(f"\n[ERROR] Debug test error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos/<int:id>', methods=['DELETE'])
def delete_prestamo(id):
    try:
        supabase_request('DELETE', 'prestamos', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== CALENDARIO ==========
@app.route('/api/calendario')
def get_calendario():
    try:
        events = []
        
        # Mantenimientos
        mants = supabase_request('GET', 'mantenimientos', '?order=proxima_revision.asc')
        if isinstance(mants, list):
            for m in mants:
                if m.get('proxima_revision'):
                    events.append({
                        'date': m['proxima_revision'],
                        'type': 'mantenimiento',
                        'title': f"Equipo ID: {m['equipo_id']}",
                        'sub': m['tipo'],
                        'id': m['id'],
                        'estado': m['estado'],
                        'descripcion': m.get('descripcion', '')
                    })
        
        # Préstamos
        prestamos = supabase_request('GET', 'prestamos', '?estado=eq.activo&order=fecha_devolucion_esperada.asc')
        if isinstance(prestamos, list):
            for p in prestamos:
                if p.get('fecha_devolucion_esperada'):
                    events.append({
                        'date': p['fecha_devolucion_esperada'],
                        'type': 'prestamo',
                        'title': f"Equipo ID: {p['equipo_id']}",
                        'sub': f"Usuario ID: {p['usuario_id']}",
                        'id': p['id'],
                        'estado': p['estado'],
                        'notas': p.get('notas', '')
                    })
        
        events.sort(key=lambda x: x['date'])
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check endpoint to verify backend and Supabase connectivity"""
    try:
        # Test Supabase connection
        test = supabase_request('GET', 'usuarios', '?limit=1')
        if isinstance(test, list) or test.get('error') is None:
            return jsonify({
                'status': 'ok',
                'message': 'Backend and Supabase connected',
                'supabase_url': SUPABASE_URL.split('://')[0] if SUPABASE_URL else 'not-set'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Supabase connection failed',
                'error': test.get('error')
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Health check failed',
            'error': str(e)
        }), 500

# @app.route('/uploads/<path:filename>')
# def serve_uploads(filename):
#     """Serve uploaded files from uploads directory - DISABLED in Vercel (read-only FS)"""
#     # All files are now in Supabase Storage, not local uploads/
#     return send_from_directory('uploads', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
