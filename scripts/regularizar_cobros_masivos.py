"""Script one-shot para regularizar cobros masivos en produccion.

Lista todas las facturas de venta confirmadas con saldo pendiente y registra
un pago en efectivo por el monto exacto del saldo, dejando saldo_pendiente=0.

Uso:
    python scripts/regularizar_cobros_masivos.py [--ejecutar]

Sin --ejecutar muestra solo el preview. Con --ejecutar realiza los POST /pagos.

Variables de entorno:
    ERP_API_URL    (default: https://erp-web-backend-i5zv.onrender.com)
    ERP_EMAIL      (default: admin@demo.com)
    ERP_PASSWORD   (default: AdminDemo123!)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

import httpx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ejecutar", action="store_true", help="Realmente registra los cobros (sin esto solo muestra preview).")
    ap.add_argument("--medio", default="efectivo")
    args = ap.parse_args()

    base = os.environ.get("ERP_API_URL", "https://erp-web-backend-i5zv.onrender.com")
    email = os.environ.get("ERP_EMAIL", "admin@demo.com")
    password = os.environ.get("ERP_PASSWORD", "AdminDemo123!")
    fecha = date.today().isoformat()

    with httpx.Client(base_url=base, timeout=60.0, follow_redirects=True) as cli:
        print(f"Login {email} en {base} ...")
        r = cli.post(
            "/auth/token",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        cli.headers["Authorization"] = f"Bearer {token}"

        print("Listando comprobantes con saldo pendiente ...")
        # Pagina hasta agotar
        pendientes: list[dict] = []
        page = 1
        while True:
            r = cli.get("/comprobantes", params={"page": page, "page_size": 200, "estado": "confirmado"})
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            pendientes.extend(data)
            if len(data) < 200:
                break
            page += 1

        # Filtrar solo ventas (cliente_id != null) con saldo > 0
        ventas_pendientes = [
            c for c in pendientes
            if c.get("cliente_id") and float(c.get("saldo_pendiente") or 0) > 0
        ]

        total = sum(float(c.get("saldo_pendiente") or 0) for c in ventas_pendientes)
        print(f"\nFacturas de venta confirmadas con saldo > 0: {len(ventas_pendientes)}")
        print(f"Saldo total pendiente: G. {total:,.0f}".replace(",", "."))

        if not ventas_pendientes:
            print("No hay nada que regularizar.")
            return 0

        if not args.ejecutar:
            print("\nPREVIEW (no se ejecuto nada). Volve a correr con --ejecutar para aplicar.")
            for c in ventas_pendientes[:10]:
                print(f"  - {c['numero_comprobante']} | {c.get('contraparte') or '-'} | saldo G. {float(c['saldo_pendiente']):,.0f}".replace(",", "."))
            if len(ventas_pendientes) > 10:
                print(f"  ... y {len(ventas_pendientes) - 10} mas")
            return 0

        print(f"\nEjecutando registro de cobros con medio={args.medio}, fecha={fecha} ...")
        ok = 0
        fallos: list[tuple[str, str]] = []
        for c in ventas_pendientes:
            payload = {
                "comprobante_id": c["id"],
                "fecha_pago": fecha,
                "monto_pagado": float(c["saldo_pendiente"]),
                "medio_pago": args.medio,
                "notas": "Regularizacion masiva 2026-05-09",
            }
            try:
                rp = cli.post("/pagos", json=payload)
                if rp.status_code in (200, 201):
                    ok += 1
                    print(f"  OK  {c['numero_comprobante']}  G. {float(c['saldo_pendiente']):,.0f}".replace(",", "."))
                else:
                    fallos.append((c["numero_comprobante"], f"HTTP {rp.status_code}: {rp.text[:120]}"))
                    print(f"  FAIL {c['numero_comprobante']}: {rp.status_code} {rp.text[:120]}")
            except Exception as exc:
                fallos.append((c["numero_comprobante"], str(exc)))
                print(f"  ERR {c['numero_comprobante']}: {exc}")

        print(f"\nResultado: {ok} cobros registrados, {len(fallos)} fallos.")
        if fallos:
            for n, e in fallos:
                print(f"  - {n}: {e}")
        return 0 if not fallos else 2


if __name__ == "__main__":
    sys.exit(main())
