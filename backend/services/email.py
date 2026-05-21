"""
Wrapper de Resend para emails transaccionales.

Casos de uso:
- Reset password (link "olvidé mi contraseña")
- Invitación de usuario nuevo (admin invita, el usuario setea su password)
- Alertas / notificaciones (futuro)

Si RESEND_API_KEY está vacía (modo dev sin Resend), se loguea el email a stdout
y devuelve un dict simulando éxito — útil para desarrollo local sin gastar quota.
"""
from __future__ import annotations
import logging
from typing import Optional

from ..core.config import settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Error al enviar email transaccional."""


def _client():
    """Lazy init del cliente Resend."""
    if not settings.RESEND_API_KEY:
        return None
    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        return resend
    except ImportError:
        logger.warning("[email] paquete `resend` no instalado")
        return None


def _enviar_resend(*, to: str, subject: str, html: str, text_alt: Optional[str] = None) -> dict:
    """Envío real vía Resend API."""
    cli = _client()
    if cli is None:
        # Modo dev sin clave: log a stdout para que el dev vea el contenido
        logger.warning(
            "[email DRY-RUN] sin RESEND_API_KEY — to=%s subject=%s\n%s",
            to, subject, text_alt or html,
        )
        return {"id": "dev-dry-run", "status": "logged"}

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text_alt:
        payload["text"] = text_alt

    try:
        result = cli.Emails.send(payload)
        logger.info("[email] enviado a %s (id=%s)", to, result.get("id", "?"))
        return result
    except Exception as e:
        logger.exception("[email] FAIL enviando a %s", to)
        raise EmailError(f"No se pudo enviar email a {to}: {e}") from e


# ─── Templates ───────────────────────────────────────────────────────────────

def _layout(contenido_html: str, titulo: str) -> str:
    """Wrapper HTML simple consistente para todos los emails."""
    return f"""\
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>{titulo}</title></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#0f172a;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
        <tr><td style="background:#1e40af;padding:20px 28px;color:white;">
          <strong style="font-size:18px;">ERP Universal</strong>
        </td></tr>
        <tr><td style="padding:28px;line-height:1.55;">
          {contenido_html}
        </td></tr>
        <tr><td style="background:#f1f5f9;padding:16px 28px;font-size:12px;color:#64748b;">
          Si no esperabas este email, podés ignorarlo.<br/>
          Este mensaje se envió automáticamente, no respondas a esta dirección.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def enviar_reset_password(to: str, nombre: str, token: str) -> dict:
    """Email para flujo 'olvidé mi contraseña'. Token plano va en la URL."""
    link = f"{settings.APP_URL}/auth/reset-password?token={token}"
    html = _layout(f"""
        <h2 style="margin:0 0 12px;">Hola {nombre},</h2>
        <p>Recibimos un pedido para restablecer la contraseña de tu cuenta. Si fuiste vos, hacé clic en el botón:</p>
        <p style="margin:24px 0;">
          <a href="{link}" style="background:#2563eb;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
            Cambiar mi contraseña
          </a>
        </p>
        <p style="color:#64748b;font-size:13px;">El link expira en 24 horas. Si el botón no funciona, copiá y pegá esta URL en tu navegador:<br/>
        <code style="background:#f1f5f9;padding:4px 8px;border-radius:4px;font-size:12px;">{link}</code></p>
    """, "Restablecer contraseña — ERP Universal")
    text_alt = f"""Hola {nombre},

Recibimos un pedido para restablecer la contraseña de tu cuenta.
Para cambiarla, abrí este enlace en tu navegador:

{link}

El enlace expira en 24 horas.
Si no fuiste vos, ignorá este mensaje.
"""
    return _enviar_resend(
        to=to,
        subject="Restablecer tu contraseña — ERP Universal",
        html=html,
        text_alt=text_alt,
    )


