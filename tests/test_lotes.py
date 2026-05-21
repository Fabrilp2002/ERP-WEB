"""Tests del servicio v7.1 — lotes + CPP."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.services.lotes import (
    LoteError,
    crear_lote,
    consumir_fefo,
    proximos_vencimientos,
)


# ── crear_lote / CPP ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_lote_calcula_cpp_inicial_cuando_no_hay_stock(db):
    # _cargar_inventario → stock 0, costo 0
    db.stub([{"id": "i1", "cantidad_actual": Decimal("0"), "costo_unitario": Decimal("0")}])
    # INSERT lote → devuelve fila
    db.stub([{
        "id": "l1", "numero_lote": "L-001",
        "cantidad": Decimal("10"), "costo_unitario": Decimal("100"),
        "fecha_ingreso": __import__("datetime").date(2026, 5, 17),
        "fecha_vencimiento": None,
    }])
    db.stub([])  # UPDATE inventario
    db.stub([])  # INSERT kardex

    resultado = await crear_lote(
        db,
        empresa_id="e1",
        inventario_id="i1",
        numero_lote="L-001",
        cantidad=Decimal("10"),
        costo_unitario=Decimal("100"),
    )
    assert resultado["cpp_resultante"] == 100.0
    assert resultado["stock_resultante"] == 10.0


@pytest.mark.asyncio
async def test_crear_lote_pondera_cpp_con_stock_previo(db):
    # Stock previo: 10 unidades a 100 (= 1000 valor). Entran 10 a 200 → CPP 150.
    db.stub([{"id": "i1", "cantidad_actual": Decimal("10"), "costo_unitario": Decimal("100")}])
    db.stub([{
        "id": "l2", "numero_lote": "L-002",
        "cantidad": Decimal("10"), "costo_unitario": Decimal("200"),
        "fecha_ingreso": __import__("datetime").date(2026, 5, 17),
        "fecha_vencimiento": None,
    }])
    db.stub([])
    db.stub([])

    resultado = await crear_lote(
        db,
        empresa_id="e1",
        inventario_id="i1",
        numero_lote="L-002",
        cantidad=Decimal("10"),
        costo_unitario=Decimal("200"),
    )
    assert resultado["cpp_resultante"] == 150.0
    assert resultado["stock_resultante"] == 20.0


@pytest.mark.asyncio
async def test_crear_lote_falla_si_cantidad_cero(db):
    with pytest.raises(LoteError) as exc:
        await crear_lote(
            db, empresa_id="e1", inventario_id="i1",
            numero_lote="L", cantidad=Decimal("0"), costo_unitario=Decimal("10"),
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_crear_lote_falla_si_costo_negativo(db):
    db.stub([{"id": "i1", "cantidad_actual": Decimal("0"), "costo_unitario": Decimal("0")}])
    with pytest.raises(LoteError) as exc:
        await crear_lote(
            db, empresa_id="e1", inventario_id="i1",
            numero_lote="L", cantidad=Decimal("1"), costo_unitario=Decimal("-5"),
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_crear_lote_falla_si_item_no_existe(db):
    db.stub([])  # _cargar_inventario devuelve vacío
    with pytest.raises(LoteError) as exc:
        await crear_lote(
            db, empresa_id="e1", inventario_id="i-no-existe",
            numero_lote="L", cantidad=Decimal("1"), costo_unitario=Decimal("10"),
        )
    assert exc.value.status_code == 404


# ── consumir_fefo ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fefo_consume_lote_que_vence_antes_primero(db):
    from datetime import date
    # _cargar_inventario: 30 unidades, costo 100
    db.stub([{"id": "i1", "cantidad_actual": Decimal("30"), "costo_unitario": Decimal("100")}])
    # 2 lotes: el que vence antes (B) y el que vence después (A)
    db.stub([
        {"id": "lB", "numero_lote": "B", "cantidad": Decimal("10"),
         "costo_unitario": Decimal("100"), "fecha_vencimiento": date(2026, 6, 1)},
        {"id": "lA", "numero_lote": "A", "cantidad": Decimal("20"),
         "costo_unitario": Decimal("100"), "fecha_vencimiento": date(2026, 12, 1)},
    ])
    # 2 UPDATE de lotes + 2 INSERT kardex + 1 UPDATE inventario = 5 execute con stub vacío
    for _ in range(5):
        db.stub([])

    res = await consumir_fefo(
        db, empresa_id="e1", inventario_id="i1", cantidad=Decimal("15"),
    )
    # Debería consumir 10 del lote B (vence antes) y 5 del lote A
    assert len(res["lotes_consumidos"]) == 2
    assert res["lotes_consumidos"][0]["numero_lote"] == "B"
    assert res["lotes_consumidos"][0]["cantidad"] == 10.0
    assert res["lotes_consumidos"][1]["numero_lote"] == "A"
    assert res["lotes_consumidos"][1]["cantidad"] == 5.0
    assert res["stock_resultante"] == 15.0


@pytest.mark.asyncio
async def test_fefo_falla_si_stock_insuficiente(db):
    db.stub([{"id": "i1", "cantidad_actual": Decimal("5"), "costo_unitario": Decimal("100")}])
    with pytest.raises(LoteError) as exc:
        await consumir_fefo(
            db, empresa_id="e1", inventario_id="i1", cantidad=Decimal("10"),
        )
    assert exc.value.status_code == 409
    assert "Stock insuficiente" in exc.value.detail


# ── proximos_vencimientos ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vencimientos_devuelve_estructura_correcta(db):
    from datetime import date
    db.stub([{
        "lote_id": "l1", "numero_lote": "L-001",
        "cantidad": Decimal("5"), "costo_unitario": Decimal("200"),
        "fecha_ingreso": date(2026, 1, 1),
        "fecha_vencimiento": date(2026, 6, 10),
        "dias_restantes": 24,
        "inventario_id": "i1", "inventario_codigo": "BRC-001",
        "inventario_descripcion": "Bronceador FPS 30",
        "unidad_medida": "unidad",
    }])
    res = await proximos_vencimientos(db, empresa_id="e1", dias=30)
    assert len(res) == 1
    assert res[0]["dias_restantes"] == 24
    assert res[0]["vencido"] is False
    # valor_lote = cantidad * costo = 5 * 200 = 1000
    assert res[0]["valor_lote"] == 1000.0


@pytest.mark.asyncio
async def test_vencimientos_marca_vencido_si_dias_negativo(db):
    from datetime import date
    db.stub([{
        "lote_id": "l1", "numero_lote": "L-001",
        "cantidad": Decimal("3"), "costo_unitario": Decimal("100"),
        "fecha_ingreso": date(2026, 1, 1),
        "fecha_vencimiento": date(2026, 5, 10),
        "dias_restantes": -7,
        "inventario_id": "i1", "inventario_codigo": "X",
        "inventario_descripcion": "Item", "unidad_medida": "unidad",
    }])
    res = await proximos_vencimientos(db, empresa_id="e1", dias=30)
    assert res[0]["vencido"] is True
