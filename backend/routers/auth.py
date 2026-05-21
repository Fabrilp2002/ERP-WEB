"""
Router /auth — autenticación y gestión de credenciales.

Endpoints:
- POST /auth/token                       Login (form OAuth2) → JWT
- POST /auth/reset-password              Pedir email de reset (público)
- POST /auth/reset-password/confirm      Cambiar password con token (público)
- POST /auth/invitar-usuario             Admin crea usuario y le manda email
- POST /auth/seteo-password/confirm      Usuario nuevo setea su primera password con token
"""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import re
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


# Validación simple de email (acepta dominios .local para dev)
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def _validar_email(v: str) -> str:
    v = (v or "").strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Email inválido")
    return v

from ..core.database import get_db
from ..core.password_policy import validar_password
from ..core.security import verify_password, create_access_token, hash_password, require_admin
from ..middleware.rate_limit import limiter
from ..models.schemas import TokenResponse
from ..services.audit import audit_with_request, extraer_ip, registrar as audit
from ..services.email import (
    enviar_cuenta_bloqueada,
    enviar_password_cambiada,
    enviar_reset_password,
    enviar_invitacion_usuario,
    EmailError,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# Tiempo de vida de los tokens
RESET_TOKEN_TTL_HOURS = 24
INVITE_TOKEN_TTL_DAYS = 7
LOCKOUT_WINDOW_MINUTES = 10
LOCKOUT_MINUTES = 15
MAX_FAILED_LOGIN_ATTEMPTS = 5
DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"erp_web_dummy_timing_attack", bcrypt.gensalt(12)
).decode("utf-8")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_token() -> tuple[str, str]:
    """Genera un token aleatorio. Devuelve (plano, hash). Solo el hash va a BD."""
    plano = secrets.token_urlsafe(32)
    hash_ = hashlib.sha256(plano.encode()).hexdigest()
    return plano, hash_


def _hash_token(plano: str) -> str:
    return hashlib.sha256(plano.encode()).hexdigest()


def _validar_password_fuerte(password: str) -> None:
    ok, errores = validar_password(password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"mensaje": "La contraseña no cumple la política de seguridad", "errores": errores},
        )


