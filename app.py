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
    timestamp = datetime.now().isoformat()
    formatted_msg = f"[{timestamp}] {msg}"
    
    # Output to stdout (visible in Vercel logs)
    print(formatted_msg, file=sys.stdout)
    sys.stdout.flush()

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
        print(f"[ERROR] get_prestamo_detalle: {e}")
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
            print(f"Unexpected result format: {result}")
            return jsonify({'error': 'Error al crear préstamo', 'result': result}), 500
            
    except Exception as e:
        print(f"Create prestamo error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos/<int:id>/firma-images', methods=['POST'])
@require_api_login
def save_loan_images(id):
    """Save only images for a loan (first step of split upload)"""
    try:
        imagen1 = request.files.get('imagen1')
        imagen2 = request.files.get('imagen2')
        tipo_firma = request.form.get('tipo', 'inicial')
        
        if not imagen1 or not imagen2:
            return jsonify({'error': 'Se requieren 2 imágenes'}), 400
        
        # Leer contenido
        img1_content = imagen1.read()
        img2_content = imagen2.read()
        
        if not img1_content or not img2_content:
            return jsonify({'error': 'Las imágenes están vacías'}), 400
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        loan_folder = f"loan_{id}"
        
        # Guardar imágenes en Storage
        prefix_img = 'imagen1' if tipo_firma == 'inicial' else 'imagen1_dev'
        prefix_img2 = 'imagen2' if tipo_firma == 'inicial' else 'imagen2_dev'
        
        img1_filename = f"{prefix_img}_{timestamp}.jpg"
        img2_filename = f"{prefix_img2}_{timestamp}.jpg"
        
        img1_path = f"{loan_folder}/{img1_filename}"
        img2_path = f"{loan_folder}/{img2_filename}"
        
        try:
            img1_url = supabase_storage_upload(img1_content, img1_path)
            img2_url = supabase_storage_upload(img2_content, img2_path)
            
            if not img1_url or not img2_url:
                return jsonify({'error': 'Error al guardar imágenes'}), 500
        except Exception as e:
            return jsonify({'error': f'Error al guardar imágenes: {str(e)}'}), 500
        
        # Guardar URLs en sesión/cache para la siguiente llamada
        session[f'loan_{id}_images'] = {
            'img1_url': img1_url,
            'img2_url': img2_url,
            'tipo': tipo_firma,
            'timestamp': timestamp
        }
        
        return jsonify({
            'ok': True,
            'img1_url': img1_url,
            'img2_url': img2_url,
            'message': 'Imágenes guardadas correctamente'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/prestamos/<int:id>/firma-sign', methods=['POST'])
@require_api_login
def save_loan_signature_only(id):
    """Save signature and complete the loan signature (second step of split upload)"""
    try:
        firma_file = request.files.get('firma_data')
        tipo_firma = request.form.get('tipo', 'inicial')
        
        if not firma_file:
            return jsonify({'error': 'Se requiere firma digital'}), 400
        
        firma_content = firma_file.read()
        if not firma_content:
            return jsonify({'error': 'La firma está vacía'}), 400
        
        # Obtener imágenes guardadas en sesión
        images_data = session.get(f'loan_{id}_images', {})
        if not images_data:
            return jsonify({'error': 'Las imágenes no fueron guardadas. Intenta de nuevo.'}), 400
        
        timestamp = images_data.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        loan_folder = f"loan_{id}"
        img1_url = images_data.get('img1_url')
        img2_url = images_data.get('img2_url')
        
        # Guardar firma
        prefix = 'firma' if tipo_firma == 'inicial' else 'firma_devolucion'
        firma_filename = f"{prefix}_{timestamp}.jpg"
        firma_path = f"{loan_folder}/{firma_filename}"
        
        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Error al guardar firma'}), 500
        except Exception as e:
            return jsonify({'error': f'Error al guardar firma: {str(e)}'}), 500
        
        # Actualizar registro en BD
        if tipo_firma == 'inicial':
            update_data = {
                'firma_url': firma_url,
                'imagen1_url': img1_url,
                'imagen2_url': img2_url,
                'estado': 'firmado',
                'fecha_firma': datetime.now().isoformat()
            }
        else:  # 'devolucion'
            update_data = {
                'firma_devolucion_url': firma_url,
                'imagen1_devolucion_url': img1_url,
                'imagen2_devolucion_url': img2_url,
                'estado': 'devuelto',
                'fecha_devolucion_real': datetime.now().isoformat()
            }
        
        result = supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f'Error en BD: {result.get("error")}'}), 500
        
        # Limpiar sesión
        if f'loan_{id}_images' in session:
            del session[f'loan_{id}_images']
        
        return jsonify({
            'ok': True,
            'firma_url': firma_url,
            'img1_url': img1_url,
            'img2_url': img2_url,
            'tipo': tipo_firma,
            'message': 'Firma y documentos guardados correctamente'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/prestamos/<int:id>/firma', methods=['POST'])
@require_api_login
def save_loan_signature(id):
    """Save signature and images for a loan to Supabase Storage - supports 'inicial' or 'devolucion"""
    try:
        # Obtener archivos y parámetro de tipo
        imagen1 = request.files.get('imagen1')
        imagen2 = request.files.get('imagen2')
        firma_file = request.files.get('firma_data')  # Ahora es un archivo en lugar de dataURL
        tipo_firma = request.form.get('tipo', 'inicial')  # 'inicial' o 'devolucion'
        
        # Validar que todos los archivos existan
        if not imagen1 or not imagen2 or not firma_file:
            return jsonify({'error': 'Se requieren firma digital y 2 imágenes'}), 400
        
        # Read files in memory only (no disk I/O)
        try:
            img1_content = imagen1.read()
            imagen1.seek(0)  # Reset file pointer
            
            img2_content = imagen2.read()
            imagen2.seek(0)  # Reset file pointer
            
            firma_content = firma_file.read()
            firma_file.seek(0)  # Reset file pointer
        except Exception as e:
            return jsonify({'error': f'Error al leer archivos: {str(e)}'}), 400
        
        # Validar que los archivos no estén vacíos
        if not img1_content:
            return jsonify({'error': 'La imagen 1 está vacía'}), 400
        
        if not img2_content:
            return jsonify({'error': 'La imagen 2 está vacía'}), 400
        
        if not firma_content:
            return jsonify({'error': 'La firma digital está vacía'}), 400
        
        # Generar timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Crear carpeta dentro del bucket para este préstamo
        loan_folder = f"loan_{id}"
        
        # ═══════════════════════════════════════════════════════════════
        # GUARDAR FIRMA a Supabase Storage como JPG
        # ═══════════════════════════════════════════════════════════════
        prefix = 'firma' if tipo_firma == 'inicial' else 'firma_devolucion'
        firma_filename = f"{prefix}_{timestamp}.jpg"
        firma_path = f"{loan_folder}/{firma_filename}"
        
        try:
            # Subir firma directamente como blob JPEG
            firma_url = supabase_storage_upload(firma_content, firma_path)
            
            if not firma_url:
                return jsonify({'error': 'Error al guardar firma en Storage'}), 500
        except Exception as e:
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
        
        # Subir imágenes a Storage
        try:
            img1_url = supabase_storage_upload(img1_content, img1_path)
            img2_url = supabase_storage_upload(img2_content, img2_path)
            
            if not img1_url or not img2_url:
                return jsonify({'error': 'Error al guardar imágenes en Storage'}), 500
        except Exception as e:
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
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f'Error al guardar en BD: {result.get("error")}'}), 500
        
        return jsonify({
            'ok': True,
            'firma_url': firma_url,
            'img1_url': img1_url,
            'img2_url': img2_url,
            'tipo': tipo_firma,
            'message': f'Firma de {tipo_firma} y documentos guardados correctamente'
        }), 201
        
    except Exception as e:
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
