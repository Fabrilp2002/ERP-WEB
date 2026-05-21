"""Anula la(s) factura(s) de proveedor con saldo pendiente exacto = G. 80.000.

Pedido del PM (2026-05-11): el dashboard muestra G. 80.000 en "Por pagar"
que no se logra ubicar visualmente; eliminar esa factura del total.

Uso:
    python scripts/anular_factura_80000.py             # solo preview
    python scripts/anular_factura_80000.py --ejecutar  # anula realmente

Variables de entorno:
    ERP_API_URL    (default: https://erp-web-backend-i5zv.onrender.com)
    ERP_EMAIL      (default: admin@demo.com)
    ERP_PASSWORD   (default: AdminDemo123!)
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx


MOTIVO = "Limpieza PM 2026-05-11 — factura no identificable, eliminada del total Por pagar"
SALDO_OBJETIVO = 80000.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ejecutar", action="store_true",
                    help="Realmente anula las facturas (sin esto solo muestra preview).")
    args = ap.parse_args()

    base = os.environ.get("ERP_API_URL", "https://erp-web-backend-i5zv.onrender.com")
    email = os.environ.get("ERP_EMAIL", "admin@demo.com")
    password = os.environ.get("ERP_PASSWORD", "AdminDemo123!")

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

        print("Listando comprobantes de proveedor con saldo pendiente ...")
        candidatos: list[dict] = []
        page = 1
        while True:
            r = cli.get("/comprobantes", params={"page": page, "page_size": 200})
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            for c in data:
                if not c.get("proveedor_id"):
                    continue
                if c.get("estado_validacion") in ("anulado", "rechazado"):
                    continue
                if abs(float(c.get("saldo_pendiente") or 0) - SALDO_OBJETIVO) < 0.01:
                    candidatos.append(c)
            if len(data) < 200:
                break
            page += 1

        print(f"\nCandidatas (proveedor + saldo G. {SALDO_OBJETIVO:,.0f}): {len(candidatos)}".replace(",", "."))
        if not candidatos:
            print("No se encontro ninguna factura con saldo G. 80.000.")
            print("Probable: alguien ya la anulo / pago, o el monto no coincide exacto.")
            return 0

        for c in candidatos:
            print(
                f"  - {c['numero_comprobante']} | proveedor: {c.get('contraparte') or '-'}"
                f" | fecha: {c.get('fecha_emision')} | total: G. {float(c['monto_total']):,.0f}"
                f" | saldo: G. {float(c['saldo_pendiente']):,.0f}"
                f" | estado: {c.get('estado_validacion')}".replace(",", ".")
            )

        if not args.ejecutar:
            print("\nPREVIEW (no se anulo nada). Volve a correr con --ejecutar para aplicar.")
            return 0

        print(f"\nAnulando con motivo: {MOTIVO!r}")
        ok = 0
        fallos: list[tuple[str, str]] = []
        for c in candidatos:
            try:
                rp = cli.patch(f"/comprobantes/{c['id']}/anular", json={"motivo": MOTIVO})
                if rp.status_code in (200, 201, 204):
                    ok += 1
                    print(f"  OK   {c['numero_comprobante']}")
                else:
                    fallos.append((c["numero_comprobante"], f"HTTP {rp.status_code}: {rp.text[:160]}"))
                    print(f"  FAIL {c['numero_comprobante']}: {rp.status_code} {rp.text[:160]}")
            except Exception as exc:
                fallos.append((c["numero_comprobante"], str(exc)))
                print(f"  ERR  {c['numero_comprobante']}: {exc}")

        print(f"\nResultado: {ok} anuladas, {len(fallos)} fallos.")
        if fallos:
            for n, e in fallos:
                print(f"  - {n}: {e}")

        # Verificar nuevo total Por pagar
        try:
            r = cli.get("/dashboard/resumen")
            if r.status_code == 200:
                resumen = r.json()
                print(f"\nNuevo monto_por_pagar: G. {float(resumen.get('monto_por_pagar') or 0):,.0f}".replace(",", "."))
        except Exception:
            pass

        return 0 if not fallos else 2


if __name__ == "__main__":
    sys.exit(main())