def _as_utc(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


async def _columnas_seguridad_login(db: AsyncSession) -> set[str]:
    """Detecta columnas de hardening sin impedir login si la migracion falta."""
    try:
        rows = (await db.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'usuarios'
                  AND column_name IN ('failed_login_attempts', 'last_failed_login', 'locked_until')
            """)
        )).scalars().all()
        return set(rows)
    except Exception:
        return set()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ResetPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _validar_email(v)


class ResetPasswordConfirm(BaseModel):
    token: str = Field(..., min_length=10)
    password_nueva: str = Field(..., min_length=8, max_length=128)


class InvitarUsuarioRequest(BaseModel):
    email: str
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str | None = Field(None, max_length=100)
    rol: str = Field("operador", pattern="^(admin|operador|viewer)$")

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _validar_email(v)


# ─── Login ───────────────────────────────────────────────────────────────────

@router.post("/token", response_model=TokenResponse, summary="Login — obtener JWT")
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Autentica al usuario y devuelve un JWT con rate limit, lockout y timing seguro."""
    limiter.check(request, "5/minute")
    email = form.username.lower().strip()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        text("""
            SELECT u.id, u.nombre, u.apellido, u.email, u.password_hash, u.empresa_id,
                   u.activo,
                   r.nombre AS rol
            FROM usuarios u
            JOIN roles_usuario r ON r.id = u.id_rol
            WHERE LOWER(u.email) = LOWER(:email)
        """),
        {"email": email},
    )
    user = result.mappings().first()
    columnas_seguridad = await _columnas_seguridad_login(db)
    tiene_lockout = {"failed_login_attempts", "last_failed_login", "locked_until"}.issubset(columnas_seguridad)

    seguridad_login = {
        "failed_login_attempts": 0,
        "last_failed_login": None,
        "locked_until": None,
    }
    if user and tiene_lockout:
        seguridad_login = (await db.execute(
            text("""
                SELECT failed_login_attempts, last_failed_login, locked_until
                FROM usuarios
                WHERE id = :id
            """),
            {"id": str(user["id"])},
        )).mappings().first() or seguridad_login

    # Timing attack fix: siempre ejecutar bcrypt aunque el usuario no exista.
    password_hash = user["password_hash"] if user and user["password_hash"] else DUMMY_PASSWORD_HASH
    password_ok = verify_password(form.password, password_hash)

    if not user or not user["activo"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    locked_until = _as_utc(seguridad_login["locked_until"])
    if locked_until and locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada temporalmente por intentos fallidos. Probá de nuevo en unos minutos.",
        )

    if not password_ok:
        failed_attempts = 1
        new_locked_until = None
        if tiene_lockout:
            last_failed = _as_utc(seguridad_login["last_failed_login"])
            previous_attempts = int(seguridad_login["failed_login_attempts"] or 0)
            within_window = bool(last_failed and now - last_failed <= timedelta(minutes=LOCKOUT_WINDOW_MINUTES))
            failed_attempts = previous_attempts + 1 if within_window else 1
            new_locked_until = now + timedelta(minutes=LOCKOUT_MINUTES) if failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS else None

            await db.execute(
                text("""
                    UPDATE usuarios
                    SET failed_login_attempts = :attempts,
                        last_failed_login = NOW(),
                        locked_until = :locked_until
                    WHERE id = :id
                """),
                {
                    "attempts": failed_attempts,
                    "locked_until": new_locked_until,
                    "id": str(user["id"]),
                },
            )
        await audit_with_request(
            request,
            db,
            usuario={"sub": str(user["id"]), "empresa_id": str(user["empresa_id"])},
            accion="IA_ACTION",
            tabla="usuarios",
            registro_id=str(user["id"]),
            datos_nuevos={"evento": "login_fallido", "intentos": failed_attempts, "bloqueado": bool(new_locked_until)},
        )
        await db.commit()

        if new_locked_until:
            try:
                enviar_cuenta_bloqueada(
                    to=user["email"],
                    nombre=user["nombre"],
                    ip=extraer_ip(request),
                    dispositivo=request.headers.get("user-agent"),
                )
            except EmailError:
                pass
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Cuenta bloqueada temporalmente por intentos fallidos. Probá de nuevo en 15 minutos.",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    token = create_access_token({
        "sub": str(user["id"]),
        "empresa_id": str(user["empresa_id"]),
        "rol": user["rol"],
    })

    if tiene_lockout:
        await db.execute(
            text("""
                UPDATE usuarios
                SET ultimo_acceso = NOW(),
                    failed_login_attempts = 0,
                    last_failed_login = NULL,
                    locked_until = NULL
                WHERE id = :id
            """),
            {"id": str(user["id"])},
        )
    else:
        await db.execute(
            text("UPDATE usuarios SET ultimo_acceso = NOW() WHERE id = :id"),
            {"id": str(user["id"])},
        )
    await audit_with_request(
        request,
        db,
        usuario={"sub": str(user["id"]), "empresa_id": str(user["empresa_id"])},
        accion="IA_ACTION",
        tabla="usuarios",
        registro_id=str(user["id"]),
        datos_nuevos={"evento": "login", "rol": user["rol"]},
    )
    await db.commit()

    return TokenResponse(
        access_token=token,
        rol=user["rol"],
        empresa_id=user["empresa_id"],
        usuario_id=user["id"],
        usuario_nombre=user["nombre"],
        usuario_apellido=user["apellido"],
    )


# ─── Reset password (flujo "olvidé mi contraseña") ───────────────────────────

