"""Tests del servicio de análisis por cliente/proveedor."""
from __future__ import annotations

import pytest

from backend.services.analisis_contraparte import _calcular_score, analizar_contraparte


def test_score_verde_cliente_saludable():
    score = _calcular_score(
        porcentaje_devolucion=2.5,
        promedio_dias_pago=25,
        plazo_promedio_dias=30,
        tiene_saldo_60_mas=False,
        dias_desde_ultima_compra=12,
        cantidad_facturas=20,
    )
    assert score["color"] == "verde"
    assert score["puntos"] == 100
    assert score["razones"] == ["Sin alertas"]


def test_score_amarillo_devoluciones_y_atraso():
    # 15% devolución (-20) + tarda 50 días sobre plazo 30 (-15) = 65 → amarillo
    score = _calcular_score(
        porcentaje_devolucion=15.0,
        promedio_dias_pago=50,
        plazo_promedio_dias=30,
        tiene_saldo_60_mas=False,
        dias_desde_ultima_compra=5,
        cantidad_facturas=10,
    )
    assert score["color"] == "amarillo"
    assert 50 <= score["puntos"] < 75
    assert any("Devoluciones" in r for r in score["razones"])


def test_score_rojo_combo_de_problemas():
    score = _calcular_score(
        porcentaje_devolucion=25.0,
        promedio_dias_pago=70,
        plazo_promedio_dias=30,
        tiene_saldo_60_mas=True,
        dias_desde_ultima_compra=120,
        cantidad_facturas=8,
    )
    assert score["color"] == "rojo"
    assert score["puntos"] < 50
    # debería listar al menos 4 razones distintas
    assert len(score["razones"]) >= 3


def test_score_datos_insuficientes_si_menos_de_3_facturas():
    score = _calcular_score(
        porcentaje_devolucion=0,
        promedio_dias_pago=None,
        plazo_promedio_dias=None,
        tiene_saldo_60_mas=False,
        dias_desde_ultima_compra=None,
        cantidad_facturas=2,
    )
    assert score["color"] == "gris"
    assert score["puntos"] is None


@pytest.mark.asyncio
async def test_analizar_contraparte_404_si_no_existe(db):
    db.stub([])  # primer SELECT a clientes devuelve vacío
    with pytest.raises(ValueError):
        await analizar_contraparte(db, empresa_id="e1", rol="cliente", contraparte_id="c1")


@pytest.mark.asyncio
async def test_analizar_contraparte_cliente_sin_movimientos(db):
    """Cliente que existe pero sin facturas: estructura completa con ceros y score gris."""
    db.stub([{"id": "c1", "nombre": "ACME", "ruc": "8001234-5", "fecha_creacion": None}])
    db.stub([{
        "cantidad_facturas": 0,
        "total_facturado": 0,
        "total_devoluciones": 0,
        "total_cargos_extra": 0,
        "saldo_pendiente": 0,
        "ultima_factura": None,
        "tiene_saldo_60_mas": False,
    }])
    db.stub([{"total": 0}])  # ya_cobrado
    db.stub([{"promedio_dias": None, "mejor_dias": None, "peor_dias": None, "plazo_promedio_dias": None}])
    db.stub([])  # medio_favorito
    db.stub([{"total": 0}])  # total_pagos
    db.stub([])  # top_productos
    db.stub([])  # devoluciones_top
    db.stub([])  # notas_credito
    db.stub([])  # notas_debito

    result = await analizar_contraparte(db, empresa_id="e1", rol="cliente", contraparte_id="c1")
    assert result["contraparte"]["nombre"] == "ACME"
    assert result["resumen"]["cantidad_facturas"] == 0
    assert result["resumen"]["total_facturado"] == "0"
    assert result["score"]["color"] == "gris"
    assert result["top_productos"] == []
    assert result["devoluciones"]["notas_credito"] == []
