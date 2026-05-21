"""
Router /admin — acciones de super-administrador.

Incluye:
  - GET /admin/auditoria        : historial de acciones filtrable
  - POST /admin/wipe-datos      : borra todos los datos de negocio (conserva usuarios/empresa)
  - DELETE /admin/comprobantes/{id} : borrado fisico definitivo
  - GET /admin/backup           : dump completo en JSON

Todas requieren rol admin. Toda accion queda en auditoria_log.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_db
from ..core.storage import storage, BUCKET_ADJUNTOS, BUCKET_LOGOS, StorageError
from ..core.security import require_admin
from ..services.audit import registrar as audit

router = APIRouter(prefix="/admin", tags=["Administración del sistema"])


def _jsonable(o):
    if o is None:
        return None
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    return o


# ── Auditoría ─────────────────────────────────────────────────────────────────

@router.get("/auditoria", summary="Historial de acciones del sistema")
async def listar_auditoria(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
    tabla: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    usuario_id: Optional[UUID] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    limite: int = Query(200, ge=1, le=1000),
):
    empresa_id = current_user["empresa_id"]
    where = ["a.empresa_id = :e"]
    params: dict = {"e": empresa_id, "lim": limite}

    if tabla:
        where.append("a.tabla_afectada = :t"); params["t"] = tabla
    if accion:
        where.append("a.accion = :ac"); params["ac"] = accion
    if usuario_id:
        where.append("a.usuario_id = :u"); params["u"] = str(usuario_id)
    if desde:
        where.append("a.fecha >= :d"); params["d"] = desde
    if hasta:
        from datetime import date as _date, timedelta as _td
        h_obj = hasta if hasattr(hasta, "year") else _date.fromisoformat(str(hasta))
        where.append("a.fecha < :h"); params["h"] = (h_obj + _td(days=1)).isoformat()

    result = await db.execute(
        text(f"""
            SELECT a.id, a.fecha, a.accion,
                   a.tabla_afectada AS tabla, a.registro_id,
                   a.origen, a.datos_anteriores, a.datos_nuevos,
                   a.usuario_id, a.empresa_id,
                   u.nombre AS usuario_nombre, u.apellido AS usuario_apellido, u.email AS usuario_email
            FROM auditoria_log a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE {' AND '.join(where)}
            ORDER BY a.fecha DESC
            LIMIT :lim
        """),
        params,
    )
    rows = [dict(r) for r in result.mappings().all()]
    return _jsonable(rows)


# ── Wipe de datos ─────────────────────────────────────────────────────────────

class WipeIn(BaseModel):
    confirmacion: str = Field(..., description='Debe ser "BORRAR TODO"')
    incluir_catalogos: bool = False  # si True, borra clientes/proveedores/inventario también


@router.post("/wipe-datos", summary="[PELIGRO] Borra todos los datos de negocio")
async def wipe_datos(
    data: WipeIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Elimina: pagos, detalle_comprobantes, comprobantes.
    Si incluir_catalogos=True: tambien clientes, proveedores, inventario, categorias.
    CONSERVA: empresas, usuarios, roles_usuario, tipos_comprobante.
    """
    if data.confirmacion != "BORRAR TODO":
        raise HTTPException(status_code=400,
                            detail='Confirmacion invalida. Escribi exactamente: BORRAR TODO')

    empresa_id = current_user["empresa_id"]
    borrados = {}

    tablas_core = [
        "pagos",
        "detalle_comprobantes",
        "comprobantes",
    ]
    for t in tablas_core:
        r = await db.execute(
            text(f"DELETE FROM {t} WHERE empresa_id = :e"), {"e": empresa_id}
        )
        borrados[t] = r.rowcount or 0

    if data.incluir_catalogos:
        # detalle_comprobantes ya esta vacio, podemos tocar items y luego catalogos
        tablas_cat = [
            "movimientos_banco",
            "cuentas_banco",
            "inventario",
            "categorias_inventario",
            "clientes",
            "proveedores",
        ]
        for t in tablas_cat:
            try:
                r = await db.execute(
                    text(f"DELETE FROM {t} WHERE empresa_id = :e"), {"e": empresa_id}
                )
                borrados[t] = r.rowcount or 0
            except Exception as e:
                borrados[t] = f"ERR: {e}"

    await audit(
        db, usuario=current_user, accion="DELETE", tabla="_sistema",
        datos_nuevos={"evento": "wipe_datos", "borrados": borrados,
                      "incluir_catalogos": data.incluir_catalogos},
    )
    await db.commit()
    return {"mensaje": "Datos borrados exitosamente", "borrados": borrados}


# ── Hard delete de comprobante ────────────────────────────────────────────────

@router.delete("/comprobantes/{comprobante_id}",
               summary="[PELIGRO] Borrar comprobante permanentemente")
