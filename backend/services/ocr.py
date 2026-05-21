"""
Servicio de extracción de datos de facturas paraguayas.

Flujo:
  1. PDF digital → PyMuPDF extrae texto → regex parsing (instantáneo)
  2. PDF escaneado / imagen → Gemini Vision API (gemini-2.0-flash)

La clave de Gemini se obtiene de key_store (configurada desde la UI una sola vez).
"""
import base64
import json
import re
import httpx
from ..core import key_store
# NOTA: el módulo `preprocesado` (OpenCV) se dejó disponible pero por
# decisión de producto NO se aplica por defecto — enviamos las imágenes
# a Gemini en su calidad original para no perder detalle de color/trazo.


# ── Prompt especializado en facturas paraguayas ───────────────────────────────

SYSTEM_PROMPT = """Sos un sistema experto en lectura de facturas comerciales paraguayas.
Las facturas paraguayas suelen ser PREIMPRESAS con los datos CLAVE ESCRITOS A MANO en tinta azul o negra. Tu tarea principal es DECODIFICAR ESA CALIGRAFÍA con máxima precisión.

═══════════════════════════════════════════════════════════════
ESTRUCTURA ESTÁNDAR DE UNA FACTURA PARAGUAYA
═══════════════════════════════════════════════════════════════

PARTE SUPERIOR (ya impresa, NO manuscrita):
• ENCABEZADO con LOGO + NOMBRE GRANDE + RUC grande = EMISOR (quien VENDE)
• Número de factura (ej: N° 001-001 0000213) — a veces impreso, a veces manuscrito
• Timbrado, fechas de vigencia — impresas
• FACTURA (palabra grande a la derecha) — impresa

CAMPOS MANUSCRITOS POR EL VENDEDOR (normalmente a mano):
• "Fecha de Emisión": día + mes + año (ej: "12 de Diciembre de 2025")
• "Nombre o Razón Social" del CLIENTE/COMPRADOR (ej: "FARMA SA")
• "RUC:" del CLIENTE/COMPRADOR (ej: "600 22877-4")
• "CONDICIÓN DE VENTA: CONTADO / CRÉDITO" (una marcada con X)

TABLA DE ITEMS (TODO manuscrito):
• Columnas: CÓDIGO | CANT. | DESCRIPCIÓN | PRECIO UNITARIO | EXENTAS | 5% | 10%
• Cada fila = un item vendido
• El monto del item aparece SOLO en la columna del IVA que le corresponde (5%, 10% o EXENTAS)

TOTALES (manuscritos al pie):
• "Valor Parcial"
• "Total a Pagar" en letras (ej: "Un millón ciento noventa mil") + en números (ej: "1.190.000")
• "Liquidación del IVA: 5%  10%" con los montos

═══════════════════════════════════════════════════════════════
CAMPOS QUE DEBÉS DEVOLVER (JSON)
═══════════════════════════════════════════════════════════════

- numero_comprobante: formato "XXX-XXX-XXXXXXX" (ej: "001-001-0000213")
- fecha_emision: "YYYY-MM-DD" (convertí "12 de Diciembre de 2025" → "2025-12-12")
- ruc_emisor: RUC del ENCABEZADO (ej: "80138891-0")
- razon_social_emisor: Nombre grande del encabezado (ej: "MP COSMETICS E.A.S.")
- ruc_cliente: RUC manuscrito debajo de "Nombre o Razón Social" (ej: "600-22877-4")
- razon_social_cliente: Nombre manuscrito en "Nombre o Razón Social" (ej: "FARMA SA")
- condicion: "contado" o "credito" (mirá cuál tiene la X marcada)
- items: array con cada fila manuscrita de la tabla.
    {
      "codigo": "código tal como aparece escrito o null si genuinamente no hay",
      "cantidad": número entero de unidades,
      "descripcion": "texto manuscrito de la descripción EN ESPAÑOL (null si ilegible)",
      "precio_unitario": número entero en guaraníes (CON IVA incluido — ver regla IVA),
      "porcentaje_iva": 0, 5 o 10 según la columna donde aparece el monto,
      "subtotal_item": cantidad × precio_unitario (= monto que aparece en la columna IVA)
    }
  ⚠️ REGLA IMPORTANTE DE CÓDIGOS: si ves dígitos en la columna CÓDIGO, transcribilos
  TAL CUAL aunque la descripción esté ilegible. El código es tu mejor pista para
  identificar un artículo — no lo omitas. Si la descripción está ilegible y hay
  código, poné descripcion=null; el sistema buscará el nombre real por el código.

  ⚠️ REGLAS CRÍTICAS DE DESCRIPCIÓN (manuscrita en cursiva española):
    a) El idioma es SIEMPRE ESPAÑOL PARAGUAYO. Nunca traduzcas, nunca "corrijas"
       al inglés. Si ves "champion" dejalo "champion" (no "shoe"); si ves
       "campera" dejalo "campera" (no "jacket"); si ves "buzo" dejalo "buzo"
       (no "onesie"); si ves "medias" dejalo "medias" (no "socks"); si ves
       "pantalón" dejalo "pantalón" (no "pants").
    b) VOCABULARIO PARAGUAYO frecuente en comercio textil/almacén:
       "campera", "championes", "champion", "conjunto", "conjunto buzo",
       "pantalón buzo", "bóxer algodón", "medias algodón", "remera", "polera",
       "camiseta", "musculosa", "calza", "chomba", "short", "zapatilla",
       "ojota", "gorra", "buzo capucha", "camperita", "body", "enterito",
       "vestido", "pollera", "blusa", "camisa", "corbata", "cinto".
       Otros rubros: "honorarios profesionales", "alquiler", "flete", "servicio
       técnico", "mano de obra", "repuestos", "mantenimiento", "consulta",
       "suscripción", "cuota mensual".
    c) COMILLAS REPETIDORAS — clásico paraguayo: si una fila tiene solo
       comillas ("), palabras "id.", "ídem", "íd.", "do.", o guiones largos en
       la columna descripción, SIGNIFICA que es la MISMA descripción de la
       fila inmediatamente anterior (o la última que tuvo texto). En ese caso
       COPIÁ la descripción completa de esa fila previa — NO pongas literal
       las comillas ni null. Ejemplo: fila 1 "campera niños", fila 2 "" →
       descripción fila 2 = "campera niños".
    d) ABREVIATURAS — transcribí TAL CUAL aparecen, sin expandir: "jvnil" NO
       "juvenil", "alg." NO "algodón", "nñs" NO "niños". El catálogo interno
       tiene sus propios nombres; nosotros cruzamos después.
    e) CANTIDAD VA SEPARADA — el número al inicio de la fila es la cantidad,
       NO parte de la descripción. "2 camperas niños" → cantidad=2,
       descripción="camperas niños" (sin el 2).
    f) Si genuinamente la caligrafía es ilegible y NO hay comillas repetidoras,
       dejá descripcion=null con baja confianza. NO adivines palabras.
- monto_subtotal: total sin IVA (entero en guaraníes)
- monto_iva_5: monto total del IVA al 5% (si hay)
- monto_iva_10: monto total del IVA al 10% (si hay)
- monto_total: valor final a pagar (entero en guaraníes)
- confianza: 0.0 a 1.0 — promedio general de legibilidad
- confianza_por_campo: objeto con la confianza individual (0.0 a 1.0) de cada campo leído
  {
    "numero_comprobante": 0.95,
    "fecha_emision": 0.9,
    "ruc_cliente": 0.8,
    "razon_social_cliente": 0.85,
    "monto_total": 0.95,
    ... (uno por cada campo que tenga valor)
  }
  ⚠️ Usá valores < 0.7 para campos donde la caligrafía es dudosa o tuviste que adivinar.
  No incluyas campos que dejaste en null.

═══════════════════════════════════════════════════════════════
REGLAS CRÍTICAS PARA LECTURA DE MANUSCRITOS
═══════════════════════════════════════════════════════════════

1. NÚMEROS MANUSCRITOS: leé con atención a los trazos paraguayos típicos:
   • "1" puede parecer "7" (los paraguayos escriben el 1 con gancho arriba)
   • "7" tiene una rayita horizontal cruzada en el medio
   • "0" puede parecer "6" o "0" con línea diagonal interna
   • "4" con la línea vertical abierta (no cerrada como imprenta)
   • "9" con bucle cerrado arriba, cola recta
   • "3" y "5" se confunden a veces — el 3 tiene dos curvas, el 5 tiene línea + curva
   Si dudás entre dos dígitos, elegí el que haga COHERENTE LA ARITMÉTICA
   (cantidad × precio = subtotal, Σsubtotales = total). La aritmética siempre es
   la fuente de verdad: si "1.190.000" cuadra con Σ(items) = 1.190.000 pero
   leíste "7.190.000", corregí a "1.190.000".

2. MONTOS CON PUNTOS: "1.190.000" = 1190000 (los puntos son separadores de miles, no decimales). NUNCA interpretes punto como decimal en guaraníes. Los guaraníes SIEMPRE son enteros. Si ves "200.000" = 200000 (doscientos mil), NO 200 con decimales.

3. ⚠️ IVA INCLUIDO — REGLA FUNDAMENTAL EN PARAGUAY ⚠️
   En las facturas paraguayas el **IVA va SIEMPRE INCLUIDO en el precio mostrado**.
   Las columnas "EXENTAS / IVA 5% / IVA 10%" de la tabla NO muestran el IVA
   pelado — muestran el **MONTO BRUTO (con IVA adentro)** del item, clasificado
   según la tasa que le corresponde.

   Ejemplo real Casa Esperanza:
     fila:  "2 | Camperas niños | 100.000 (precio unit.) | | | 200.000 (col. IVA 10%)"
     → cantidad=2, precio_unitario=100000, porcentaje_iva=10, subtotal_item=200000
     (el 200.000 es lo que el cliente paga por las 2 camperas, IVA adentro)

   Totales:
     • monto_total = "Total a Pagar" al pie = suma de columnas (exentas+5%+10%)
       = lo que el cliente efectivamente paga. Ejemplo: 835.000.
     • monto_iva_10 = valor que aparece en la fila "Liquidación del IVA (10%)"
       al pie. Ejemplo: 75.909 (= 835.000 × 10/110, porque es IVA incluido).
     • monto_iva_5 = valor en la fila "Liquidación del IVA (5%)". Si no aparece
       o está vacío, poné 0.
     • monto_subtotal = monto_total - monto_iva_5 - monto_iva_10 (base imponible).
       En el ejemplo: 835.000 - 75.909 = 759.091.

   Si la factura SOLO muestra "Valor Parcial" y "Total a Pagar" sin
   "Liquidación del IVA" separada, CALCULÁ el IVA asumiendo incluido:
     • Si todos los items son IVA 10% → iva_10 = total × 10/110, subtotal = total × 100/110
     • Si todos son IVA 5%            → iva_5  = total × 5/105,  subtotal = total × 100/105
     • Si hay mezcla → sumá cada base por separado.

4. VALIDACIÓN CRUZADA OBLIGATORIA (la aritmética es la fuente de verdad):
   • Leé el monto EN LETRAS ("ochocientos treinta y cinco mil") y compará con
     el escrito en números ("835.000") — DEBEN coincidir. Si discrepan, priorizá
     el que sea coherente con la suma de items.
   • Verificá Σ(subtotal_item) ≈ monto_total. Si no cuadra, revisá los dígitos
     dudosos — elegí la lectura que haga cerrar la cuenta.
   • cantidad × precio_unitario = subtotal_item (sin excepciones).
   • Si un item tiene monto escrito en columna "10%" → porcentaje_iva=10,
     en columna "5%" → porcentaje_iva=5, en columna "EXENTAS" → porcentaje_iva=0.
   • NUNCA inventes un monto. Si un casillero está en blanco en la factura,
     dejá 0 — no lo completes "porque te parece".

4. EMISOR ≠ CLIENTE:
   • "MP COSMETICS E.A.S." (logo grande) = EMISOR = VENDEDOR
   • "FARMA SA" (escrito a mano en "Nombre o Razón Social") = CLIENTE = COMPRADOR
   • NUNCA confundas estos dos.

5. CONDICIÓN: buscá la X o tilde en los cuadritos. Si CONTADO tiene X → "contado". Si CRÉDITO tiene X → "credito".

6. IVA — SÓLO tres valores posibles en Paraguay: 0% (EXENTO), 5% o 10%.
   • Item con monto en columna "10%" → porcentaje_iva = 10
   • Item con monto en columna "5%"  → porcentaje_iva = 5
   • Item con monto en columna "EXENTAS" (o "0%") → porcentaje_iva = 0
   Si la factura tiene items exentos, `monto_iva_5` y `monto_iva_10` pueden ser 0
   aunque haya items — eso es normal. No inventes IVA que no está en la factura.
   El `monto_subtotal` = total de exentos + base del 5% + base del 10% (todo sin IVA).

7. CAMPO ILEGIBLE: si realmente NO podés leer algo con razonable seguridad, poné null. NO inventes.

8. FORMATO DE RUC PARAGUAYO (regla estricta):
   • El RUC se compone de un número base + UN dígito verificador al final.
   • El guión va SIEMPRE y SOLO antes del último dígito (el verificador).
   • Ejemplos correctos: "80138891-0", "6022877-4", "1234567-8".
   • Ejemplos INCORRECTOS que debés corregir: "600-22877-4" → "6022877-4", "80138 891-0" → "80138891-0", "8013889-10" → "80138891-0".
   • Si ves "600 22877-4" o "600-22877-4", reescribilo como "6022877-4" (unir los bloques, guión solo antes del último dígito).

9. PREFIJOS TÍPICOS DEL RUC (informativo — NO fuerces):
   • ruc_emisor: si la empresa es persona jurídica (S.A., E.A.S., S.R.L.) suele empezar con 8. PERO muchísimos emisores paraguayos son personas físicas con RUC propio (pequeños comercios, profesionales independientes, honorarios, talleres, almacenes) y pueden empezar con CUALQUIER dígito (ej: "523402-6", "2157357-3", "1158414-9"). NO asumas 8 por defecto — leé lo que realmente está impreso en el encabezado.
   • ruc_cliente: puede ser persona física o empresa, cualquier dígito es válido.
   • Si el "cliente" tiene formato de CÉDULA sin guión (ej: "1.310.137", "4.824.504") es una CI paraguaya, NO un RUC. En ese caso poné ruc_cliente = null y usá razon_social_cliente con el nombre del comprador.
   • Nunca inventes dígitos — si genuinamente no lo podés leer, dejá null.

10. IMÁGENES ROTADAS: algunas facturas pueden venir rotadas 90°, 180° o 270°
    (fotos tomadas de costado, PDFs de escáner mal orientados). Leé el contenido
    SIN importar la orientación física — vos rotás mentalmente. No devuelvas
    "no se puede leer porque está rotada"; extraé los datos igual.

11. ITEMS SIN PRECIO UNITARIO: muy común en facturas manuscritas paraguayas, el
    vendedor NO escribe el precio unitario y pone directamente el subtotal del
    item en la columna de IVA. Ejemplo: "1 | Campera juvenil dama | | 135.000".
    En ese caso: cantidad=1, precio_unitario=135000, subtotal_item=135000. Si la
    cantidad es >1 y solo hay subtotal, dividí: precio_unitario = subtotal / cantidad.

12. REGLA DE ORO — NUNCA INVENTES DATOS:
    • Si no estás seguro de un monto, dígito, nombre o fecha → poné null y baja
      la confianza de ese campo a <0.5. El usuario revisa todo antes de guardar.
    • Es MEJOR devolver null que un valor inventado. El HITL (human-in-the-loop)
      captura los null y los resalta para que el usuario los complete a mano.
    • Específicamente: NO rellenes el IVA 10% con un valor calculado si no lo ves
      escrito — a menos que la factura diga explícitamente "IVA incluido" y
      tengas el total claro.

13. FACTURAS DE SERVICIOS (honorarios, electricidad, agua): suelen tener UN solo
    item con descripción larga (ej: "Honorarios profesionales Marzo-Abril 2023")
    y el monto va directo. cantidad=1, precio_unitario=monto, descripcion=texto
    completo del servicio. No intentes dividir en sub-items.

14. FACTURAS DE SERVICIO PÚBLICO (ANDE, ESSAP, COPACO): el "número de factura"
    suele aparecer como "Nro. Factura: 00104-23-0075-12-00/0004" o similar. En
    estos casos usá ese número completo como numero_comprobante aunque no calce
    con el formato XXX-XXX-XXXXXXX. También el RUC del emisor es el de la
    empresa pública (ANDE: 80000058-0, ESSAP: 80013570-8).

═══════════════════════════════════════════════════════════════
EJEMPLO DE SALIDA (Casa "Esperanza" manuscrita → Santiago Aquino)
═══════════════════════════════════════════════════════════════

Fila de la tabla visible en la factura:
  "2 | Camperas niños |  | 100.000 | (vacío) | (vacío) | 200.000"
  "2 | championes     |  |  85.000 | (vacío) | (vacío) | 170.000"
  "1 | campera juvenil dama |  | (vacío) | (vacío) | (vacío) | 135.000"
Total a pagar: 835.000   Liquidación IVA (10%): 75.909

{
  "numero_comprobante": "001-001-0006528",
  "fecha_emision": "2024-05-25",
  "ruc_emisor": "523402-6",
  "razon_social_emisor": "Casa Esperanza",
  "ruc_cliente": null,
  "razon_social_cliente": "Santiago Aquino",
  "condicion": "contado",
  "items": [
    {"codigo": null, "cantidad": 2, "descripcion": "Camperas niños", "precio_unitario": 100000, "porcentaje_iva": 10, "subtotal_item": 200000},
    {"codigo": null, "cantidad": 2, "descripcion": "championes", "precio_unitario": 85000, "porcentaje_iva": 10, "subtotal_item": 170000},
    {"codigo": null, "cantidad": 1, "descripcion": "campera juvenil dama", "precio_unitario": 135000, "porcentaje_iva": 10, "subtotal_item": 135000}
  ],
  "monto_subtotal": 759091,
  "monto_iva_5": 0,
  "monto_iva_10": 75909,
  "monto_total": 835000,
  "confianza": 0.82,
  "confianza_por_campo": {
    "numero_comprobante": 0.95,
    "fecha_emision": 0.9,
    "ruc_emisor": 1.0,
    "razon_social_emisor": 1.0,
    "razon_social_cliente": 0.7,
    "monto_total": 0.95,
    "monto_iva_10": 0.9
  }
}

Notá: "1.310.137" en el campo "RUC/Cédula" es CÉDULA de una persona física
(formato X.XXX.XXX sin guión verificador) → ruc_cliente=null, solo se guarda
el nombre. El IVA 10% (75.909) NO se suma al total — ya está INCLUIDO en los
835.000 (regla fundamental Paraguay).

RESPONDÉ ÚNICAMENTE CON UN JSON VÁLIDO, sin texto adicional, sin markdown, sin backticks."""


