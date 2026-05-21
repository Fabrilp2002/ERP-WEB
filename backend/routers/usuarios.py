"""
Router de administración de usuarios.
Solo usuarios con rol 'admin' pueden listar, crear, editar o desactivar.
"""
from uuid import UUID
import io
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.password_policy import validar_password
from ..core.security import get_current_user, hash_password, require_admin
from ..services.audit import registrar as audit

router = APIRouter(prefix="/usuarios", tags=["Administración de usuarios"])


def _jsonable(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return str(obj)


def _rows(rows) -> list[dict]:
    return [_jsonable(dict(r)) for r in rows]


def _validar_password_fuerte(password: str) -> None:
    ok, errores = validar_password(password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"mensaje": "La contraseña no cumple la política de seguridad", "errores": errores},
        )


class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    apellido: str | None = Field(None, max_length=150)
    email: EmailStr
    telefono: str | None = Field(None, max_length=30)
    cargo: str | None = Field(None, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    rol: str = Field(..., pattern="^(admin|operador|viewer)$")


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=150)
    apellido: str | None = Field(None, max_length=150)
    telefono: str | None = Field(None, max_length=30)
    cargo: str | None = Field(None, max_length=100)
    rol: str | None = Field(None, pattern="^(admin|operador|viewer)$")
    activo: bool | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class MeUpdate(BaseModel):
    """Lo que cualquier usuario puede actualizar de SU PROPIO perfil."""
    nombre: str | None = Field(None, min_length=2, max_length=150)
    apellido: str | None = Field(None, max_length=150)
    telefono: str | None = Field(None, max_length=30)
    cargo: str | None = Field(None, max_length=100)
    modo_ui: str | None = Field(None, pattern="^(basico|avanzado)$")


# ─── Endpoints "/me" — cualquier usuario sobre su propio perfil ──────────────

