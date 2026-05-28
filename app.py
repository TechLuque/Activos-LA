from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_compress import Compress
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta
import base64
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import quote

from db import (
    supabase_request, supabase_storage_upload,
    cache_invalidate, get_tipos_map,
    SUPABASE_URL, SUPABASE_KEY, SUPABASE_SECRET_KEY
)
import repositories as repo

# Cargar variables de entorno (db.py ya llama load_dotenv, pero lo mantenemos por compatibilidad)
from dotenv import load_dotenv
load_dotenv()

# Flask app
app = Flask(__name__, static_folder=None, template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'tu-clave-secreta-super-segura-24-de-marzo-2026')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
Compress(app)

@app.after_request
def set_response_headers(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    elif any(ext in request.path for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.svg']):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

# ═══════════════════════════════════════════════════════════════
# CONSTANTES DE DOMINIO
# ═══════════════════════════════════════════════════════════════

DEPARTAMENTOS_VALIDOS = ['Finanzas', 'Plataformas', 'Producción', 'Academia', 'Contenido', 'Gerencia']
TIPOS_MANTENIMIENTO = ['preventivo', 'correctivo', 'inspección']
ESTADOS_MANTENIMIENTO = ['pendiente', 'completado', 'cancelado', 'en_progreso']
ESTADOS_USUARIO = ['activo', 'inactivo']
WHATSAPP_STATUS = ['activo', 'bloqueado']
ESTADOS_SIM = ['activo', 'reserva', 'bloqueado', 'desactivado']

def _server_error(e):
    """Loguea el error real internamente y devuelve respuesta genérica al cliente."""
    import traceback
    print(f"[ERROR] {type(e).__name__}: {e}\n{traceback.format_exc()}", flush=True)
    return jsonify({'error': 'Error interno del servidor'}), 500

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
        
        user = repo.get_usuario_by_email(username)
        if not user:
            user = repo.get_usuario_by_nombre_ilike(username)
        if not user:
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
        
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
        return _server_error(e)

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

        equipos_list = repo.get_all_equipos()
        usuarios_list = repo.get_all_usuarios()
        prestamos_list = repo.get_prestamos_raw()
        mants_list = repo.get_mantenimientos_raw()
        tipos_map = get_tipos_map()

        # Mapas para lookups O(1)
        equipos_map = {eq['id']: eq for eq in equipos_list}
        usuarios_map = {u['id']: u for u in usuarios_list}

        # Conteos de equipos
        total_equipos = len(equipos_list)
        estados = {}
        tipos_count = {}
        valor_total = 0
        for eq in equipos_list:
            estado = eq.get('estado', 'desconocido')
            estados[estado] = estados.get(estado, 0) + 1
            tipo = eq.get('tipo_nombre') or tipos_map.get(eq.get('tipo_id'), eq.get('tipo', 'Sin tipo'))
            tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
            valor_total += int(eq.get('valor', 0) or 0)

        tipos_equipos = [
            {'tipo_nombre': k, 'tipo': k, 'count': v}
            for k, v in sorted(tipos_count.items(), key=lambda x: x[1], reverse=True)[:7]
        ]

        # Conteos de usuarios
        total_usuarios = sum(1 for u in usuarios_list if u.get('estado') == 'activo')

        # Préstamos — una sola pasada para todos los cálculos
        prestamos_activos = 0
        prestamos_vencidos = []
        proximos_vencer = []
        for p in prestamos_list:
            eq = equipos_map.get(p.get('equipo_id'), {})
            p['equipo_nombre'] = eq.get('nombre', 'Equipo desconocido')
            usr = usuarios_map.get(p.get('usuario_id'), {})
            p['usuario_nombre'] = usr.get('nombre', 'Usuario desconocido')

            if p.get('estado') != 'devuelto':
                prestamos_activos += 1
                fecha_dev = p.get('fecha_devolucion_esperada')
                if fecha_dev:
                    if fecha_dev < today:
                        prestamos_vencidos.append(p)
                    elif fecha_dev <= in7:
                        proximos_vencer.append(p)

        # Mantenimientos — una sola pasada
        mant_en_proceso = 0
        preventivos_vencidos = 0
        for m in mants_list:
            if m.get('estado') != 'completado':
                mant_en_proceso += 1
            if m.get('tipo') == 'preventivo' and m.get('proxima_revision') and m['proxima_revision'] < today:
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
        return _server_error(e)


@app.route('/api/init', methods=['GET'])
@require_api_login
def get_init_data():
    """Carga inicial en una sola request: paraleliza 11 queries a Supabase con ThreadPoolExecutor."""
    try:
        tasks = {
            'equipos': repo.get_all_equipos,
            'usuarios': repo.get_all_usuarios,
            'prestamos': repo.get_all_prestamos,
            'mantenimientos': repo.get_all_mantenimientos,
            'licencias': repo.get_all_licencias,
            'aplicativos': repo.get_all_aplicativos,
            'celulares': repo.get_all_celulares,
            'simcards': repo.get_all_simcards,
            'asignaciones': repo.get_all_asignaciones,
            'tipos': repo.get_all_tipos_equipos,
            'roles': repo.get_all_roles,
        }
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {k: executor.submit(fn) for k, fn in tasks.items()}
            return jsonify({k: f.result() for k, f in futures.items()})
    except Exception as e:
        return _server_error(e)


# ========== USUARIOS ==========
@app.route('/api/usuarios', methods=['GET'])
@require_api_login
def get_usuarios():
    try:
        return jsonify(repo.get_all_usuarios())
    except Exception as e:
        return _server_error(e)

@app.route('/api/usuarios', methods=['POST'])
@require_api_login
def create_usuario():
    try:
        d = request.json
        
        # Departamentos permitidos
        
        # Validar contraseña
        password = d.get('password', '').strip()
        if not password or len(password) < 6:
            return jsonify({'error': 'Contraseña requerida y debe tener al menos 6 caracteres'}), 400
        
        # Resolver rol_id
        rol_id = d.get('rol_id', None)
        if not rol_id and d.get('rol_nombre'):
            rol = repo.get_rol_by_nombre(d['rol_nombre'])
            if rol:
                rol_id = rol['id']

        if not rol_id:
            return jsonify({'error': 'Rol es requerido'}), 400

        rol_obj = repo.get_rol(rol_id)
        rol_dept = rol_obj.get('departamento', '') if rol_obj else ''
        departamento = d.get('departamento', '').strip() or rol_dept

        if not departamento or departamento not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400

        usuario_data = {
            'nombre': d['nombre'],
            'email': d['email'],
            'password': generate_password_hash(password),
            'departamento': departamento,
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo'),
            'rol_id': rol_id
        }

        result = repo.create_usuario(usuario_data)
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'email' in str(e).lower():
            return jsonify({'error': 'El email ya existe'}), 400
        return _server_error(e)

@app.route('/api/usuarios/<int:id>', methods=['PUT'])
@require_api_login
def update_usuario(id):
    try:
        if not repo.get_usuario(id):
            return jsonify({'error': 'Usuario no encontrado'}), 404

        d = request.json or {}
        if not isinstance(d, dict):
            return jsonify({'error': 'Datos inválidos'}), 400

        if d.get('departamento') and d.get('departamento') not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400

        rol_id = d.get('rol_id', None)
        if not rol_id and d.get('rol_nombre'):
            rol = repo.get_rol_by_nombre(d['rol_nombre'])
            if rol:
                rol_id = rol['id']

        if rol_id and not repo.get_rol(rol_id):
            return jsonify({'error': f'Rol con ID {rol_id} no existe'}), 400

        update_data = {
            'nombre': d.get('nombre', ''),
            'email': d.get('email', ''),
            'departamento': d.get('departamento', ''),
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo')
        }

        if d.get('password', '').strip():
            password = d.get('password', '').strip()
            if len(password) < 6:
                return jsonify({'error': 'Contraseña debe tener al menos 6 caracteres'}), 400
            update_data['password'] = generate_password_hash(password)

        if rol_id:
            update_data['rol_id'] = rol_id

        result = repo.update_usuario(id, update_data)
        return jsonify(result if isinstance(result, dict) else (result[0] if result else {}))
    except Exception as e:
        return _server_error(e)

@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
@require_api_login
def delete_usuario(id):
    try:
        if not repo.get_usuario(id):
            return jsonify({'error': 'Usuario no encontrado'}), 404
        repo.delete_usuario(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# Tipos de equipos ahora se cargan desde BD (tipos_equipos)
# Ver endpoints /api/tipos-equipos para CRUD

@app.route('/api/equipos', methods=['GET'])
def get_equipos():
    try:
        return jsonify(repo.get_all_equipos())
    except Exception as e:
        return _server_error(e)

@app.route('/api/tipos-equipos', methods=['GET'])
def get_tipos_equipos():
    try:
        return jsonify(repo.get_all_tipos_equipos()), 200
    except Exception as e:
        return jsonify([]), 200

@app.route('/api/tipos-equipos', methods=['POST'])
@require_api_login
def create_tipo_equipo():
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        serial_prefix = data.get('serial_prefix') or None
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        result = repo.create_tipo_equipo(nombre, descripcion, serial_prefix)
        if isinstance(result, list) and len(result) > 0:
            cache_invalidate('tipos_equipos')
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': 'Este tipo de equipo ya existe'}), 400
        return _server_error(e)

@app.route('/api/tipos-equipos/<int:id>', methods=['PUT'])
@require_api_login
def update_tipo_equipo(id):
    try:
        if not repo.get_tipo_equipo(id):
            return jsonify({'error': 'Tipo de equipo no encontrado'}), 404
        data = request.json or {}
        if not isinstance(data, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        serial_prefix = data.get('serial_prefix') or None
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        result = repo.update_tipo_equipo(id, nombre, descripcion, serial_prefix)
        if isinstance(result, dict) and result.get('error'):
            return jsonify(result), 400
        updated = repo.get_tipo_equipo(id)
        cache_invalidate('tipos_equipos')
        return jsonify(updated or {'id': id, 'nombre': nombre, 'descripcion': descripcion}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/tipos-equipos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_tipo_equipo(id):
    try:
        if not repo.get_tipo_equipo(id):
            return jsonify({'error': 'Tipo de equipo no encontrado'}), 404
        repo.delete_tipo_equipo(id)
        cache_invalidate('tipos_equipos')
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos/<int:id>', methods=['GET'])
def get_equipo(id):
    try:
        equipo = repo.get_equipo(id)
        if equipo:
            return jsonify(equipo)
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos', methods=['POST'])
@require_api_login
def create_equipo():
    try:
        d = request.json
        tipo_nombre = d['tipo']

        tipo_obj = repo.get_tipo_by_nombre(tipo_nombre)
        tipo_id = tipo_obj['id'] if tipo_obj else None

        fecha_adquisicion = d.get('fecha_adquisicion', '')
        fecha_ingreso = d.get('fecha_ingreso', '')

        equipo_data = {
            'nombre': d['nombre'],
            'tipo_id': tipo_id,
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'disponibilidad': d.get('disponibilidad', 'Disponible'),
            'usuario_id': d.get('usuario_id', None),
            'fecha_adquisicion': fecha_adquisicion if fecha_adquisicion else None,
            'valor': d.get('valor', 0),
            'descripcion': d.get('descripcion', ''),
            'num_factura': d.get('num_factura', ''),
            'nombre_proveedor': d.get('nombre_proveedor', ''),
            'nombre_empresa': d.get('nombre_empresa', ''),
            'fecha_ingreso': fecha_ingreso if fecha_ingreso else None
        }

        equipo_result = repo.create_equipo(equipo_data)

        if isinstance(equipo_result, list) and len(equipo_result) > 0:
            equipo_id = equipo_result[0]['id']
            repo.create_hoja_vida({
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
        return _server_error(e)

@app.route('/api/equipos/<int:id>', methods=['PUT'])
@require_api_login
def update_equipo(id):
    try:
        if not repo.get_equipo(id):
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
        d = request.json or {}
        
        if not isinstance(d, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
        tipo_nombre = d.get('tipo')
        tipo_id = None
        if tipo_nombre:
            tipo_obj = repo.get_tipo_by_nombre(tipo_nombre)
            if tipo_obj:
                tipo_id = tipo_obj['id']
            else:
                return jsonify({'error': f'Tipo de equipo "{tipo_nombre}" no existe'}), 400

        fecha_adquisicion = d.get('fecha_adquisicion', '')
        fecha_ingreso = d.get('fecha_ingreso', '')

        update_data = {
            'nombre': d.get('nombre', ''),
            'tipo_id': tipo_id,
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'disponibilidad': d.get('disponibilidad', 'Disponible'),
            'usuario_id': d.get('usuario_id', None),
            'fecha_adquisicion': fecha_adquisicion if fecha_adquisicion else None,
            'valor': d.get('valor', 0),
            'descripcion': d.get('descripcion', ''),
            'num_factura': d.get('num_factura', ''),
            'nombre_proveedor': d.get('nombre_proveedor', ''),
            'nombre_empresa': d.get('nombre_empresa', ''),
            'fecha_ingreso': fecha_ingreso if fecha_ingreso else None
        }

        result = repo.update_equipo(id, update_data)
        return jsonify(result if isinstance(result, dict) else (result[0] if result else {}))
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_equipo(id):
    try:
        if not repo.get_equipo(id):
            return jsonify({'error': 'Equipo no encontrado'}), 404
        repo.delete_equipo(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ========== ROLES DE EMPRESA ==========
@app.route('/api/roles', methods=['GET'])
def get_roles():
    try:
        return jsonify(repo.get_all_roles()), 200
    except Exception as e:
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
        
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        if not departamento or departamento not in DEPARTAMENTOS_VALIDOS:
            return jsonify({'error': f'Departamento inválido. Deben ser: {", ".join(DEPARTAMENTOS_VALIDOS)}'}), 400
        
        result = repo.create_rol({
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
        return _server_error(e)

@app.route('/api/roles/<int:id>', methods=['PUT'])
@require_api_login
def update_rol(id):
    """Actualizar rol"""
    try:
        if not repo.get_rol(id):
            return jsonify({'error': 'Rol no encontrado'}), 404

        data = request.json or {}
        
        if not isinstance(data, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
        nombre = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '')
        departamento = data.get('departamento', '')
        
        
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
        
        result = repo.update_rol(id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify(result), 400

        updated = repo.get_rol(id)
        return jsonify(updated or {'id': id, 'nombre': nombre, 'descripcion': descripcion, 'departamento': departamento}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/roles/<int:id>', methods=['DELETE'])
@require_api_login
def delete_rol(id):
    try:
        if not repo.get_rol(id):
            return jsonify({'error': 'Rol no encontrado'}), 404
        repo.delete_rol(id)
        return jsonify({'ok': True}), 200
    except Exception as e:
        return _server_error(e)

# ========== MANTENIMIENTOS ==========
@app.route('/api/mantenimientos', methods=['GET'])
def get_all_mantenimientos():
    try:
        return jsonify(repo.get_all_mantenimientos())
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos/<int:id>/mantenimientos', methods=['GET'])
def get_mants_equipo(id):
    try:
        return jsonify(repo.get_mantenimientos_by_equipo(id))
    except Exception as e:
        return _server_error(e)

@app.route('/api/mantenimientos', methods=['POST'])
@require_api_login
def create_mantenimiento():
    try:
        d = request.json
        
        # Validar enums
        
        if d.get('tipo') not in TIPOS_MANTENIMIENTO:
            return jsonify({'error': f'Tipo inválido. Debe ser uno de: {", ".join(TIPOS_MANTENIMIENTO)}'}), 400
        if d.get('estado', 'completado') not in ESTADOS_MANTENIMIENTO:
            return jsonify({'error': f'Estado inválido. Debe ser uno de: {", ".join(ESTADOS_MANTENIMIENTO)}'}), 400
        
        mant_result = repo.create_mantenimiento({
            'equipo_id': d['equipo_id'],
            'tipo': d['tipo'],
            'descripcion': d['descripcion'],
            'fecha': d['fecha'],
            'tecnico': d.get('tecnico', ''),
            'costo': d.get('costo', 0),
            'estado': d.get('estado', 'completado'),
            'proxima_revision': d.get('proxima_revision') or None
        })

        repo.create_hoja_vida({
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
        return _server_error(e)

@app.route('/api/mantenimientos/<int:id>', methods=['PUT'])
@require_api_login
def update_mantenimiento(id):
    try:
        if not repo.get_mantenimiento(id):
            return jsonify({'error': 'Mantenimiento no encontrado'}), 404
        
        d = request.json or {}
        
        if not isinstance(d, dict):
            return jsonify({'error': 'Datos inválidos'}), 400
        
        # Validar estados de mantenimiento
        if d.get('estado') and d.get('estado') not in ESTADOS_MANTENIMIENTO:
            return jsonify({'error': f'Estado inválido. Debe ser uno de: {", ".join(ESTADOS_MANTENIMIENTO)}'}), 400
        
        # Validar tipo de mantenimiento
        if d.get('tipo') and d.get('tipo') not in TIPOS_MANTENIMIENTO:
            return jsonify({'error': f'Tipo inválido. Debe ser uno de: {", ".join(TIPOS_MANTENIMIENTO)}'}), 400
        
        result = repo.update_mantenimiento(id, {
            'tipo': d['tipo'],
            'descripcion': d['descripcion'],
            'fecha': d['fecha'],
            'tecnico': d.get('tecnico', ''),
            'costo': d.get('costo', 0),
            'estado': d.get('estado', 'completado'),
            'proxima_revision': d.get('proxima_revision') or None
        })

        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 200

        if isinstance(result, list):
            updated = repo.get_mantenimiento(id)
            if updated:
                return jsonify(updated), 200

        return jsonify({'ok': True}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/mantenimientos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_mantenimiento(id):
    try:
        if not repo.get_mantenimiento(id):
            return jsonify({'error': 'Mantenimiento no encontrado'}), 404
        repo.delete_mantenimiento(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ========== HOJA DE VIDA ==========
@app.route('/api/equipos/<int:id>/hoja_vida', methods=['GET'])
def get_hoja_vida(id):
    try:
        return jsonify(repo.get_hoja_vida_by_equipo(id))
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos/<int:id>/hoja_vida', methods=['POST'])
def add_hoja_vida(id):
    try:
        d = request.json
        result = repo.create_hoja_vida({
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
        return _server_error(e)

@app.route('/api/hoja_vida/<int:id>', methods=['DELETE'])
def delete_hoja_vida(id):
    try:
        repo.delete_hoja_vida(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ========== PRÉSTAMOS ==========
@app.route('/api/prestamos', methods=['GET'])
@require_api_login
def get_prestamos():
    try:
        return jsonify(repo.get_all_prestamos())
    except Exception as e:
        return _server_error(e)

@app.route('/api/prestamos/<int:id>', methods=['GET'])
def get_prestamo(id):
    """Público — usado por la página de firma."""
    try:
        loan = repo.get_prestamo(id)
        if loan is None:
            return jsonify({'error': 'Préstamo no encontrado'}), 404
        return jsonify(loan)
    except Exception as e:
        return _server_error(e)


@app.route('/api/prestamos/<int:id>/detalle', methods=['GET'])
@require_api_login
def get_prestamo_detalle(id):
    """Get detailed loan information including timeline"""
    try:
        loan = repo.get_prestamo(id)
        if loan is None:
            return jsonify({'error': 'Préstamo no encontrado'}), 404

        if loan.get('equipo_id'):
            eq = repo.get_equipo(loan['equipo_id'])
            if eq:
                loan['equipo'] = {
                    'id': eq.get('id'),
                    'nombre': eq.get('nombre'),
                    'tipo': eq.get('tipo'),
                    'serialno': eq.get('serialno'),
                    'valor': eq.get('valor')
                }

        if loan.get('usuario_id'):
            usr = repo.get_usuario(loan['usuario_id'])
            if usr:
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
        return _server_error(e)

@app.route('/api/prestamos', methods=['POST'])
@require_api_login
def create_prestamo():
    try:
        d = request.json

        equipo = repo.get_equipo(d['equipo_id'])
        if not equipo:
            return jsonify({'error': f'Equipo con ID {d["equipo_id"]} no encontrado'}), 400

        if not repo.get_usuario(d['usuario_id']):
            return jsonify({'error': f'Usuario con ID {d["usuario_id"]} no encontrado'}), 400

        if equipo.get('disponibilidad') == 'Retirado':
            return jsonify({'error': 'No se pueden crear préstamos de equipos retirados'}), 400

        if repo.get_prestamos_activos_by_equipo(d['equipo_id']):
            return jsonify({'error': 'El equipo ya tiene un prestamo no devuelto'}), 400

        result = repo.create_prestamo({
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
        return _server_error(e)

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
            return _server_error(e)
        
        # Guardar URL en sesión
        session_key = f'loan_{id}_img{numero}'
        session[session_key] = img_url
        
        return jsonify({'ok': True, 'url': img_url}), 201
        
    except Exception as e:
        return _server_error(e)


@app.route('/api/prestamos/<int:id>/save-signature', methods=['POST'])
def save_signature_complete(id):
    """Save signature and update loan record"""
    try:
        firma_file = request.files.get('firma')
        tipo_firma = request.form.get('tipo', 'inicial')
        img1_url = request.form.get('img1_url')
        img2_url = request.form.get('img2_url')
        terminos_aceptados = request.form.get('terminos_aceptados', 'false').lower() == 'true'
        
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
            return _server_error(e)
        
        # Actualizar BD
        if tipo_firma == 'inicial':
            update_data = {
                'firma_url': firma_url,
                'imagen1_url': img1_url,
                'imagen2_url': img2_url,
                'estado': 'firmado',
                'fecha_firma': datetime.now().isoformat(),
                'terminos_aceptados': terminos_aceptados,
                'fecha_aceptacion_terminos': datetime.now().isoformat()
            }
        else:
            update_data = {
                'firma_devolucion_url': firma_url,
                'imagen1_devolucion_url': img1_url,
                'imagen2_devolucion_url': img2_url,
                'estado': 'devuelto',
                'fecha_devolucion_real': datetime.now().isoformat()
            }
        
        result = repo.update_prestamo(id, update_data)

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
        return _server_error(e)


@app.route('/api/prestamos/<int:id>/devolver', methods=['PUT'])
def devolver_prestamo(id):
    """Marcar prestamo como devuelto (después de que firma la devolución)"""
    try:
        repo.update_prestamo(id, {
            'estado': 'devuelto',
            'fecha_devolucion_real': date.today().isoformat()
        })
        return jsonify({'ok': True, 'message': 'Prestamo marcado como devuelto'})
    except Exception as e:
        return _server_error(e)

@app.route('/api/prestamos/<int:id>', methods=['PUT'])
@require_api_login
def update_prestamo(id):
    """Editar un préstamo existente"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        prestamo_actual = repo.get_prestamo(id)
        if not prestamo_actual:
            return jsonify({'error': 'Préstamo no encontrado'}), 404

        nuevo_equipo_id = d.get('equipo_id', prestamo_actual.get('equipo_id'))
        equipo = repo.get_equipo(nuevo_equipo_id)
        if not equipo:
            return jsonify({'error': f'Equipo con ID {nuevo_equipo_id} no encontrado'}), 400

        nuevo_usuario_id = d.get('usuario_id', prestamo_actual.get('usuario_id'))
        if not repo.get_usuario(nuevo_usuario_id):
            return jsonify({'error': f'Usuario con ID {nuevo_usuario_id} no encontrado'}), 400

        if equipo.get('disponibilidad') == 'Retirado':
            return jsonify({'error': 'No se pueden editar préstamos a equipos retirados'}), 400

        if nuevo_equipo_id != prestamo_actual.get('equipo_id'):
            if repo.get_prestamos_activos_by_equipo(nuevo_equipo_id, exclude_id=id):
                return jsonify({'error': 'El nuevo equipo ya tiene un prestamo no devuelto'}), 400

        update_data = {
            'equipo_id': nuevo_equipo_id,
            'usuario_id': nuevo_usuario_id,
            'fecha_prestamo': d.get('fecha_prestamo', prestamo_actual.get('fecha_prestamo')),
            'fecha_devolucion_esperada': d.get('fecha_devolucion_esperada') or None,
            'notas': d.get('notas', '')
        }

        result = repo.update_prestamo(id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': 'No se pudo actualizar el préstamo: ' + str(result.get('error'))}), 500

        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return _server_error(e)

# ========== PRÉSTAMOS - DELETE ==========
@app.route('/api/prestamos/<int:id>', methods=['DELETE'])
def delete_prestamo(id):
    try:
        repo.delete_prestamo(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ========== LICENCIAS ==========
@app.route('/api/licencias', methods=['GET'])
@require_api_login
def get_licencias():
    try:
        return jsonify(repo.get_all_licencias()), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/licencias/<int:id>', methods=['GET'])
@require_api_login
def get_licencia(id):
    try:
        lic = repo.get_licencia(id)
        if lic:
            return jsonify(lic), 200
        return jsonify({'error': 'Licencia no encontrada'}), 404
    except Exception as e:
        return _server_error(e)

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
        
        result = repo.create_licencia({
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

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error en Supabase: {result.get('error')}"}), 500

        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        elif isinstance(result, dict) and 'id' in result:
            return jsonify({'id': result.get('id'), 'ok': True}), 201
        else:
            return jsonify({'error': 'Respuesta inesperada de Supabase', 'details': str(result)}), 500
    except Exception as e:
        return _server_error(e)

@app.route('/api/licencias/<int:id>', methods=['PUT'])
@require_api_login
def update_licencia(id):
    """Editar una licencia existente"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        licencia = repo.get_licencia(id)
        if not licencia:
            return jsonify({'error': 'Licencia no encontrada'}), 404

        costo = licencia.get('costo', 0) or 0
        try:
            costo_str = str(d.get('costo', costo)).strip()
            if costo_str and costo_str not in ['NaN', 'nan', '']:
                costo = float(costo_str)
        except (ValueError, TypeError):
            costo = licencia.get('costo', 0) or 0

        update_data = {
            'nombre': d.get('nombre', licencia.get('nombre')).strip(),
            'tipo': d.get('tipo', licencia.get('tipo')),
            'fecha_inicio': d.get('fecha_inicio', licencia.get('fecha_inicio')),
            'fecha_caducidad': d.get('fecha_caducidad', licencia.get('fecha_caducidad')),
            'proveedor': d.get('proveedor', licencia.get('proveedor', '')).strip(),
            'costo': costo,
            'descripcion': d.get('descripcion', licencia.get('descripcion', '')).strip(),
            'notas': d.get('notas', licencia.get('notas', '')).strip(),
            'estado': d.get('estado', licencia.get('estado', 'activa'))
        }

        result = repo.update_licencia(id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error en Supabase: {result.get('error')}"}), 500

        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/licencias/<int:id>', methods=['DELETE'])
@require_api_login
def delete_licencia(id):
    try:
        repo.delete_licencia(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ════════════════════════════════════════════════════════════════
# ASIGNACIÓN DE LICENCIAS A EQUIPOS (Relación muchos-a-muchos)
# ════════════════════════════════════════════════════════════════

@app.route('/api/equipos/<int:equipo_id>/licencias', methods=['GET'])
@require_api_login
def get_equipo_licencias(equipo_id):
    """Obtener todas las licencias asignadas a un equipo"""
    try:
        return jsonify(repo.get_licencias_by_equipo(equipo_id))
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos/<int:equipo_id>/licencias', methods=['POST'])
@require_api_login
def assign_licencia_to_equipo(equipo_id):
    """Asignar una licencia a un equipo"""
    try:
        d = request.json
        if not d or 'licencia_id' not in d:
            return jsonify({'error': 'licencia_id es requerido'}), 400
        
        if not repo.get_equipo(equipo_id):
            return jsonify({'error': 'Equipo no encontrado'}), 404

        if not repo.get_licencia(d['licencia_id']):
            return jsonify({'error': 'Licencia no encontrada'}), 404

        result = repo.assign_licencia_to_equipo({
            'equipo_id': equipo_id,
            'licencia_id': d['licencia_id'],
            'fecha_asignacion': d.get('fecha_asignacion', date.today().isoformat()),
            'notas': d.get('notas', '')
        })
        if isinstance(result, list) and len(result) > 0:
            return jsonify(result[0]), 201
        return jsonify(result), 201
    except Exception as e:
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return jsonify({'error': 'Esta licencia ya está asignada a este equipo'}), 400
        return _server_error(e)

@app.route('/api/equipos/<int:equipo_id>/licencias/<int:licencia_id>', methods=['DELETE'])
@require_api_login
def remove_licencia_from_equipo(equipo_id, licencia_id):
    """Desasignar una licencia de un equipo (método antiguo - por compatibilidad)"""
    try:
        repo.remove_licencia_from_equipo(equipo_id, licencia_id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

@app.route('/api/equipos-licencias/<int:asignacion_id>', methods=['DELETE'])
@require_api_login
def delete_equipos_licencias(asignacion_id):
    """Desasignar una licencia de un equipo por ID de asignación"""
    try:
        repo.delete_equipo_licencia(asignacion_id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ========== CALENDARIO ==========
@app.route('/api/calendario')
def get_calendario():
    try:
        events = []
        
        equipos = repo.get_all_equipos()
        usuarios = repo.get_all_usuarios()
        tipos = repo.get_all_tipos_equipos()
        
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
        mants = repo.get_mantenimientos_proxima_revision()
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
        
        # Préstamos - Mostrar TODOS con fechas relevantes
        prestamos = repo.get_prestamos_por_devolucion()
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
        return _server_error(e)

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
            equipos = repo.get_all_equipos()
            if equipos:
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
            usuarios = repo.get_all_usuarios()
            if usuarios:
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
            prestamos = repo.get_prestamos_raw()
            if prestamos:
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
        return _server_error(e)

# ========== HISTORIAL DE RESPONSABLES ==========
@app.route('/api/equipos/<int:id>/historial-responsables', methods=['GET'])
@require_api_login
def get_historial_responsables(id):
    """Obtener historial de cambios de responsable de un equipo"""
    try:
        equipo = repo.get_equipo(id)
        if not equipo:
            return jsonify({'error': 'Equipo no encontrado'}), 404

        hvs = repo.get_hoja_vida_by_equipo(id)
        hvs = [hv for hv in hvs if hv.get('tipo') == 'cambio_responsable']

        historial = []

        if equipo.get('usuario_id'):
            usr = repo.get_usuario(equipo['usuario_id'])
            usuario_actual = usr['nombre'] if usr else 'Desconocido'
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
        return _server_error(e)

# ========== MATRIZ DE RESPONSABILIDAD ==========
@app.route('/api/estadisticas/matriz-responsabilidad')
@require_api_login
def matriz_responsabilidad():
    """Estadísticas: quién tiene cuántos equipos"""
    try:
        equipos = repo.get_all_equipos()
        usuarios = repo.get_all_usuarios()
        
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
        return _server_error(e)

# ========== REGISTRAR CAMBIO DE RESPONSABLE ==========
@app.route('/api/equipos/<int:id>/cambiar-responsable', methods=['POST'])
@require_api_login
def cambiar_responsable(id):
    """Cambiar responsable de un equipo y registrar en hoja_vida"""
    try:
        # Validar que request.json existe
        if not request.json:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        equipo = repo.get_equipo(id)
        if not equipo:
            return jsonify({'error': 'Equipo no encontrado'}), 404

        d = request.json
        nuevo_usuario_id = d.get('nuevo_usuario_id')
        motivo = d.get('motivo', 'Cambio de asignación')

        if not nuevo_usuario_id:
            return jsonify({'error': 'Nuevo usuario requerido'}), 400

        usuario_anterior_id = equipo.get('usuario_id')
        usuario_anterior_nombre = 'Desconocido'
        if usuario_anterior_id:
            usr_ant = repo.get_usuario(usuario_anterior_id)
            if usr_ant:
                usuario_anterior_nombre = usr_ant.get('nombre', 'Desconocido')

        usr_nuevo = repo.get_usuario(nuevo_usuario_id)
        if not usr_nuevo:
            return jsonify({'error': 'Usuario nuevo no encontrado'}), 400

        usuario_nuevo_nombre = usr_nuevo.get('nombre', 'Desconocido')

        today = date.today().isoformat()
        update_result = repo.update_equipo(id, {
            'usuario_id': nuevo_usuario_id,
            'fecha_asignacion': today
        })

        if isinstance(update_result, dict) and update_result.get('error'):
            return jsonify({'error': 'No se pudo actualizar el equipo: ' + str(update_result.get('error'))}), 500

        titulo = f"Cambio de responsable: {usuario_anterior_nombre} → {usuario_nuevo_nombre}"
        repo.create_hoja_vida({
            'equipo_id': id,
            'tipo': 'cambio_responsable',
            'titulo': titulo,
            'descripcion': motivo,
            'fecha': today,
            'responsable': session.get('username', 'Sistema')
        })
        
        return jsonify({
            'ok': True,
            'mensaje': f'Responsable cambiado de {usuario_anterior_nombre} a {usuario_nuevo_nombre}'
        }), 200
    except Exception as e:
        return _server_error(e)

# ========== APLICATIVOS Y PAGOS ==========
@app.route('/api/aplicativos', methods=['GET'])
@require_api_login
def get_aplicativos():
    """Obtener todos los aplicativos"""
    try:
        return jsonify(repo.get_all_aplicativos()), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/aplicativos/<int:id>', methods=['GET'])
@require_api_login
def get_aplicativo(id):
    try:
        ap = repo.get_aplicativo(id)
        if ap:
            return jsonify(ap), 200
        return jsonify({'error': 'Aplicativo no encontrado'}), 404
    except Exception as e:
        return _server_error(e)

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
        
        result = repo.create_aplicativo({
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
        return _server_error(e)

@app.route('/api/aplicativos/<int:id>', methods=['PUT'])
@require_api_login
def update_aplicativo(id):
    """Actualizar un aplicativo"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        app_exist = repo.get_aplicativo(id)
        if not app_exist:
            return jsonify({'error': 'Aplicativo no encontrado'}), 404

        if d.get('periodicidad'):
            PERIODICIDADES = ['Mensual', 'Trimestral', 'Semestral', 'Anual']
            if d.get('periodicidad') not in PERIODICIDADES:
                return jsonify({'error': f'Periodicidad inválida. Debe ser: {", ".join(PERIODICIDADES)}'}), 400

        if d.get('tarjeta'):
            TARJETAS = ['4184', '1111']
            if d.get('tarjeta') not in TARJETAS:
                return jsonify({'error': f'Tarjeta inválida. Debe ser: {", ".join(TARJETAS)}'}), 400

        update_data = {
            'nombre': d.get('nombre', app_exist.get('nombre')).strip(),
            'fecha_pago': d.get('fecha_pago', app_exist.get('fecha_pago')),
            'fecha_caducidad': d.get('fecha_caducidad', app_exist.get('fecha_caducidad')),
            'periodicidad': d.get('periodicidad', app_exist.get('periodicidad')),
            'tarjeta': d.get('tarjeta', app_exist.get('tarjeta')),
            'estado': d.get('estado', app_exist.get('estado', 'activo'))
        }

        result = repo.update_aplicativo(id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/aplicativos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_aplicativo(id):
    try:
        repo.delete_aplicativo(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ════════════════════════════════════════════════════════════════
# HISTORIAL DE PAGOS DE APLICATIVOS
# ════════════════════════════════════════════════════════════════

@app.route('/api/aplicativos/<int:aplicativo_id>/pagos', methods=['GET'])
@require_api_login
def get_pagos_aplicativo(aplicativo_id):
    """Obtener historial de pagos de un aplicativo"""
    try:
        return jsonify(repo.get_pagos_by_aplicativo(aplicativo_id)), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/aplicativos/<int:aplicativo_id>/pagos', methods=['POST'])
@require_api_login
def add_pago_aplicativo(aplicativo_id):
    """Agregar un pago al historial de un aplicativo"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        app_data = repo.get_aplicativo(aplicativo_id)
        if not app_data:
            return jsonify({'error': 'Aplicativo no encontrado'}), 404

        fecha_pago = d.get('fecha_pago', date.today().isoformat())
        fecha_caducidad = d.get('fecha_caducidad') or app_data.get('fecha_caducidad', date.today().isoformat())

        result = repo.create_pago_aplicativo({
            'aplicativo_id': aplicativo_id,
            'fecha_pago': fecha_pago,
            'fecha_caducidad': fecha_caducidad,
            'monto': d.get('monto', 0),
            'metodo_pago': d.get('metodo_pago', app_data.get('tarjeta', ''))
        })

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        repo.update_aplicativo(aplicativo_id, {
            'fecha_pago': fecha_pago,
            'fecha_caducidad': fecha_caducidad
        })
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        elif isinstance(result, dict) and 'id' in result:
            return jsonify({'id': result.get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return _server_error(e)

@app.route('/api/pagos-aplicativos/<int:pago_id>', methods=['DELETE'])
@require_api_login
def delete_pago_aplicativo_route(pago_id):
    try:
        repo.delete_pago_aplicativo(pago_id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ========== CELULARES Y SIM CARDS ==========
@app.route('/api/celulares', methods=['GET'])
@require_api_login
def get_celulares():
    """Obtener todos los celulares"""
    try:
        celulares = repo.get_all_celulares()
        simcards = repo.get_all_simcards()
        simcards_map: dict = {}
        for sim in simcards:
            cid = sim.get('celular_id')
            if cid:
                simcards_map.setdefault(cid, []).append(sim)
        for cel in celulares:
            cel['simcard'] = simcards_map.get(cel['id'], [])
        return jsonify(celulares), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/celulares/<int:id>', methods=['GET'])
@require_api_login
def get_celular(id):
    try:
        cel = repo.get_celular(id)
        if not cel:
            return jsonify({'error': 'Celular no encontrado'}), 404
        cel['simcard'] = repo.get_simcards_by_celular(id)
        return jsonify(cel), 200
    except Exception as e:
        return _server_error(e)

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
        if d.get('whatsapp') and d.get('whatsapp') not in WHATSAPP_STATUS:
            return jsonify({'error': f'WhatsApp debe ser: {", ".join(WHATSAPP_STATUS)}'}), 400
        
        # Validar Estado
        ESTADO_CELULAR = ['bueno', 'regular', 'dañado', 'en_reparacion', 'bloqueado', 'reserva']
        if d.get('estado') and d.get('estado') not in ESTADO_CELULAR:
            return jsonify({'error': f'Estado debe ser: {", ".join(ESTADO_CELULAR)}'}), 400
        
        result = repo.create_celular({
            'nombre': d['nombre'].strip(),
            'marca': d['marca'].strip(),
            'imei': d['imei'].strip(),
            'imei2': d.get('imei2', '').strip(),
            'whatsapp': d.get('whatsapp', 'activo'),
            'estado': d.get('estado', 'bueno')
        })
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return _server_error(e)

@app.route('/api/celulares/<int:id>', methods=['PUT'])
@require_api_login
def update_celular(id):
    """Actualizar un celular"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        cel_exist = repo.get_celular(id)
        if not cel_exist:
            return jsonify({'error': 'Celular no encontrado'}), 404

        if d.get('whatsapp') and d.get('whatsapp') not in WHATSAPP_STATUS:
            return jsonify({'error': f'WhatsApp debe ser: {", ".join(WHATSAPP_STATUS)}'}), 400

        if d.get('estado'):
            ESTADO_CELULAR = ['bueno', 'regular', 'dañado', 'en_reparacion', 'bloqueado', 'reserva']
            if d.get('estado') not in ESTADO_CELULAR:
                return jsonify({'error': f'Estado debe ser: {", ".join(ESTADO_CELULAR)}'}), 400

        update_data = {
            'nombre': d.get('nombre', cel_exist.get('nombre')).strip(),
            'marca': d.get('marca', cel_exist.get('marca')).strip(),
            'imei': d.get('imei', cel_exist.get('imei')).strip(),
            'imei2': d.get('imei2', cel_exist.get('imei2', '')).strip(),
            'whatsapp': d.get('whatsapp', cel_exist.get('whatsapp', 'activo')),
            'estado': d.get('estado', cel_exist.get('estado', 'bueno'))
        }

        result = repo.update_celular(id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        return jsonify({'ok': True, 'id': id}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/celulares/<int:id>', methods=['DELETE'])
@require_api_login
def delete_celular_route(id):
    try:
        repo.delete_celular(id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ════════════════════════════════════════════════════════════════
# SIM CARDS - HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════

def cleanup_simcard_duplicates():
    """Elimina SIM cards duplicadas (mantiene la más antigua)"""
    try:
        all_sims = repo.get_all_simcards_raw()
        numero_map: dict = {}
        for sim in all_sims:
            numero = sim.get('numero')
            if numero:
                numero_map.setdefault(numero, []).append(sim)
        for sims_list in numero_map.values():
            if len(sims_list) > 1:
                sims_list.sort(key=lambda x: x.get('created_at', ''))
                for sim_to_delete in sims_list[1:]:
                    repo.delete_simcard(sim_to_delete['id'])
    except Exception as e:
        print(f"Error limpiando duplicados: {str(e)}")

# ════════════════════════════════════════════════════════════════
# SIM CARDS
# ════════════════════════════════════════════════════════════════

@app.route('/api/simcards', methods=['GET'])
@require_api_login
def get_simcards():
    """Obtener todas las SIM cards"""
    try:
        simcards = repo.get_all_simcards()
        celulares_map = {c['id']: c for c in repo.get_all_celulares()}
        for sim in simcards:
            sim['celular'] = celulares_map.get(sim.get('celular_id'))
        return jsonify(simcards), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/simcards/<int:id>', methods=['GET'])
@require_api_login
def get_simcard_route(id):
    """Obtener una SIM card específica"""
    try:
        sim = repo.get_simcard(id)
        if not sim:
            return jsonify({'error': 'SIM card no encontrada'}), 404
        if sim.get('celular_id'):
            sim['celular'] = repo.get_celular(sim['celular_id'])
        sim['historial_bloqueos'] = repo.get_bloqueos_by_simcard(id)
        return jsonify(sim), 200
    except Exception as e:
        return _server_error(e)

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
        
        numero_limpio = d.get('numero').strip()
        numero_encoded = quote(numero_limpio, safe='')
        if repo.get_simcard_by_numero(numero_encoded):
            return jsonify({'error': f'Ya existe una SIM card con el número {numero_limpio}'}), 400

        OPERADORES = ['Movistar', 'Claro', 'Tigo', 'WOM', 'Exito']
        if d.get('operador') not in OPERADORES:
            return jsonify({'error': f'Operador debe ser: {", ".join(OPERADORES)}'}), 400

        if d.get('estado') and d.get('estado') not in ESTADOS_SIM:
            return jsonify({'error': f'Estado debe ser: {", ".join(ESTADOS_SIM)}'}), 400

        APPS = ['whatsapp', 'whatsapp_business']
        if d.get('app') and d.get('app') not in APPS:
            return jsonify({'error': f'App debe ser: {", ".join(APPS)}'}), 400

        if d.get('celular_id'):
            if not repo.get_celular(d['celular_id']):
                return jsonify({'error': 'Celular no encontrado'}), 404
            if repo.get_simcard_count_by_celular(d['celular_id']) >= 3:
                return jsonify({'error': 'Este celular ya tiene 3 números. Máximo permitido es 3 por celular'}), 400

        result = repo.create_simcard({
            'numero': numero_limpio,
            'serial': d.get('serial', '').strip(),
            'operador': d['operador'],
            'estado': d.get('estado', 'activo'),
            'app': d.get('app', 'whatsapp'),
            'sendflow': d.get('sendflow', 'no'),
            'celular_id': d.get('celular_id', None)
        })

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        if isinstance(result, list) and len(result) > 0:
            new_id = result[0].get('id')
            if d.get('celular_id'):
                repo.create_historial_sim_celular({'celular_id': d['celular_id'], 'simcard_id': new_id})
            cleanup_simcard_duplicates()
            return jsonify({'id': new_id, 'ok': True}), 201
        else:
            cleanup_simcard_duplicates()
            return jsonify({'ok': True}), 201
    except Exception as e:
        return _server_error(e)

@app.route('/api/simcards/<int:id>', methods=['PUT'])
@require_api_login
def update_simcard(id):
    """Actualizar una SIM card"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        sim_exist = repo.get_simcard(id)
        if not sim_exist:
            return jsonify({'error': 'SIM card no encontrada'}), 404

        old_celular_id = sim_exist.get('celular_id')
        new_celular_id = d.get('celular_id') if 'celular_id' in d else old_celular_id

        if d.get('numero') and d.get('numero').strip() != sim_exist.get('numero'):
            numero_nuevo = d.get('numero').strip()
            numero_encoded = quote(numero_nuevo, safe='')
            if repo.get_simcard_by_numero(numero_encoded):
                return jsonify({'error': f'Ya existe una SIM card con el número {numero_nuevo}'}), 400

        if d.get('operador'):
            OPERADORES = ['Movistar', 'Claro', 'Tigo', 'WOM', 'Exito']
            if d.get('operador') not in OPERADORES:
                return jsonify({'error': f'Operador debe ser: {", ".join(OPERADORES)}'}), 400

        if d.get('estado') and d.get('estado') not in ESTADOS_SIM:
            return jsonify({'error': f'Estado debe ser: {", ".join(ESTADOS_SIM)}'}), 400

        if d.get('app'):
            APPS = ['whatsapp', 'whatsapp_business']
            if d.get('app') not in APPS:
                return jsonify({'error': f'App debe ser: {", ".join(APPS)}'}), 400

        if new_celular_id:
            if not repo.get_celular(new_celular_id):
                return jsonify({'error': 'Celular no encontrado'}), 404
            if new_celular_id != old_celular_id and repo.get_simcard_count_by_celular(new_celular_id) >= 3:
                return jsonify({'error': 'El nuevo celular ya tiene 3 números. Máximo permitido es 3 por celular'}), 400

        update_data = {
            'numero': d.get('numero', sim_exist.get('numero')).strip(),
            'serial': d.get('serial', sim_exist.get('serial', '')).strip(),
            'operador': d.get('operador', sim_exist.get('operador')),
            'estado': d.get('estado', sim_exist.get('estado', 'activo')),
            'app': d.get('app', sim_exist.get('app', 'whatsapp')),
            'sendflow': d.get('sendflow', sim_exist.get('sendflow', 'no')),
            'celular_id': new_celular_id
        }

        old_estado = sim_exist.get('estado')
        new_estado = update_data.get('estado')
        if old_estado != new_estado:
            repo.create_historial_accion_simcard({
                'simcard_id': id,
                'accion': 'cambio_estado',
                'valor_anterior': old_estado,
                'valor_nuevo': new_estado,
                'fecha_hora': datetime.now().isoformat()
            })

        if old_celular_id != new_celular_id:
            if old_celular_id:
                repo.update_historial_sim_celular_by_sim(id, {'fecha_removida': datetime.now().isoformat()})
            if new_celular_id:
                repo.create_historial_sim_celular({'celular_id': new_celular_id, 'simcard_id': id})

        result = repo.update_simcard(id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        if repo.get_simcard(id):
            cleanup_simcard_duplicates()
            return jsonify({'ok': True, 'id': id}), 200
        else:
            return jsonify({'error': 'Error al actualizar SIM card'}), 500
    except Exception as e:
        return _server_error(e)

@app.route('/api/simcards/<int:id>', methods=['DELETE'])
@require_api_login
def delete_simcard(id):
    """Desasignar una SIM card del celular actual (no la elimina)
    
    Parámetro query: ?permanently=true para eliminar completamente
    """
    try:
        permanently = request.args.get('permanently', 'false').lower() == 'true'
        
        sim_data = repo.get_simcard(id)
        if not sim_data:
            return jsonify({'error': 'SIM card no encontrada'}), 404

        celular_id = sim_data.get('celular_id')

        if permanently:
            if celular_id:
                repo.update_historial_sim_celular_by_sim(id, {'fecha_removida': datetime.now().isoformat()})
            repo.delete_simcard(id)
            return jsonify({'ok': True, 'message': 'SIM card eliminada permanentemente'})
        else:
            if celular_id:
                repo.update_historial_sim_celular_by_sim(id, {'fecha_removida': datetime.now().isoformat()})
            repo.update_simcard(id, {'celular_id': None})
            return jsonify({'ok': True, 'message': 'SIM card desasignada del celular'})
    except Exception as e:
        return _server_error(e)

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
        
        sim_data = repo.get_simcard(id)
        if not sim_data:
            return jsonify({'error': 'SIM card no encontrada'}), 404

        old_celular_id = sim_data.get('celular_id')

        if not repo.get_celular(nuevo_celular_id):
            return jsonify({'error': 'Celular destino no encontrado'}), 404

        if nuevo_celular_id != old_celular_id and repo.get_simcard_count_by_celular(nuevo_celular_id) >= 3:
            return jsonify({'error': 'El celular destino ya tiene 3 números. Máximo permitido es 3 por celular'}), 400

        result = repo.update_simcard(id, {'celular_id': nuevo_celular_id})

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        if old_celular_id:
            repo.update_historial_sim_celular_by_sim(id, {'fecha_removida': datetime.now().isoformat()})
        repo.create_historial_sim_celular({'celular_id': nuevo_celular_id, 'simcard_id': id})
        
        return jsonify({'ok': True, 'id': id, 'message': f'SIM card reasignada de celular {old_celular_id} a {nuevo_celular_id}'}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/simcards/cleanup/duplicates', methods=['POST'])
@require_api_login
def cleanup_duplicates_route():
    """Limpia manualmente duplicados en SIM cards"""
    try:
        cleanup_simcard_duplicates()
        return jsonify({'ok': True, 'message': 'Duplicados eliminados'}), 200
    except Exception as e:
        return _server_error(e)

# ════════════════════════════════════════════════════════════════
# HISTORIAL DE BLOQUEOS DE SIM CARDS
# ════════════════════════════════════════════════════════════════

@app.route('/api/simcards/<int:simcard_id>/bloqueos', methods=['GET'])
@require_api_login
def get_bloqueos_simcard(simcard_id):
    """Obtener historial de bloqueos de una SIM card"""
    try:
        return jsonify(repo.get_bloqueos_by_simcard(simcard_id)), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/simcards/<int:simcard_id>/historial-acciones', methods=['GET'])
@require_api_login
def get_historial_acciones_simcard(simcard_id):
    """Obtener historial automático de cambios en una SIM card"""
    try:
        result = repo.get_historial_acciones_simcard(simcard_id)
        if isinstance(result, list):
            return jsonify(result), 200
        return jsonify([]), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/simcards/<int:simcard_id>/bloqueos', methods=['POST'])
@require_api_login
def add_bloqueo_simcard(simcard_id):
    """Registrar un bloqueo de SIM card"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        if not repo.get_simcard(simcard_id):
            return jsonify({'error': 'SIM card no encontrada'}), 404

        result = repo.create_bloqueo_simcard({
            'simcard_id': simcard_id,
            'fecha_bloqueo': d.get('fecha_bloqueo', date.today().isoformat()),
            'fecha_desbloqueo': d.get('fecha_desbloqueo', None),
            'razon': d.get('razon', ''),
            'notas': d.get('notas', '')
        })

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        repo.update_simcard(simcard_id, {'estado': 'bloqueado'})
        
        if isinstance(result, list) and len(result) > 0:
            return jsonify({'id': result[0].get('id'), 'ok': True}), 201
        else:
            return jsonify({'ok': True}), 201
    except Exception as e:
        return _server_error(e)

@app.route('/api/bloqueos/<int:bloqueo_id>', methods=['PUT'])
@require_api_login
def update_bloqueo_simcard(bloqueo_id):
    """Actualizar un registro de bloqueo (especialmente fecha_desbloqueo)"""
    try:
        d = request.json
        if not d:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        bloqueo_exist = repo.get_bloqueo(bloqueo_id)
        if not bloqueo_exist:
            return jsonify({'error': 'Bloqueo no encontrado'}), 404

        update_data = {
            'fecha_bloqueo': d.get('fecha_bloqueo', bloqueo_exist.get('fecha_bloqueo')),
            'fecha_desbloqueo': d.get('fecha_desbloqueo', bloqueo_exist.get('fecha_desbloqueo')),
            'razon': d.get('razon', bloqueo_exist.get('razon', '')),
            'notas': d.get('notas', bloqueo_exist.get('notas', ''))
        }

        result = repo.update_bloqueo_simcard(bloqueo_id, update_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f"Error: {result.get('error')}"}), 500

        return jsonify({'ok': True, 'id': bloqueo_id}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/bloqueos/<int:bloqueo_id>', methods=['DELETE'])
@require_api_login
def delete_bloqueo_simcard_route(bloqueo_id):
    try:
        repo.delete_bloqueo_simcard(bloqueo_id)
        return jsonify({'ok': True})
    except Exception as e:
        return _server_error(e)

# ════════════════════════════════════════════════════════════════
# HISTORIAL DE SIM CARDS POR CELULAR
# ════════════════════════════════════════════════════════════════

@app.route('/api/celulares/<int:celular_id>/historial-sims', methods=['GET'])
@require_api_login
def get_historial_sims_celular(celular_id):
    """Obtener historial completo de SIM cards para un celular"""
    try:
        # Obtener historial con detalles de las SIM cards
        historial = repo.get_historial_sims_celular(celular_id)
        historial_enriquecido = []
        for h in historial:
            sim = repo.get_simcard(h.get('simcard_id'))
            historial_enriquecido.append({
                'id': h.get('id'),
                'celular_id': h.get('celular_id'),
                'simcard_id': h.get('simcard_id'),
                'fecha_agregada': h.get('fecha_agregada'),
                'fecha_removida': h.get('fecha_removida'),
                'notas': h.get('notas'),
                'simcard': sim
            })
        
        return jsonify(historial_enriquecido), 200
    except Exception as e:
        return _server_error(e)

# ════════════════════════════════════════════════════════════════
# ASIGNACIONES DE EQUIPOS - Entrada/Salida con Firma Digital
# ════════════════════════════════════════════════════════════════

@app.route('/api/asignaciones-equipos', methods=['GET'])
@require_api_login
def get_asignaciones_equipos():
    try:
        return jsonify(repo.get_all_asignaciones()), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/asignaciones-equipos/<int:id>', methods=['GET'])
@require_api_login
def get_asignacion_equipo(id):
    try:
        asig = repo.get_asignacion(id)
        if asig is None:
            return jsonify({'error': 'Asignación no encontrada'}), 404
        return jsonify(asig), 200
    except Exception as e:
        return _server_error(e)

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
        
        equipo = repo.get_equipo(equipo_id)
        if not equipo:
            return jsonify({'error': f'Equipo con ID {equipo_id} no encontrado'}), 404

        usuario = repo.get_usuario(usuario_id)
        if not usuario:
            return jsonify({'error': f'Usuario con ID {usuario_id} no encontrado'}), 404

        if usuario.get('estado') != 'activo':
            return jsonify({'error': 'El usuario debe estar activo para recibir equipos'}), 400

        disponibilidad = equipo.get('disponibilidad', '')
        if 'retirado' in disponibilidad.lower() or 'baja' in disponibilidad.lower():
            return jsonify({'error': f'No se puede asignar equipo con estado: {disponibilidad}'}), 400

        existing_list = repo.get_asignaciones_activas_by_equipo(equipo_id)
        if existing_list:
            asig_exist = existing_list[0]
            cinco_segundos_atras = (datetime.now() - timedelta(seconds=5)).isoformat()
            if (asig_exist.get('usuario_id') == usuario_id
                    and asig_exist.get('fecha_asignacion', '') > cinco_segundos_atras):
                return jsonify({
                    'id': asig_exist.get('id'),
                    'ok': True,
                    'message': 'Asignación ya existe (posible click duplicado)'
                }), 201
            return jsonify({'error': 'Este equipo ya tiene una asignación abierta'}), 400

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

        result = repo.create_asignacion(asig_data)

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f'Database error: {result.get("error")}'}), 500

        asignacion_id = None
        if isinstance(result, list) and len(result) > 0:
            asignacion_id = result[0].get('id')
        elif isinstance(result, dict) and 'id' in result:
            asignacion_id = result.get('id')
        elif isinstance(result, list) and len(result) == 0:
            recuperado = repo.get_ultima_asignacion_abierta_by_equipo_usuario(equipo_id, usuario_id)
            if recuperado:
                asignacion_id = recuperado.get('id')

        if not asignacion_id:
            return jsonify({'error': 'Failed to create assignment: ID not found after creation', 'debug': str(result)}), 500

        repo.update_equipo(equipo_id, {'usuario_id': usuario_id})

        repo.create_hoja_vida({
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
        return _server_error(e)

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
            return _server_error(e)
        
        # Guardar URL en sesión
        session_key = f'asig_{id}_img{numero}_{tipo}'
        session[session_key] = img_url
        
        return jsonify({'ok': True, 'url': img_url}), 201
    except Exception as e:
        return _server_error(e)

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
        
        if not repo.get_asignacion_raw(id):
            return jsonify({'error': 'Asignación no encontrada'}), 404

        firma_content = firma_file.read()
        if not firma_content or len(firma_content) == 0:
            return jsonify({'error': 'Signature is empty'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"asignacion_{id}"
        firma_path = f"{folder}/firma_entrada_{timestamp}.jpg"

        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return _server_error(e)

        result = repo.update_asignacion(id, {
            'firma_entrada_url': firma_url,
            'fecha_firma_entrada': datetime.now().isoformat()
        })

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': str(result.get('error'))}), 500
        
        return jsonify({
            'ok': True,
            'message': 'Firma de entrada registrada exitosamente'
        }), 200
    except Exception as e:
        return _server_error(e)

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
        
        asig = repo.get_asignacion_raw(id)
        if not asig:
            return jsonify({'error': 'Asignación no encontrada'}), 404

        if asig.get('estado') != 'abierta':
            return jsonify({'error': 'Solo se pueden cerrar asignaciones abiertas'}), 400

        firma_content = firma_file.read()
        if not firma_content or len(firma_content) == 0:
            return jsonify({'error': 'Signature is empty'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"asignacion_{id}"
        firma_path = f"{folder}/firma_salida_{timestamp}.jpg"

        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return _server_error(e)

        result = repo.update_asignacion(id, {
            'firma_salida_url': firma_url,
            'estado_equipo_salida': estado_equipo,
            'notas_salida': notas,
            'fecha_firma_salida': datetime.now().isoformat(),
            'fecha_devolucion': datetime.now().isoformat(),
            'estado': 'cerrada'
        })

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': str(result.get('error'))}), 500

        equipo_id = asig.get('equipo_id')
        if equipo_id:
            repo.update_equipo(equipo_id, {'usuario_id': None, 'disponibilidad': 'Disponible'})

        usr = repo.get_usuario(asig.get('usuario_id'))
        usuario_nombre = usr.get('nombre', 'Desconocido') if usr else 'Desconocido'

        repo.create_hoja_vida({
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
        return _server_error(e)


@app.route('/api/asignaciones-equipos/<int:id>', methods=['DELETE'])
@require_api_login
def delete_asignacion_route(id):
    """Eliminar una asignacion de equipo"""
    try:
        asig = repo.get_asignacion_raw(id)
        if not asig:
            return jsonify({'error': 'Asignacion no encontrada'}), 404

        equipo_id = asig.get('equipo_id')
        if equipo_id:
            repo.update_equipo(equipo_id, {'usuario_id': None, 'disponibilidad': 'Disponible'})

        repo.delete_asignacion(id)
        return jsonify({'ok': True, 'message': 'Asignacion eliminada'}), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/asignaciones-equipos/<int:id>/reasignar', methods=['PATCH'])
@require_api_login
def reassign_asignacion(id):
    """Reasignar equipo de un usuario a otro (requiere desasignación previa o equipo sin responsable)"""
    try:
        # Obtener ID del nuevo usuario
        data = request.json or {}
        nuevo_usuario_id = data.get('nuevo_usuario_id')
        
        if not nuevo_usuario_id:
            return jsonify({'error': 'nuevo_usuario_id es requerido'}), 400
        
        # Convertir a int
        try:
            nuevo_usuario_id = int(nuevo_usuario_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'nuevo_usuario_id debe ser un número'}), 400
        
        asig = repo.get_asignacion_raw(id)
        if not asig:
            return jsonify({'error': 'Asignacion no encontrada'}), 404

        if asig.get('estado') != 'desasignada':
            return jsonify({'error': 'Solo se pueden reasignar asignaciones que han sido desasignadas. Estado actual: ' + asig.get('estado', 'desconocido')}), 400

        nuevo_usuario = repo.get_usuario(nuevo_usuario_id)
        if not nuevo_usuario:
            return jsonify({'error': f'Usuario con ID {nuevo_usuario_id} no encontrado'}), 404

        if nuevo_usuario.get('estado') != 'activo':
            return jsonify({'error': 'El nuevo usuario debe estar activo'}), 400

        update_result = repo.update_asignacion(id, {
            'usuario_id': nuevo_usuario_id,
            'estado': 'abierta',
            'fecha_asignacion': datetime.now().isoformat()
        })

        if isinstance(update_result, dict) and update_result.get('error'):
            return jsonify({'error': f'Error al actualizar asignación: {update_result.get("error")}'}), 500

        equipo_id = asig.get('equipo_id')
        if equipo_id:
            equipo_update = repo.update_equipo(equipo_id, {'usuario_id': nuevo_usuario_id})

            if isinstance(equipo_update, dict) and equipo_update.get('error'):
                return jsonify({'error': f'Error al actualizar responsable del equipo: {equipo_update.get("error")}'}), 500

            nuevo_usuario_nombre = nuevo_usuario.get('nombre', 'Desconocido')
            repo.create_hoja_vida({
                'equipo_id': equipo_id,
                'tipo': 'reasignacion',
                'titulo': f'Reasignado a {nuevo_usuario_nombre}',
                'descripcion': f'Equipo reasignado a {nuevo_usuario_nombre}.',
                'fecha': date.today().isoformat(),
                'responsable': session.get('username', 'Sistema')
            })
        
        return jsonify({
            'ok': True,
            'message': f'Equipo reasignado a {nuevo_usuario.get("nombre")} exitosamente'
        }), 200
    except Exception as e:
        return _server_error(e)

@app.route('/api/asignaciones-equipos/<int:id>/desasignar', methods=['PATCH'])
@require_api_login
def unassign_asignacion(id):
    """Desasignar equipo: cambiar estado a desasignada, limpiar usuario_id y guardar en historial"""
    try:
        asig = repo.get_asignacion_raw(id)
        if not asig:
            return jsonify({'error': 'Asignacion no encontrada'}), 404

        if asig.get('estado') != 'cerrada':
            return jsonify({'error': 'Solo se pueden desasignar asignaciones cerradas'}), 400

        equipo_id = asig.get('equipo_id')
        usuario_id = asig.get('usuario_id')

        usr = repo.get_usuario(usuario_id)
        usuario_nombre = usr.get('nombre', 'Desconocido') if usr else 'Desconocido'

        if equipo_id:
            equipo_update = repo.update_equipo(equipo_id, {'usuario_id': None, 'disponibilidad': 'Disponible'})
            if isinstance(equipo_update, dict) and equipo_update.get('error'):
                return jsonify({'error': f'Error al limpiar responsable del equipo: {equipo_update.get("error")}'}), 500

        result = repo.update_asignacion(id, {'estado': 'desasignada'})

        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': f'Error al actualizar estado: {result.get("error")}'}), 500

        repo.create_hoja_vida({
            'equipo_id': equipo_id,
            'tipo': 'desasignacion',
            'titulo': f'Desasignado de {usuario_nombre}',
            'descripcion': f'Equipo desasignado del responsable {usuario_nombre}.',
            'fecha': date.today().isoformat(),
            'responsable': session.get('username', 'Sistema')
        })
        
        return jsonify({'ok': True, 'message': 'Equipo desasignado y liberado del responsable'}), 200
    except Exception as e:
        return _server_error(e)



# ════════════════════════════════════════════════════════════════════════════
# PUBLIC SIGNATURE ENDPOINTS (para asignaciones - sin login requerido)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/asignaciones-equipos/<int:id>/publico', methods=['GET'])
def get_asignacion_publico(id):
    """Obtener datos de asignacion para pagina de firma publica"""
    try:
        asig = repo.get_asignacion_raw(id)
        if not asig:
            return jsonify({'error': 'Asignacion no encontrada'}), 404

        equipo_id = asig.get('equipo_id')
        equipo_data = {}
        if equipo_id:
            equipo_data = repo.get_equipo(equipo_id) or {}
            asig['equipo_nombre'] = equipo_data.get('nombre', 'Equipo desconocido')
            asig['equipo_codigo'] = equipo_data.get('serial', 'N/A')
            asig['equipo_serial'] = equipo_data.get('serial', '')

        usuario_id = asig.get('usuario_id')
        if usuario_id:
            usr = repo.get_usuario(usuario_id)
            if usr:
                asig['usuario_nombre'] = usr.get('nombre', 'Usuario desconocido')
        
        # ═══════════════════════════════════════════════════════════════
        # Construir campo de notas combinadas (asignación + equipo)
        # ═══════════════════════════════════════════════════════════════
        notas_list = []
        
        # Notas de la asignación (según el tipo de firma)
        tipo_firma = 'entrada'  # Default
        notas_asig = asig.get('notas_entrada') or asig.get('notas_salida') or asig.get('notas')
        if notas_asig:
            notas_list.append(f"📝 Observaciones de la asignación:\n{notas_asig}")
        
        # Descripción/notas del equipo
        desc_equipo = equipo_data.get('descripcion') or equipo_data.get('notas')
        if desc_equipo:
            notas_list.append(f"💻 Notas del equipo:\n{desc_equipo}")
        
        # Estado del equipo si existe
        estado_equipo = asig.get('estado_equipo_entrada')
        if estado_equipo:
            notas_list.append(f"⚙️ Estado del equipo: {estado_equipo}")
        
        # Combinar todas las notas
        if notas_list:
            asig['notas'] = '\n\n'.join(notas_list)
        else:
            asig['notas'] = 'Sin observaciones'
        
        return jsonify(asig)
    except Exception as e:
        return _server_error(e)


@app.route('/api/asignaciones-equipos/<int:id>/save-signature-public', methods=['POST'])
def save_asignacion_signature_public(id):
    """Guardar firma de asignacion desde link publico (máximo 1 intento)"""
    try:
        firma_file = request.files.get('firma')
        tipo_firma = request.form.get('tipo', 'entrada')
        politica_aceptada = request.form.get('politica_aceptada', 'false').lower() == 'true'
        
        if not firma_file:
            return jsonify({'error': 'Missing signature'}), 400
        
        asig = repo.get_asignacion_raw(id)
        if not asig:
            return jsonify({'error': 'Asignacion no encontrada'}), 404

        # Validar que solo se puede firmar 1 vez por tipo
        if tipo_firma == 'entrada' and asig.get('firma_entrada_url'):
            return jsonify({'error': 'Esta asignación ya ha sido firmada en entrada. No se permite firmar de nuevo.'}), 403
        elif tipo_firma == 'salida' and asig.get('firma_salida_url'):
            return jsonify({'error': 'Esta asignación ya ha sido firmada en salida. No se permite firmar de nuevo.'}), 403
        elif tipo_firma == 'desasignacion' and asig.get('firma_desasignacion_url'):
            return jsonify({'error': 'Esta desasignación ya ha sido firmada. No se permite firmar de nuevo.'}), 403
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
            return _server_error(e)
        
        # Preparar datos minimalistas solo con campos que definitivamente existen
        update_data = {}
        
        if tipo_firma == 'entrada':
            update_data['firma_entrada_url'] = firma_url
            update_data['fecha_firma_entrada'] = datetime.now().isoformat()
            update_data['politica_aceptada'] = politica_aceptada
            update_data['fecha_aceptacion_politica'] = datetime.now().isoformat()
        elif tipo_firma == 'desasignacion':
            update_data['firma_desasignacion_url'] = firma_url
            update_data['fecha_firma_desasignacion'] = datetime.now().isoformat()
            update_data['estado'] = 'desasignada'  # ✅ Cambiar estado
            
            # Limpiar usuario_id del equipo (dejar sin dueño) - CRITICAL
            equipo_id = asig.get('equipo_id')
            usuario_id = asig.get('usuario_id')
            if equipo_id:
                repo.update_equipo(equipo_id, {'usuario_id': None, 'disponibilidad': 'Disponible'})

                usuario_nombre = 'Desconocido'
                if usuario_id:
                    usr = repo.get_usuario(usuario_id)
                    if usr:
                        usuario_nombre = usr.get('nombre', 'Desconocido')

                repo.create_hoja_vida({
                    'equipo_id': equipo_id,
                    'tipo': 'desasignacion',
                    'titulo': f'Desasignado de {usuario_nombre}',
                    'descripcion': f'Equipo desasignado del responsable {usuario_nombre} mediante firma de desasignación.',
                    'fecha': date.today().isoformat(),
                    'responsable': 'Sistema (Firma Pública)'
                })
        else:  # 'salida'
            update_data['firma_salida_url'] = firma_url
            update_data['fecha_firma_salida'] = datetime.now().isoformat()
            update_data['estado'] = 'cerrada'

            equipo_id = asig.get('equipo_id')
            usuario_id = asig.get('usuario_id')
            if equipo_id:
                repo.update_equipo(equipo_id, {'usuario_id': None, 'disponibilidad': 'Disponible'})
                usuario_nombre = 'Desconocido'
                if usuario_id:
                    usr = repo.get_usuario(usuario_id)
                    if usr:
                        usuario_nombre = usr.get('nombre', 'Desconocido')
                repo.create_hoja_vida({
                    'equipo_id': equipo_id,
                    'tipo': 'devolucion',
                    'titulo': f'Devuelto por {usuario_nombre}',
                    'descripcion': 'Equipo devuelto mediante firma pública de devolución.',
                    'fecha': date.today().isoformat(),
                    'responsable': 'Sistema (Firma Pública)'
                })
        
        try:
            result = repo.update_asignacion(id, update_data)
            if isinstance(result, dict) and result.get('error'):
                return jsonify({'error': f'Error al actualizar asignación: {result.get("error")}'}), 500
        except Exception as e:
            return _server_error(e)
        
        return jsonify({'ok': True, 'message': f'Firma de {tipo_firma} guardada exitosamente'}), 201
    except Exception as e:
        import traceback
        error_msg = f"{str(e)} | {traceback.format_exc()}"
        return jsonify({'error': error_msg}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