def enviar_invitacion_usuario(to: str, nombre: str, token: str, empresa: str) -> dict:
    """Email cuando admin crea un usuario nuevo. Le pide que setee su password."""
    link = f"{settings.APP_URL}/auth/seteo-password?token={token}"
    html = _layout(f"""
        <h2 style="margin:0 0 12px;">¡Bienvenido/a, {nombre}!</h2>
        <p>El administrador de <strong>{empresa}</strong> te creó una cuenta en el sistema.</p>
        <p>Para activar tu cuenta y crear tu contraseña, hacé clic acá:</p>
        <p style="margin:24px 0;">
          <a href="{link}" style="background:#10b981;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
            Activar mi cuenta
          </a>
        </p>
        <p style="color:#64748b;font-size:13px;">Este enlace expira en 7 días. Si tenés problemas, copiá esta URL:<br/>
        <code style="background:#f1f5f9;padding:4px 8px;border-radius:4px;font-size:12px;">{link}</code></p>
    """, "Te invitaron al ERP Universal")
    text_alt = f"""Hola {nombre},

El administrador de {empresa} te creó una cuenta en el sistema.
Para activarla y crear tu contraseña, abrí este enlace:

{link}

El enlace expira en 7 días.
"""
    return _enviar_resend(
        to=to,
        subject=f"Tu cuenta en {empresa} está lista para activar",
        html=html,
        text_alt=text_alt,
    )


def enviar_cuenta_bloqueada(
    to: str,
    nombre: str,
    ip: str | None = None,
    dispositivo: str | None = None,
) -> dict:
    """Email de alerta cuando la cuenta se bloquea por intentos fallidos."""
    ip_txt = ip or "IP no disponible"
    disp_txt = dispositivo or "dispositivo no identificado"
    html = _layout(f"""
        <h2 style="margin:0 0 12px;">Hola {nombre},</h2>
        <p>Bloqueamos temporalmente tu cuenta por varios intentos fallidos de inicio de sesión.</p>
        <ul style="color:#334155;">
          <li><strong>Duración:</strong> 15 minutos</li>
          <li><strong>IP:</strong> {ip_txt}</li>
          <li><strong>Dispositivo:</strong> {disp_txt}</li>
        </ul>
        <p>Si fuiste vos, esperá unos minutos e intentá de nuevo. Si no reconocés esta actividad, cambiá tu contraseña cuando puedas ingresar.</p>
    """, "Cuenta bloqueada temporalmente — ERP Universal")
    text_alt = f"""Hola {nombre},

Bloqueamos temporalmente tu cuenta por varios intentos fallidos de inicio de sesión.
Duración: 15 minutos
IP: {ip_txt}
Dispositivo: {disp_txt}

Si no reconocés esta actividad, cambiá tu contraseña cuando puedas ingresar.
"""
    return _enviar_resend(
        to=to,
        subject="Tu cuenta fue bloqueada temporalmente — ERP Universal",
        html=html,
        text_alt=text_alt,
    )



def enviar_password_cambiada(
    to: str,
    nombre: str,
    ip: str | None = None,
    dispositivo: str | None = None,
) -> dict:
    """Email de alerta cuando se cambia la contraseña de una cuenta."""
    ip_txt = ip or "IP no disponible"
    disp_txt = dispositivo or "dispositivo no identificado"
    html = _layout(f"""
        <h2 style="margin:0 0 12px;">Hola {nombre},</h2>
        <p>Te avisamos que la contraseña de tu cuenta fue cambiada correctamente.</p>
        <ul style="color:#334155;">
          <li><strong>IP:</strong> {ip_txt}</li>
          <li><strong>Dispositivo:</strong> {disp_txt}</li>
        </ul>
        <p>Si fuiste vos, no necesitás hacer nada. Si no reconocés esta actividad, contactá inmediatamente al administrador.</p>
    """, "Contraseña cambiada — ERP Universal")
    text_alt = f"""Hola {nombre},

Te avisamos que la contraseña de tu cuenta fue cambiada correctamente.
IP: {ip_txt}
Dispositivo: {disp_txt}

Si no reconocés esta actividad, contactá inmediatamente al administrador.
"""
    return _enviar_resend(
        to=to,
        subject="Tu contraseña fue cambiada — ERP Universal",
        html=html,
        text_alt=text_alt,
    )