# ── PDF → texto (PDFs digitales) ─────────────────────────────────────────────

def _extraer_texto_pdf(pdf_bytes: bytes) -> str:
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto = "\n".join(page.get_text() for page in doc)
    doc.close()
    return texto.strip()


def _pdf_a_png_bytes(pdf_bytes: bytes, dpi: int = 180) -> bytes:
    """Convierte SOLO la primera página de un PDF a imagen bytes (compat legacy)."""
    paginas = _pdf_a_imagenes_bytes_multi(pdf_bytes, dpi=dpi, max_paginas=1)
    return paginas[0] if paginas else b""


def _pixmap_a_jpeg_bytes(pix) -> bytes:
    """Devuelve JPEG comprimido; fallback a PNG si PyMuPDF no soporta JPEG."""
    try:
        return pix.tobytes("jpeg", jpg_quality=82)
    except Exception:
        try:
            return pix.tobytes("jpg", jpg_quality=82)
        except Exception:
            return pix.tobytes("png")


def _pdf_a_imagenes_bytes_multi(pdf_bytes: bytes, dpi: int = 180, max_paginas: int = 3) -> list[bytes]:
    """
    Rasteriza hasta `max_paginas` del PDF a JPEG en color, a resolución moderada.
    Render free es sensible a payloads enormes; esto evita OOM/502 en OCR.
    """
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out: list[bytes] = []
    try:
        for i, page in enumerate(doc):
            if i >= max_paginas:
                break
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
            out.append(_pixmap_a_jpeg_bytes(pix))
    finally:
        doc.close()
    return out


