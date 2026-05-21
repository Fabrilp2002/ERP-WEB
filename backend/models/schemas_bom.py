"""
Pydantic schemas para Bill of Materials (BOM) — recetas de productos.
"""
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ── Receta Items ──────────────────────────────────────────────────────────────

class RecetaItemCreate(BaseModel):
    insumo_id: UUID
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    unidad_medida: str = Field(..., max_length=20)
    orden: int = 0
    es_critico: bool = False
    notas: Optional[str] = None


class RecetaItemRead(BaseModel):
    id: UUID
    insumo_id: UUID
    insumo_nombre: Optional[str] = None
    insumo_codigo: Optional[str] = None
    insumo_stock_actual: Optional[Decimal] = None
    insumo_costo_unitario: Optional[Decimal] = None
    cantidad: Decimal
    unidad_medida: str
    orden: int
    es_critico: bool
    notas: Optional[str] = None
    subtotal_costo: Optional[Decimal] = None  # cantidad * costo_unitario insumo

    model_config = {"from_attributes": True}


# ── Recetas ───────────────────────────────────────────────────────────────────

class RecetaCreate(BaseModel):
    producto_id: UUID
    nombre: str = Field(..., max_length=200)
    version: str = Field(default="v1", max_length=50)
    rendimiento: Decimal = Field(default=Decimal("1"), gt=0, decimal_places=4)
    unidad_rendimiento: str = Field(default="unidad", max_length=20)
    activa: bool = True
    notas: Optional[str] = None
    items: list[RecetaItemCreate] = Field(default_factory=list)


class RecetaUpdate(BaseModel):
    nombre: Optional[str] = None
    version: Optional[str] = None
    rendimiento: Optional[Decimal] = None
    unidad_rendimiento: Optional[str] = None
    activa: Optional[bool] = None
    notas: Optional[str] = None
    items: Optional[list[RecetaItemCreate]] = None


class RecetaRead(BaseModel):
    id: UUID
    empresa_id: UUID
    producto_id: UUID
    producto_nombre: Optional[str] = None
    producto_codigo: Optional[str] = None
    producto_precio_venta: Optional[Decimal] = None
    nombre: str
    version: str
    rendimiento: Decimal
    unidad_rendimiento: str
    activa: bool
    notas: Optional[str] = None
    fecha_creacion: datetime
    fecha_modificacion: datetime

    # Campos calculados
    costo_total_receta: Optional[Decimal] = None
    costo_unitario: Optional[Decimal] = None
    margen_pct: Optional[Decimal] = None  # (precio_venta - costo_unitario) / precio_venta * 100
    cantidad_items: Optional[int] = None
    items: list[RecetaItemRead] = []

    model_config = {"from_attributes": True}


# ── Capacidad de Produccion ───────────────────────────────────────────────────

class CapacidadProduccion(BaseModel):
    receta_id: UUID
    producto_id: UUID
    producto_nombre: str
    batches_posibles: int
    unidades_posibles: Decimal  # batches * rendimiento
    insumo_limitante: Optional[str] = None
    items_status: list[dict] = []  # status detallado por insumo


# ── Lotes de Produccion ───────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    receta_id: UUID
    numero_lote: str = Field(..., max_length=50)
    cantidad_planificada: Decimal = Field(..., gt=0, decimal_places=4)
    fecha_planificada: date
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None


class LoteRead(BaseModel):
    id: UUID
    empresa_id: UUID
    receta_id: UUID
    receta_nombre: Optional[str] = None
    producto_nombre: Optional[str] = None
    numero_lote: str
    cantidad_planificada: Decimal
    cantidad_producida: Decimal
    estado: Literal["planificado", "en_proceso", "completado", "cancelado"]
    fecha_planificada: date
    fecha_completado: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    costo_total: Optional[Decimal] = None
    notas: Optional[str] = None
    fecha_creacion: datetime

    model_config = {"from_attributes": True}
