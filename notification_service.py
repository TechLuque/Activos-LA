"""
Servicio de notificaciones.
- Email: Gmail SMTP via App Password. Corre desde GitHub Actions diariamente.
- WhatsApp: Meta Cloud API — pendiente de implementar.

Variables de entorno requeridas:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  GMAIL_SENDER              (ej: tech@luqueacademy.com)
  GMAIL_APP_PASSWORD        (App Password de Google, no la contraseña normal)
  NOTIFICATION_RECIPIENT_OVERRIDE  (opcional — fuerza todos los correos a esta dirección, útil en pruebas)
"""

import os
import smtplib
import logging
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests as http_requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
GMAIL_SENDER = os.getenv('GMAIL_SENDER', '')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
RECIPIENT_OVERRIDE = os.getenv('NOTIFICATION_RECIPIENT_OVERRIDE', '')

META_PHONE_NUMBER_ID = os.getenv('META_WHATSAPP_PHONE_NUMBER_ID', '')
META_ACCESS_TOKEN = os.getenv('META_WHATSAPP_ACCESS_TOKEN', '')


# ---------------------------------------------------------------------------
# Supabase queries
# ---------------------------------------------------------------------------

def _supabase_get(path: str) -> list:
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    }
    resp = http_requests.get(f'{SUPABASE_URL}/rest/v1/{path}', headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_expiring_loans(days: int = 3) -> list:
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=days)).isoformat()
    path = (
        'prestamos'
        '?select=id,fecha_devolucion_esperada,estado,notas,'
        'equipos(nombre,serial),'
        'usuarios(nombre,email)'
        f'&estado=neq.devuelto'
        f'&fecha_devolucion_esperada=gte.{today}'
        f'&fecha_devolucion_esperada=lte.{future}'
        '&order=fecha_devolucion_esperada.asc'
    )
    return _supabase_get(path)


def get_overdue_loans() -> list:
    today = date.today().isoformat()
    path = (
        'prestamos'
        '?select=id,fecha_devolucion_esperada,estado,notas,'
        'equipos(nombre,serial),'
        'usuarios(nombre,email)'
        f'&estado=neq.devuelto'
        f'&fecha_devolucion_esperada=lt.{today}'
        '&order=fecha_devolucion_esperada.asc'
    )
    return _supabase_get(path)


def _fetch_maintenance_with_equipos(path: str) -> list:
    items = _supabase_get(path)
    if not items:
        return []
    equipo_ids = ','.join(str(m['equipo_id']) for m in items)
    equipos = _supabase_get(f'equipos?select=id,nombre,serial&id=in.({equipo_ids})')
    equipos_map = {e['id']: e for e in equipos} if isinstance(equipos, list) else {}
    for m in items:
        m['equipos'] = equipos_map.get(m['equipo_id'], {})
    return items


def get_overdue_maintenance() -> list:
    today = date.today().isoformat()
    # proxima_revision la setea un registro completado para indicar cuándo
    # toca el próximo mantenimiento — se filtra solo por fecha, sin importar estado.
    path = (
        'mantenimientos'
        '?select=id,equipo_id,tipo,estado,proxima_revision,descripcion,tecnico'
        f'&proxima_revision=lt.{today}'
        f'&proxima_revision=not.is.null'
        '&order=proxima_revision.asc'
    )
    return _fetch_maintenance_with_equipos(path)


def get_upcoming_maintenance(days: int = 3) -> list:
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=days)).isoformat()
    path = (
        'mantenimientos'
        '?select=id,equipo_id,tipo,estado,proxima_revision,descripcion,tecnico'
        f'&proxima_revision=gte.{today}'
        f'&proxima_revision=lte.{future}'
        '&order=proxima_revision.asc'
    )
    return _fetch_maintenance_with_equipos(path)


# ---------------------------------------------------------------------------
# Email building
# ---------------------------------------------------------------------------

def _days_label(fecha_str: str) -> str:
    delta = (date.fromisoformat(fecha_str) - date.today()).days
    if delta == 0:
        return '<span style="color:#dc2626;font-weight:bold">HOY</span>'
    if delta == 1:
        return '<span style="color:#ea580c;font-weight:bold">mañana</span>'
    if delta < 0:
        return f'<span style="color:#dc2626;font-weight:bold">venció hace {abs(delta)} día(s)</span>'
    return f'<span style="color:#ca8a04;font-weight:bold">en {delta} día(s)</span>'


def _date_fmt(fecha_str: str) -> str:
    d = date.fromisoformat(fecha_str)
    return d.strftime('%d/%m/%Y')


