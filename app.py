from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import json
import base64

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

# Credenciales de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

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

@app.route('/api/dashboard')
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
                tipo = eq.get('tipo', 'desconocido')
                tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
        tipos_equipos = [{'tipo': k, 'count': v} for k, v in sorted(tipos_count.items(), key=lambda x: x[1], reverse=True)[:7]]
        
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
        result = supabase_request('POST', 'usuarios', '', {
            'nombre': d['nombre'],
            'email': d['email'],
            'cargo': d.get('cargo', ''),
            'departamento': d.get('departamento', ''),
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo')
        })
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
        result = supabase_request('PATCH', 'usuarios', f'?id=eq.{id}', {
            'nombre': d['nombre'],
            'email': d['email'],
            'cargo': d.get('cargo', ''),
            'departamento': d.get('departamento', ''),
            'telefono': d.get('telefono', ''),
            'estado': d.get('estado', 'activo')
        })
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

@app.route('/api/equipos', methods=['GET'])
def get_equipos():
    try:
        result = supabase_request('GET', 'equipos', '?order=nombre.asc')
        if isinstance(result, list):
            return jsonify(result)
        return jsonify([])
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
        equipo_result = supabase_request('POST', 'equipos', '', {
            'nombre': d['nombre'],
            'tipo': d['tipo'],
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'usuario_id': d.get('usuario_id', None),
            'fecha_adquisicion': d.get('fecha_adquisicion', ''),
            'valor': d.get('valor', 0),
            'descripcion': d.get('descripcion', '')
        })
        
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
        result = supabase_request('PATCH', 'equipos', f'?id=eq.{id}', {
            'nombre': d['nombre'],
            'tipo': d['tipo'],
            'marca': d.get('marca', ''),
            'modelo': d.get('modelo', ''),
            'serial': d.get('serial', ''),
            'estado': d.get('estado', 'bueno'),
            'usuario_id': d.get('usuario_id', None),
            'fecha_adquisicion': d.get('fecha_adquisicion', ''),
            'valor': d.get('valor', 0),
            'descripcion': d.get('descripcion', '')
        })
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

# ========== MANTENIMIENTOS ==========
@app.route('/api/mantenimientos', methods=['GET'])
def get_all_mantenimientos():
    try:
        mants = supabase_request('GET', 'mantenimientos', '?order=fecha.desc')
        if isinstance(mants, list):
            return jsonify(mants)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipos/<int:id>/mantenimientos', methods=['GET'])
