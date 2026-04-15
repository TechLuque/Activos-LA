from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect, url_for
import os
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import base64
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Cargar variables de entorno
load_dotenv()

import sys

# Detectar si estamos en Vercel (read-only filesystem)
IS_VERCEL = 'VERCEL' in os.environ or os.getenv('VERCEL_ENV') == 'production'

# Debug logging function
def debug_log(msg):
    """Write debug message to console/stdout (works on Vercel)"""
    # Debug logging disabled for security
    pass

# Verificar que las variables se cargaron

app = Flask(
    __name__,
    static_folder='static' if not IS_VERCEL else None,
    template_folder='templates'
)
app.secret_key = os.getenv('SECRET_KEY', 'tu-clave-secreta-super-segura-24-de-marzo-2026')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # Máximo 20 MB para uploads

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
        # Ensure file_content is bytes
        if not isinstance(file_content, bytes):
            file_content = bytes(file_content)
        
        storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{file_path}"
        
        # Validate credentials are loaded
        if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SECRET_KEY:
            return None
        
        # Headers with Authorization using Service Role Key
        headers = {
            'Authorization': f'Bearer {SUPABASE_SECRET_KEY}',
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/octet-stream'
        }
        
        resp = requests.post(storage_url, headers=headers, data=file_content, timeout=10)
        
        if resp.status_code in [200, 201]:
            # Generar URL pública
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{file_path}"
            return public_url
        else:
            return None
    except Exception as e:
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
                json_resp = resp.json()
                return json_resp
            except Exception as e:
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
        
        if not username or not password:
            return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
        
        # Buscar usuario en BD por email (primero)
        usuarios = supabase_request('GET', 'usuarios', f'?email=eq.{username}')
        
        if not isinstance(usuarios, list) or len(usuarios) == 0:
            # Si no existe por email, buscar por nombre (case-insensitive)
            usuarios = supabase_request('GET', 'usuarios', f'?nombre=ilike.{username}')
        
        if not isinstance(usuarios, list) or len(usuarios) == 0:
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
        
        user = usuarios[0]
        
        # Verificar contraseña (comparar contra hash)
        stored_password = user.get('password', '')
        if not check_password_hash(stored_password, password):
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
        
        # Verificar que el usuario esté activo
        if user.get('estado') != 'activo':
            return jsonify({'error': 'Usuario inactivo'}), 403
        
        # Crear sesión
        session['user_id'] = user.get('id')
        session['username'] = user.get('nombre')
        session['email'] = user.get('email')
        
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
        return jsonify({'error': f'Error al autenticar: {str(e)}'}), 500

