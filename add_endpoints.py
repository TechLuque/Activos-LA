with open('app.py', 'r') as f:
    content = f.read()

# Add the new endpoints before if __name__
new_endpoints = '''
# ════════════════════════════════════════════════════════════════════════════
# PUBLIC SIGNATURE ENDPOINTS (para asignaciones - sin login requerido)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/asignaciones-equipos/<int:id>/publico', methods=['GET'])
def get_asignacion_publico(id):
    """Obtener datos de asignacion para pagina de firma publica"""
    try:
        # Obtener asignacion
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignacion no encontrada'}), 404
        
        asig = asig[0]
        
        # Obtener equipo
        equipo_id = asig.get('equipo_id')
        if equipo_id:
            equipos = supabase_request('GET', 'equipos', f'?id=eq.{equipo_id}')
            if isinstance(equipos, list) and len(equipos) > 0:
                asig['equipo_nombre'] = equipos[0].get('nombre', 'Equipo desconocido')
                asig['equipo_serial'] = equipos[0].get('serial', '')
                asig['equipo_tipo'] = equipos[0].get('tipo_nombre', '')
        
        # Obtener usuario
        usuario_id = asig.get('usuario_id')
        if usuario_id:
            usuarios = supabase_request('GET', 'usuarios', f'?id=eq.{usuario_id}')
            if isinstance(usuarios, list) and len(usuarios) > 0:
                asig['usuario_nombre'] = usuarios[0].get('nombre', 'Usuario desconocido')
                asig['usuario_email'] = usuarios[0].get('email', '')
        
        return jsonify(asig)
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/asignaciones-equipos/<int:id>/save-signature-public', methods=['POST'])
def save_asignacion_signature_public(id):
    """Guardar firma de asignacion desde link publico (sin login)"""
    try:
        firma_file = request.files.get('firma')
        tipo_firma = request.form.get('tipo', 'entrada')
        img1_url = request.form.get('img1_url', '')
        img2_url = request.form.get('img2_url', '')
        estado_equipo = request.form.get('estado_equipo', 'bueno')
        notas = request.form.get('notas', '')
        
        if not firma_file:
            return jsonify({'error': 'Missing signature'}), 400
        
        # Verificar asignacion existe
        asig = supabase_request('GET', 'asignaciones_equipos', f'?id=eq.{id}')
        if not isinstance(asig, list) or len(asig) == 0:
            return jsonify({'error': 'Asignacion no encontrada'}), 404
        
        asig = asig[0]
        
        firma_content = firma_file.read()
        if not firma_content or len(firma_content) == 0:
            return jsonify({'error': 'Signature is empty'}), 400
        
        # Guardar firma
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"asignacion_{id}"
        prefix = 'firma_entrada' if tipo_firma == 'entrada' else 'firma_salida'
        firma_filename = f"{prefix}_{timestamp}.jpg"
        firma_path = f"{folder}/{firma_filename}"
        
        try:
            firma_url = supabase_storage_upload(firma_content, firma_path)
            if not firma_url:
                return jsonify({'error': 'Storage upload failed'}), 500
        except Exception as e:
            return jsonify({'error': f'Storage error: {str(e)}'}), 500
        
        # Actualizar asignacion
        if tipo_firma == 'entrada':
            update_data = {
                'firma_entrada_url': firma_url,
                'imagen1_entrada_url': img1_url or None,
                'imagen2_entrada_url': img2_url or None,
                'estado_equipo_entrada': 'bueno',
                'fecha_firma_entrada': datetime.now().isoformat()
            }
        else:  # salida/devolucion
            update_data = {
                'firma_salida_url': firma_url,
                'imagen1_salida_url': img1_url or None,
                'imagen2_salida_url': img2_url or None,
                'estado_equipo_salida': estado_equipo,
                'notas_salida': notas,
                'fecha_firma_salida': datetime.now().isoformat(),
                'estado': 'cerrada'
            }
            
            # Limpiar usuario_id del equipo
            equipo_id = asig.get('equipo_id')
            if equipo_id:
                supabase_request('PATCH', 'equipos', f'?id=eq.{equipo_id}', {
                    'usuario_id': None
                })
        
        result = supabase_request('PATCH', 'asignaciones_equipos', f'?id=eq.{id}', update_data)
        
        if isinstance(result, dict) and result.get('error'):
            return jsonify({'error': str(result.get('error'))}), 500
        
        return jsonify({
            'ok': True,
            'message': f'Firma de {tipo_firma} completada'
        }), 201
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

'''

# Find and replace the if __name__ section
if "if __name__ == '__main__':" in content:
    # Insert new endpoints before if __name__
    content = content.replace(
        "if __name__ == '__main__':",
        new_endpoints + "\nif __name__ == '__main__':"
    )
    
    with open('app.py', 'w') as f:
        f.write(content)
    
    print("Endpoints added successfully")
else:
    print("Could not find if __name__ marker")
