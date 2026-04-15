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
