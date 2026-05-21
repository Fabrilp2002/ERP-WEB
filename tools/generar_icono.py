"""
Genera icon.ico para el ERP Universal — diseño limpio, profesional.
Usa: python tools/generar_icono.py
Produce: frontend/public/icon.ico  +  frontend/public/icon.png
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "frontend" / "public"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Paleta (matching Tailwind sidebar color)
AZUL_OSCURO = (15, 23, 42)       # slate-900 (fondo)
AZUL_MARCA  = (29, 78, 216)      # primary-700 (bloque interior)
AZUL_CLARO  = (96, 165, 250)     # blue-400 (acento barras)
BLANCO      = (255, 255, 255)


def crear_icono(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Fondo redondeado (degradé simulado por dos rectángulos)
    margin = max(2, size // 40)
    radius = size // 5
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=AZUL_OSCURO,
    )

    # Bloque interior — representa "edificio"
    cx, cy = size / 2, size / 2
    w = size * 0.55
    h = size * 0.62
    left = cx - w / 2
    top = cy - h / 2 + size * 0.03
    right = cx + w / 2
    bottom = cy + h / 2 + size * 0.03

    d.rounded_rectangle(
        [left, top, right, bottom],
        radius=max(3, size // 28),
        fill=AZUL_MARCA,
    )

    # Barras internas estilo "gráfico"
    bar_width = (right - left - size * 0.16) / 3
    bar_gap = size * 0.04
    bar_bottom = bottom - size * 0.12
    alturas = [0.18, 0.34, 0.26]  # relativas al tamaño total
    x = left + size * 0.08
    for alt in alturas:
        bar_top = bar_bottom - size * alt
        d.rounded_rectangle(
            [x, bar_top, x + bar_width, bar_bottom],
            radius=max(1, size // 60),
            fill=BLANCO,
        )
        x += bar_width + bar_gap

    # Línea inferior tipo "base contable"
    d.rectangle(
        [left + size * 0.08, bottom - size * 0.09,
         right - size * 0.08, bottom - size * 0.07],
        fill=AZUL_CLARO,
    )

    return img


# Generar PNG grande para referencia
png = crear_icono(512)
png.save(OUT_DIR / "icon.png", "PNG")
print(f"OK:{OUT_DIR / 'icon.png'}")

# Generar ICO con múltiples tamaños
sizes = [16, 24, 32, 48, 64, 128, 256]
imgs = [crear_icono(s) for s in sizes]
imgs[0].save(
    OUT_DIR / "icon.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes],
    append_images=imgs[1:],
)
print(f"OK:{OUT_DIR / 'icon.ico'} ({len(sizes)} tamaños)")
