"""
Modelos Pydantic — esquemas de entrada/salida de la API.
Cada modelo tiene su versión Create (entrada) y Read (salida con id y fechas).
DECIMAL: todos los montos usan Decimal de Python, nunca float.
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Base común ───────────────────────────────────────────────────────────────

class BaseRead(BaseModel):
    id: UUID
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


# ── Empresas ─────────────────────────────────────────────────────────────────

class EmpresaCreate(BaseModel):
    nombre: str = Field(..., max_length=200)
    ruc: Optional[str] = Field(None, max_length=50)
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    moneda_principal: str = Field("PYG", max_length=10)


class EmpresaRead(BaseRead):
    nombre: str
    ruc: Optional[str]
    moneda_principal: str
    activa: bool


# ── Usuarios ─────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    nombre: str = Field(..., max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    id_rol: UUID


class UsuarioRead(BaseRead):
    empresa_id: UUID
    nombre: str
    email: str
    activo: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    empresa_id: UUID
    usuario_id: Optional[UUID] = None
    usuario_nombre: str
    usuario_apellido: Optional[str] = None


# ── Clientes / Proveedores ────────────────────────────────────────────────────

class ClienteCreate(BaseModel):
    nombre: str = Field(..., max_length=200)
    ruc: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None


class ClienteRead(BaseRead):
    empresa_id: UUID
    nombre: str
    ruc: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: bool


class ProveedorCreate(ClienteCreate):
    pass  # misma estructura que cliente


class ProveedorRead(ClienteRead):
    pass


# ── Inventario ────────────────────────────────────────────────────────────────

class InventarioCreate(BaseModel):
    categoria_id: Optional[UUID] = None
    codigo: Optional[str] = None
    descripcion: str = Field(..., max_length=300)
    unidad_medida: Optional[str] = None
    cantidad_actual: Decimal = Field(default=Decimal("0"), decimal_places=4)
    costo_unitario: Decimal = Field(default=Decimal("0"), decimal_places=2)
    punto_reorden: Decimal = Field(default=Decimal("0"), decimal_places=4)

    @field_validator("costo_unitario", "cantidad_actual", "punto_reorden")
    @classmethod
    def no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El valor no puede ser negativo")
        return v


class InventarioRead(BaseRead):
    empresa_id: UUID
    codigo: Optional[str] = None
    descripcion: str
    cantidad_actual: Decimal
    costo_unitario: Decimal
    unidad_medida: Optional[str] = None
    punto_reorden: Decimal
    activo: bool
    categoria_id: Optional[UUID] = None
    categoria_nombre: Optional[str] = None


# ── Comprobantes ──────────────────────────────────────────────────────────────

class DetalleCreate(BaseModel):
    inventario_id: Optional[UUID] = None
    descripcion: str = Field(..., max_length=300)
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    precio_unitario: Decimal = Field(..., ge=0, decimal_places=2)
    porcentaje_iva: Decimal = Field(default=Decimal("0"), decimal_places=2)

    @field_validator("porcentaje_iva")
    @classmethod
    def iva_valido(cls, v: Decimal) -> Decimal:
        if v not in (Decimal("0"), Decimal("5"), Decimal("10")):
            raise ValueError("IVA paraguayo debe ser 0%, 5% o 10%")
        return v


class DetalleRead(BaseModel):
    id: UUID
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    porcentaje_iva: Decimal
    subtotal: Decimal
    iva_monto: Decimal

    model_config = {"from_attributes": True}


class NotaVinculadaRead(BaseModel):
    id: UUID
    numero_comprobante: str
    fecha_emision: date
    monto_total: Decimal
    estado_validacion: str
    tipo_nombre: Optional[str] = None
    notas: Optional[str] = None

    model_config = {"from_attributes": True}


class ComprobanteCreate(BaseModel):
    tipo_id: UUID
    numero_comprobante: str = Field(..., max_length=50)
    fecha_emision: date
    fecha_vencimiento: Optional[date] = None
    cliente_id: Optional[UUID] = None
    proveedor_id: Optional[UUID] = None
    monto_subtotal: Decimal = Field(..., ge=0, decimal_places=2)
    monto_iva: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    monto_total: Decimal = Field(..., gt=0, decimal_places=2)
    metodo_carga: Literal["manual", "ocr_pdf", "ocr_imagen"] = "manual"
    condicion: Literal["contado", "credito"] = "credito"
    medio_pago_contado: Optional[Literal["efectivo", "transferencia", "cheque", "tarjeta", "otro"]] = None
    ruta_archivo: Optional[str] = None
    notas: Optional[str] = None
    comprobante_origen_id: Optional[UUID] = None   # NC/ND: factura que compensa
    detalle: list[DetalleCreate] = Field(default_factory=list)

    @field_validator("cliente_id", "proveedor_id")
    @classmethod
    def solo_uno(cls, v, info):
        # Validación cruzada en el router (Pydantic v2 lo maneja en model_validator)
        return v


class ComprobanteUpdate(BaseModel):
    numero_comprobante: Optional[str] = Field(None, max_length=50)
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None
    condicion: Optional[Literal["contado", "credito"]] = None
    medio_pago_contado: Optional[Literal["efectivo", "transferencia", "cheque", "tarjeta", "otro"]] = None


class ComprobanteRead(BaseRead):
    empresa_id: UUID
    tipo_id: Optional[UUID] = None
    comprobante_origen_id: Optional[UUID] = None
    numero_comprobante: str
    fecha_emision: date
    fecha_vencimiento: Optional[date] = None
    monto_total: Decimal
    monto_pagado: Optional[Decimal] = None
    saldo_pendiente: Decimal
    estado_pago: Optional[
        Literal["pagado", "no_pagado", "pago_parcial", "anulado", "rechazado", "no_aplica"]
    ] = None
    metodo_carga: str
    estado_validacion: str
    condicion: Optional[str] = None
    medio_pago_contado: Optional[str] = None
    cliente_id: Optional[UUID] = None
    proveedor_id: Optional[UUID] = None
    contraparte: Optional[str] = None
    tipo: Optional[str] = None
    ruta_archivo: Optional[str] = None
    ubicacion_fisica: Optional[str] = None
    notas: Optional[str] = None
    descripcion: Optional[str] = None      # primer item (preview en el listado)
    cant_items: Optional[int] = None       # cantidad de items en el detalle
    cargado_por: Optional[str] = None
    detalle: list[DetalleRead] = []
    notas_vinculadas: list[NotaVinculadaRead] = []


class TipoComprobanteRead(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str

    model_config = {"from_attributes": True}


# ── Pagos ─────────────────────────────────────────────────────────────────────

class PagoCreate(BaseModel):
    comprobante_id: UUID
    numero_recibo: Optional[str] = None
    fecha_pago: date
    monto_pagado: Decimal = Field(..., gt=0, decimal_places=2)
    medio_pago: Literal["efectivo", "transferencia", "cheque", "tarjeta", "otro"] = "efectivo"
    cuenta_banco_id: Optional[UUID] = None
    notas: Optional[str] = None


class PagoRead(BaseRead):
    comprobante_id: UUID
    fecha_pago: date
    monto_pagado: Decimal
    medio_pago: str


# ── Dashboard (solo lectura) ──────────────────────────────────────────────────

class ResumenDashboard(BaseModel):
    # Conteo agregado (ventas + compras) — mantenido por compatibilidad
    total_facturas_pendientes: int
    # Desglose nuevo (v7.2): pendientes diferenciadas
    facturas_pendientes_cobrar: int = 0   # ventas con saldo > 0
    facturas_pendientes_pagar: int = 0    # compras con saldo > 0
    monto_por_cobrar: Decimal
    monto_por_pagar: Decimal
    items_bajo_stock: int
    ultima_actualizacion: datetime