@router.get("/me", summary="Datos del usuario logueado (perfil propio)")
async def obtener_me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    row = (await db.execute(
        text("""
            SELECT u.id, u.empresa_id, u.nombre, u.apellido, u.email,
                   u.telefono, u.cargo, u.activo, u.modo_ui,
                   u.ultimo_acceso, r.nombre AS rol
            FROM usuarios u
            JOIN roles_usuario r ON r.id = u.id_rol
            WHERE u.id = :id
        """),
        {"id": user_id},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return dict(row)


@router.patch("/me", summary="Actualizar mi perfil (nombre, modo_ui, etc)")
async def actualizar_me(
    data: MeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    El usuario actualiza datos de su propio perfil. NO puede cambiar su rol,
    activo ni email — eso es exclusivo de admin (PATCH /usuarios/{id}).
    """
    user_id = current_user["sub"]
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nada para actualizar")

    set_parts = ", ".join(f"{k} = :{k}" for k in updates)
    params = {**updates, "id": user_id}
    await db.execute(
        text(f"UPDATE usuarios SET {set_parts} WHERE id = :id"),
        params,
    )
    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="usuarios",
        registro_id=user_id, datos_nuevos={**updates, "evento": "perfil_propio"},
    )
    await db.commit()
    return await obtener_me(db, current_user)


@router.get("/me/seguridad", summary="Mi seguridad: últimos accesos e intentos")
async def mi_seguridad(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    usuario = (await db.execute(
        text("""
            SELECT ultimo_acceso, failed_login_attempts, last_failed_login,
                   locked_until, password_changed_at
            FROM usuarios
            WHERE id = :id
        """),
        {"id": user_id},
    )).mappings().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    eventos = (await db.execute(
        text("""
            SELECT fecha, accion, tabla_afectada, datos_nuevos, origen, ip_origen, user_agent
            FROM auditoria_log
            WHERE usuario_id = :id
              AND (
                datos_nuevos->>'evento' IN (
                  'login', 'login_fallido', 'password_reset_confirmado',
                  'seteo_password_inicial', 'perfil_propio', 'delete_account_self'
                )
                OR tabla_afectada = 'usuarios'
              )
            ORDER BY fecha DESC
            LIMIT 10
        """),
        {"id": user_id},
    )).mappings().all()

    return {
        "usuario": _jsonable(dict(usuario)),
        "eventos": _rows(eventos),
    }


@router.get("/me/exportar-datos", summary="Exportar mis datos personales")
async def exportar_mis_datos(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    empresa_id = current_user["empresa_id"]

    perfil = (await db.execute(
        text("""
            SELECT u.id, u.empresa_id, u.nombre, u.apellido, u.email, u.telefono,
                   u.cargo, u.activo, u.modo_ui, u.ultimo_acceso, u.fecha_creacion,
                   u.password_changed_at, r.nombre AS rol
            FROM usuarios u
            JOIN roles_usuario r ON r.id = u.id_rol
            WHERE u.id = :id AND u.empresa_id = :e
        """),
        {"id": user_id, "e": empresa_id},
    )).mappings().first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    comprobantes = (await db.execute(
        text("""
            SELECT id, numero_comprobante, fecha_emision, monto_total, saldo_pendiente,
                   metodo_carga, estado_validacion, notas, fecha_creacion
            FROM comprobantes
            WHERE empresa_id = :e AND usuario_carga_id = :id
            ORDER BY fecha_creacion DESC
        """),
        {"id": user_id, "e": empresa_id},
    )).mappings().all()
    pagos = (await db.execute(
        text("""
            SELECT id, comprobante_id, numero_recibo, fecha_pago, monto_pagado,
                   medio_pago, notas, fecha_creacion
            FROM pagos
            WHERE empresa_id = :e AND usuario_id = :id
            ORDER BY fecha_creacion DESC
        """),
        {"id": user_id, "e": empresa_id},
    )).mappings().all()
    auditoria = (await db.execute(
        text("""
            SELECT fecha, accion, tabla_afectada, registro_id, datos_anteriores,
                   datos_nuevos, origen, ip_origen, user_agent
            FROM auditoria_log
            WHERE empresa_id = :e AND usuario_id = :id
            ORDER BY fecha DESC
        """),
        {"id": user_id, "e": empresa_id},
    )).mappings().all()

    payload = {
        "generado_en": datetime.utcnow().isoformat() + "Z",
        "perfil": _jsonable(dict(perfil)),
        "comprobantes_cargados": _rows(comprobantes),
        "pagos_registrados": _rows(pagos),
        "auditoria": _rows(auditoria),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mis_datos_erp.json", json.dumps(payload, ensure_ascii=False, indent=2))
    buffer.seek(0)

    await audit(
        db, usuario=current_user, accion="SELECT", tabla="usuarios",
        registro_id=user_id, datos_nuevos={"evento": "exportar_datos_propios"},
    )
    await db.commit()

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="mis_datos_erp.zip"'},
    )


@router.delete("/me", summary="Eliminar/anonimizar mi cuenta")
async def eliminar_mi_cuenta(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    empresa_id = current_user["empresa_id"]
    anon_email = f"deleted-{user_id}@deleted.local"

    row = (await db.execute(
        text("""
            UPDATE usuarios
            SET nombre = 'Usuario Eliminado',
                apellido = NULL,
                email = :email,
                telefono = NULL,
                cargo = NULL,
                activo = FALSE,
                failed_login_attempts = 0,
                last_failed_login = NULL,
                locked_until = NULL
            WHERE id = :id AND empresa_id = :e
            RETURNING id
        """),
        {"id": user_id, "e": empresa_id, "email": anon_email},
    )).scalar()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="usuarios", registro_id=user_id,
        datos_nuevos={"evento": "delete_account_self", "anonimizado": True},
    )
    await db.commit()
    return {"mensaje": "Cuenta anonimizada. Se preservan los registros contables y de auditoría."}


@router.get("/", summary="Listar usuarios de la empresa")
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT u.id, u.nombre, u.apellido, u.email, u.telefono, u.cargo,
                   u.activo, u.fecha_creacion, u.ultimo_acceso,
                   r.nombre AS rol
            FROM usuarios u
            JOIN roles_usuario r ON r.id = u.id_rol
            WHERE u.empresa_id = :e
            ORDER BY u.fecha_creacion DESC
        """),
        {"e": empresa_id},
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/", status_code=201, summary="Crear nuevo usuario")
async def crear_usuario(
    data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    _validar_password_fuerte(data.password)

    existe = (await db.execute(
        text("SELECT 1 FROM usuarios WHERE empresa_id = :e AND LOWER(email) = LOWER(:em)"),
        {"e": empresa_id, "em": data.email},
    )).scalar()
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email en la empresa")

    rol_id = (await db.execute(
        text("SELECT id FROM roles_usuario WHERE nombre = :n"),
        {"n": data.rol},
    )).scalar()
    if not rol_id:
        raise HTTPException(status_code=422, detail=f"Rol inválido: {data.rol}")

    nuevo = (await db.execute(
        text("""
            INSERT INTO usuarios (empresa_id, nombre, apellido, email, telefono, cargo, password_hash, id_rol, activo)
            VALUES (:e, :n, :a, :em, :tel, :cg, :p, :r, TRUE)
            RETURNING id, nombre, apellido, email, telefono, cargo, activo, fecha_creacion
        """),
        {
            "e": empresa_id,
            "n": data.nombre,
            "a": data.apellido,
            "em": data.email,
            "tel": data.telefono,
            "cg": data.cargo,
            "p": hash_password(data.password),
            "r": str(rol_id),
        },
    )).mappings().first()
    await audit(
        db, usuario=current_user, accion="INSERT", tabla="usuarios",
        registro_id=str(nuevo["id"]),
        datos_nuevos={"nombre": data.nombre, "apellido": data.apellido,
                      "email": data.email, "telefono": data.telefono,
                      "cargo": data.cargo, "rol": data.rol},
    )
    await db.commit()
    return {**dict(nuevo), "rol": data.rol}


@router.patch("/{usuario_id}", summary="Actualizar usuario (nombre, apellido, rol, activo, password)")
async def actualizar_usuario(
    usuario_id: UUID,
    data: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    campos = []
    params: dict = {"id": str(usuario_id), "e": empresa_id}
    cambios: dict = {}

    if data.nombre is not None:
        campos.append("nombre = :nombre")
        params["nombre"] = data.nombre
        cambios["nombre"] = data.nombre
    if data.apellido is not None:
        campos.append("apellido = :apellido")
        params["apellido"] = data.apellido
        cambios["apellido"] = data.apellido
    if data.telefono is not None:
        campos.append("telefono = :telefono")
        params["telefono"] = data.telefono
        cambios["telefono"] = data.telefono
    if data.cargo is not None:
        campos.append("cargo = :cargo")
        params["cargo"] = data.cargo
        cambios["cargo"] = data.cargo
    if data.activo is not None:
        campos.append("activo = :activo")
        params["activo"] = data.activo
        cambios["activo"] = data.activo
    if data.password is not None:
        _validar_password_fuerte(data.password)
        campos.append("password_hash = :pwd")
        campos.append("password_changed_at = NOW()")
        params["pwd"] = hash_password(data.password)
        cambios["password"] = "***"
    if data.rol is not None:
        rol_id = (await db.execute(
            text("SELECT id FROM roles_usuario WHERE nombre = :n"),
            {"n": data.rol},
        )).scalar()
        if not rol_id:
            raise HTTPException(status_code=422, detail=f"Rol inválido: {data.rol}")
        campos.append("id_rol = :rol")
        params["rol"] = str(rol_id)
        cambios["rol"] = data.rol

    if not campos:
        raise HTTPException(status_code=400, detail="Nada para actualizar")

    if str(usuario_id) == str(current_user.get("sub")):
        if data.activo is False or data.rol in ("operador", "viewer"):
            raise HTTPException(
                status_code=409,
                detail="No podés desactivarte ni cambiar tu propio rol. Pedile a otro admin.",
            )

    result = await db.execute(
        text(f"UPDATE usuarios SET {', '.join(campos)} WHERE id = :id AND empresa_id = :e RETURNING id"),
        params,
    )
    if result.scalar() is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await audit(
        db, usuario=current_user, accion="UPDATE", tabla="usuarios",
        registro_id=str(usuario_id), datos_nuevos=cambios,
    )
    await db.commit()
    return {"mensaje": "Usuario actualizado"}


@router.delete("/{usuario_id}", summary="Eliminar usuario permanentemente")
async def eliminar_usuario(
    usuario_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Borrado fisico. El admin no puede auto-eliminarse."""
    if str(usuario_id) == str(current_user.get("sub")):
        raise HTTPException(status_code=409, detail="No podés eliminar tu propia cuenta.")

    empresa_id = current_user["empresa_id"]
    existente = (await db.execute(
        text("SELECT nombre, apellido, email FROM usuarios WHERE id = :id AND empresa_id = :e"),
        {"id": str(usuario_id), "e": empresa_id},
    )).mappings().first()
    if not existente:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # borrar referencias en auditoria (o dejar con usuario_id null)
    await db.execute(
        text("UPDATE auditoria_log SET usuario_id = NULL WHERE usuario_id = :id"),
        {"id": str(usuario_id)},
    )
    await db.execute(
        text("DELETE FROM usuarios WHERE id = :id AND empresa_id = :e"),
        {"id": str(usuario_id), "e": empresa_id},
    )
    await audit(
        db, usuario=current_user, accion="DELETE", tabla="usuarios",
        registro_id=str(usuario_id), datos_anteriores=dict(existente),
    )
    await db.commit()
    return {"mensaje": "Usuario eliminado permanentemente"}