def get_mants_equipo(id):
    try:
        result = supabase_request('GET', 'mantenimientos', f'?equipo_id=eq.{id}&order=fecha.desc')
        if isinstance(result, list):
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
def get_prestamos():
    try:
        prestamos = supabase_request('GET', 'prestamos', '?order=creado_en.desc')
        if isinstance(prestamos, list):
            # Enriquecer con nombres de equipo y usuario
            for loan in prestamos:
                # Obtener nombre del equipo
                if 'equipo_id' in loan:
                    equipos = supabase_request('GET', 'equipos', f'?id=eq.{loan["equipo_id"]}')
                    if isinstance(equipos, list) and len(equipos) > 0:
                        loan['equipo_nombre'] = equipos[0].get('nombre', 'Equipo desconocido')
                        loan['equipo_tipo'] = equipos[0].get('tipo', '')
                    else:
                        loan['equipo_nombre'] = 'Equipo desconocido'
                
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
        prestamos = supabase_request('GET', 'prestamos', f'?id=eq.{id}')
        
        if isinstance(prestamos, list) and len(prestamos) > 0:
            loan = prestamos[0]
            
            # Obtener nombre del equipo
            if 'equipo_id' in loan and loan['equipo_id']:
                equipos = supabase_request('GET', 'equipos', f'?id=eq.{loan["equipo_id"]}')
                if isinstance(equipos, list) and len(equipos) > 0:
                    loan['equipo_nombre'] = equipos[0].get('nombre', 'Equipo desconocido')
                else:
                    loan['equipo_nombre'] = 'Equipo desconocido'
            else:
                loan['equipo_nombre'] = 'Sin equipo'
            
            # Obtener nombre del usuario
            if 'usuario_id' in loan and loan['usuario_id']:
                usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{loan["usuario_id"]}')
                if isinstance(usuarios, list) and len(usuarios) > 0:
                    loan['usuario_nombre'] = usuarios[0].get('nombre', 'Usuario desconocido')
                else:
                    loan['usuario_nombre'] = 'Usuario desconocido'
            else:
                loan['usuario_nombre'] = 'Sin responsable'
            
            return jsonify(loan)
        return jsonify({'error': 'Préstamo no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos', methods=['POST'])
def create_prestamo():
    try:
        d = request.json
        
        # Verificar si el equipo ya tiene un préstamo activo
        existing = supabase_request('GET', 'prestamos', f'?equipo_id=eq.{d["equipo_id"]}&estado=eq.activo')
        if isinstance(existing, list) and len(existing) > 0:
            return jsonify({'error': 'El equipo ya tiene un prestamo activo'}), 400
        
        result = supabase_request('POST', 'prestamos', '', {
            'equipo_id': d['equipo_id'],
            'usuario_id': d['usuario_id'],
            'fecha_prestamo': d['fecha_prestamo'],
            'fecha_devolucion_esperada': d.get('fecha_devolucion_esperada') or None,
            'estado': 'activo',
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
    """Save signature and images for a loan"""
    try:
        # Obtener archivos
        imagen1 = request.files.get('imagen1')
        imagen2 = request.files.get('imagen2')
        firma_data = request.form.get('firma_data', '')
        
        if not imagen1 or not imagen2:
            return jsonify({'error': 'Se requieren 2 imágenes'}), 400
        
        # Crear directorio de uploads si no existe
        os.makedirs('uploads/prestamos', exist_ok=True)
        
        # Generar nombres únicos para los archivos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar imágenes localmente
        img1_filename = f"image1_{id}_{timestamp}.jpg"
        img2_filename = f"image2_{id}_{timestamp}.jpg"
        
        img1_path = f"uploads/prestamos/{img1_filename}"
        img2_path = f"uploads/prestamos/{img2_filename}"
        
        # Guardar archivos
        imagen1.save(img1_path)
        imagen2.save(img2_path)
        
        # URLs para acceso frontend
        img1_url = f"/uploads/prestamos/{img1_filename}"
        img2_url = f"/uploads/prestamos/{img2_filename}"
        
        # Guardar firma como base64 o dataURL en la BD (es pequeño)
        firma_url = firma_data  # DataURL - puede ser ineficiente pero funciona
        
        print(f"Images saved: {img1_path}, {img2_path}")
        print(f"URLs: {img1_url}, {img2_url}")
        
        # Actualizar préstamo en BD con firma e imágenes
        update_data = {
            'firma_url': firma_url[:2000] if len(firma_url) > 2000 else firma_url,  # Limitar tamaño dataURL
            'imagen1_url': img1_url,
            'imagen2_url': img2_url
        }
        
        result = supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': 'Error al guardar préstamo'}), 500
        
        return jsonify({
            'ok': True,
            'firma_url': firma_url,
            'img1_url': img1_url,
            'img2_url': img2_url
        }), 201
        
    except Exception as e:
        print(f"Signature save error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prestamos/<int:id>/devolver', methods=['PUT'])
def devolver_prestamo(id):
    try:
        supabase_request('PATCH', 'prestamos', f'?id=eq.{id}', {
            'estado': 'devuelto',
            'fecha_devolucion_real': date.today().isoformat()
        })
        return jsonify({'ok': True})
    except Exception as e:
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

@app.route('/')
def index(): 
    return send_from_directory('templates', 'index.html')

@app.route('/firma/<int:loan_id>')
def firma_page(loan_id):
    """Public signature page for a specific loan"""
    return send_from_directory('templates', 'firma.html')

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded files from uploads directory"""
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
