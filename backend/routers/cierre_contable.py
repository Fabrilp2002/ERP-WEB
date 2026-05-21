"""
Router de Cierre Contable — Fase J.4
Gestión de períodos contables: apertura, cierre y bloqueo de modificaciones.
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import get_current_user, require_admin
from ..services.audit import registrar as audit

router = APIRouter(prefix="/periodos-contables", tags=["Cierre Contable"])


class PeriodoCreate(BaseModel):
    periodo: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")
    notas: Optional[str] = Field(None, max_length=500)


class CierreRequest(BaseModel):
    notas: Optional[str] = Field(None, max_length=500)


@router.get("/", summary="Listar períodos contables")
async def listar_periodos(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT pc.id, pc.periodo, pc.estado, pc.fecha_cierre, pc.notas,
                   pc.fecha_creacion,
                   TRIM(COALESCE(u.nombre,'') || ' ' || COALESCE(u.apellido,'')) AS cerrado_por,
                   -- Estadísticas del período
                   COUNT(DISTINCT a.id)  AS total_asientos,
                   COUNT(DISTINCT c.id)  AS total_comprobantes
            FROM periodos_contables pc
            LEFT JOIN usuarios u ON u.id = pc.usuario_cierre_id
            LEFT JOIN asientos_contables a
                ON a.empresa_id = pc.empresa_id
                AND substr(CAST(a.fecha AS TEXT), 1, 7) = pc.periodo
            LEFT JOIN comprobantes c
                ON c.empresa_id = pc.empresa_id
                AND substr(CAST(c.fecha_emision AS TEXT), 1, 7) = pc.periodo
                AND c.estado_validacion = 'confirmado'
            WHERE pc.empresa_id = :eid
            GROUP BY pc.id, u.nombre, u.apellido
            ORDER BY pc.periodo DESC
        """),
        {"eid": empresa_id},
    )
    return result.mappings().all()


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Abrir período contable")
async def abrir_periodo(
    data: PeriodoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]

    # Verificar que no exista ya
    existing = (await db.execute(
        text("SELECT id, estado FROM periodos_contables WHERE empresa_id = :eid AND periodo = :p"),
        {"eid": empresa_id, "p": data.periodo},
    )).mappings().first()
    if existing:
        if existing["estado"] == "abierto":
            raise HTTPException(status_code=409, detail=f"El período {data.periodo} ya está abierto")
        raise HTTPException(status_code=409,
                            detail=f"El período {data.periodo} ya existe con estado '{existing['estado']}'")

    result = await db.execute(
        text("""
            INSERT INTO periodos_contables (empresa_id, periodo, notas)
            VALUES (:eid, :periodo, :notas)
            RETURNING id, periodo, estado, fecha_creacion
        """),
        {"eid": empresa_id, "periodo": data.periodo, "notas": data.notas},
    )
    p = result.mappings().first()
    await audit(db, usuario=current_user, accion="INSERT", tabla="periodos_contables",
                registro_id=str(p["id"]), datos_nuevos={"periodo": data.periodo, "estado": "abierto"})
    await db.commit()
    return p


@router.patch("/{periodo_id}/cerrar", summary="Cerrar período contable")
async def cerrar_periodo(
    periodo_id: UUID,
    data: CierreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Cierra un período contable. Una vez cerrado, no se podrán crear ni modificar
    comprobantes cuya fecha_emision pertenezca a ese período (verificado en /comprobantes POST).
    """
    empresa_id = current_user["empresa_id"]

    p = (await db.execute(
        text("SELECT id, periodo, estado FROM periodos_contables WHERE id = :id AND empresa_id = :eid"),
        {"id": str(periodo_id), "eid": empresa_id},
    )).mappings().first()
    if not p:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    if p["estado"] == "cerrado":
        raise HTTPException(status_code=409, detail="El período ya está cerrado")

    await db.execute(
        text("""
            UPDATE periodos_contables
            SET estado = 'cerrado', fecha_cierre = NOW(),
                usuario_cierre_id = :uid, notas = COALESCE(:notas, notas)
            WHERE id = :id AND empresa_id = :eid
        """),
        {"id": str(periodo_id), "eid": empresa_id,
         "uid": current_user["sub"], "notas": data.notas},
    )
    await audit(db, usuario=current_user, accion="UPDATE", tabla="periodos_contables",
                registro_id=str(periodo_id),
                datos_nuevos={"periodo": p["periodo"], "estado": "cerrado"})
    await db.commit()
    return {"mensaje": f"Período {p['periodo']} cerrado correctamente"}


@router.patch("/{periodo_id}/reabrir", summary="Reabrir período cerrado (admin)")
async def reabrir_periodo(
    periodo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Reabre un período para correcciones. Solo admin."""
    empresa_id = current_user["empresa_id"]
    p = (await db.execute(
        text("SELECT id, periodo, estado FROM periodos_contables WHERE id = :id AND empresa_id = :eid"),
        {"id": str(periodo_id), "eid": empresa_id},
    )).mappings().first()
    if not p:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    if p["estado"] == "abierto":
        raise HTTPException(status_code=409, detail="El período ya está abierto")

    await db.execute(
        text("""
            UPDATE periodos_contables
            SET estado = 'abierto', fecha_cierre = NULL, usuario_cierre_id = NULL
            WHERE id = :id AND empresa_id = :eid
        """),
        {"id": str(periodo_id), "eid": empresa_id},
    )
    await audit(db, usuario=current_user, accion="UPDATE", tabla="periodos_contables",
                registro_id=str(periodo_id),
                datos_nuevos={"periodo": p["periodo"], "estado": "abierto"})
    await db.commit()
    return {"mensaje": f"Período {p['periodo']} reabierto"}


# ── Helper reutilizable por otros routers ────────────────────────────────────

async def verificar_periodo_abierto(db: AsyncSession, empresa_id: str, fecha: str) -> None:
    """
    Verifica que el período YYYY-MM de 'fecha' no esté cerrado.
    Lanza HTTPException 409 si está cerrado.
    Solo valida si existen períodos registrados (si no hay ninguno, pasa libremente).
    Si la tabla periodos_contables aún no existe (migración pendiente), también pasa libremente.
    """
    periodo = fecha[:7]  # 'YYYY-MM'
    try:
        row = (await db.execute(
            text("""
                SELECT estado FROM periodos_contables
                WHERE empresa_id = :eid AND periodo = :p
            """),
            {"eid": empresa_id, "p": periodo},
        )).mappings().first()
    except Exception:
        # Tabla no existe aún (migración pendiente) — pasar libremente
        return

    if row and row["estado"] == "cerrado":
        raise HTTPException(
            status_code=409,
            detail=f"El período {periodo} está cerrado. Reabrir desde Contabilidad → Cierre antes de registrar.",
        )