# ── Parseo regex para PDFs digitales ─────────────────────────────────────────

def _parsear_texto_factura(texto: str) -> dict:
    resultado = {
        "numero_comprobante": None,
        "fecha_emision": None,
        "ruc_emisor": None,
        "razon_social_emisor": None,
        "ruc_cliente": None,
        "razon_social_cliente": None,
        "condicion": None,
        "items": [],
        "monto_subtotal": 0.0,
        "monto_iva_5": 0.0,
        "monto_iva_10": 0.0,
        "monto_total": 0.0,
        "confianza": 0.0,
        "confianza_por_campo": {},
        "motor_usado": "texto_directo",
    }

    # Número de comprobante
    m = re.search(r'\b(\d{3}[-\s]\d{3}[-\s]\d{7})\b', texto)
    if m:
        resultado["numero_comprobante"] = m.group(1).replace(" ", "-")

    # Fecha
    m = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', texto)
    if m:
        d, mo, y = m.group(1), m.group(2), m.group(3)
        resultado["fecha_emision"] = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"

    # RUCs: buscar todos en el texto y asignar por posición
    rucs = re.findall(r'\b(\d{5,10}[\-–]\d)\b', texto)
    rucs = [_normalizar_ruc(r.replace('–', '-')) for r in rucs]
    rucs = [r for r in rucs if r]
    if rucs:
        resultado["ruc_emisor"] = rucs[0]  # El primero suele ser el del encabezado (emisor)
    if len(rucs) > 1:
        resultado["ruc_cliente"] = rucs[1]  # El segundo es el del campo RUC del comprador

    # Razón Social del emisor (encabezado, antes del campo "Nombre o Razón Social")
    m = re.search(r'(?:Raz[oó]n\s+Social\s+(?:del\s+)?[Ee]misor|Empresa\s+[Ee]misora)[:\s]+([^\n]+)', texto, re.IGNORECASE)
    if m:
        resultado["razon_social_emisor"] = m.group(1).strip()

    # Cliente: campo "Nombre o Razón Social" / "Cliente"
    m = re.search(r'(?:Nombre\s+o\s+Raz[oó]n\s+Social|Cliente)[:\s]+([^\n]+)', texto, re.IGNORECASE)
    if m:
        resultado["razon_social_cliente"] = m.group(1).strip()

    # Condición
    if re.search(r'\bCR[ÉE]DITO\b', texto, re.IGNORECASE):
        resultado["condicion"] = "credito"
    elif re.search(r'\bCONTADO\b', texto, re.IGNORECASE):
        resultado["condicion"] = "contado"

    def monto(s: str) -> float:
        try:
            return float(s.replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    m = re.search(r'TOTAL\s+GENERAL[:\s]*([\d.,]+)|TOTAL\s+A\s+PAGAR[:\s]*([\d.,]+)|TOTAL[:\s]*([\d.,]+)', texto, re.IGNORECASE)
    if m:
        resultado["monto_total"] = monto(next(g for g in m.groups() if g))

    m = re.search(r'IVA\s+10\s*%[:\s]*([\d.,]+)', texto, re.IGNORECASE)
    if m:
        resultado["monto_iva_10"] = monto(m.group(1))

    m = re.search(r'IVA\s+5\s*%[:\s]*([\d.,]+)', texto, re.IGNORECASE)
    if m:
        resultado["monto_iva_5"] = monto(m.group(1))

    m = re.search(r'SUBTOTAL[:\s]*([\d.,]+)', texto, re.IGNORECASE)
    if m:
        resultado["monto_subtotal"] = monto(m.group(1))
    elif resultado["monto_total"] > 0:
        resultado["monto_subtotal"] = max(0.0, resultado["monto_total"] - resultado["monto_iva_5"] - resultado["monto_iva_10"])

    campos_ok = sum([
        bool(resultado["numero_comprobante"]),
        bool(resultado["fecha_emision"]),
        bool(resultado["ruc_emisor"]),
        resultado["monto_total"] > 0,
    ])
    resultado["confianza"] = round(campos_ok / 4, 2)
    return resultado


# ── Gemini Vision ─────────────────────────────────────────────────────────────

async def _extraer_gemini(imagenes: list[tuple[str, str]]) -> dict:
    """
    Llama a Gemini con una o varias imágenes en una sola request.
    Args:
        imagenes: lista de (base64, mime_type) — cada una es una página/foto de la misma factura.
    """
    key = key_store.get_key()
    if not key:
        raise ValueError("Clave de Gemini no configurada")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={key}"
    )

    # Prompt + todas las imágenes como parts del mismo contenido
    parts: list[dict] = [{"text": SYSTEM_PROMPT}]
    if len(imagenes) > 1:
        parts.append({
            "text": (
                f"\n\nIMPORTANTE: Se adjuntan {len(imagenes)} imágenes que corresponden "
                "a la MISMA factura (páginas o fotos frente/dorso). Combiná la información "
                "de todas para extraer un único JSON con TODOS los items y totales."
            )
        })
    for b64, mime in imagenes:
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        return {
            "error": "No se pudo conectar con Gemini (DNS/internet). Verificá tu "
                     "conexión y probá de nuevo en unos segundos."
        }
    except httpx.TimeoutException:
        return {
            "error": "Gemini tardó demasiado en responder. Probá con menos imágenes "
                     "o volvé a intentar."
        }
    except httpx.HTTPStatusError as e:
        codigo = e.response.status_code if e.response is not None else "?"
        detalle = ""
        try:
            detalle = (e.response.json().get("error", {}) or {}).get("message", "")
        except Exception:
            pass
        return {
            "error": f"Gemini devolvió un error ({codigo}): "
                     f"{detalle or 'revisá la clave o probá de nuevo'}."
        }

    texto = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    resultado = _parse_json_response(texto)
    resultado["motor_usado"] = "gemini"
    return resultado