@app.route('/logout', methods=['GET'])
def logout():
    """Cerrar sesión"""
    session.clear()
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
        prestamos_act = supabase_request('GET', 'prestamos', '?estado=neq.devuelto')
        prestamos_activos = len(prestamos_act) if isinstance(prestamos_act, list) else 0
        
        # Mantenimientos en proceso
        mant_proc = supabase_request('GET', 'mantenimientos', '?estado=neq.completado')
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
        
        # Obtener datos para mapeo (más eficiente que búsquedas individuales)
        equipos_data = supabase_request('GET', 'equipos')
        usuarios_data = supabase_request('GET', 'usuarios')
        tipos_result = supabase_request('GET', 'tipos_equipos')
        
        # Crear mapas para búsquedas rápidas
        equipos_map = {eq['id']: eq for eq in equipos_data} if isinstance(equipos_data, list) else {}
        usuarios_map = {u['id']: u for u in usuarios_data} if isinstance(usuarios_data, list) else {}
        tipos_map = {t['id']: t['nombre'] for t in tipos_result} if isinstance(tipos_result, list) else {}
        
        if isinstance(todos_prestamos, list):
            for p in todos_prestamos:
                # Enriquecer con información del equipo
                if 'equipo_id' in p and p['equipo_id'] in equipos_map:
                    eq = equipos_map[p['equipo_id']]
                    p['equipo_nombre'] = eq.get('nombre', 'Equipo desconocido')
                
                # Enriquecer con información del usuario
                if 'usuario_id' in p and p['usuario_id'] in usuarios_map:
                    p['usuario_nombre'] = usuarios_map[p['usuario_id']].get('nombre', 'Usuario desconocido')
                
                if p.get('estado') != 'devuelto' and p.get('fecha_devolucion_esperada'):
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
        
        result = {
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
        }
        return jsonify(result)
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
@require_api_login
def create_usuario():
    try:
        d = request.json
        
        # Departamentos permitidos
        DEPARTAMENTOS_VALIDOS = ['Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia']
        
        # Validar contraseña
        password = d.get('password', '').strip()
        if not password or len(password) < 6:
            return jsonify({'error': 'Contraseña requerida y debe tener al menos 6 caracteres'}), 400
        
        # Resolver rol_id
        rol_id = d.get('rol_id', None)
        if not rol_id and d.get('rol_nombre'):
            # Buscar rol por nombre
            roles_result = supabase_request('GET', 'roles_empresa', f'?nombre=eq.{d["rol_nombre"]}')
            if isinstance(roles_result, list) and len(roles_result) > 0:
                rol_id = roles_result[0]['id']
        
        if not rol_id:
            return jsonify({'error': 'Rol es requerido'}), 400
        
        # Obtener información del rol para asignar departamento
        rol_result = supabase_request('GET', 'roles_empresa', f'?id=eq.{rol_id}')
        rol_dept = ''
        if isinstance(rol_result, list) and len(rol_result) > 0:
            rol_dept = rol_result[0].get('departamento', '')
        
        # Usar departamento del rol si no se proporciona
        departamento = d.get('departamento', '').strip() or rol_dept
        
        # Validar departamento
        if not departamento or departamento not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400
        
        usuario_data = {
            'nombre': d['nombre'],
            'email': d['email'],
            'password': generate_password_hash(password),  # Hash la contraseña
            'departamento': departamento,
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
@require_api_login
def update_usuario(id):
    try:
        # Validar que usuario existe
        existing = supabase_request('GET', 'usuarios', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        d = request.json or {}
        
        if not isinstance(d, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
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
        
        # Validar rol_id si se proporcionó
        if rol_id:
            roles = supabase_request('GET', 'roles_empresa', f'?id=eq.{rol_id}')
            if not isinstance(roles, list) or len(roles) == 0:
                return jsonify({'error': f'Rol con ID {rol_id} no existe'}), 400
        
        update_data = {
            'nombre': d.get('nombre', ''),
            'email': d.get('email', ''),
            'departamento': d.get('departamento', ''),
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo')
        }
        
        # Solo hashear contraseña si se proporcionó una nueva
        if d.get('password', '').strip():
            password = d.get('password', '').strip()
            if len(password) < 6:
                return jsonify({'error': 'Contraseña debe tener al menos 6 caracteres'}), 400
            update_data['password'] = generate_password_hash(password)
        
        # Solo actualizar rol_id si fue proporcionado
        if rol_id:
            update_data['rol_id'] = rol_id
        
        result = supabase_request('PATCH', 'usuarios', f'?id=eq.{id}', update_data)
        return jsonify(result if isinstance(result, dict) else (result[0] if result else {}))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
@require_api_login
def delete_usuario(id):
    try:
        # Validar que usuario existe
        existing = supabase_request('GET', 'usuarios', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
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
@require_api_login
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
@require_api_login
def update_tipo_equipo(id):
    """Actualizar tipo de equipo"""
    try:
        # Validar que tipo existe
        existing = supabase_request('GET', 'tipos_equipos', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Tipo de equipo no encontrado'}), 404
        
        data = request.json or {}
        
        if not isinstance(data, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        # Hacer el PATCH
        result = supabase_request('PATCH', 'tipos_equipos', f'?id=eq.{id}', {
            'nombre': nombre,
            'descripcion': descripcion
        })
        
        # Verificar si hubo error en el PATCH
        if isinstance(result, dict) and result.get('error'):
            return jsonify(result), 400
        
        # SIEMPRE obtener los datos actualizados (para asegurar respuesta consistente)
        updated = supabase_request('GET', 'tipos_equipos', f'?id=eq.{id}')
        if isinstance(updated, list) and len(updated) > 0:
            return jsonify(updated[0]), 200
        
        # Fallback: retornar lo que sabemos del tipo actualizado
        return jsonify({'id': id, 'nombre': nombre, 'descripcion': descripcion}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tipos-equipos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_tipo_equipo(id):
    """Eliminar tipo de equipo"""
    try:
        # Validar que tipo existe
        existing = supabase_request('GET', 'tipos_equipos', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Tipo de equipo no encontrado'}), 404
        
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
@require_api_login
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
            'disponibilidad': d.get('disponibilidad', 'Disponible'),
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
@require_api_login
def update_equipo(id):
    try:
        # Validar que equipo existe
        existing = supabase_request('GET', 'equipos', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
        d = request.json or {}
        
        if not isinstance(d, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
        tipo_nombre = d.get('tipo')
        
        # Buscar ID del tipo en tipos_equipos
        tipo_id = None
        if tipo_nombre:
            tipos_result = supabase_request('GET', 'tipos_equipos', f'?nombre=eq.{tipo_nombre}')
            if isinstance(tipos_result, list) and len(tipos_result) > 0:
                tipo_id = tipos_result[0]['id']
            elif tipo_nombre:
                return jsonify({'error': f'Tipo de equipo "{tipo_nombre}" no existe'}), 400
        
        # Actualizar solo tipo_id (la columna tipo no existe)
        update_data = {
            'nombre': d.get('nombre', ''),
            'tipo_id': tipo_id,
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'disponibilidad': d.get('disponibilidad', 'Disponible'),
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
@require_api_login
def delete_equipo(id):
    try:
        # Validar que equipo existe
        existing = supabase_request('GET', 'equipos', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
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
@require_api_login
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
@require_api_login
def update_rol(id):
    """Actualizar rol"""
    try:
        # Validar que rol existe
        existing = supabase_request('GET', 'roles_empresa', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Rol no encontrado'}), 404
        
        data = request.json or {}
        
        if not isinstance(data, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
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
        
        # Hacer el PATCH
        result = supabase_request('PATCH', 'roles_empresa', f'?id=eq.{id}', update_data)
        
        # Verificar si hubo error en el PATCH
        if isinstance(result, dict) and result.get('error'):
            return jsonify(result), 400
        
        # SIEMPRE obtener los datos actualizados (para asegurar respuesta consistente)
        updated = supabase_request('GET', 'roles_empresa', f'?id=eq.{id}')
        if isinstance(updated, list) and len(updated) > 0:
            return jsonify(updated[0]), 200
        
        # Fallback: retornar lo que sabemos del rol actualizado
        return jsonify({'id': id, 'nombre': nombre, 'descripcion': descripcion, 'departamento': departamento}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/roles/<int:id>', methods=['DELETE'])
@require_api_login
def delete_rol(id):
    """Eliminar rol"""
    try:
        # Validar que rol existe
        existing = supabase_request('GET', 'roles_empresa', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Rol no encontrado'}), 404
        
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
@require_api_login
def create_mantenimiento():
    try:
        d = request.json
        
        # Validar enums
        TIPOS_MANTENIMIENTO = ['preventivo', 'correctivo', 'inspección']
        ESTADOS_MANTENIMIENTO = ['pendiente', 'completado', 'cancelado', 'en_progreso']
        
        if d.get('tipo') not in TIPOS_MANTENIMIENTO:
            return jsonify({'error': f'Tipo inválido. Debe ser uno de: {", ".join(TIPOS_MANTENIMIENTO)}'}), 400
        if d.get('estado', 'completado') not in ESTADOS_MANTENIMIENTO:
            return jsonify({'error': f'Estado inválido. Debe ser uno de: {", ".join(ESTADOS_MANTENIMIENTO)}'}), 400
        
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
        
        # Retornar ID del mantenimiento creado
        if isinstance(mant_result, list) and len(mant_result) > 0:
            return jsonify({'id': mant_result[0].get('id'), 'ok': True}), 201
        elif isinstance(mant_result, dict) and 'id' in mant_result:
            return jsonify({'id': mant_result.get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mantenimientos/<int:id>', methods=['PUT'])
@require_api_login
def update_mantenimiento(id):
    try:
        # Validar que mantenimiento existe
        existing = supabase_request('GET', 'mantenimientos', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Mantenimiento no encontrado'}), 404
        
        d = request.json or {}
        
        if not isinstance(d, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
        # Validar estados de mantenimiento
        ESTADOS_MANTENIMIENTO = ['pendiente', 'completado', 'cancelado', 'en_progreso']
        if d.get('estado') and d.get('estado') not in ESTADOS_MANTENIMIENTO:
            return jsonify({'error': f'Estado inválido. Debe ser uno de: {", ".join(ESTADOS_MANTENIMIENTO)}'}), 400
        
        # Validar tipo de mantenimiento
        TIPOS_MANTENIMIENTO = ['preventivo', 'correctivo', 'inspección']
        if d.get('tipo') and d.get('tipo') not in TIPOS_MANTENIMIENTO:
            return jsonify({'error': f'Tipo inválido. Debe ser uno de: {", ".join(TIPOS_MANTENIMIENTO)}'}), 400
        
        result = supabase_request('PATCH', 'mantenimientos', f'?id=eq.{id}', {
            'tipo': d['tipo'],
            'descripcion': d['descripcion'],
            'fecha': d['fecha'],
            'tecnico': d.get('tecnico', ''),
            'costo': d.get('costo', 0),
            'estado': d.get('estado', 'completado'),
            'proxima_revision': d.get('proxima_revision') or None
        })
        
        # Retornar datos actualizados
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 200
        
        # Si resultado vacío, obtener datos actualizados
        if isinstance(result, list):
            updated = supabase_request('GET', 'mantenimientos', f'?id=eq.{id}')
            if isinstance(updated, list) and len(updated) > 0:
                return jsonify(updated[0]), 200
        
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mantenimientos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_mantenimiento(id):
    try:
        # Validar que mantenimiento existe
        existing = supabase_request('GET', 'mantenimientos', f'?id=eq.{id}')
        if not isinstance(existing, list) or len(existing) == 0:
            return jsonify({'error': 'Mantenimiento no encontrado'}), 404
        
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
        
        # ═══════════════════════════════════════════════════════════════
        # 1. OBTENER PRÉSTAMO
        # ═══════════════════════════════════════════════════════════════
        prestamos = supabase_request('GET', 'prestamos', f'?id=eq.{id}')
        
        if isinstance(prestamos, dict) and prestamos.get('error'):
            return jsonify({'error': f"Error al obtener préstamo: {prestamos.get('error')}"}), 500
        
        if not isinstance(prestamos, list) or len(prestamos) == 0:
            return jsonify({'error': 'Préstamo no encontrado'}), 404
        
        loan = prestamos[0]
        
        # ═══════════════════════════════════════════════════════════════
        # 2. OBTENER NOMBRE DEL EQUIPO
        # ═══════════════════════════════════════════════════════════════
        equipo_id = loan.get('equipo_id')
        if equipo_id:
            equipos = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
            
            if isinstance(equipos, list) and len(equipos) > 0:
                loan['equipo_nombre'] = equipos[0].get('nombre', 'Equipo desconocido')
                loan['equipo_tipo'] = equipos[0].get('tipo', 'N/A')
                loan['equipo_serialno'] = equipos[0].get('serialno', 'N/A')
            else:
                loan['equipo_nombre'] = 'Equipo desconocido'
        else:
            loan['equipo_nombre'] = 'Sin equipo'
        
        # ═══════════════════════════════════════════════════════════════
        # 3. OBTENER NOMBRE DEL USUARIO
        # ═══════════════════════════════════════════════════════════════
        usuario_id = loan.get('usuario_id')
        if usuario_id:
            usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
            
            if isinstance(usuarios, list) and len(usuarios) > 0:
                loan['usuario_nombre'] = usuarios[0].get('nombre', 'Usuario desconocido')
                loan['usuario_email'] = usuarios[0].get('email', '')
                loan['usuario_telefono'] = usuarios[0].get('telefono', '')
            else:
                loan['usuario_nombre'] = 'Usuario desconocido'
        else:
            loan['usuario_nombre'] = 'Sin responsable'
        
        # ═══════════════════════════════════════════════════════════════
        # 4. RETORNAR RESPUESTA COMPLETA
        # ═══════════════════════════════════════════════════════════════
        return jsonify(loan)
        
    except Exception as e:
        return jsonify({'error': f"Error al obtener préstamo: {str(e)}"}), 500


@app.route('/api/prestamos/<int:id>/detalle', methods=['GET'])
@require_api_login
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
        pass
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos', methods=['POST'])
@require_api_login
def create_prestamo():
    try:
        d = request.json
        
        # Validar que equipo existe
        equipo = supabase_request('GET', 'equipos', f'?id=eq.{d["equipo_id"]}')
        if not isinstance(equipo, list) or len(equipo) == 0:
            return jsonify({'error': f'Equipo con ID {d["equipo_id"]} no encontrado'}), 400
        
        # Validar que usuario existe
        usuario = supabase_request('GET', 'usuarios', f'?id=eq.{d["usuario_id"]}')
        if not isinstance(usuario, list) or len(usuario) == 0:
            return jsonify({'error': f'Usuario con ID {d["usuario_id"]} no encontrado'}), 400
        
        # Validar que equipo no está Retirado
        if equipo[0].get('disponibilidad') == 'Retirado':
            return jsonify({'error': 'No se pueden crear préstamos de equipos retirados'}), 400
        
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
            pass
            return jsonify({'error': 'Error al crear préstamo', 'result': result}), 500
            
    except Exception as e:
        pass
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos/<int:id>/upload-image', methods=['POST'])
def upload_single_image(id):
    """Upload a single image (minimal processing)"""
    try:
        imagen = request.files.get('imagen')
        numero = request.form.get('numero', '1')
        tipo_firma = request.form.get('tipo', 'inicial')
        
        if not imagen:
            return jsonify({'error': 'No image provided'}), 400
        
        img_content = imagen.read()
        if not img_content or len(img_content) == 0:
            return jsonify({'error': 'Image is empty'}), 400
        
        # Generar path único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = 'imagen' + numero if tipo_firma == 'inicial' else f'imagen{numero}_dev'
        loan_folder = f"loan_{id}"
        img_filename = f"{prefix}_{timestamp}.jpg"
        img_path = f"{loan_folder}/{img_filename}"
        
        # Subir directamente a Storage
        try:
            img_url = supabase_storage_upload(img_content, img_path)
            if not img_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Guardar URL en sesión
        session_key = f'loan_{id}_img{numero}'
        session[session_key] = img_url
        
        return jsonify({'ok': True, 'url': img_url}), 201
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/prestamos/<int:id>/save-signature', methods=['POST'])
def save_signature_complete(id):
    """Save signature and update loan record"""
    try:
        firma_file = request.files.get('firma')
        tipo_firma = request.form.get('tipo', 'inicial')
        img1_url = request.form.get('img1_url')
        img2_url = request.form.get('img2_url')
        
        if not firma_file or not img1_url or not img2_url:
            return jsonify({'error': 'Missing required data'}), 400
        
        firma_content = firma_file.read()
        if not firma_content or len(firma_content) == 0:
            return jsonify({'error': 'Signature is empty'}), 400
        
        # Guardar firma
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = 'firma' if tipo_firma == 'inicial' else 'firma_devolucion'
        loan_folder = f"loan_{id}"
        firma_filename = f"{prefix}_{timestamp}.jpg"
        firma_path = f"{loan_folder}/{firma_filename}"
        
        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Actualizar BD
        if tipo_firma == 'inicial':
            update_data = {
                'firma_url': firma_url,
                'imagen1_url': img1_url,
                'imagen2_url': img2_url,
                'estado': 'firmado',
                'fecha_firma': datetime.now().isoformat()
            }
        else:
            update_data = {
                'firma_devolucion_url': firma_url,
                'imagen1_devolucion_url': img1_url,
                'imagen2_devolucion_url': img2_url,
                'estado': 'devuelto',
                'fecha_devolucion_real': datetime.now().isoformat()
            }
        
        result = supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': str(result.get('error'))}), 500
        
        return jsonify({
            'ok': True,
            'firma_url': firma_url,
            'img1_url': img1_url,
            'img2_url': img2_url,
            'message': f'Firma de {tipo_firma} completada'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


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

@app.route('/api/prestamos/<int:id>', methods=['PUT'])
@require_api_login
def update_prestamo(id):
    """Editar un préstamo existente"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener préstamo existente
        prestamo = supabase_request('GET', 'prestamos', f'?id=eq.{id}')
        if not isinstance(prestamo, list) or len(prestamo) == 0:
            return jsonify({'error': 'Préstamo no encontrado'}), 404
        
        prestamo_actual = prestamo[0]
        
        # Validar que equipo existe (en caso de cambiar)
        nuevo_equipo_id = d.get('equipo_id', prestamo_actual.get('equipo_id'))
        equipo = supabase_request('GET', 'equipos', f'?id=eq.{nuevo_equipo_id}')
        if not isinstance(equipo, list) or len(equipo) == 0:
            return jsonify({'error': f'Equipo con ID {nuevo_equipo_id} no encontrado'}), 400
        
        # Validar que usuario existe (en caso de cambiar)
        nuevo_usuario_id = d.get('usuario_id', prestamo_actual.get('usuario_id'))
        usuario = supabase_request('GET', 'usuarios', f'?id=eq.{nuevo_usuario_id}')
        if not isinstance(usuario, list) or len(usuario) == 0:
            return jsonify({'error': f'Usuario con ID {nuevo_usuario_id} no encontrado'}), 400
        
        # Validar que equipo no está Retirado
        if equipo[0].get('disponibilidad') == 'Retirado':
            return jsonify({'error': 'No se pueden editar préstamos a equipos retirados'}), 400
        
        # Si se cambia el equipo, verificar que no hay otro préstamo no devuelto
        if nuevo_equipo_id != prestamo_actual.get('equipo_id'):
            existing = supabase_request('GET', 'prestamos', f'?equipo_id=eq.{nuevo_equipo_id}&estado=ne.devuelto&id=neq.{id}')
            if isinstance(existing, list) and len(existing) > 0:
                return jsonify({'error': 'El nouveau equipo ya tiene un prestamo no devuelto'}), 400
        
        # Actualizar préstamo
        update_data = {
            'equipo_id': nuevo_equipo_id,
            'usuario_id': nuevo_usuario_id,
            'fecha_prestamo': d.get('fecha_prestamo', prestamo_actual.get('fecha_prestamo')),
            'fecha_devolucion_esperada': d.get('fecha_devolucion_esperada') or None,
            'notas': d.get('notas', '')
        }
        
        result = supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': 'No se pudo actualizar el préstamo: ' + str(result.get('error'))}), 500
        
        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== DEBUG ENDPOINT ==========
@app.route('/api/prestamos/<int:id>', methods=['DELETE'])
def delete_prestamo(id):
    try:
        supabase_request('DELETE', 'prestamos', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== LICENCIAS ==========
@app.route('/api/licencias', methods=['GET'])
@require_api_login
def get_licencias():
    """Obtener todas las licencias"""
    try:
        result = supabase_request('GET', 'licencias', '?order=fecha_caducidad.asc')
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/licencias/<int:id>', methods=['GET'])
@require_api_login
def get_licencia(id):
    """Obtener una licencia específica"""
    try:
        result = supabase_request('GET', 'licencias', f'?id=eq.{id}')
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 200
        return jsonify({'error': 'Licencia no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/licencias', methods=['POST'])
@require_api_login
def create_licencia():
    """Crear una nueva licencia"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        if not d.get('nombre') or not d.get('tipo') or not d.get('fecha_inicio') or not d.get('fecha_caducidad'):
            return jsonify({'error': 'nombre, tipo, fecha_inicio y fecha_caducidad son requeridos'}), 400
        
        # Convertir costo de forma segura
        costo = 0
        try:
            costo_str = str(d.get('costo', '0')).strip()
            if costo_str and costo_str not in ['NaN', 'nan', '']:
                costo = float(costo_str)
        except (ValueError, TypeError):
            costo = 0
        
        result = supabase_request('POST', 'licencias', '', {
            'nombre': d['nombre'].strip(),
            'tipo': d['tipo'],
            'fecha_inicio': d['fecha_inicio'],
            'fecha_caducidad': d['fecha_caducidad'],
            'proveedor': d.get('proveedor', '').strip(),
            'costo': costo,
            'descripcion': d.get('descripcion', '').strip(),
            'notas': d.get('notas', '').strip(),
            'estado': 'activa'
        })
        
        # Verificar si hay error en la respuesta
        if isinstance(result, dict) and result.get('error'):
            debug_log(f"[ERROR] Supabase error creating licencia: {result.get('error')}")
            return jsonify({'error': f"Error en Supabase: {result.get('error')}"}), 500
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        elif isinstance(result, dict) and 'id' in result:
            return jsonify({'id': result.get('id'), 'ok': True}), 201
        else:
            debug_log(f"[WARN] Unexpected response from Supabase: {result}")
            return jsonify({'error': 'Respuesta inesperada de Supabase', 'details': str(result)}), 500
    except Exception as e:
        debug_log(f"[ERROR] Exception in create_licencia: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/licencias/<int:id>', methods=['PUT'])
@require_api_login
def update_licencia(id):
    """Editar una licencia existente"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener licencia existente
        licencia = supabase_request('GET', 'licencias', f'?id=eq.{id}')
        if not isinstance(licencia, list) or len(licencia) == 0:
            return jsonify({'error': 'Licencia no encontrada'}), 404
        
        # Convertir costo de forma segura
        costo = licencia[0].get('costo', 0) or 0
        try:
            costo_str = str(d.get('costo', costo)).strip()
            if costo_str and costo_str not in ['NaN', 'nan', '']:
                costo = float(costo_str)
        except (ValueError, TypeError):
            costo = licencia[0].get('costo', 0) or 0
        
        update_data = {
            'nombre': d.get('nombre', licencia[0].get('nombre')).strip(),
            'tipo': d.get('tipo', licencia[0].get('tipo')),
            'fecha_inicio': d.get('fecha_inicio', licencia[0].get('fecha_inicio')),
            'fecha_caducidad': d.get('fecha_caducidad', licencia[0].get('fecha_caducidad')),
            'proveedor': d.get('proveedor', licencia[0].get('proveedor', '')).strip(),
            'costo': costo,
            'descripcion': d.get('descripcion', licencia[0].get('descripcion', '')).strip(),
            'notas': d.get('notas', licencia[0].get('notas', '')).strip(),
            'estado': d.get('estado', licencia[0].get('estado', 'activa'))
        }
        
        result = supabase_request('PATCH', 'licencias', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            debug_log(f"[ERROR] Supabase error updating licencia {id}: {result.get('error')}")
            return jsonify({'error': f"Error en Supabase: {result.get('error')}"}), 500
        
        debug_log(f"[OK] Licencia {id} actualizada exitosamente")
        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        debug_log(f"[ERROR] Exception in update_licencia: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/licencias/<int:id>', methods=['DELETE'])
@require_api_login
def delete_licencia(id):
    """Eliminar una licencia"""
    try:
        supabase_request('DELETE', 'licencias', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════
# ASIGNACIÓN DE LICENCIAS A EQUIPOS (Relación muchos-a-muchos)
# ════════════════════════════════════════════════════════════════

@app.route('/api/equipos/<int:equipo_id>/licencias', methods=['GET'])
@require_api_login
def get_equipo_licencias(equipo_id):
    """Obtener todas las licencias asignadas a un equipo"""
    try:
        result = supabase_request('GET', 'equipos_licencias', f'?equipo_id=eq.{equipo_id}&order=fecha_asignacion.desc')
        if isinstance(result, list):
            # Obtener detalles de las licencias
            licencias_info = []
            for item in result:
                lic_result = supabase_request('GET', 'licencias', f'?id=eq.{item.get("licencia_id")}')
                if isinstance(lic_result, list) and len(lic_result) > 0:
                    lic_data = lic_result[0]
                    lic_data['asignacion_id'] = item['id']
                    lic_data['fecha_asignacion'] = item.get('fecha_asignacion')
                    lic_data['notas_asignacion'] = item.get('notas', '')
                    licencias_info.append(lic_data)
            return jsonify(licencias_info)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:equipo_id>/licencias', methods=['POST'])
@require_api_login
def assign_licencia_to_equipo(equipo_id):
    """Asignar una licencia a un equipo"""
    try:
        d = request.json
        if not d or 'licencia_id' not in d:
            return jsonify({'error': 'licencia_id es requerido'}), 400
        
        # Verificar que el equipo existe
        equipo_check = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
        if not isinstance(equipo_check, list) or len(equipo_check) == 0:
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
        # Verificar que la licencia existe
        licencia_check = supabase_request('GET', 'licencias', f'?id=eq.{d["licencia_id"]}')
        if not isinstance(licencia_check, list) or len(licencia_check) == 0:
            return jsonify({'error': 'Licencia no encontrada'}), 404
        
        # Crear la asignación
        assignment_data = {
            'equipo_id': equipo_id,
            'licencia_id': d['licencia_id'],
            'fecha_asignacion': d.get('fecha_asignacion', date.today().isoformat()),
            'notas': d.get('notas', '')
        }
        
        result = supabase_request('POST', 'equipos_licencias', '', assignment_data)
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return jsonify({'error': 'Esta licencia ya está asignada a este equipo'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:equipo_id>/licencias/<int:licencia_id>', methods=['DELETE'])
@require_api_login
def remove_licencia_from_equipo(equipo_id, licencia_id):
    """Desasignar una licencia de un equipo (método antiguo - por compatibilidad)"""
    try:
        result = supabase_request('DELETE', 'equipos_licencias', f'?equipo_id=eq.{equipo_id}&licencia_id=eq.{licencia_id}')
        debug_log(f"[OK] Licencia {licencia_id} removida de equipo {equipo_id}")
        return jsonify({'ok': True})
    except Exception as e:
        debug_log(f"[ERROR] Error removiendo licencia: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos-licencias/<int:asignacion_id>', methods=['DELETE'])
@require_api_login
def delete_equipos_licencias(asignacion_id):
    """Desasignar una licencia de un equipo por ID de asignación"""
    try:
        result = supabase_request('DELETE', 'equipos_licencias', f'?id=eq.{asignacion_id}')
        debug_log(f"[OK] Asignación {asignacion_id} eliminada")
        return jsonify({'ok': True})
    except Exception as e:
        debug_log(f"[ERROR] Error eliminando asignación: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ========== CALENDARIO ==========
@app.route('/api/calendario')
def get_calendario():
    try:
        events = []
        
        # Fetch equipos, usuarios y tipos para mapeo
        equipos = supabase_request('GET', 'equipos')
        usuarios = supabase_request('GET', 'usuarios')
        tipos = supabase_request('GET', 'tipos_equipos')
        
        eq_map = {}
        if isinstance(equipos, list):
            for eq in equipos:
                eq_map[eq['id']] = {
                    'nombre': eq.get('nombre', 'Equipo desconocido'),
                    'tipo_id': eq.get('tipo_id')
                }
        
        usr_map = {}
        if isinstance(usuarios, list):
            for u in usuarios:
                usr_map[u['id']] = u.get('nombre', 'Usuario desconocido')
        
        tipos_map = {}
        if isinstance(tipos, list):
            for t in tipos:
                tipos_map[t['id']] = t.get('nombre', 'Tipo desconocido')
        
        # Mantenimientos
        mants = supabase_request('GET', 'mantenimientos', '?order=proxima_revision.asc')
        if isinstance(mants, list):
            for m in mants:
                if m.get('proxima_revision'):
                    eq_id = m.get('equipo_id')
                    eq_nombre = eq_map.get(eq_id, {}).get('nombre', 'Equipo desconocido')
                    tipo_id = eq_map.get(eq_id, {}).get('tipo_id')
                    tipo_nombre = tipos_map.get(tipo_id, 'Tipo desconocido')
                    
                    events.append({
                        'date': m['proxima_revision'],
                        'type': 'mantenimiento',
                        'title': eq_nombre,
                        'sub': f"{m['tipo'].capitalize()} · {tipo_nombre}",
                        'id': m['id'],
                        'estado': m['estado'],
                        'descripcion': m.get('descripcion', '')
                    })
        
        # Préstamos - Mostrar TODOS con fe fechas relevantes
        prestamos = supabase_request('GET', 'prestamos', '?order=fecha_devolucion_esperada.asc')
        if isinstance(prestamos, list):
            for p in prestamos:
                eq_id = p.get('equipo_id')
                usr_id = p.get('usuario_id')
                eq_nombre = eq_map.get(eq_id, {}).get('nombre', 'Equipo desconocido')
                tipo_id = eq_map.get(eq_id, {}).get('tipo_id')
                tipo_nombre = tipos_map.get(tipo_id, 'Tipo desconocido')
                usr_nombre = usr_map.get(usr_id, 'Usuario desconocido')
                
                # Mostrar fecha de devolución esperada (principal)
                if p.get('fecha_devolucion_esperada'):
                    estado_label = 'Para devolver'
                    if p.get('estado') == 'devuelto':
                        estado_label = 'Devuelto'
                    elif p.get('estado') == 'firmado':
                        estado_label = 'Pendiente firma'
                    
                    events.append({
                        'date': p['fecha_devolucion_esperada'],
                        'type': 'prestamo',
                        'title': eq_nombre,
                        'sub': f"{estado_label} · {tipo_nombre}",
                        'detail': f"Responsable: {usr_nombre}",
                        'id': p['id'],
                        'estado': p['estado'],
                        'notas': p.get('notas', '')
                    })
                
                # Si no hay fecha esperada pero hay fecha de préstamo, mostrarla
                elif p.get('fecha_prestamo'):
                    events.append({
                        'date': p['fecha_prestamo'],
                        'type': 'prestamo',
                        'title': eq_nombre,
                        'sub': f"Préstamo iniciado · {tipo_nombre}",
                        'detail': f"Responsable: {usr_nombre}",
                        'id': p['id'],
                        'estado': p['estado'],
                        'notas': p.get('notas', '')
                    })
        
        events.sort(key=lambda x: x['date'])
        return jsonify(events)
    except Exception as e:
        debug_log(f"[ERROR] Error in get_calendario: {e}")
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

# ========== BÚSQUEDA GLOBAL AVANZADA ==========
@app.route('/api/busqueda-global', methods=['GET'])
@require_api_login
def busqueda_global():
    """Búsqueda global en equipos, usuarios y préstamos"""
    try:
        query = request.args.get('q', '').lower().strip()
        filtro_tipo = request.args.get('tipo', 'todos')  # todos, equipos, usuarios, prestamos
        limite = int(request.args.get('limit', 20))
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Búsqueda muy corta (mínimo 2 caracteres)'}), 400
        
        resultados = {
            'equipos': [],
            'usuarios': [],
            'prestamos': [],
            'mantenimientos': []
        }
        
        # Búsqueda en equipos
        if filtro_tipo in ['todos', 'equipos']:
            equipos = supabase_request('GET', 'equipos')
            if isinstance(equipos, list) and equipos:
                for eq in equipos:
                    if isinstance(eq, dict) and (
                        query in (eq.get('nombre', '') or '').lower() or
                        query in (eq.get('serial', '') or '').lower() or
                        query in (eq.get('marca', '') or '').lower()):
                        resultados['equipos'].append({
                            'id': eq.get('id'),
                            'tipo': 'equipo',
                            'nombre': eq.get('nombre'),
                            'serial': eq.get('serial'),
                            'marca': eq.get('marca'),
                            'estado': eq.get('estado')
                        })
        
        # Búsqueda en usuarios
        if filtro_tipo in ['todos', 'usuarios']:
            usuarios = supabase_request('GET', 'usuarios')
            if isinstance(usuarios, list) and usuarios:
                for usr in usuarios:
                    if isinstance(usr, dict) and (
                        query in (usr.get('nombre', '') or '').lower() or
                        query in (usr.get('email', '') or '').lower()):
                        resultados['usuarios'].append({
                            'id': usr.get('id'),
                            'tipo': 'usuario',
                            'nombre': usr.get('nombre'),
                            'email': usr.get('email'),
                            'departamento': usr.get('departamento')
                        })
        
        # Búsqueda en préstamos
        if filtro_tipo in ['todos', 'prestamos']:
            prestamos = supabase_request('GET', 'prestamos')
            if isinstance(prestamos, list) and prestamos:
                for p in prestamos:
                    if isinstance(p, dict):
                        equipo_nombre = p.get('equipo_nombre', '') or ''
                        usuario_nombre = p.get('usuario_nombre', '') or ''
                        if (query in equipo_nombre.lower() or 
                            query in usuario_nombre.lower()):
                            resultados['prestamos'].append({
                                'id': p.get('id'),
                                'tipo': 'prestamo',
                                'equipo': equipo_nombre,
                                'responsable': usuario_nombre,
                                'estado': p.get('estado')
                            })
        
        # Limitar resultados
        for key in resultados:
            resultados[key] = resultados[key][:limite]
        
        return jsonify(resultados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== HISTORIAL DE RESPONSABLES ==========
@app.route('/api/equipos/<int:id>/historial-responsables', methods=['GET'])
@require_api_login
def get_historial_responsables(id):
    """Obtener historial de cambios de responsable de un equipo"""
    try:
        # Obtener equipo actual
        eq = supabase_request('GET', 'equipos', f'?id=eq.{id}')
        if not isinstance(eq, list) or len(eq) == 0:
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
        equipo = eq[0]
        
        # Obtener eventos de cambio de responsable de hoja_vida
        hvs = supabase_request('GET', 'hoja_vida', f'?equipo_id=eq.{id}&tipo=eq.cambio_responsable&order=fecha.desc')
        
        historial = []
        
        # Evento actual
        if equipo.get('usuario_id'):
            usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{equipo["usuario_id"]}')
            usuario_actual = usuarios[0]['nombre'] if isinstance(usuarios, list) and len(usuarios) > 0 else 'Desconocido'
            fecha_asignacion = equipo.get('fecha_asignacion')
            if not fecha_asignacion:
                fecha_asignacion = date.today().isoformat()
            historial.append({
                'fecha': fecha_asignacion,
                'responsable': usuario_actual,
                'usuario_id': equipo.get('usuario_id'),
                'estado': 'actual',
                'notas': 'Responsable actual'
            })
        
        # Eventos históricos - validar que hvs sea lista
        if isinstance(hvs, list) and hvs:
            for hv in hvs:
                if isinstance(hv, dict):
                    historial.append({
                        'fecha': hv.get('fecha'),
                        'responsable': hv.get('responsable', 'Desconocido'),
                        'estado': 'historico',
                        'notas': hv.get('descripcion', '')
                    })
        
        return jsonify(historial), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== MATRIZ DE RESPONSABILIDAD ==========
@app.route('/api/estadisticas/matriz-responsabilidad')
@require_api_login
def matriz_responsabilidad():
    """Estadísticas: quién tiene cuántos equipos"""
    try:
        equipos = supabase_request('GET', 'equipos')
        usuarios = supabase_request('GET', 'usuarios')
        
        # Crear mapa de usuarios - validar que sea lista
        usr_map = {}
        if isinstance(usuarios, list) and usuarios:
            for u in usuarios:
                if isinstance(u, dict) and u.get('id'):
                    usr_map[u['id']] = {
                        'nombre': u.get('nombre'),
                        'departamento': u.get('departamento'),
                        'equipos': [],
                        'total': 0
                    }
        
        # Contar equipos por usuario - validar que sea lista
        if isinstance(equipos, list) and equipos:
            for eq in equipos:
                if isinstance(eq, dict) and eq.get('usuario_id') and eq.get('usuario_id') in usr_map:
                    usr_map[eq['usuario_id']]['equipos'].append({
                        'id': eq.get('id'),
                        'nombre': eq.get('nombre'),
                        'estado': eq.get('estado')
                    })
                    usr_map[eq['usuario_id']]['total'] += 1
        
        # Convertir a lista ordenada
        matriz = []
        for usr_id, datos in usr_map.items():
            if datos['total'] > 0:
                matriz.append({
                    'usuario_id': usr_id,
                    'nombre': datos['nombre'],
                    'departamento': datos['departamento'],
                    'total_equipos': datos['total'],
                    'equipos': datos['equipos']
                })
        
        # Ordenar por total descendente
        matriz.sort(key=lambda x: x['total_equipos'], reverse=True)
        
        return jsonify(matriz), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== REGISTRAR CAMBIO DE RESPONSABLE ==========
@app.route('/api/equipos/<int:id>/cambiar-responsable', methods=['POST'])
@require_api_login
def cambiar_responsable(id):
    """Cambiar responsable de un equipo y registrar en hoja_vida"""
    try:
        # Validar que request.json existe
        if not request.json:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener equipo actual
        eq = supabase_request('GET', 'equipos', f'?id=eq.{id}')
        if not isinstance(eq, list) or len(eq) == 0:
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
        equipo = eq[0]
        d = request.json
        
        nuevo_usuario_id = d.get('nuevo_usuario_id')
        motivo = d.get('motivo', 'Cambio de asignación')
        
        if not nuevo_usuario_id:
            return jsonify({'error': 'Nuevo usuario requerido'}), 400
        
        # Obtener info del usuario anterior
        usuario_anterior_id = equipo.get('usuario_id')
        usuario_anterior_nombre = 'Desconocido'
        
        if usuario_anterior_id:
            usr_ant = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_anterior_id}')
            if isinstance(usr_ant, list) and len(usr_ant) > 0:
                usuario_anterior_nombre = usr_ant[0].get('nombre', 'Desconocido')
        
        # Obtener info del usuario nuevo
        usr_nuevo = supabase_request('GET', 'usuarios', f'?id=eq.{nuevo_usuario_id}')
        if not isinstance(usr_nuevo, list) or len(usr_nuevo) == 0:
            return jsonify({'error': 'Usuario nuevo no encontrado'}), 400
        
        usuario_nuevo_nombre = usr_nuevo[0].get('nombre', 'Desconocido')
        
        # Actualizar equipo
        today = date.today().isoformat()
        update_result = supabase_request('PATCH', 'equipos', f'?id=eq.{id}', {
            'usuario_id': nuevo_usuario_id,
            'fecha_asignacion': today
        })
        
        # Validar actualización
        if isinstance(update_result, dict) and update_result.get('error'):
            return jsonify({'error': 'No se pudo actualizar el equipo: ' + str(update_result.get('error'))}), 500
        
        # Registrar en hoja_vida
        titulo = f"Cambio de responsable: {usuario_anterior_nombre} → {usuario_nuevo_nombre}"
        hv_result = supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': id,
            'tipo': 'cambio_responsable',
            'titulo': titulo,
            'descripcion': motivo,
            'fecha': today,
            'responsable': session.get('username', 'Sistema')
        })
        
        # Log pero no fallar si hoja_vida no se puede registrar
        if isinstance(hv_result, dict) and hv_result.get('error'):
            debug_log(f"Warning: Could not register in hoja_vida: {hv_result.get('error')}")
        
        return jsonify({
            'ok': True,
            'mensaje': f'Responsable cambiado de {usuario_anterior_nombre} a {usuario_nuevo_nombre}'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== APLICATIVOS Y PAGOS ==========
@app.route('/api/aplicativos', methods=['GET'])
@require_api_login
def get_aplicativos():
    """Obtener todos los aplicativos"""
    try:
        result = supabase_request('GET', 'aplicativos', '?order=nombre.asc')
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aplicativos/<int:id>', methods=['GET'])
@require_api_login
def get_aplicativo(id):
    """Obtener un aplicativo específico"""
    try:
        result = supabase_request('GET', 'aplicativos', f'?id=eq.{id}')
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 200
        return jsonify({'error': 'Aplicativo no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aplicativos', methods=['POST'])
@require_api_login
def create_aplicativo():
    """Crear nuevo aplicativo"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        if not d.get('nombre') or not d.get('fecha_pago') or not d.get('periodicidad') or not d.get('tarjeta'):
            return jsonify({'error': 'nombre, fecha_pago, periodicidad y tarjeta son requeridos'}), 400
        
        # Validar periodicidad
        PERIODICIDADES = ['Mensual', 'Trimestral', 'Semestral', 'Anual']
        if d.get('periodicidad') not in PERIODICIDADES:
            return jsonify({'error': f'Periodicidad inválida. Debe ser: {", ".join(PERIODICIDADES)}'}), 400
        
        # Validar tarjeta
        TARJETAS = ['4184', '1111']
        if d.get('tarjeta') not in TARJETAS:
            return jsonify({'error': f'Tarjeta inválida. Debe ser: {", ".join(TARJETAS)}'}), 400
        
        result = supabase_request('POST', 'aplicativos', '', {
            'nombre': d['nombre'].strip(),
            'fecha_pago': d['fecha_pago'],
            'fecha_caducidad': d.get('fecha_caducidad'),
            'periodicidad': d['periodicidad'],
            'tarjeta': d['tarjeta'],
            'estado': 'activo'
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        elif isinstance(result, dict) and 'id' in result:
            return jsonify({'id': result.get('id'), 'ok': True}), 201
        else:
            return jsonify({'error': 'Error al crear aplicativo'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aplicativos/<int:id>', methods=['PUT'])
@require_api_login
def update_aplicativo(id):
    """Actualizar un aplicativo"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener aplicativo existente
        app_exist = supabase_request('GET', 'aplicativos', f'?id=eq.{id}')
        if not isinstance(app_exist, list) or len(app_exist) == 0:
            return jsonify({'error': 'Aplicativo no encontrado'}), 404
        
        # Validar periodicidad si fue proporcionada
        if d.get('periodicidad'):
            PERIODICIDADES = ['Mensual', 'Trimestral', 'Semestral', 'Anual']
            if d.get('periodicidad') not in PERIODICIDADES:
                return jsonify({'error': f'Periodicidad inválida. Debe ser: {", ".join(PERIODICIDADES)}'}), 400
        
        # Validar tarjeta si fue proporcionada
        if d.get('tarjeta'):
            TARJETAS = ['4184', '1111']
            if d.get('tarjeta') not in TARJETAS:
                return jsonify({'error': f'Tarjeta inválida. Debe ser: {", ".join(TARJETAS)}'}), 400
        
        update_data = {
            'nombre': d.get('nombre', app_exist[0].get('nombre')).strip(),
            'fecha_pago': d.get('fecha_pago', app_exist[0].get('fecha_pago')),
            'fecha_caducidad': d.get('fecha_caducidad', app_exist[0].get('fecha_caducidad')),
            'periodicidad': d.get('periodicidad', app_exist[0].get('periodicidad')),
            'tarjeta': d.get('tarjeta', app_exist[0].get('tarjeta')),
            'estado': d.get('estado', app_exist[0].get('estado', 'activo'))
        }
        
        result = supabase_request('PATCH', 'aplicativos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aplicativos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_aplicativo(id):
    """Eliminar un aplicativo"""
    try:
        result = supabase_request('DELETE', 'aplicativos', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════
# HISTORIAL DE PAGOS DE APLICATIVOS
# ════════════════════════════════════════════════════════════════

@app.route('/api/aplicativos/<int:aplicativo_id>/pagos', methods=['GET'])
@require_api_login
def get_pagos_aplicativo(aplicativo_id):
    """Obtener historial de pagos de un aplicativo"""
    try:
        result = supabase_request('GET', 'pagos_aplicativos', f'?aplicativo_id=eq.{aplicativo_id}&order=fecha_pago.desc')
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aplicativos/<int:aplicativo_id>/pagos', methods=['POST'])
@require_api_login
def add_pago_aplicativo(aplicativo_id):
    """Agregar un pago al historial de un aplicativo"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Verificar que aplicativo existe
        app_check = supabase_request('GET', 'aplicativos', f'?id=eq.{aplicativo_id}')
        if not isinstance(app_check, list) or len(app_check) == 0:
            return jsonify({'error': 'Aplicativo no encontrado'}), 404
        
        app_data = app_check[0]
        
        # Si no se proporciona fecha de pago, usar la fecha actual
        fecha_pago = d.get('fecha_pago', date.today().isoformat())
        
        # Calcular nueva fecha de caducidad basada en la periodicidad
        fecha_caducidad = d.get('fecha_caducidad')
        if not fecha_caducidad:
            fecha_caducidad = app_data.get('fecha_caducidad', date.today().isoformat())
        
        result = supabase_request('POST', 'pagos_aplicativos', '', {
            'aplicativo_id': aplicativo_id,
            'fecha_pago': fecha_pago,
            'fecha_caducidad': d.get('fecha_caducidad', fecha_caducidad),
            'monto': d.get('monto', 0),
            'metodo_pago': d.get('metodo_pago', app_data.get('tarjeta', ''))
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        # Actualizar la fecha de pago y caducidad del aplicativo
        update_data = {
            'fecha_pago': fecha_pago,
            'fecha_caducidad': d.get('fecha_caducidad', fecha_caducidad)
        }
        
        supabase_request('PATCH', 'aplicativos', f'?id=eq.{aplicativo_id}', update_data)
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        elif isinstance(result, dict) and 'id' in result:
            return jsonify({'id': result.get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pagos-aplicativos/<int:pago_id>', methods=['DELETE'])
@require_api_login
def delete_pago_aplicativo(pago_id):
    """Eliminar un pago del historial"""
    try:
        result = supabase_request('DELETE', 'pagos_aplicativos', f'?id=eq.{pago_id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== CELULARES Y SIM CARDS ==========
@app.route('/api/celulares', methods=['GET'])
@require_api_login
def get_celulares():
    """Obtener todos los celulares"""
    try:
        result = supabase_request('GET', 'celulares', '?order=nombre.asc')
        if isinstance(result, list):
            # Enriquecer con datos de SIM asociada
            simcards = supabase_request('GET', 'simcards', '?order=numero.asc')
            simcards_map = {}
            if isinstance(simcards, list):
                for sim in simcards:
                    if sim.get('celular_id'):
                        if sim['celular_id'] not in simcards_map:
                            simcards_map[sim['celular_id']] = []
                        simcards_map[sim['celular_id']].append(sim)
            
            for cel in result:
                cel['simcard'] = simcards_map.get(cel['id'], [])
            
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/celulares/<int:id>', methods=['GET'])
@require_api_login
def get_celular(id):
    """Obtener un celular específico"""
    try:
        result = supabase_request('GET', 'celulares', f'?id=eq.{id}')
        if isinstance(result, list) and len(result) > 0:
            cel = result[0]
            # Obtener SIM cards asociadas
            simcards = supabase_request('GET', 'simcards', f'?celular_id=eq.{id}&order=numero.asc')
            cel['simcard'] = simcards if isinstance(simcards, list) else []
            return jsonify(cel), 200
        return jsonify({'error': 'Celular no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/celulares', methods=['POST'])
@require_api_login
def create_celular():
    """Crear nuevo celular"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        if not d.get('nombre') or not d.get('marca') or not d.get('imei'):
            return jsonify({'error': 'nombre, marca e imei son requeridos'}), 400
        
        # Validar WhatsApp
        WHATSAPP_STATUS = ['activo', 'bloqueado']
        if d.get('whatsapp') and d.get('whatsapp') not in WHATSAPP_STATUS:
            return jsonify({'error': f'WhatsApp debe ser: {", ".join(WHATSAPP_STATUS)}'}), 400
        
        result = supabase_request('POST', 'celulares', '', {
            'nombre': d['nombre'].strip(),
            'marca': d['marca'].strip(),
            'imei': d['imei'].strip(),
            'imei2': d.get('imei2', '').strip(),
            'whatsapp': d.get('whatsapp', 'activo'),
            'estado': 'activo'
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/celulares/<int:id>', methods=['PUT'])
@require_api_login
def update_celular(id):
    """Actualizar un celular"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener celular existente
        cel_exist = supabase_request('GET', 'celulares', f'?id=eq.{id}')
        if not isinstance(cel_exist, list) or len(cel_exist) == 0:
            return jsonify({'error': 'Celular no encontrado'}), 404
        
        # Validar WhatsApp si fue proporcionado
        if d.get('whatsapp'):
            WHATSAPP_STATUS = ['activo', 'bloqueado']
            if d.get('whatsapp') not in WHATSAPP_STATUS:
                return jsonify({'error': f'WhatsApp debe ser: {", ".join(WHATSAPP_STATUS)}'}), 400
        
        update_data = {
            'nombre': d.get('nombre', cel_exist[0].get('nombre')).strip(),
            'marca': d.get('marca', cel_exist[0].get('marca')).strip(),
            'imei': d.get('imei', cel_exist[0].get('imei')).strip(),
            'imei2': d.get('imei2', cel_exist[0].get('imei2', '')).strip(),
            'whatsapp': d.get('whatsapp', cel_exist[0].get('whatsapp', 'activo')),
            'estado': d.get('estado', cel_exist[0].get('estado', 'activo'))
        }
        
        result = supabase_request('PATCH', 'celulares', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/celulares/<int:id>', methods=['DELETE'])
@require_api_login
def delete_celular(id):
    """Eliminar un celular"""
    try:
        result = supabase_request('DELETE', 'celulares', f'?id=eq.{id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════
# SIM CARDS
# ════════════════════════════════════════════════════════════════

@app.route('/api/simcards', methods=['GET'])
@require_api_login
def get_simcards():
    """Obtener todas las SIM cards"""
    try:
        result = supabase_request('GET', 'simcards', '?order=numero.asc')
        if isinstance(result, list):
            # Enriquecer con datos del celular asociado
            celulares = supabase_request('GET', 'celulares')
            celulares_map = {c['id']: c for c in celulares} if isinstance(celulares, list) else {}
            
            for sim in result:
                if sim.get('celular_id') and sim['celular_id'] in celulares_map:
                    sim['celular'] = celulares_map[sim['celular_id']]
                else:
                    sim['celular'] = None
            
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simcards/<int:id>', methods=['GET'])
@require_api_login
def get_simcard(id):
    """Obtener una SIM card específica"""
    try:
        result = supabase_request('GET', 'simcards', f'?id=eq.{id}')
        if isinstance(result, list) and len(result) > 0:
            sim = result[0]
            
            # Obtener datos del celular asociado
            if sim.get('celular_id'):
                cel = supabase_request('GET', 'celulares', f'?id=eq.{sim["celular_id"]}')
                if isinstance(cel, list) and len(cel) > 0:
                    sim['celular'] = cel[0]
            
            # Obtener historial de bloqueos
            historial = supabase_request('GET', 'historial_bloqueos_sim', f'?simcard_id=eq.{id}&order=fecha_bloqueo.desc')
            sim['historial_bloqueos'] = historial if isinstance(historial, list) else []
            
            return jsonify(sim), 200
        return jsonify({'error': 'SIM card no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simcards', methods=['POST'])
@require_api_login
def create_simcard():
    """Crear nueva SIM card"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        if not d.get('numero') or not d.get('operador'):
            return jsonify({'error': 'número y operador son requeridos'}), 400
        
        # Validar operador
        OPERADORES = ['Movistar', 'Claro', 'Tigo', 'WOM']
        if d.get('operador') not in OPERADORES:
            return jsonify({'error': f'Operador debe ser: {", ".join(OPERADORES)}'}), 400
        
        # Validar estado
        ESTADOS = ['activo', 'desactivado']
        if d.get('estado') and d.get('estado') not in ESTADOS:
            return jsonify({'error': f'Estado debe ser: {", ".join(ESTADOS)}'}), 400
        
        # Validar app
        APPS = ['whatsapp', 'whatsapp_business']
        if d.get('app') and d.get('app') not in APPS:
            return jsonify({'error': f'App debe ser: {", ".join(APPS)}'}), 400
        
        # Verificar que celular existe si fue proporcionado
        if d.get('celular_id'):
            cel_check = supabase_request('GET', 'celulares', f'?id=eq.{d["celular_id"]}')
            if not isinstance(cel_check, list) or len(cel_check) == 0:
                return jsonify({'error': 'Celular no encontrado'}), 404
            
            # Validar que no exceeda 3 números por celular
            sim_count = supabase_request('GET', 'simcards', f'?celular_id=eq.{d["celular_id"]}')
            if isinstance(sim_count, list) and len(sim_count) >= 3:
                return jsonify({'error': 'Este celular ya tiene 3 números. Máximo permitido es 3 por celular'}), 400
        
        result = supabase_request('POST', 'simcards', '', {
            'numero': d['numero'].strip(),
            'serial': d.get('serial', '').strip(),
            'operador': d['operador'],
            'estado': d.get('estado', 'activo'),
            'app': d.get('app', 'whatsapp'),
            'celular_id': d.get('celular_id', None)
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        if isinstance(result, list) and len(result) > 0:
            new_id = result[0].get('id')
            # Registrar en historial si tiene celular_id
            if d.get('celular_id'):
                supabase_request('POST', 'historial_simcards_celular', '', {
                    'celular_id': d['celular_id'],
                    'simcard_id': new_id
                })
            return jsonify({'id': new_id, 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simcards/<int:id>', methods=['PUT'])
@require_api_login
def update_simcard(id):
    """Actualizar una SIM card"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener SIM card existente
        sim_exist = supabase_request('GET', 'simcards', f'?id=eq.{id}')
        if not isinstance(sim_exist, list) or len(sim_exist) == 0:
            return jsonify({'error': 'SIM card no encontrada'}), 404
        
        old_celular_id = sim_exist[0].get('celular_id')
        new_celular_id = d.get('celular_id') if 'celular_id' in d else old_celular_id
        
        # Validar operador si fue proporcionado
        if d.get('operador'):
            OPERADORES = ['Movistar', 'Claro', 'Tigo', 'WOM']
            if d.get('operador') not in OPERADORES:
                return jsonify({'error': f'Operador debe ser: {", ".join(OPERADORES)}'}), 400
        
        # Validar estado si fue proporcionado
        if d.get('estado'):
            ESTADOS = ['activo', 'desactivado']
            if d.get('estado') not in ESTADOS:
                return jsonify({'error': f'Estado debe ser: {", ".join(ESTADOS)}'}), 400
        
        # Validar app si fue proporcionado
        if d.get('app'):
            APPS = ['whatsapp', 'whatsapp_business']
            if d.get('app') not in APPS:
                return jsonify({'error': f'App debe ser: {", ".join(APPS)}'}), 400
        
        # Verificar que nuevo celular existe si fue proporcionado
        if new_celular_id:
            cel_check = supabase_request('GET', 'celulares', f'?id=eq.{new_celular_id}')
            if not isinstance(cel_check, list) or len(cel_check) == 0:
                return jsonify({'error': 'Celular no encontrado'}), 404
            
            # Si cambió de celular, validar que no exceeda 3 números en el nuevo
            if new_celular_id != old_celular_id:
                sim_count = supabase_request('GET', 'simcards', f'?celular_id=eq.{new_celular_id}')
                if isinstance(sim_count, list) and len(sim_count) >= 3:
                    return jsonify({'error': 'El nuevo celular ya tiene 3 números. Máximo permitido es 3 por celular'}), 400
        
        update_data = {
            'numero': d.get('numero', sim_exist[0].get('numero')).strip(),
            'serial': d.get('serial', sim_exist[0].get('serial', '')).strip(),
            'operador': d.get('operador', sim_exist[0].get('operador')),
            'estado': d.get('estado', sim_exist[0].get('estado', 'activo')),
            'app': d.get('app', sim_exist[0].get('app', 'whatsapp')),
            'celular_id': new_celular_id
        }
        
        # Registrar cambio de celular en historial
        if old_celular_id != new_celular_id:
            if old_celular_id:
                # Marcar fecha_removida en el registro anterior
                supabase_request('PATCH', 'historial_simcards_celular', 
                    f'?celular_id=eq.{old_celular_id}&simcard_id=eq.{id}&fecha_removida=is.null',
                    {'fecha_removida': datetime.now().isoformat()})
            
            if new_celular_id:
                # Crear nuevo registro en historial
                supabase_request('POST', 'historial_simcards_celular', '', {
                    'celular_id': new_celular_id,
                    'simcard_id': id
                })
        
        result = supabase_request('PATCH', 'simcards', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simcards/<int:id>', methods=['DELETE'])
@require_api_login
def delete_simcard(id):
    """Desasignar una SIM card del celular actual (no la elimina)
    
    Parámetro query: ?permanently=true para eliminar completamente
    """
    try:
        permanently = request.args.get('permanently', 'false').lower() == 'true'
        
        # Obtener SIM card actual
        sim_data = supabase_request('GET', 'simcards', f'?id=eq.{id}')
        if not isinstance(sim_data, list) or len(sim_data) == 0:
            return jsonify({'error': 'SIM card no encontrada'}), 404
        
        celular_id = sim_data[0].get('celular_id')
        
        if permanently:
            # Eliminar completamente la SIM card
            if celular_id:
                # Marcar fecha_removida en el historial
                supabase_request('PATCH', 'historial_simcards_celular',
                    f'?celular_id=eq.{celular_id}&simcard_id=eq.{id}&fecha_removida=is.null',
                    {'fecha_removida': datetime.now().isoformat()})
            
            result = supabase_request('DELETE', 'simcards', f'?id=eq.{id}')
            return jsonify({'ok': True, 'message': 'SIM card eliminada permanentemente'})
        else:
            # Solo desasignar del celular
            if celular_id:
                # Marcar fecha_removida en el historial
                supabase_request('PATCH', 'historial_simcards_celular',
                    f'?celular_id=eq.{celular_id}&simcard_id=eq.{id}&fecha_removida=is.null',
                    {'fecha_removida': datetime.now().isoformat()})
            
            # Desasignar: poner celular_id en NULL
            result = supabase_request('PATCH', 'simcards', f'?id=eq.{id}', {
                'celular_id': None
            })
            
            return jsonify({'ok': True, 'message': 'SIM card desasignada del celular'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simcards/<int:id>/reasignar', methods=['POST'])
@require_api_login
def reasignar_simcard(id):
    """Reasignar una SIM card a otro celular"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        nuevo_celular_id = d.get('nuevo_celular_id')
        if not nuevo_celular_id:
            return jsonify({'error': 'nuevo_celular_id es requerido'}), 400
        
        # Obtener SIM card actual
        sim_data = supabase_request('GET', 'simcards', f'?id=eq.{id}')
        if not isinstance(sim_data, list) or len(sim_data) == 0:
            return jsonify({'error': 'SIM card no encontrada'}), 404
        
        old_celular_id = sim_data[0].get('celular_id')
        
        # Verificar que nuevo celular existe
        cel_check = supabase_request('GET', 'celulares', f'?id=eq.{nuevo_celular_id}')
        if not isinstance(cel_check, list) or len(cel_check) == 0:
            return jsonify({'error': 'Celular destino no encontrado'}), 404
        
        # Validar que no exceeda 3 números en el nuevo celular
        if nuevo_celular_id != old_celular_id:
            sim_count = supabase_request('GET', 'simcards', f'?celular_id=eq.{nuevo_celular_id}')
            if isinstance(sim_count, list) and len(sim_count) >= 3:
                return jsonify({'error': 'El celular destino ya tiene 3 números. Máximo permitido es 3 por celular'}), 400
        
        # Actualizar celular_id
        result = supabase_request('PATCH', 'simcards', f'?id=eq.{id}', {
            'celular_id': nuevo_celular_id
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        # Registrar cambio en historial
        if old_celular_id:
            # Marcar fecha_removida en el registro anterior
            supabase_request('PATCH', 'historial_simcards_celular',
                f'?celular_id=eq.{old_celular_id}&simcard_id=eq.{id}&fecha_removida=is.null',
                {'fecha_removida': datetime.now().isoformat()})
        
        # Crear nuevo registro en historial
        supabase_request('POST', 'historial_simcards_celular', '', {
            'celular_id': nuevo_celular_id,
            'simcard_id': id
        })
        
        return jsonify({'ok': True, 'id': id, 'message': f'SIM card reasignada de celular {old_celular_id} a {nuevo_celular_id}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════
# HISTORIAL DE BLOQUEOS DE SIM CARDS
# ════════════════════════════════════════════════════════════════

@app.route('/api/simcards/<int:simcard_id>/bloqueos', methods=['GET'])
@require_api_login
def get_bloqueos_simcard(simcard_id):
    """Obtener historial de bloqueos de una SIM card"""
    try:
        result = supabase_request('GET', 'historial_bloqueos_sim', f'?simcard_id=eq.{simcard_id}&order=fecha_bloqueo.desc')
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simcards/<int:simcard_id>/bloqueos', methods=['POST'])
@require_api_login
def add_bloqueo_simcard(simcard_id):
    """Registrar un bloqueo de SIM card"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Verificar que SIM card existe
        sim_check = supabase_request('GET', 'simcards', f'?id=eq.{simcard_id}')
        if not isinstance(sim_check, list) or len(sim_check) == 0:
            return jsonify({'error': 'SIM card no encontrada'}), 404
        
        fecha_bloqueo = d.get('fecha_bloqueo', date.today().isoformat())
        fecha_desbloqueo = d.get('fecha_desbloqueo', None)
        
        result = supabase_request('POST', 'historial_bloqueos_sim', '', {
            'simcard_id': simcard_id,
            'fecha_bloqueo': fecha_bloqueo,
            'fecha_desbloqueo': fecha_desbloqueo,
            'razon': d.get('razon', ''),
            'notas': d.get('notas', '')
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        # Actualizar estado de SIM a bloqueado
        supabase_request('PATCH', 'simcards', f'?id=eq.{simcard_id}', {
            'estado': 'desactivado'
        })
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bloqueos/<int:bloqueo_id>', methods=['PUT'])
@require_api_login
def update_bloqueo_simcard(bloqueo_id):
    """Actualizar un registro de bloqueo (especialmente fecha_desbloqueo)"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener bloqueo existente
        bloqueo_exist = supabase_request('GET', 'historial_bloqueos_sim', f'?id=eq.{bloqueo_id}')
        if not isinstance(bloqueo_exist, list) or len(bloqueo_exist) == 0:
            return jsonify({'error': 'Bloqueo no encontrado'}), 404
        
        update_data = {
            'fecha_bloqueo': d.get('fecha_bloqueo', bloqueo_exist[0].get('fecha_bloqueo')),
            'fecha_desbloqueo': d.get('fecha_desbloqueo', bloqueo_exist[0].get('fecha_desbloqueo')),
            'razon': d.get('razon', bloqueo_exist[0].get('razon', '')),
            'notas': d.get('notas', bloqueo_exist[0].get('notas', ''))
        }
        
        result = supabase_request('PATCH', 'historial_bloqueos_sim', f'?id=eq.{bloqueo_id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        return jsonify({'ok': True, 'id': bloqueo_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bloqueos/<int:bloqueo_id>', methods=['DELETE'])
@require_api_login
def delete_bloqueo_simcard(bloqueo_id):
    """Eliminar un registro de bloqueo"""
    try:
        result = supabase_request('DELETE', 'historial_bloqueos_sim', f'?id=eq.{bloqueo_id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════
# HISTORIAL DE SIM CARDS POR CELULAR
# ════════════════════════════════════════════════════════════════

@app.route('/api/celulares/<int:celular_id>/historial-sims', methods=['GET'])
@require_api_login
def get_historial_sims_celular(celular_id):
    """Obtener historial completo de SIM cards para un celular"""
    try:
        # Obtener historial con detalles de las SIM cards
        result = supabase_request('GET', 'historial_simcards_celular', 
            f'?celular_id=eq.{celular_id}&order=fecha_agregada.desc')
        
        if not isinstance(result, list):
            return jsonify([]), 200
        
        # Enriquecer con datos de simcard y celular
        historial_enriquecido = []
        for h in result:
            simcard_id = h.get('simcard_id')
            sim_data = supabase_request('GET', 'simcards', f'?id=eq.{simcard_id}')
            
            historial_enriquecido.append({
                'id': h.get('id'),
                'celular_id': h.get('celular_id'),
                'simcard_id': h.get('simcard_id'),
                'fecha_agregada': h.get('fecha_agregada'),
                'fecha_removida': h.get('fecha_removida'),
                'notas': h.get('notas'),
                'simcard': sim_data[0] if isinstance(sim_data, list) and len(sim_data) > 0 else None
            })
        
        return jsonify(historial_enriquecido), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════
# ASIGNACIONES DE EQUIPOS - Entrada/Salida con Firma Digital
# ════════════════════════════════════════════════════════════════

@app.route('/api/asignaciones-equipos', methods=['GET'])
@require_api_login
def get_asignaciones_equipos():
    """Obtener lista de asignaciones de equipos (con enriquecimiento de datos)"""
    try:
        result = supabase_request('GET', 'asignaciones_equipos', '?order=fecha_asignacion.desc')
        
        if isinstance(result, list):
            # Enriquecer con datos de equipos y usuarios
            equipos = supabase_request('GET', 'equipos')
            usuarios = supabase_request('GET', 'usuarios')
            
            eq_map = {e['id']: e for e in equipos} if isinstance(equipos, list) else {}
            usr_map = {u['id']: u for u in usuarios} if isinstance(usuarios, list) else {}
            
            for asig in result:
                asig['equipo'] = eq_map.get(asig.get('equipo_id'), {})
                asig['usuario'] = usr_map.get(asig.get('usuario_id'), {})
            
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/asignaciones-equipos/<int:id>', methods=['GET'])
@require_api_login
def get_asignacion_equipo(id):
    """Obtener detalles completos de una asignación"""
    try:
        result = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        
        if isinstance(result, list) and len(result) > 0:
            asig = result[0]
            
            # Enriquecer con datos relacionados
            equipo = supabase_request('GET', 'equipos', f'?id=eq.{asig.get("equipo_id")}')
            usuario = supabase_request('GET', 'usuarios', f'?id=eq.{asig.get("usuario_id")}')
            
            asig['equipo'] = equipo[0] if isinstance(equipo, list) and len(equipo) > 0 else {}
            asig['usuario'] = usuario[0] if isinstance(usuario, list) and len(usuario) > 0 else {}
            
            return jsonify(asig), 200
        
        return jsonify({'error': 'Asignación no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/asignaciones-equipos', methods=['POST'])
@require_api_login
def create_asignacion_equipo():
    """Crear nueva asignación de equipo (entrada)"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Obtener y convertir IDs a integers
        try:
            equipo_id = int(d.get('equipo_id'))
            usuario_id = int(d.get('usuario_id'))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'IDs deben ser números enteros: {str(e)}'}), 400
        
        if not equipo_id or not usuario_id:
            return jsonify({'error': 'equipo_id y usuario_id son requeridos'}), 400
        
        # Verificar que equipo existe
        equipo = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
        if not isinstance(equipo, list) or len(equipo) == 0:
            return jsonify({'error': f'Equipo con ID {equipo_id} no encontrado'}), 404
        
        equipo = equipo[0]
        
        # Verificar que usuario existe y está activo
        usuario = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
        if not isinstance(usuario, list) or len(usuario) == 0:
            return jsonify({'error': f'Usuario con ID {usuario_id} no encontrado'}), 404
        
        usuario = usuario[0]
        
        if usuario.get('estado') != 'activo':
            return jsonify({'error': 'El usuario debe estar activo para recibir equipos'}), 400
        
        # Verificar que equipo no está retirado
        disponibilidad = equipo.get('disponibilidad', '')
        if 'retirado' in disponibilidad.lower() or 'baja' in disponibilidad.lower():
            return jsonify({'error': f'No se puede asignar equipo con estado: {disponibilidad}'}), 400
        
        # Verificar que no hay asignación abierta anterior
        existing = supabase_request('GET', 'asignaciones_equipos', 
            f'?equipo_id=eq.{equipo_id}&estado=eq.abierta')
        if isinstance(existing, list) and len(existing) > 0:
            return jsonify({'error': 'Este equipo ya tiene una asignación abierta'}), 400
        
        # Crear la asignación
        estado_equipo = d.get('estado_equipo', 'bueno')
        notas = d.get('notas', '').strip()
        
        asig_data = {
            'equipo_id': equipo_id,
            'usuario_id': usuario_id,
            'fecha_asignacion': datetime.now().isoformat(),
            'estado_equipo_entrada': estado_equipo,
            'notas_entrada': notas,
            'estado': 'abierta'
        }
        
        result = supabase_request('POST', 'asignaciones_equipos', '', asig_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f'Database error: {result.get("error")}'}), 500
        
        # Manejar diferentes formatos de respuesta de Supabase
        asignacion_id = None
        
        # Intento 1: Si es lista con datos
        if isinstance(result, list) and len(result) > 0:
            nueva_asig = result[0]
            asignacion_id = nueva_asig.get('id')
        
        # Intento 2: Si es dict con id
        elif isinstance(result, dict) and 'id' in result:
            asignacion_id = result.get('id')
        
        # Intento 3: Si es lista vacía, intentar GET
        elif isinstance(result, list) and len(result) == 0:
            # Buscar la asignación más reciente
            recent = supabase_request('GET', 'asignaciones_equipos', 
                f'?equipo_id=eq.{equipo_id}&estado=eq.abierta&order=id.desc&limit=1')
            if isinstance(recent, list) and len(recent) > 0:
                asignacion_id = recent[0].get('id')
        
        # Si aún no tenemos ID, retornar error
        if not asignacion_id:
            # Intentar uno más: buscar por equipo_id y usuario_id combinación
            search_query = f'?equipo_id=eq.{equipo_id}&usuario_id=eq.{usuario_id}&estado=eq.abierta&limit=1'
            recent = supabase_request('GET', 'asignaciones_equipos', search_query)
            if isinstance(recent, list) and len(recent) > 0:
                asignacion_id = recent[0].get('id')
            else:
                return jsonify({'error': 'Failed to create assignment: ID not found after creation', 'debug': str(result)}), 500
        
        # Actualizar equipos.usuario_id para marcar actual responsable
        supabase_request('PATCH', 'equipos', f'?id=eq.{equipo_id}', {
            'usuario_id': usuario_id
        })
        
        # Crear entrada en hoja_vida
        supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': equipo_id,
            'tipo': 'asignacion',
            'titulo': f'Asignado a {usuario.get("nombre")}',
            'descripcion': f'Equipo asignado en entrada con estado: {estado_equipo}',
            'fecha': date.today().isoformat(),
            'responsable': session.get('username', 'Sistema')
        })
        
        return jsonify({
            'id': asignacion_id,
            'ok': True,
            'message': 'Asignación creada. Proceda con firma de entrada.'
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear asignación: {str(e)}'}), 500

@app.route('/api/asignaciones-equipos/<int:id>/upload-image', methods=['POST'])
@require_api_login
def upload_asignacion_image(id):
    """Subir imagen de entrada o salida"""
    try:
        imagen = request.files.get('imagen')
        numero = request.form.get('numero', '1')
        tipo = request.form.get('tipo', 'entrada')  # 'entrada' o 'salida'
        
        if not imagen:
            return jsonify({'error': 'No image provided'}), 400
        
        img_content = imagen.read()
        if not img_content or len(img_content) == 0:
            return jsonify({'error': 'Image is empty'}), 400
        
        # Generar path único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = f'imagen{numero}_{tipo}' if tipo == 'salida' else f'imagen{numero}'
        folder = f"asignacion_{id}"
        img_filename = f"{prefix}_{timestamp}.jpg"
        img_path = f"{folder}/{img_filename}"
        
        # Subir a Storage
        try:
            img_url = supabase_storage_upload(img_content, img_path)
            if not img_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Guardar URL en sesión
        session_key = f'asig_{id}_img{numero}_{tipo}'
        session[session_key] = img_url
        
        return jsonify({'ok': True, 'url': img_url}), 201
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/asignaciones-equipos/<int:id>/firma-entrada', methods=['POST'])
@require_api_login
def save_firma_entrada(id):
    """Guardar firma de entrada (asignación)"""
    try:
        firma_file = request.files.get('firma')
        img1_url = request.form.get('img1_url')
        img2_url = request.form.get('img2_url')
        
        if not firma_file or not img1_url or not img2_url:
            return jsonify({'error': 'Missing required data (firma)'}), 400
        
        # Verificar que asignación existe
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignación no encontrada'}), 404
        
        firma_content = firma_file.read()
        if not firma_content or len(firma_content) == 0:
            return jsonify({'error': 'Signature is empty'}), 400
        
        # Guardar firma en Storage
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"asignacion_{id}"
        firma_filename = f"firma_entrada_{timestamp}.jpg"
        firma_path = f"{folder}/{firma_filename}"
        
        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Actualizar asignación con datos de entrada
        update_data = {
            'firma_entrada_url': firma_url,
            'fecha_firma_entrada': datetime.now().isoformat()
        }
        
        result = supabase_request('PATCH', 'asignaciones_equipos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': str(result.get('error'))}), 500
        
        return jsonify({
            'ok': True,
            'message': 'Firma de entrada registrada exitosamente'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/asignaciones-equipos/<int:id>/firma-salida', methods=['POST'])
@require_api_login
def save_firma_salida(id):
    """Guardar firma de salida (devolución)"""
    try:
        firma_file = request.files.get('firma')
        img1_url = request.form.get('img1_url')
        img2_url = request.form.get('img2_url')
        estado_equipo = request.form.get('estado_equipo', 'bueno')
        notas = request.form.get('notas', '').strip()
        
        if not firma_file or not img1_url or not img2_url:
            return jsonify({'error': 'Missing required data (firma)'}), 400
        
        # Verificar que asignación existe y está abierta
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignación no encontrada'}), 404
        
        if asig[0].get('estado') != 'abierta':
            return jsonify({'error': 'Solo se pueden cerrar asignaciones abiertas'}), 400
        
        firma_content = firma_file.read()
        if not firma_content or len(firma_content) == 0:
            return jsonify({'error': 'Signature is empty'}), 400
        
        # Guardar firma en Storage
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"asignacion_{id}"
        firma_filename = f"firma_salida_{timestamp}.jpg"
        firma_path = f"{folder}/{firma_filename}"
        
        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Actualizar asignación con datos de salida y cerrarla
        update_data = {
            'firma_salida_url': firma_url,
            'estado_equipo_salida': estado_equipo,
            'notas_salida': notas,
            'fecha_firma_salida': datetime.now().isoformat(),
            'fecha_devolucion': datetime.now().isoformat(),
            'estado': 'cerrada'
        }
        
        result = supabase_request('PATCH', 'asignaciones_equipos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': str(result.get('error'))}), 500
        
        # Limpiar usuario_id del equipo cuando se devuelve (marca como libre)
        equipoId = asig[0].get('equipo_id')
        if equipoId:
            supabase_request('PATCH', 'equipos', f'?id=eq.{equipoId}', {'usuario_id': None})
        
        # Limpiar usuario_id del equipo (ya no está en posesión de nadie)
        equipo_id = asig[0].get('equipo_id')
        supabase_request('PATCH', 'equipos', f'?id=eq.{equipo_id}', {
            'usuario_id': None
        })
        
        # Crear entrada en hoja_vida
        usuario = supabase_request('GET', 'usuarios', f'?id=eq.{asig[0].get("usuario_id")}')
        usuario_nombre = usuario[0].get('nombre') if isinstance(usuario, list) and len(usuario) > 0 else 'Desconocido'
        
        supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': equipo_id,
            'tipo': 'devolucion',
            'titulo': f'Devuelto por {usuario_nombre}',
            'descripcion': f'Equipo devuelto con estado: {estado_equipo}. Notas: {notas}',
            'fecha': date.today().isoformat(),
            'responsable': session.get('username', 'Sistema')
        })
        
        return jsonify({
            'ok': True,
            'message': 'Asignación cerrada. Firma de salida registrada.'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/asignaciones-equipos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_asignacion(id):
    """Eliminar una asignacion de equipo"""
    try:
        # Verificar que asignacion existe
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignacion no encontrada'}), 404
        
        asig = asig[0]
        equipo_id = asig.get('equipo_id')
        
        # Limpiar usuario_id del equipo
        if equipo_id:
            supabase_request('PATCH', 'equipos', f'?id=eq.{equipo_id}', {
                'usuario_id': None
            })
        
        # Eliminar asignacion
        result = supabase_request('DELETE', 'asignaciones_equipos', f'?id=eq.{id}')
        
        return jsonify({'ok': True, 'message': 'Asignacion eliminada'}), 200
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/asignaciones-equipos/<int:id>/desasignar', methods=['PATCH'])
@require_api_login
def unassign_asignacion(id):
    """Desasignar equipo: cambiar estado a desasignada, limpiar usuario_id y guardar en historial"""
    try:
        # Verificar que asignacion existe
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignacion no encontrada'}), 404
        
        asig = asig[0]
        
        if asig.get('estado') != 'cerrada':
            return jsonify({'error': 'Solo se pueden desasignar asignaciones cerradas'}), 400
        
        equipo_id = asig.get('equipo_id')
        usuario_id = asig.get('usuario_id')
        
        # Obtener datos del usuario para el historial
        usuario = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
        usuario_nombre = usuario[0].get('nombre') if isinstance(usuario, list) and len(usuario) > 0 else 'Desconocido'
        
        # Limpiar usuario_id del equipo
        if equipo_id:
            supabase_request('PATCH', 'equipos', f'?id=eq.{equipo_id}', {
                'usuario_id': None
            })
        
        # Cambiar estado a desasignada
        result = supabase_request('PATCH', 'asignaciones_equipos', f'?id=eq.{id}', {
            'estado': 'desasignada'
        })
        
        # Guardar en hoja_vida el evento de desasignación
        supabase_request('POST', 'hoja_vida', '', {
            'equipo_id': equipo_id,
            'tipo': 'desasignacion',
            'titulo': f'Desasignado de {usuario_nombre}',
            'descripcion': f'Equipo desasignado del responsable {usuario_nombre} después de ser devuelto.',
            'fecha': date.today().isoformat(),
            'responsable': session.get('username', 'Sistema')
        })
        
        return jsonify({'ok': True, 'message': 'Equipo desasignado y liberado del responsable'}), 200
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500



# ════════════════════════════════════════════════════════════════════════════
# PUBLIC SIGNATURE ENDPOINTS (para asignaciones - sin login requerido)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/asignaciones-equipos/<int:id>/publico', methods=['GET'])
def get_asignacion_publico(id):
    """Obtener datos de asignacion para pagina de firma publica"""
    try:
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignacion no encontrada'}), 404
        
        asig = asig[0]
        
        equipo_id = asig.get('equipo_id')
        if equipo_id:
            equipos = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
            if isinstance(equipos, list) and len(equipos) > 0:
                asig['equipo_nombre'] = equipos[0].get('nombre', 'Equipo desconocido')
                asig['equipo_serial'] = equipos[0].get('serial', '')
        
        usuario_id = asig.get('usuario_id')
        if usuario_id:
            usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
            if isinstance(usuarios, list) and len(usuarios) > 0:
                asig['usuario_nombre'] = usuarios[0].get('nombre', 'Usuario desconocido')
        
        return jsonify(asig)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/asignaciones-equipos/<int:id>/save-signature-public', methods=['POST'])
def save_asignacion_signature_public(id):
    """Guardar firma de asignacion desde link publico"""
    try:
        firma_file = request.files.get('firma')
        tipo_firma = request.form.get('tipo', 'entrada')
        
        if not firma_file:
            return jsonify({'error': 'Missing signature'}), 400
        
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignacion no encontrada'}), 404
        
        asig = asig[0]
        firma_content = firma_file.read()
        if not firma_content:
            return jsonify({'error': 'Signature is empty'}), 400
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"asignacion_{id}"
        
        # Determinar prefijo según tipo de firma
        if tipo_firma == 'entrada':
            prefix = 'firma_entrada'
        elif tipo_firma == 'desasignacion':
            prefix = 'firma_desasignacion'
        else:  # 'salida'
            prefix = 'firma_salida'
            
        firma_filename = f"{prefix}_{timestamp}.jpg"
        firma_path = f"{folder}/{firma_filename}"
        
        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Preparar datos minimalistas solo con campos que definitivamente existen
        update_data = {}
        
        if tipo_firma == 'entrada':
            update_data['firma_entrada_url'] = firma_url
            update_data['fecha_firma_entrada'] = datetime.now().isoformat()
        elif tipo_firma == 'desasignacion':
            update_data['firma_desasignacion_url'] = firma_url
            update_data['fecha_firma_desasignacion'] = datetime.now().isoformat()
            update_data['estado'] = 'desasignada'  # ✅ Cambiar estado
        else:  # 'salida'
            update_data['firma_salida_url'] = firma_url
            update_data['fecha_firma_salida'] = datetime.now().isoformat()
        
        # Intenta actualizar. Si falla, aún así retorna éxito (firma se guardó en storage)
        try:
            result = supabase_request('PATCH', 'asignaciones_equipos', f'?id=eq.{id}', update_data)
            
            if isinstance(result, dict) and result.get('error'):
                # No retornar error si es solo actualización de tabla fallida
                # La firma ya está guardada en storage
                pass
        except Exception as e:
            # No fallar, la firma ya se guardó en storage
            pass
        
        return jsonify({'ok': True, 'message': f'Firma de {tipo_firma} guardada exitosamente'}), 201
    except Exception as e:
        import traceback
        error_msg = f"{str(e)} | {traceback.format_exc()}"
        return jsonify({'error': error_msg}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
