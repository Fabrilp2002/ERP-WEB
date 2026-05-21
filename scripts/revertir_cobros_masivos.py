"""Revierte la regularizacion masiva de cobros del 2026-05-09.

Identifica los pagos cuya nota contiene 'Regularizacion masiva 2026-05-09' y
los elimina via DELETE /pagos/{id}. El backend revierte automaticamente el
saldo_pendiente del comprobante y el asiento contable.
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx

NOTA_OBJETIVO = "Regularizacion masiva 2026-05-09"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ejecutar", action="store_true")
    args = ap.parse_args()

    base = os.environ.get("ERP_API_URL", "https://erp-web-backend-i5zv.onrender.com")
    email = os.environ.get("ERP_EMAIL", "admin@demo.com")
    password = os.environ.get("ERP_PASSWORD", "AdminDemo123!")

    with httpx.Client(base_url=base, timeout=60.0, follow_redirects=True) as cli:
        print(f"Login {email} ...")
        r = cli.post(
            "/auth/token",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        cli.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        print("Listando todos los movimientos ...")
        r = cli.get("/pagos/movimientos")
        r.raise_for_status()
        movs = r.json().get("movimientos", [])
        objetivo = [
            m for m in movs
            if m.get("tipo") == "cobro" and (m.get("notas") or "").strip() == NOTA_OBJETIVO
        ]

        total = sum(float(m.get("monto_pagado") or 0) for m in objetivo)
        print(f"\nPagos a eliminar: {len(objetivo)}")
        print(f"Monto total a revertir: G. {total:,.0f}".replace(",", "."))

        if not objetivo:
            print("No hay pagos con la nota de regularizacion. Nada que hacer.")
            return 0

        if not args.ejecutar:
            print("\nPREVIEW (no se elimino nada). Volve a correr con --ejecutar.")
            for m in objetivo[:10]:
                print(f"  - pago {m['id']} | factura {m['numero_comprobante']} | G. {float(m['monto_pagado']):,.0f}".replace(",", "."))
            if len(objetivo) > 10:
                print(f"  ... y {len(objetivo) - 10} mas")
            return 0

        print(f"\nEliminando {len(objetivo)} pagos ...")
        ok = 0
        fallos = []
        for m in objetivo:
            try:
                rd = cli.delete(f"/pagos/{m['id']}")
                if rd.status_code in (200, 204):
                    ok += 1
                    print(f"  OK  {m['numero_comprobante']}  G. {float(m['monto_pagado']):,.0f}".replace(",", "."))
                else:
                    fallos.append((m["id"], f"HTTP {rd.status_code}: {rd.text[:120]}"))
                    print(f"  FAIL {m['id']}: {rd.status_code} {rd.text[:120]}")
            except Exception as exc:
                fallos.append((m["id"], str(exc)))
                print(f"  ERR {m['id']}: {exc}")

        print(f"\nResultado: {ok} pagos eliminados, {len(fallos)} fallos.")
        for fid, err in fallos:
            print(f"  - {fid}: {err}")
        return 0 if not fallos else 2


if __name__ == "__main__":
    sys.exit(main())