# ── Utilidades ────────────────────────────────────────────────────────────────

def _parse_json_response(texto: str) -> dict:
    """
    Extrae el JSON del response de Gemini, resistente a:
    - Envoltorio ```json ... ```
    - Texto antes/después del JSON
    - JSON con objetos anidados (items)
    - Respuestas truncadas por maxOutputTokens (intenta auto-cerrar)
    """
    texto = (texto or "").strip()

    # 1) Si viene con fences de markdown, quitarlas
    if texto.startswith("```"):
        nl = texto.find("\n")
        if nl >= 0:
            texto = texto[nl + 1 :]
        if texto.rstrip().endswith("```"):
            texto = texto.rstrip()[:-3]
        texto = texto.strip()

    # 2) Recortar desde la primera "{"
    if not texto.startswith("{"):
        start = texto.find("{")
        if start >= 0:
            texto = texto[start:]

    # 3) Si termina con "}", intentar parse normal
    end = texto.rfind("}")
    candidato = texto[: end + 1] if end >= 0 else texto
    try:
        return _normalizar(json.loads(candidato))
    except json.JSONDecodeError:
        pass

    # 4) Fallback: JSON truncado → intentar cerrarlo
    reparado = _reparar_json_truncado(texto)
    if reparado:
        try:
            return _normalizar(json.loads(reparado))
        except json.JSONDecodeError:
            pass

    return {"error": f"No se pudo parsear la respuesta: {texto[:200]}"}


