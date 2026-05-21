"""
Enriquece los detalles de las facturas con items REALES distribuidos.

Contexto:
  El script `migrar_excels.py` cargó cada factura con 1 solo ítem genérico
  ("Venta facturada — Factura X" + monto total). Eso satisface la integridad
  contable pero no muestra qué se vendió realmente.

Esta versión usa la **matriz productos × cliente** del archivo
`COSTOS MP - INSUMOS - PROD TERMINADOS (1).xlsx` (sheet VENTAS 2025-2026)
que tiene cantidades agregadas por producto y por cliente, y las distribuye
proporcionalmente entre las facturas de ese cliente según el monto de cada
factura sobre el total del cliente.

Es idempotente: borra los detalles previos antes de re-generar.

Uso:
    python scripts/enriquecer_items_facturas.py [--dry-run] [--excel-dir "C:/ruta/a/excels"]
"""
from __future__ import annotations
import argparse
import asyncio
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import asyncpg
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXCEL_DIR = Path(r"C:\Users\gfcar\Desktop\IA\Empresa 1\Datos Generales de la empresa")
EXCEL_DIR = Path(os.environ.get("ERP_EXCEL_DIR", DEFAULT_EXCEL_DIR))
XLS_INV = EXCEL_DIR / "COSTOS MP - INSUMOS - PROD TERMINADOS (1).xlsx"


def configurar_excel_dir(excel_dir: str | Path | None) -> None:
    global EXCEL_DIR, XLS_INV
    if excel_dir:
        EXCEL_DIR = Path(excel_dir).expanduser().resolve()
    XLS_INV = EXCEL_DIR / "COSTOS MP - INSUMOS - PROD TERMINADOS (1).xlsx"


def validar_excel_dir() -> None:
    if not XLS_INV.exists():
        sys.exit(
            "ERROR: no encontre el Excel de costos. Usa --excel-dir o ERP_EXCEL_DIR.\n"
            f"Faltante: {XLS_INV}"
        )

# Mapping: nombre del cliente en la MATRIZ (Excel) → nombre del cliente en BD.
# La matriz usa nombres distintos a los del Excel de ventas. Acá los unificamos.
MAPEO_MATRIZ_A_BD = {
    # En la matriz aparece como "ALIMENTOS ESPECIALES S.A. - CASA RICA" (combinado)
    "ALIMENTOS ESPECIALES S.A. - CASA RICA": [
        "ALIMENTOS ESPECIALES S.A.", "ALIMENTOS ESPECIALES S.A",
        "ALIMENTOS ESPECIALES S.A(españa)", "ALIMENTOS ESPECIALES S.A(molas)",
        "CASA RICA ESPAÑA", "CASA RICA LOS LAURELES", "CASA RICA MOLAS LOPEZ",
        "CASA RICA PERSEVERANCIA",
    ],
    "ALIMENTOS ESPECIALES S.A.":   ["ALIMENTOS ESPECIALES S.A.", "ALIMENTOS ESPECIALES S.A",
                                     "ALIMENTOS ESPECIALES S.A(españa)", "ALIMENTOS ESPECIALES S.A(molas)"],
    "CAFSA S.A. - ARETE":          ["CAFSA S.A.", "CAFSA S.A", "CAFSA S.A.- ARETE LAMBARE",
                                     "CAFSA S.A.- ARETE PINEDO", "CAFSA S.A.- ARETE PRIMER PRESIDENTE",
                                     "CAFSA S.A.- ARETE SAUSALITO", "CAFSA S.A ARETE(lambare)",
                                     "CAFSA S.A ARETE(pinedo)", "CAFSA S.A ARETE(sausalito)"],
    "COSCOM":                      ["COSCOM S.A.", "COSCOM S.A. - ASUNCIÓN", "MEGA COSMETICOS - SAN LORENZO"],
    "FARMA S.A.":                  ["FARMA S.A.", "FARMA S.A. PUNTOFARMA (distribuidora ñemby)",
                                     "FARMA S.A.- PUNTOFARMA"],
    "MARTIN LEON":                 ["MARTIN LEON", "MARTIN LEON - SPACIO 1 SANBER",
                                     "Martin leon SPACIO SAN BERNARDINO"],
    "BELEN GIMENEZ":               ["MARIA BELEN GIMENEZ"],
    "CADENA REAL":                 ["CADENA REAL S.A.", "CADENA REAL S.A", "CADENA REAL VILLA MORRA",
                                     "CADENA REAL SAN VICENTE", "CADENA REAL FELIX BOGADO",
                                     "CADENA REAL FERNANDO DE LA MORA", "CADENA REAL S.A(villa morra)",
                                     "CADENA REAL S.A(fdo de la mora)", "CADENA REAL S.A(san vicente)"],
}


def cargar_database_url() -> str:
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    env_file = ROOT / "backend" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                return v.replace("postgresql+asyncpg://", "postgresql://", 1)
    sys.exit("ERROR: DATABASE_URL no encontrada")