@router.post("/reset-password", summary="Pedir email para restablecer contraseña")
async def reset_password_request(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manda email con link de reset si el usuario existe.
    Por seguridad, devuelve el mismo mensaje exista o no — para no filtrar
    qué emails están registrados.
    """
    email = data.email.lower().strip()
    user = (await db.execute(
        text("SELECT id, nombre, activo FROM usuarios WHERE email = :e"),
        {"e": email},
    )).mappings().first()

    # Solo creamos token y mandamos email si el usuario existe y está activo
    if user and user["activo"]:
        token_plano, token_hash = _generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)

        await db.execute(
            text("""
                INSERT INTO password_reset_tokens (usuario_id, token_hash, expires_at, proposito)
                VALUES (:uid, :h, :exp, 'reset')
            """),
            {"uid": str(user["id"]), "h": token_hash, "exp": expires_at},
        )
        await db.commit()

        try:
            enviar_reset_password(to=email, nombre=user["nombre"], token=token_plano)
        except EmailError:
            # Loguear pero no filtrar el error al cliente
            pass

    # Mensaje genérico
    return {"mensaje": "Si tu email está registrado, recibirás un enlace para restablecer tu contraseña."}


@router.post("/reset-password/confirm", summary="Confirmar reset con token")
async def reset_password_confirm(
    data: ResetPasswordConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cambia la password si el token es válido y no expiró."""
    token_hash = _hash_token(data.token)

    row = (await db.execute(
        text("""
            SELECT t.id AS token_id, t.usuario_id, t.expires_at, t.used_at, t.proposito,
                   u.email, u.nombre
            FROM password_reset_tokens t
            JOIN usuarios u ON u.id = t.usuario_id
            WHERE t.token_hash = :h AND t.proposito = 'reset'
        """),
        {"h": token_hash},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=400, detail="Enlace inválido")
    if row["used_at"]:
        raise HTTPException(status_code=400, detail="Este enlace ya fue usado")

    expires_at = row["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="El enlace expiró. Pedí uno nuevo.")

    _validar_password_fuerte(data.password_nueva)
    nuevo_hash = hash_password(data.password_nueva)
    await db.execute(
        text("UPDATE usuarios SET password_hash = :h, password_changed_at = NOW() WHERE id = :id"),
        {"h": nuevo_hash, "id": str(row["usuario_id"])},
    )
    await db.execute(
        text("UPDATE password_reset_tokens SET used_at = NOW() WHERE id = :tid"),
        {"tid": str(row["token_id"])},
    )
    await audit(
        db, usuario={"sub": str(row["usuario_id"]), "empresa_id": "system"},
        accion="UPDATE", tabla="usuarios", registro_id=str(row["usuario_id"]),
        datos_nuevos={"evento": "password_reset_confirmado"},
    )
    await db.commit()
    try:
        enviar_password_cambiada(
            to=row["email"],
            nombre=row["nombre"],
            ip=extraer_ip(request),
            dispositivo=request.headers.get("user-agent"),
        )
    except EmailError:
        pass
    return {"mensaje": "Contraseña actualizada. Ya podés iniciar sesión."}


# ─── Invitación de usuario nuevo ─────────────────────────────────────────────

@router.post("/invitar-usuario", summary="Admin invita usuario por email")
async def invitar_usuario(
    data: InvitarUsuarioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Crea un usuario nuevo (sin password) y le manda email para que setee la suya.
    Solo admin.
    """
    empresa_id = current_user["empresa_id"]
    email = data.email.lower().strip()

    # Verificar que no exista
    existe = (await db.execute(
        text("SELECT id FROM usuarios WHERE empresa_id = :e AND email = :em"),
        {"e": empresa_id, "em": email},
    )).scalar()
    if existe:
        raise HTTPException(status_code=409, detail="Ya hay un usuario con ese email en tu empresa.")

    # Buscar el rol
    rol_id = (await db.execute(
        text("SELECT id FROM roles_usuario WHERE nombre = :n"),
        {"n": data.rol},
    )).scalar()
    if not rol_id:
        raise HTTPException(status_code=400, detail=f"Rol '{data.rol}' no existe")

    # Nombre de la empresa para el email
    empresa_nombre = (await db.execute(
        text("SELECT nombre FROM empresas WHERE id = :id"),
        {"id": empresa_id},
    )).scalar() or "tu empresa"

    # Crear usuario inactivo con password placeholder. Activado al confirmar.
    placeholder_hash = bcrypt.hashpw(secrets.token_urlsafe(32).encode(), bcrypt.gensalt(12)).decode()
    nuevo_id = (await db.execute(
        text("""
            INSERT INTO usuarios (empresa_id, nombre, apellido, email, password_hash, id_rol, activo)
            VALUES (:e, :n, :a, :em, :ph, :r, FALSE)
            RETURNING id
        """),
        {"e": empresa_id, "n": data.nombre, "a": data.apellido,
         "em": email, "ph": placeholder_hash, "r": str(rol_id)},
    )).scalar()

    # Token de invitación (TTL 7 días)
    token_plano, token_hash = _generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_TOKEN_TTL_DAYS)
    await db.execute(
        text("""
            INSERT INTO password_reset_tokens (usuario_id, token_hash, expires_at, proposito)
            VALUES (:uid, :h, :exp, 'invitacion')
        """),
        {"uid": str(nuevo_id), "h": token_hash, "exp": expires_at},
    )
    await audit(
        db, usuario=current_user, accion="INSERT", tabla="usuarios",
        registro_id=str(nuevo_id),
        datos_nuevos={"evento": "invitar_usuario", "email": email, "rol": data.rol},
    )
    await db.commit()

    # Mandar email
    try:
        enviar_invitacion_usuario(
            to=email, nombre=data.nombre, token=token_plano, empresa=empresa_nombre,
        )
    except EmailError as e:
        # El usuario quedó creado pero el email falló. Devolver warning.
        return {
            "id": str(nuevo_id),
            "email": email,
            "warning": f"Usuario creado pero el email no se pudo enviar: {e}. "
                       f"Pasale este link manualmente: {token_plano}",
        }

    return {
        "id": str(nuevo_id),
        "email": email,
        "mensaje": f"Invitación enviada a {email}. Tiene 7 días para activar la cuenta.",
    }


@router.post("/seteo-password/confirm", summary="Setear primera password con token de invitación")
async def seteo_password_confirm(
    data: ResetPasswordConfirm,  # mismo shape: token + password_nueva
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Activa el usuario y setea su primera password."""
    token_hash = _hash_token(data.token)

    row = (await db.execute(
        text("""
            SELECT t.id AS token_id, t.usuario_id, t.expires_at, t.used_at, t.proposito,
                   u.email, u.nombre
            FROM password_reset_tokens t
            JOIN usuarios u ON u.id = t.usuario_id
            WHERE t.token_hash = :h AND t.proposito = 'invitacion'
        """),
        {"h": token_hash},
    )).mappings().first()

    if not row:
        raise HTTPException(status_code=400, detail="Enlace inválido")
    if row["used_at"]:
        raise HTTPException(status_code=400, detail="Este enlace ya fue usado")

    expires_at = row["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=400,
            detail="La invitación expiró. Pedile al administrador que te invite de nuevo.",
        )

    _validar_password_fuerte(data.password_nueva)
    nuevo_hash = hash_password(data.password_nueva)
    await db.execute(
        text("UPDATE usuarios SET password_hash = :h, activo = TRUE, password_changed_at = NOW() WHERE id = :id"),
        {"h": nuevo_hash, "id": str(row["usuario_id"])},
    )
    await db.execute(
        text("UPDATE password_reset_tokens SET used_at = NOW() WHERE id = :tid"),
        {"tid": str(row["token_id"])},
    )
    await audit(
        db, usuario={"sub": str(row["usuario_id"]), "empresa_id": "system"},
        accion="UPDATE", tabla="usuarios", registro_id=str(row["usuario_id"]),
        datos_nuevos={"evento": "seteo_password_inicial"},
    )
    await db.commit()
    try:
        enviar_password_cambiada(
            to=row["email"],
            nombre=row["nombre"],
            ip=extraer_ip(request),
            dispositivo=request.headers.get("user-agent"),
        )
    except EmailError:
        pass
    return {"mensaje": "¡Cuenta activada! Ya podés iniciar sesión."}