def _reparar_json_truncado(texto: str) -> str | None:
    """
    Intenta reparar JSON cortado a mitad de camino (típico de maxOutputTokens).
    Estrategia:
      1. Cortar en el último valor completo (última "," o "}" o "]" fuera de string)
      2. Cerrar corchetes/llaves abiertos en el orden correcto
    Devuelve el JSON reparado o None si no fue posible.
    """
    # Caminar el texto rastreando strings y balance de {} []
    stack: list[str] = []
    in_string = False
    escape = False
    ultimo_corte_seguro = -1  # posición del último carácter después del cual se podría cerrar

    for i, ch in enumerate(texto):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch == "}" or ch == "]":
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                return None  # desbalance no reparable
        elif ch in (",", "}", "]") or (ch == "}" and not stack):
            pass

        # Punto seguro para truncar: después de una coma o de un valor completo
        if not in_string and ch in (",", "}", "]"):
            ultimo_corte_seguro = i

    if ultimo_corte_seguro < 0:
        return None

    # Cortar justo después del último punto seguro; si terminó en coma, removerla
    recortado = texto[: ultimo_corte_seguro + 1].rstrip()
    if recortado.endswith(","):
        recortado = recortado[:-1]

    # Re-calcular stack sobre el recortado para saber qué cerrar
    stack = []
    in_string = False
    escape = False
    for ch in recortado:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch == "}" or ch == "]":
            if stack and stack[-1] == ch:
                stack.pop()

    # Cerrar todo lo que quedó abierto (en orden inverso)
    return recortado + "".join(reversed(stack))