def normalizar_nombre(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def extraer_matriz_productos_clientes() -> dict[str, list[tuple[str, int]]]:
    """
    Parsea la hoja 'VENTAS 2025-2026' del archivo de inventario.
    Devuelve: { 'CLIENTE_MATRIZ': [(producto_nombre, cantidad_total), ...] }
    """
    wb = openpyxl.load_workbook(XLS_INV, read_only=True, data_only=True)
    ws = wb["VENTAS 2025-2026"]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 4:
        return {}

    # R1 = clientes (con merged cells; algunos colapsan a None tras el primero).
    # R3 = sucursales (el cliente real es la sucursal cuando el header es genérico).
    # Columnas usables empiezan en col 4 (D) según el patrón.
    header_r1 = rows[0]

    # Construir cliente por columna: si R1 tiene valor, ese es el cliente;
    # si R1 es None, hereda del último cliente seen
    cliente_por_col: dict[int, str] = {}
    last_cliente = None
    for col_idx, val in enumerate(header_r1):
        if isinstance(val, str) and len(val.strip()) > 2:
            last_cliente = normalizar_nombre(val)
        if last_cliente and col_idx >= 4:
            cliente_por_col[col_idx] = last_cliente

    # Las columnas válidas son las que tienen nombre de sucursal en R3.
    # Las cols 22+ son totales/costos (VENTAS, COSTO UN, COSTO PRODUCCIÓN, etc.) — IGNORAR.
    header_r3 = rows[2] if len(rows) > 2 else ()
    BLACKLIST_R3 = ("VENTAS", "COSTO", "TOTAL", "PRODUCC")
    cols_validas = set()
    for col_idx in cliente_por_col:
        if col_idx >= len(header_r3):
            continue
        sucursal = header_r3[col_idx]
        if not isinstance(sucursal, str) or not sucursal.strip():
            continue
        if any(b in sucursal.upper() for b in BLACKLIST_R3):
            continue
        cols_validas.add(col_idx)

    # Producto por fila: col C (idx 2)
    result: dict[str, list[tuple[str, int]]] = {}
    for row in rows[3:]:  # desde R4
        nom = row[2] if len(row) > 2 else None
        if not nom or not isinstance(nom, str):
            continue
        if "VENTAS" in nom.upper() or "COSTO" in nom.upper():
            continue
        producto = normalizar_nombre(nom)
        if len(producto) < 5:
            continue
        for col_idx, qty in enumerate(row):
            if col_idx not in cols_validas:
                continue
            if not isinstance(qty, (int, float)) or qty <= 0:
                continue
            # Sanity: cantidades en sucursales son < 10000 normalmente
            if qty > 10000:
                continue
            cli = cliente_por_col.get(col_idx)
            if not cli:
                continue
            result.setdefault(cli, []).append((producto, int(qty)))

    # Consolidar duplicados (mismo producto en múltiples columnas del mismo cliente)
    for cli in list(result.keys()):
        agg: dict[str, int] = {}
        for prod, qty in result[cli]:
            agg[prod] = agg.get(prod, 0) + qty
        result[cli] = sorted(agg.items(), key=lambda x: -x[1])

    wb.close()
    return result


async def main(dry: bool, excel_dir: str | None = None):
    print(f"{'═' * 60}")
    print(f"  ENRIQUECIMIENTO DE ITEMS POR FACTURA  {'(DRY)' if dry else '(REAL)'}")
    print(f"{'═' * 60}")

    configurar_excel_dir(excel_dir)
    validar_excel_dir()
    print(f"\n→ Excel dir: {EXCEL_DIR}")

    db_url = cargar_database_url()
    print(f"\n→ Conectando…")
    conn = await asyncpg.connect(db_url, ssl="require")

    try:
        empresa_id = await conn.fetchval("SELECT id FROM empresas ORDER BY fecha_creacion ASC LIMIT 1")
        if not empresa_id:
            sys.exit("ERROR: no hay empresa")
        empresa_id = str(empresa_id)
        print(f"  empresa_id = {empresa_id}")

        # 1. Leer matriz
        print("\n→ Leyendo matriz productos×cliente del Excel...")
        matriz = extraer_matriz_productos_clientes()
        print(f"  Clientes en matriz: {len(matriz)}")
        for cli, prods in matriz.items():
            print(f"    {cli}: {len(prods)} productos, total {sum(q for _,q in prods)} unidades")

        # 2. Para cada cliente_matriz, juntar todas las facturas en BD de los clientes mapeados
        print(f"\n→ Procesando facturas de cada grupo de cliente...")
        total_items_creados = 0
        total_facturas_enriquecidas = 0
        facturas_sin_matriz = 0

        for cli_matriz, prods in matriz.items():
            # Buscar todas las facturas de TODOS los nombres mapeados
            nombres_bd = MAPEO_MATRIZ_A_BD.get(cli_matriz, [cli_matriz])

            facturas = await conn.fetch(
                """
                SELECT c.id, c.numero_comprobante, c.monto_total, c.monto_subtotal, c.monto_iva
                FROM comprobantes c
                JOIN clientes cl ON cl.id = c.cliente_id
                WHERE c.empresa_id = $1
                  AND cl.nombre = ANY($2::text[])
                  AND c.estado_validacion NOT IN ('anulado','rechazado')
                ORDER BY c.fecha_emision
                """,
                empresa_id, nombres_bd,
            )
            if not facturas:
                continue

            total_monto = sum(float(f["monto_total"]) for f in facturas)
            if total_monto <= 0:
                continue

            print(f"\n  [{cli_matriz}]")
            print(f"    {len(facturas)} factura(s), total ₲{int(total_monto):,}")
            print(f"    Distribuyendo {len(prods)} productos:")
            print(f"      - {prods[0][0][:40]}... ({prods[0][1]} ud)" if prods else "")

            # 3. Para cada factura: borrar items, generar items distribuidos
            for fact in facturas:
                fact_id = str(fact["id"])
                fact_total = Decimal(str(fact["monto_total"]))
                fact_subtotal = Decimal(str(fact["monto_subtotal"]))

                # Proporción de esta factura sobre el total del cliente
                fraccion = float(fact_total) / total_monto

                # Items distribuidos
                items_factura = []
                subtotal_acumulado = Decimal("0")
                for j, (prod, qty_total) in enumerate(prods):
                    qty_factura = qty_total * fraccion
                    if qty_factura < 0.01:
                        continue
                    qty_redondeada = round(qty_factura, 2)
                    if qty_redondeada <= 0:
                        continue

                    # El precio_unitario lo calculamos al final para que cuadre con monto_subtotal
                    items_factura.append({
                        "producto": prod,
                        "cantidad": qty_redondeada,
                    })

                if not items_factura:
                    facturas_sin_matriz += 1
                    continue

                # Calcular precio unitario para que sume el subtotal exacto
                # Distribuimos el subtotal proporcionalmente a la cantidad de cada item
                cant_total_items = sum(it["cantidad"] for it in items_factura)
                if cant_total_items <= 0:
                    facturas_sin_matriz += 1
                    continue

                # Precio unitario uniforme = subtotal / cant_total
                precio_unit_promedio = float(fact_subtotal) / cant_total_items

                # Asignar precio y subtotal a cada ítem
                subtotal_check = Decimal("0")
                for k, it in enumerate(items_factura):
                    if k == len(items_factura) - 1:
                        # último: ajustar para que cuadre exacto
                        sub_item = float(fact_subtotal) - float(subtotal_check)
                        precio = sub_item / it["cantidad"] if it["cantidad"] > 0 else 0
                    else:
                        sub_item = round(it["cantidad"] * precio_unit_promedio, 2)
                        precio = precio_unit_promedio
                    iva_item = round(sub_item * 0.10, 2)
                    it["precio_unitario"] = round(precio, 2)
                    it["subtotal"] = round(sub_item, 2)
                    it["iva_monto"] = iva_item
                    subtotal_check += Decimal(str(sub_item))

                if dry:
                    total_items_creados += len(items_factura)
                    total_facturas_enriquecidas += 1
                    continue

                # Aplicar: borrar detalles existentes y crear nuevos
                await conn.execute(
                    "DELETE FROM detalle_comprobantes WHERE comprobante_id = $1",
                    fact_id,
                )
                for it in items_factura:
                    await conn.execute(
                        """
                        INSERT INTO detalle_comprobantes
                          (empresa_id, comprobante_id, descripcion, cantidad,
                           precio_unitario, porcentaje_iva, subtotal, iva_monto)
                        VALUES ($1, $2, $3, $4, $5, 10, $6, $7)
                        """,
                        empresa_id, fact_id, it["producto"][:300], it["cantidad"],
                        it["precio_unitario"], it["subtotal"], it["iva_monto"],
                    )
                total_items_creados += len(items_factura)
                total_facturas_enriquecidas += 1

        # 4. Resumen
        print(f"\n{'═' * 60}")
        print(f"  Resumen")
        print(f"{'═' * 60}")
        print(f"  Facturas enriquecidas:           {total_facturas_enriquecidas}")
        print(f"  Items totales generados:         {total_items_creados}")
        print(f"  Facturas sin match en matriz:    {facturas_sin_matriz}")
        if not dry:
            promedio = total_items_creados / max(total_facturas_enriquecidas, 1)
            print(f"  Promedio items por factura:      {promedio:.1f}")
            cant_total_items = await conn.fetchval(
                "SELECT COUNT(*) FROM detalle_comprobantes WHERE empresa_id=$1",
                empresa_id,
            )
            print(f"  Total detalles en BD ahora:      {cant_total_items}")
        else:
            print("\n[DRY RUN] Nada se guardó.")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--excel-dir", help="Carpeta que contiene el Excel de costos")
    args = parser.parse_args()
    asyncio.run(main(dry=args.dry_run, excel_dir=args.excel_dir))