async def hard_delete_comprobante(
    comprobante_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Borrado fisico + cascada. Anular (soft) es el camino normal, esto es solo admin."""
    empresa_id = current_user["empresa_id"]
    existente = (await db.execute(
        text("""
            SELECT numero_comprobante, monto_total, cliente_id, proveedor_id
            FROM comprobantes WHERE id = :id AND empresa_id = :e
        """),
        {"id": str(comprobante_id), "e": empresa_id},
    )).mappings().first()
    if not existente:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    await db.execute(text("DELETE FROM pagos WHERE comprobante_id = :id"),
                     {"id": str(comprobante_id)})
    await db.execute(text("DELETE FROM detalle_comprobantes WHERE comprobante_id = :id"),
                     {"id": str(comprobante_id)})
    await db.execute(text("DELETE FROM comprobantes WHERE id = :id AND empresa_id = :e"),
                     {"id": str(comprobante_id), "e": empresa_id})

    await audit(
        db, usuario=current_user, accion="DELETE", tabla="comprobantes",
        registro_id=str(comprobante_id), datos_anteriores=dict(existente),
    )
    await db.commit()
    return {"mensaje": "Comprobante eliminado permanentemente"}


# ── Backup completo ───────────────────────────────────────────────────────────

@router.get("/backup", summary="Backup JSON de todos los datos de la empresa")
async def backup_empresa(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    tablas = [
        "empresas", "usuarios", "roles_usuario",
        "clientes", "proveedores",
        "categorias_inventario", "inventario",
        "tipos_comprobante", "comprobantes", "detalle_comprobantes",
        "pagos", "cuentas_banco", "movimientos_banco",
        "auditoria_log",
    ]
    dump: dict = {"exportado": datetime.now().isoformat(), "empresa_id": str(empresa_id),
                  "tablas": {}}

    for t in tablas:
        try:
            if t in ("roles_usuario",):
                r = await db.execute(text(f"SELECT * FROM {t}"))
            elif t == "empresas":
                r = await db.execute(text(f"SELECT * FROM empresas WHERE id = :e"),
                                     {"e": empresa_id})
            else:
                r = await db.execute(text(f"SELECT * FROM {t} WHERE empresa_id = :e"),
                                     {"e": empresa_id})
            dump["tablas"][t] = [_jsonable(dict(row)) for row in r.mappings().all()]
        except Exception as e:
            dump["tablas"][t] = {"error": str(e)}

    await audit(
        db, usuario=current_user, accion="SELECT", tabla="_sistema",
        datos_nuevos={"evento": "backup", "tablas": list(dump["tablas"].keys())},
    )
    await db.commit()

    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return JSONResponse(
        content=dump,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Backup completo en ZIP (datos + adjuntos + logos) ────────────────────────

@router.get(
    "/backup-zip",
    summary="Backup completo (ZIP con datos JSON + adjuntos + logos)",
)
async def backup_zip(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Arma un .zip en memoria con:
      - `datos.json`            : dump de todas las tablas de la empresa
      - `adjuntos/comprobantes/`: archivos de comprobantes de ESTA empresa
      - `adjuntos/pagos/`       : archivos de pagos de ESTA empresa
      - `logos/`                : logo de la empresa (si existe)
      - `manifest.txt`          : resumen legible del contenido

    Filtra por `empresa_id` en todos los cruces — nunca incluye datos de
    otra empresa.
    """
    empresa_id = current_user["empresa_id"]

    # ── 1) dump JSON ────────────────────────────────────────────────────────
    tablas = [
        "empresas", "usuarios", "roles_usuario",
        "clientes", "proveedores",
        "categorias_inventario", "inventario",
        "tipos_comprobante", "comprobantes", "detalle_comprobantes",
        "pagos", "cuentas_banco", "movimientos_banco",
        "auditoria_log",
    ]
    dump: dict = {
        "exportado": datetime.now().isoformat(),
        "empresa_id": str(empresa_id),
        "tablas": {},
    }
    for t in tablas:
        try:
            if t == "roles_usuario":
                r = await db.execute(text("SELECT * FROM roles_usuario"))
            elif t == "empresas":
                r = await db.execute(
                    text("SELECT * FROM empresas WHERE id = :e"), {"e": empresa_id},
                )
            elif t == "detalle_comprobantes":
                r = await db.execute(text("""
                    SELECT d.* FROM detalle_comprobantes d
                    JOIN comprobantes c ON c.id = d.comprobante_id
                    WHERE c.empresa_id = :e
                """), {"e": empresa_id})
            elif t == "movimientos_banco":
                r = await db.execute(text("""
                    SELECT m.* FROM movimientos_banco m
                    JOIN cuentas_banco cb ON cb.id = m.cuenta_id
                    WHERE cb.empresa_id = :e
                """), {"e": empresa_id})
            else:
                r = await db.execute(
                    text(f"SELECT * FROM {t} WHERE empresa_id = :e"),
                    {"e": empresa_id},
                )
            dump["tablas"][t] = [_jsonable(dict(row)) for row in r.mappings().all()]
        except Exception as e:  # noqa: BLE001
            dump["tablas"][t] = {"error": str(e)}

    # ── 2) listar IDs de esta empresa para filtrar archivos ────────────────
    comp_ids = set()
    pago_ids = set()
    try:
        r = await db.execute(
            text("SELECT id FROM comprobantes WHERE empresa_id = :e"),
            {"e": empresa_id},
        )
        comp_ids = {str(row["id"]) for row in r.mappings().all()}
        r = await db.execute(
            text("SELECT id FROM pagos WHERE empresa_id = :e"),
            {"e": empresa_id},
        )
        pago_ids = {str(row["id"]) for row in r.mappings().all()}
    except Exception:
        pass

    # ── 3) armar zip en memoria ────────────────────────────────────────────
    buffer = io.BytesIO()
    manifest_lines = [
        f"ERP Universal — Backup de empresa",
        f"Generado: {datetime.now().isoformat()}",
        f"Empresa ID: {empresa_id}",
        f"",
        f"Contenido:",
    ]
    archivos_adj_comp = 0
    archivos_adj_pago = 0
    archivos_logo = 0

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # datos.json
        zf.writestr("datos.json", json.dumps(dump, ensure_ascii=False, indent=2))

        # ── Adjuntos desde Supabase Storage (bucket privado) ──────────────
        # Path layout: adjuntos/<empresa_id>/comprobantes/<id>.<ext>
        #              adjuntos/<empresa_id>/pagos/<id>.<ext>
        try:
            archivos_comp = storage.list_files(BUCKET_ADJUNTOS, f"{empresa_id}/comprobantes")
            for entry in archivos_comp:
                name = entry.get("name", "")
                if not name:
                    continue
                stem = name.rsplit(".", 1)[0]
                if stem in comp_ids:
                    try:
                        contenido = storage.download(BUCKET_ADJUNTOS, f"{empresa_id}/comprobantes/{name}")
                        zf.writestr(f"adjuntos/comprobantes/{name}", contenido)
                        archivos_adj_comp += 1
                    except StorageError:
                        pass

            archivos_pago = storage.list_files(BUCKET_ADJUNTOS, f"{empresa_id}/pagos")
            for entry in archivos_pago:
                name = entry.get("name", "")
                if not name:
                    continue
                stem = name.rsplit(".", 1)[0]
                if stem in pago_ids:
                    try:
                        contenido = storage.download(BUCKET_ADJUNTOS, f"{empresa_id}/pagos/{name}")
                        zf.writestr(f"adjuntos/pagos/{name}", contenido)
                        archivos_adj_pago += 1
                    except StorageError:
                        pass
        except Exception:
            pass  # backup parcial es mejor que ninguno

        # ── Logo de empresa desde bucket público ───────────────────────────
        try:
            archivos_logo_list = storage.list_files(BUCKET_LOGOS, empresa_id)
            for entry in archivos_logo_list:
                name = entry.get("name", "")
                if not name:
                    continue
                try:
                    contenido = storage.download(BUCKET_LOGOS, f"{empresa_id}/{name}")
                    zf.writestr(f"logos/{name}", contenido)
                    archivos_logo += 1
                except StorageError:
                    pass
        except Exception:
            pass

        # manifest legible
        manifest_lines += [
            f"  - datos.json                  ({sum(len(v) if isinstance(v, list) else 0 for v in dump['tablas'].values())} filas totales)",
            f"  - adjuntos/comprobantes/*     ({archivos_adj_comp} archivos)",
            f"  - adjuntos/pagos/*            ({archivos_adj_pago} archivos)",
            f"  - logos/*                     ({archivos_logo} archivos)",
            f"",
            f"Para restaurar: contactar soporte — este backup es de lectura.",
        ]
        zf.writestr("manifest.txt", "\n".join(manifest_lines))

    buffer.seek(0)

    await audit(
        db, usuario=current_user, accion="SELECT", tabla="_sistema",
        datos_nuevos={
            "evento": "backup_zip",
            "tablas": len(dump["tablas"]),
            "adjuntos_comprobantes": archivos_adj_comp,
            "adjuntos_pagos": archivos_adj_pago,
            "logos": archivos_logo,
            "bytes": len(buffer.getvalue()),
        },
    )
    await db.commit()

    filename = f"erp_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Estadisticas para panel admin ─────────────────────────────────────────────

@router.get("/stats", summary="Estadisticas globales del sistema")
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    empresa_id = current_user["empresa_id"]
    result = await db.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM usuarios WHERE empresa_id = :e) AS usuarios,
                (SELECT COUNT(*) FROM clientes WHERE empresa_id = :e) AS clientes,
                (SELECT COUNT(*) FROM proveedores WHERE empresa_id = :e) AS proveedores,
                (SELECT COUNT(*) FROM comprobantes WHERE empresa_id = :e) AS comprobantes,
                (SELECT COUNT(*) FROM pagos p JOIN comprobantes c ON c.id = p.comprobante_id
                 WHERE c.empresa_id = :e) AS pagos,
                (SELECT COUNT(*) FROM inventario WHERE empresa_id = :e) AS inventario,
                (SELECT COUNT(*) FROM auditoria_log WHERE empresa_id = :e) AS eventos_auditoria
        """),
        {"e": empresa_id},
    )
    return dict(result.mappings().first())