def _normalizar_ruc(ruc: str | None) -> str | None:
    """
    Normaliza un RUC paraguayo al formato canónico: "XXXXXXX-Y" donde Y es el
    dígito verificador (siempre 1 dígito, siempre precedido por un único guión).
    - Quita espacios, puntos y guiones intermedios.
    - Si después de limpiar quedan < 2 dígitos, devuelve None (inválido).
    - Si queda un número sin dígito verificador separable, devuelve tal cual limpio.
    """
    if not ruc or not isinstance(ruc, str):
        return ruc
    solo_digitos = re.sub(r"[^\d]", "", ruc)
    if len(solo_digitos) < 2:
        return None
    return f"{solo_digitos[:-1]}-{solo_digitos[-1]}"


def _validar_prefijo_ruc(ruc: str | None, rol: str) -> bool:
    """
    En Paraguay el RUC puede arrancar con CUALQUIER dígito — tanto personas físicas
    como jurídicas. Antes bajábamos la confianza si el emisor no empezaba con 8,
    pero muchísimos emisores son pequeños comercios / profesionales independientes
    con RUC propio que empieza con cualquier dígito (ej: "523402-6" = Casa
    Esperanza, "2157357-3" = Estudio Contable). Dejamos esta función como
    gancho por si en el futuro queremos revalidar con algoritmo de dígito
    verificador, pero hoy siempre True.
    """
    return True