def _loans_section(loans: list) -> str:
    rows = ''
    for loan in loans:
        equipo = loan.get('equipos') or {}
        usuario = loan.get('usuarios') or {}
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">
            <strong>{equipo.get('nombre', '—')}</strong><br>
            <span style="color:#6b7280;font-size:13px">Serial: {equipo.get('serial', '—')}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">{usuario.get('nombre', '—')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">
            {_date_fmt(loan['fecha_devolucion_esperada'])}<br>
            <span style="font-size:13px">Vence {_days_label(loan['fecha_devolucion_esperada'])}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-transform:capitalize">{loan.get('estado', '—')}</td>
        </tr>"""

    return f"""
    <h2 style="color:#1e40af;margin-top:32px;margin-bottom:8px">📋 Préstamos próximos a vencer</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <thead>
        <tr style="background:#1e40af;color:#fff">
          <th style="padding:10px 12px;text-align:left">Equipo</th>
          <th style="padding:10px 12px;text-align:left">Responsable</th>
          <th style="padding:10px 12px;text-align:left">Fecha devolución</th>
          <th style="padding:10px 12px;text-align:left">Estado</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _maintenance_section(items: list) -> str:
    rows = ''
    for m in items:
        equipo = m.get('equipos') or {}
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">
            <strong>{equipo.get('nombre', '—')}</strong><br>
            <span style="color:#6b7280;font-size:13px">Serial: {equipo.get('serial', '—')}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-transform:capitalize">{m.get('tipo', '—')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">
            {_date_fmt(m['proxima_revision'])}<br>
            <span style="font-size:13px">Vence {_days_label(m['proxima_revision'])}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">{m.get('tecnico', '—')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#374151">{m.get('descripcion', '')}</td>
        </tr>"""

    return f"""
    <h2 style="color:#065f46;margin-top:32px;margin-bottom:8px">🔧 Mantenimientos próximos</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <thead>
        <tr style="background:#065f46;color:#fff">
          <th style="padding:10px 12px;text-align:left">Equipo</th>
          <th style="padding:10px 12px;text-align:left">Tipo</th>
          <th style="padding:10px 12px;text-align:left">Próxima revisión</th>
          <th style="padding:10px 12px;text-align:left">Técnico</th>
          <th style="padding:10px 12px;text-align:left">Descripción</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def build_email_html(loans: list, maintenance: list) -> str:
    today_str = date.today().strftime('%d/%m/%Y')
    sections = ''
    if loans:
        sections += _loans_section(loans)
    if maintenance:
        sections += _maintenance_section(maintenance)

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:24px">
  <div style="max-width:720px;margin:0 auto">
    <div style="background:#1e293b;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
      <h1 style="margin:0;font-size:20px">📌 Resumen de Activos — {today_str}</h1>
      <p style="margin:4px 0 0;color:#94a3b8;font-size:13px">Notificación automática · Activos EQ</p>
    </div>
    <div style="background:#f1f5f9;padding:20px 24px">
      {sections}
    </div>
    <div style="background:#e2e8f0;padding:12px 24px;border-radius:0 0 8px 8px;font-size:12px;color:#64748b;text-align:center">
      Este correo es generado automáticamente. No responder.
    </div>
  </div>
