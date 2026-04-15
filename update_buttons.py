import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the buttons section - more flexible pattern
old_section = """      <td>
        ${!tieneEntrada?`<button class="btn btn-primary btn-sm" onclick="openFirmaEntradaModal(${a.id})">Firmar</button>`:''}
        ${tieneEntrada&&!tieneSalida?`<button class="btn btn-teal btn-sm" onclick="openFirmaSalidaModal(${a.id})">Devolver</button>`:''}
        ${tieneSalida?`<button class="btn btn-ghost btn-sm" onclick="viewAsignacionDetail(${a.id})">Ver</button>`:''}
      </td>"""

new_section = """      <td style="display:flex;gap:4px;flex-wrap:wrap">
        ${!tieneEntrada?`<button class="btn btn-primary btn-sm" onclick="openFirmaEntradaModal(${a.id})">Firmar</button>`:''}
        ${tieneEntrada&&!tieneSalida?`<button class="btn btn-teal btn-sm" onclick="openFirmaSalidaModal(${a.id})">Devolver</button>`:''}
        ${tieneSalida?`<button class="btn btn-ghost btn-sm" onclick="viewAsignacionDetail(${a.id})">Ver</button>`:''}
        ${a.estado==='cerrada'?`<button class="btn btn-warning btn-sm" onclick="unassignAsignacion(${a.id})">Desasignar</button>`:''}
        <button class="btn btn-danger btn-sm" onclick="deleteAsignacion(${a.id})" style="background:var(--error);color:white">Eliminar</button>
      </td>"""

if old_section in content:
    content = content.replace(old_section, new_section)
    print("Updated buttons section")
else:
    print("Could not find old section")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