def _normalizar(data: dict) -> dict:
    for campo in ("monto_subtotal", "monto_iva_5", "monto_iva_10", "monto_total"):
        try:
            data[campo] = float(data.get(campo) or 0)
        except Exception:
            data[campo] = 0.0
    data["confianza"] = min(max(float(data.get("confianza") or 0.5), 0), 1)
    # Confianza por campo: normalizar a dict con floats en [0,1]
    cpc_raw = data.get("confianza_por_campo") or {}
    if isinstance(cpc_raw, dict):
        cpc: dict[str, float] = {}
        for k, v in cpc_raw.items():
            try:
                cpc[str(k)] = min(max(float(v), 0.0), 1.0)
            except (TypeError, ValueError):
                continue
        data["confianza_por_campo"] = cpc
    else:
        data["confianza_por_campo"] = {}
    # Asegurar que los campos de cliente existan siempre
    data.setdefault("ruc_cliente", None)
    data.setdefault("razon_social_cliente", None)

    # Normalizar RUCs al formato canónico "XXXXXXX-Y"
    data["ruc_emisor"] = _normalizar_ruc(data.get("ruc_emisor"))
    data["ruc_cliente"] = _normalizar_ruc(data.get("ruc_cliente"))

    # Validar que los RUCs tengan al menos 6 dígitos (longitud mínima sensata).
    # Si son demasiado cortos, bajar la confianza para que el usuario los revise.
    cpc: dict[str, float] = data.get("confianza_por_campo") or {}
    for campo in ("ruc_emisor", "ruc_cliente"):
        valor = data.get(campo)
        if valor:
            solo_digitos = re.sub(r"[^\d]", "", valor)
            if len(solo_digitos) < 6:
                cpc[campo] = min(cpc.get(campo, 0.6), 0.4)
    data["confianza_por_campo"] = cpc
    items = data.get("items") or []
    for item in items:
        iva = item.get("porcentaje_iva")
        # Paraguay: sólo 0 (exento), 5 o 10. Si Gemini devuelve algo raro,
        # asumimos EXENTO (0) para no inventar IVA que no existe en la factura.
        if iva not in (0, 5, 10):
            item["porcentaje_iva"] = 0
        item["cantidad"] = max(float(item.get("cantidad") or 1), 0.0001)
        item["precio_unitario"] = max(float(item.get("precio_unitario") or 0), 0)
        # Si Gemini devuelve subtotal_item pero cantidad×precio no cuadra,
        # recalculamos desde subtotal_item (suele ser lo más confiable en
        # manuscritas donde el precio unitario queda en blanco).
        subtotal_recibido = float(item.get("subtotal_item") or 0)
        calculado = item["cantidad"] * item["precio_unitario"]
        if subtotal_recibido > 0 and abs(calculado - subtotal_recibido) > 1:
            # El subtotal visible en la columna IVA tiene prioridad — derivamos
            # el precio unitario para mantener la coherencia.
            if item["cantidad"] > 0:
                item["precio_unitario"] = round(subtotal_recibido / item["cantidad"])
        item["subtotal_item"] = item["cantidad"] * item["precio_unitario"]
    data["items"] = items

    # ── Validación aritmética global (regla IVA INCLUIDO paraguaya) ─────
    # Si Σ(subtotal_item) por tasa de IVA no cuadra con los totales, añadimos
    # un aviso para que el HITL lo muestre en amarillo. NO reescribimos los
    # montos silenciosamente — solo marcamos el mismatch.
    warnings: list[str] = list(data.get("warnings") or [])
    suma_por_tasa: dict[int, float] = {0: 0.0, 5: 0.0, 10: 0.0}
    for item in items:
        tasa = int(item.get("porcentaje_iva") or 0)
        suma_por_tasa[tasa] = suma_por_tasa.get(tasa, 0.0) + float(item.get("subtotal_item") or 0)
    suma_items = sum(suma_por_tasa.values())
    total = float(data.get("monto_total") or 0)
    if total > 0 and suma_items > 0 and abs(suma_items - total) > max(total * 0.01, 10):
        warnings.append(
            f"La suma de los items ({int(suma_items):,} Gs) no coincide con el "
            f"total declarado ({int(total):,} Gs). Revisá los montos."
            .replace(",", ".")
        )
    # Si los IVAs vienen en 0 pero hay items con tasa > 0, calculamos según
    # la regla IVA INCLUIDO y avisamos que fueron derivados (el usuario puede
    # corregirlos si la factura mostraba otro valor).
    iva_10_doc = float(data.get("monto_iva_10") or 0)
    iva_5_doc = float(data.get("monto_iva_5") or 0)
    iva_10_calc = round(suma_por_tasa.get(10, 0.0) * 10 / 110)
    iva_5_calc = round(suma_por_tasa.get(5, 0.0) * 5 / 105)
    if iva_10_doc == 0 and iva_10_calc > 0:
        data["monto_iva_10"] = iva_10_calc
        warnings.append(f"IVA 10% calculado automáticamente: {iva_10_calc:,} Gs (IVA incluido).".replace(",", "."))
    if iva_5_doc == 0 and iva_5_calc > 0:
        data["monto_iva_5"] = iva_5_calc
        warnings.append(f"IVA 5% calculado automáticamente: {iva_5_calc:,} Gs (IVA incluido).".replace(",", "."))
    # Subtotal: si viene en 0 pero tenemos total, derivamos como total - ivas.
    if float(data.get("monto_subtotal") or 0) == 0 and total > 0:
        data["monto_subtotal"] = max(0.0, total - float(data.get("monto_iva_10") or 0) - float(data.get("monto_iva_5") or 0))
    data["warnings"] = warnings
    return data