</body>
</html>"""


def _overdue_loans_section(loans: list) -> str:
    rows = ''
    for loan in loans:
        equipo = loan.get('equipos') or {}
        usuario = loan.get('usuarios') or {}
        dias = abs((date.fromisoformat(loan['fecha_devolucion_esperada']) - date.today()).days)
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2">
            <strong>{equipo.get('nombre', '—')}</strong><br>
            <span style="color:#6b7280;font-size:13px">Serial: {equipo.get('serial', '—')}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2">{usuario.get('nombre', '—')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2">
            {_date_fmt(loan['fecha_devolucion_esperada'])}<br>
            <span style="color:#dc2626;font-weight:bold;font-size:13px">Hace {dias} día(s)</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2;text-transform:capitalize">{loan.get('estado', '—')}</td>
        </tr>"""

    return f"""
    <h2 style="color:#991b1b;margin-top:32px;margin-bottom:8px">⚠️ Préstamos vencidos sin devolver</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <thead>
        <tr style="background:#991b1b;color:#fff">
          <th style="padding:10px 12px;text-align:left">Equipo</th>
          <th style="padding:10px 12px;text-align:left">Responsable</th>
          <th style="padding:10px 12px;text-align:left">Fecha vencimiento</th>
          <th style="padding:10px 12px;text-align:left">Estado</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _overdue_maintenance_section(items: list) -> str:
    rows = ''
    for m in items:
        equipo = m.get('equipos') or {}
        dias = abs((date.fromisoformat(m['proxima_revision']) - date.today()).days)
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2">
            <strong>{equipo.get('nombre', '—')}</strong><br>
            <span style="color:#6b7280;font-size:13px">Serial: {equipo.get('serial', '—')}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2;text-transform:capitalize">{m.get('tipo', '—')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2">
            {_date_fmt(m['fecha'])}<br>
            <span style="color:#dc2626;font-weight:bold;font-size:13px">Hace {dias} día(s)</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2">{m.get('tecnico', '—')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #fee2e2;font-size:13px;color:#374151">{m.get('descripcion', '')}</td>
        </tr>"""

    return f"""
    <h2 style="color:#991b1b;margin-top:32px;margin-bottom:8px">⚠️ Mantenimientos vencidos sin completar</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <thead>
        <tr style="background:#991b1b;color:#fff">
          <th style="padding:10px 12px;text-align:left">Equipo</th>
          <th style="padding:10px 12px;text-align:left">Tipo</th>
          <th style="padding:10px 12px;text-align:left">Fecha vencimiento</th>
          <th style="padding:10px 12px;text-align:left">Técnico</th>
          <th style="padding:10px 12px;text-align:left">Descripción</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def build_overdue_email_html(loans: list, maintenance: list) -> str:
    today_str = date.today().strftime('%d/%m/%Y')
    sections = ''
    if loans:
        sections += _overdue_loans_section(loans)
    if maintenance:
        sections += _overdue_maintenance_section(maintenance)

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:24px">
  <div style="max-width:720px;margin:0 auto">
    <div style="background:#7f1d1d;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
      <h1 style="margin:0;font-size:20px">🚨 Activos Vencidos — {today_str}</h1>
      <p style="margin:4px 0 0;color:#fca5a5;font-size:13px">Requieren atención inmediata · Activos EQ</p>
    </div>
    <div style="background:#fef2f2;padding:20px 24px">
      {sections}
    </div>
    <div style="background:#fee2e2;padding:12px 24px;border-radius:0 0 8px 8px;font-size:12px;color:#64748b;text-align:center">
      Este correo es generado automáticamente. No responder.
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, html: str) -> bool:
    recipient = RECIPIENT_OVERRIDE or to
    if not recipient:
        logger.warning('send_email: sin destinatario para "%s"', subject)
        return False
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        logger.error('send_email: faltan GMAIL_SENDER o GMAIL_APP_PASSWORD')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = GMAIL_SENDER
        msg['To'] = recipient
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER, recipient, msg.as_string())
        logger.info('Correo enviado a %s: %s', recipient, subject)
        return True
    except Exception as e:
        logger.error('Error enviando correo a %s: %s', recipient, e)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_notifications():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error('Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY')
        return

    recipient = RECIPIENT_OVERRIDE or GMAIL_SENDER
    today_str = date.today().strftime('%d/%m/%Y')

    # — Correo 1: próximos a vencer (dentro de 3 días) —
    logger.info('Consultando préstamos próximos a vencer...')
    loans = get_expiring_loans(3)
    logger.info('Encontrados: %d préstamo(s)', len(loans))

    logger.info('Consultando mantenimientos próximos...')
    maintenance = get_upcoming_maintenance(3)
    logger.info('Encontrados: %d mantenimiento(s)', len(maintenance))

    if loans or maintenance:
        html = build_email_html(loans, maintenance)
        send_email(recipient, f'📌 Resumen de Activos — {today_str}', html)
    else:
        logger.info('Sin próximos vencimientos. No se envía correo 1.')

    # — Correo 2: ya vencidos —
    logger.info('Consultando préstamos vencidos...')
    overdue_loans = get_overdue_loans()
    logger.info('Encontrados: %d préstamo(s) vencido(s)', len(overdue_loans))

    logger.info('Consultando mantenimientos vencidos...')
    overdue_maintenance = get_overdue_maintenance()
    logger.info('Encontrados: %d mantenimiento(s) vencido(s)', len(overdue_maintenance))

    if overdue_loans or overdue_maintenance:
        html = build_overdue_email_html(overdue_loans, overdue_maintenance)
        send_email(recipient, f'🚨 Activos Vencidos — {today_str}', html)
    else:
        logger.info('Sin vencidos. No se envía correo 2.')


# ---------------------------------------------------------------------------
# WhatsApp (pendiente)
# ---------------------------------------------------------------------------

def _normalize_phone(phone: str) -> str:
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        digits = '57' + digits
    return digits


def send_whatsapp(to_phone: str, message: str) -> bool:
    if not META_PHONE_NUMBER_ID or not META_ACCESS_TOKEN:
        logger.warning('WhatsApp no configurado: faltan META_WHATSAPP_PHONE_NUMBER_ID o META_WHATSAPP_ACCESS_TOKEN')
        return False
    if not to_phone:
        return False
    try:
        phone = _normalize_phone(to_phone)
        if len(phone) < 10:
            logger.warning('Teléfono inválido: %s', to_phone)
            return False
        resp = http_requests.post(
            f'https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages',
            json={
                'messaging_product': 'whatsapp',
                'to': phone,
                'type': 'text',
                'text': {'body': message},
            },
            headers={
                'Authorization': f'Bearer {META_ACCESS_TOKEN}',
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        if resp.status_code == 200:
            logger.info('WhatsApp enviado a %s', phone)
            return True
        logger.error('WhatsApp error %s → %s: %s', phone, resp.status_code, resp.text[:200])
        return False
    except Exception as e:
        logger.error('Error enviando WhatsApp a %s: %s', to_phone, e)
        return False


if __name__ == '__main__':
    run_notifications()