def _sin_clave() -> dict:
    return {
        "numero_comprobante": None, "fecha_emision": None,
        "ruc_emisor": None, "razon_social_emisor": None,
        "ruc_cliente": None, "razon_social_cliente": None,
        "condicion": None, "items": [],
        "monto_subtotal": 0, "monto_iva_5": 0,
        "monto_iva_10": 0, "monto_total": 0,
        "confianza": 0,
        "confianza_por_campo": {},
        "motor_usado": "sin_configurar",
        "aviso": "Configurá la clave en Ajustes para procesar facturas automáticamente.",
    }


# ── Función principal ─────────────────────────────────────────────────────────

async def extraer_datos_factura(
    archivos: list[tuple[bytes, str]] | bytes,
    mime_type: str = "image/jpeg",
) -> dict:
    """
    Extrae datos de una factura desde una o varias imágenes / páginas PDF.

    Args:
        archivos: lista de tuplas (bytes, mime_type) — una por imagen/PDF/página.
                  Por compatibilidad también acepta (bytes, mime_type) en el formato viejo.
        mime_type: solo se usa si archivos es bytes (modo legacy).

    Estrategia por cada archivo:
      - PDF: si tiene capa de texto útil, intentamos regex primero (solo funciona
        para PDFs 100% digitales). Si no, rasterizamos a PNG @ 300 DPI.
      - Imagen: se envía en su formato y calidad original, sin preprocesado destructivo.

    Todas las imágenes finales se mandan a Gemini Vision en UNA sola llamada,
    para que el modelo las combine como páginas de la misma factura.
    """
    # Retrocompatibilidad: si llega bytes suelto, lo envolvemos
    if isinstance(archivos, (bytes, bytearray)):
        archivos = [(bytes(archivos), mime_type)]
    if not archivos:
        return {"error": "No se recibió ningún archivo"}

    # Caso especial — un solo PDF con capa de texto útil: intentar regex antes
    # de gastar una llamada a Gemini.
    if len(archivos) == 1 and archivos[0][1] == "application/pdf":
        pdf_bytes = archivos[0][0]
        try:
            texto = _extraer_texto_pdf(pdf_bytes)
        except Exception:
            texto = ""
        if len(texto) > 200:
            parsed = _parsear_texto_factura(texto)
            if (
                parsed.get("numero_comprobante")
                and parsed.get("monto_total", 0) > 0
                and parsed.get("ruc_emisor")
            ):
                return parsed

    # Preparar las imágenes para Gemini preservando la calidad original
    if not key_store.is_configured():
        return _sin_clave()

    imagenes_gemini: list[tuple[str, str]] = []
    for contenido, mime in archivos:
        if mime == "application/pdf":
            # Rasterizar hasta 3 páginas en JPEG comprimido para no tumbar Render.
            paginas = _pdf_a_imagenes_bytes_multi(contenido)
            for imagen in paginas:
                imagenes_gemini.append((base64.b64encode(imagen).decode("utf-8"), "image/jpeg"))
        else:
            # Imagen: se envía TAL CUAL (sin grayscale ni denoise) para no degradar calidad.
            # Gemini Vision se encarga del resto.
            imagenes_gemini.append((base64.b64encode(contenido).decode("utf-8"), mime))

    if not imagenes_gemini:
        return {"error": "No se pudieron procesar los archivos"}

    return await _extraer_gemini(imagenes_gemini)
