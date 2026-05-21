"""
Manual de uso del ERP Universal — guía para enseñar el sistema.

Documento moderno, una idea por sección, escaneable en 10 min.
Salida: docs/Manual_Uso_ERP.pdf

Actualizado a: v7.0-rc1 (Aurora, Análisis Cliente, Lotes + CPP, RLS).
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether,
)


# ── Paleta moderna ──────────────────────────────────────────────────────────
SLATE      = HexColor('#0f172a')
SLATE_2    = HexColor('#334155')
SLATE_3    = HexColor('#64748b')
SLATE_4    = HexColor('#cbd5e1')
SLATE_BG   = HexColor('#f8fafc')
INDIGO     = HexColor('#4f46e5')
VIOLET     = HexColor('#7c3aed')
FUCHSIA    = HexColor('#c026d3')
EMERALD    = HexColor('#10b981')
EMERALD_BG = HexColor('#d1fae5')
AMBER      = HexColor('#f59e0b')
AMBER_BG   = HexColor('#fef3c7')
ROSE       = HexColor('#f43f5e')
ROSE_BG    = HexColor('#ffe4e6')
BLUE       = HexColor('#3b82f6')
BLUE_BG    = HexColor('#dbeafe')
BORDE      = HexColor('#e2e8f0')


# ── Estilos ─────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

S_TITULO_DOC = ParagraphStyle(
    'TitDoc', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=28, leading=34, textColor=SLATE,
)
S_SUBTIT_DOC = ParagraphStyle(
    'SubDoc', parent=ss['Normal'],
    fontName='Helvetica', fontSize=11, leading=15, textColor=SLATE_3,
)
S_H1 = ParagraphStyle(
    'H1', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=SLATE,
    spaceBefore=4, spaceAfter=2,
)
S_H2 = ParagraphStyle(
    'H2', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=12.5, leading=16, textColor=SLATE,
    spaceBefore=10, spaceAfter=4,
)
S_BODY = ParagraphStyle(
    'Body', parent=ss['Normal'],
    fontName='Helvetica', fontSize=10, leading=14, textColor=SLATE_2,
    alignment=TA_LEFT, spaceAfter=5,
)
S_LISTA = ParagraphStyle(
    'Lista', parent=S_BODY,
    leftIndent=14, bulletIndent=2, spaceAfter=3,
)
S_PEQUE = ParagraphStyle(
    'Peq', parent=ss['Normal'],
    fontName='Helvetica', fontSize=8.5, leading=11, textColor=SLATE_3,
)
S_PASO_T = ParagraphStyle(
    'PasoT', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=SLATE,
)
S_PASO_D = ParagraphStyle(
    'PasoD', parent=ss['Normal'],
    fontName='Helvetica', fontSize=10, leading=14, textColor=SLATE_2,
)
S_NUM = ParagraphStyle(
    'Num', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=12, leading=14,
    textColor=white, alignment=TA_CENTER,
)


# ── Header / Footer ─────────────────────────────────────────────────────────
def encabezado(canv, doc):
    canv.saveState()
    w, h = A4
    # franja superior gradient simulada (banda violeta)
    canv.setFillColor(INDIGO)
    canv.rect(0, h - 0.65 * cm, w * 0.33, 0.65 * cm, fill=1, stroke=0)
    canv.setFillColor(VIOLET)
    canv.rect(w * 0.33, h - 0.65 * cm, w * 0.34, 0.65 * cm, fill=1, stroke=0)
    canv.setFillColor(FUCHSIA)
    canv.rect(w * 0.67, h - 0.65 * cm, w * 0.33, 0.65 * cm, fill=1, stroke=0)

    canv.setFillColor(white)
    canv.setFont('Helvetica-Bold', 8.5)
    canv.drawString(2 * cm, h - 0.43 * cm, 'ERP UNIVERSAL  ·  Manual de uso')
    canv.setFont('Helvetica', 8)
    canv.drawRightString(w - 2 * cm, h - 0.43 * cm, f'pág. {doc.page:02d}')

    # pie
    canv.setStrokeColor(BORDE)
    canv.setLineWidth(0.4)
    canv.line(2 * cm, 1.0 * cm, w - 2 * cm, 1.0 * cm)
    canv.setFillColor(SLATE_3)
    canv.setFont('Helvetica', 7.5)
    canv.drawString(2 * cm, 0.55 * cm,
                    'v7.0-rc1  ·  Esta guía cambia con cada versión — buscá la más reciente en /docs')
    canv.drawRightString(w - 2 * cm, 0.55 * cm, 'docs/Manual_Uso_ERP.pdf')
    canv.restoreState()


# ── Helpers visuales ────────────────────────────────────────────────────────
def chip(texto, color):
    return (f'<font face="Helvetica-Bold" size="8" color="{white.hexval()}" '
            f'backcolor="{color.hexval()}">  {texto.upper()}  </font>')


def kbd(s):
    return (f'<font face="Courier-Bold" color="{SLATE.hexval()}" size="9" '
            f'backcolor="{SLATE_BG.hexval()}">  {s}  </font>')


def paso(num, color, titulo, descripcion, ancho=16.0):
    box = Table([[Paragraph(str(num), S_NUM)]],
                colWidths=[0.95 * cm], rowHeights=[0.95 * cm])
    box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',  (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))
    texto = [Paragraph(f'<b>{titulo}</b>', S_PASO_T),
             Paragraph(descripcion, S_PASO_D)]
    fila = Table([[box, texto]],
                 colWidths=[1.25 * cm, (ancho - 1.25) * cm])
    fila.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    return fila


def callout(tipo, titulo, texto):
    cfg = {
        'tip':  ('CONSEJO', AMBER,  AMBER_BG),
        'ojo':  ('OJO',     ROSE,   ROSE_BG),
        'info': ('NOTA',    BLUE,   BLUE_BG),
        'ok':   ('LISTO',   EMERALD, EMERALD_BG),
    }[tipo]
    label, color, bg = cfg
    cab = Paragraph(
        f'<font face="Helvetica-Bold" size="8" color="{white.hexval()}" '
        f'backcolor="{color.hexval()}">  {label}  </font>'
        f'  <font face="Helvetica-Bold" size="9.5" color="{SLATE.hexval()}">{titulo}</font>',
        ss['Normal']
    )
    body = Paragraph(texto, ParagraphStyle(
        'cb', parent=S_BODY, fontSize=9.5, leading=13, textColor=SLATE_2,
    ))
    inner = Table([[cab], [body]], colWidths=[16.5 * cm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 1), (0, 1), bg),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',(0, 0), (-1, -1), 10),
        ('TOPPADDING',  (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
        ('LINEBEFORE',  (0, 0), (0, -1), 3, color),
    ]))
    return inner


def seccion_header(numero, titulo, descripcion, color):
    """Encabezado destacado al inicio de cada sección."""
    num_p = Paragraph(
        f'<font face="Helvetica-Bold" size="24" color="{color.hexval()}">{numero:02d}</font>',
        ss['Normal'],
    )
    tit_p = Paragraph(
        f'<font face="Helvetica-Bold" size="16" color="{SLATE.hexval()}">{titulo}</font><br/>'
        f'<font face="Helvetica" size="9.5" color="{SLATE_3.hexval()}">{descripcion}</font>',
        ParagraphStyle('sh', parent=ss['Normal'], leading=14),
    )
    t = Table([[num_p, tit_p]], colWidths=[1.6 * cm, 14.9 * cm])
    t.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 14),
        ('BACKGROUND',   (0, 0), (-1, -1), SLATE_BG),
        ('LINEBEFORE',   (0, 0), (0, -1), 5, color),
    ]))
    return t


def tarjeta_indice(numero, titulo, descripcion, color):
    contenido = Paragraph(
        f'<font face="Helvetica-Bold" size="9" color="{color.hexval()}">{numero:02d}</font>  '
        f'<font face="Helvetica-Bold" size="10.5" color="{SLATE.hexval()}">{titulo}</font><br/>'
        f'<font face="Helvetica" size="8.5" color="{SLATE_3.hexval()}">{descripcion}</font>',
        ParagraphStyle('ti', parent=ss['Normal'], leading=13),
    )
    t = Table([[contenido]], colWidths=[8.1 * cm])
    t.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
        ('LINEBEFORE',   (0, 0), (0, -1), 3, color),
        ('BACKGROUND',   (0, 0), (-1, -1), SLATE_BG),
    ]))
    return t


def lista_simple(items):
    """Lista con bullets sutiles."""
    parrafos = []
    for it in items:
        parrafos.append(Paragraph(f'•  {it}', S_LISTA))
    return parrafos


def tabla_atajos(filas):
    """Tabla de 2 columnas: tecla, descripción."""
    data = [[Paragraph(f'<font face="Courier-Bold" size="9" color="{SLATE.hexval()}">{t}</font>',
                       ss['Normal']),
             Paragraph(d, S_BODY)] for t, d in filas]
    t = Table(data, colWidths=[3.5 * cm, 13 * cm])
    t.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND',   (0, 0), (0, -1), SLATE_BG),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('LINEBELOW',    (0, 0), (-1, -2), 0.25, BORDE),
    ]))
    return t


# ── Construcción del documento ─────────────────────────────────────────────
def construir():
    out_path = Path(__file__).resolve().parent.parent / 'docs' / 'Manual_Uso_ERP.pdf'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=1.6 * cm,
        title='Manual de uso — ERP Universal',
        author='ERP Universal',
        subject='Guía rápida para usuarios del sistema',
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id='normal',
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=encabezado)])

    flow = []

    # ── PORTADA ─────────────────────────────────────────────────────────────
    flow.append(Spacer(1, 1.5 * cm))
    flow.append(Paragraph(
        f'Manual <font color="{VIOLET.hexval()}">·</font> de uso',
        S_TITULO_DOC,
    ))
    flow.append(Paragraph('ERP Universal — versión 7.0-rc1', S_SUBTIT_DOC))
    flow.append(Spacer(1, 0.4 * cm))

    flow.append(Paragraph(
        'Una guía corta para entender qué hace cada parte del sistema, '
        'sin jerga técnica. Pensado para enseñar.',
        ParagraphStyle('intro', parent=S_BODY, fontSize=11.5, leading=16,
                       textColor=SLATE_2),
    ))
    flow.append(Spacer(1, 0.6 * cm))

    # Línea decorativa con gradient simulado
    deco = Table([['', '', '']], colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm], rowHeights=[0.1 * cm])
    deco.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), INDIGO),
        ('BACKGROUND', (1, 0), (1, 0), VIOLET),
        ('BACKGROUND', (2, 0), (2, 0), FUCHSIA),
    ]))
    flow.append(deco)
    flow.append(Spacer(1, 0.8 * cm))

    # Quién es este manual para
    flow.append(Paragraph('¿Para quién es esto?', S_H2))
    for t in [
        'Personas que recién entran al sistema y quieren entender qué hay en cada pantalla.',
        'Operadores que ya lo usan pero quieren saber cómo aprovechar lo nuevo (Aurora, lotes, análisis por cliente).',
        'Para enseñar el sistema sin tener que mostrar cada botón.',
    ]:
        flow.append(Paragraph(f'•  {t}', S_LISTA))
    flow.append(Spacer(1, 0.4 * cm))

    # ── ÍNDICE ──────────────────────────────────────────────────────────────
    flow.append(Paragraph('Contenido', S_H2))
    flow.append(Spacer(1, 0.2 * cm))

    indice = [
        (1, 'Entrar al sistema',         'Login, roles y primer recorrido',      INDIGO),
        (2, 'Dashboard',                 'Lo que ves apenas entrás',             VIOLET),
        (3, 'Cargar una factura',        'Con foto, con Excel o a mano',         FUCHSIA),
        (4, 'Cobros y pagos',            'Registrar y consultar movimientos',    EMERALD),
        (5, 'Clientes y proveedores',    'Ficha y análisis histórico',           BLUE),
        (6, 'Inventario y lotes',        'Stock, vencimientos, CPP',             AMBER),
        (7, 'Asistente Aurora',          'Chat con IA, Ctrl+J',                  VIOLET),
        (8, 'Reportes',                  'IVA, aging, P&L, forecast',            INDIGO),
        (9, 'Buenas prácticas',          'Cómo no romperlo, qué hacer si falla', ROSE),
    ]
    filas_indice = []
    for i in range(0, len(indice), 2):
        izq = tarjeta_indice(*indice[i])
        der = tarjeta_indice(*indice[i + 1]) if i + 1 < len(indice) else ''
        filas_indice.append([izq, der])

    tabla_ind = Table(filas_indice, colWidths=[8.25 * cm, 8.25 * cm])
    tabla_ind.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    flow.append(tabla_ind)
    flow.append(PageBreak())

    # ── 01 — ENTRAR AL SISTEMA ──────────────────────────────────────────────
    flow.append(seccion_header(1, 'Entrar al sistema', 'Login, roles y primer recorrido', INDIGO))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Acceso', S_H2))
    flow.append(Paragraph(
        'Abrí <b>https://erp-web-app-delta.vercel.app</b> en cualquier navegador moderno. '
        'No hace falta instalar nada.',
        S_BODY,
    ))
    flow.append(paso(1, INDIGO, 'Ingresá tu email y contraseña',
                     'Si no tenés cuenta, el admin la crea desde Usuarios.'))
    flow.append(paso(2, INDIGO, 'Si sos nuevo, hacé el primer recorrido',
                     'El sistema te muestra dónde está cada cosa. Tarda 1 minuto.'))
    flow.append(paso(3, INDIGO, 'Cambiá tu contraseña al primer login',
                     'Perfil → Seguridad. Es buena costumbre.'))
    flow.append(Spacer(1, 0.4 * cm))
    flow.append(Paragraph('Roles', S_H2))
    flow.append(Paragraph(
        'Cada usuario tiene uno de tres roles. El rol define qué pueden hacer.',
        S_BODY,
    ))
    roles = Table(
        [
            [Paragraph(f'<font color="{ROSE.hexval()}" face="Helvetica-Bold" size="10">ADMIN</font>',
                       ss['Normal']),
             Paragraph('Hace todo: configura empresa, da de alta usuarios, '
                       'puede anular facturas, eliminar pagos.', S_BODY)],
            [Paragraph(f'<font color="{AMBER.hexval()}" face="Helvetica-Bold" size="10">OPERADOR</font>',
                       ss['Normal']),
             Paragraph('Trabaja a diario: carga facturas, registra cobros, gestiona '
                       'inventario y clientes. NO puede gestionar usuarios.', S_BODY)],
            [Paragraph(f'<font color="{EMERALD.hexval()}" face="Helvetica-Bold" size="10">VIEWER</font>',
                       ss['Normal']),
             Paragraph('Sólo lectura. Ideal para contador externo o gerencia. '
                       'No puede modificar nada.', S_BODY)],
        ],
        colWidths=[2.5 * cm, 14 * cm],
    )
    roles.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',(0, 0), (-1, -1), 10),
        ('TOPPADDING',  (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LINEBELOW',   (0, 0), (-1, -2), 0.4, BORDE),
        ('BACKGROUND',  (0, 0), (-1, -1), SLATE_BG),
    ]))
    flow.append(roles)
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('info', 'La sesión se cierra sola',
        'Por seguridad, si no hacés nada por 30 minutos el sistema te cierra sesión. '
        'Volvés a entrar y seguís donde estabas.'))

    flow.append(PageBreak())

    # ── 02 — DASHBOARD ──────────────────────────────────────────────────────
    flow.append(seccion_header(2, 'Dashboard', 'La pantalla de inicio', VIOLET))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        'Es lo primero que ves al entrar. Tres números grandes arriba, '
        'gráfico abajo, accesos rápidos al medio.',
        S_BODY,
    ))
    flow.append(Paragraph('Los 3 recuadros grandes', S_H2))
    for label, desc in [
        ('Por cobrar',
         'Total que te deben tus clientes. Tocá para ver las facturas pendientes.'),
        ('Por pagar',
         'Total que le debés a tus proveedores. Tocá para ver las facturas pendientes.'),
        ('Ingresos cobrados',
         'Lo que entró a caja en el período elegido. Tiene filtro de fechas integrado.'),
    ]:
        flow.append(Paragraph(f'•  <b>{label}.</b> {desc}', S_LISTA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Filtro de período del card "Ingresos cobrados"', S_H2))
    flow.append(Paragraph(
        'Arriba del monto hay una barrita con botones: <b>Mes / Trim. / Sem. / 6M / 12M / Año / Todo</b>. '
        'Cambiá el período y el monto se ajusta al instante.',
        S_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Que querés hacer? — accesos rápidos', S_H2))
    flow.append(Paragraph(
        'Botones grandes con la acción más común: cargar factura con foto, factura manual, '
        'cargar cobro, cargar pago, nuevo cliente, ver deudas, resumen IVA. '
        'Un clic, llegás directo.',
        S_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('tip', 'Alertas en el dashboard',
        'Si hay lotes vencidos o por vencer, aparece un cartel ámbar/rojo. '
        'Tocalo y vas directo a /inventario/lotes.'))

    flow.append(PageBreak())

    # ── 03 — CARGAR UNA FACTURA ─────────────────────────────────────────────
    flow.append(seccion_header(3, 'Cargar una factura', 'Tres formas: foto, Excel o manual', FUCHSIA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Opción A — Con foto (OCR Gemini)', S_H2))
    flow.append(paso(1, FUCHSIA, 'Dashboard → "Cargar factura"',
                     'O directamente desde el menú lateral → Facturas → Cargar con foto.'))
    flow.append(paso(2, FUCHSIA, 'Sacá foto o subí el PDF',
                     'Puede ser foto del celular o un PDF escaneado. La IA lee número, fechas, '
                     'cliente, monto e IVA.'))
    flow.append(paso(3, FUCHSIA, 'Revisá los datos sugeridos',
                     'Lo que la IA no entendió aparece en amarillo. Corregí lo necesario.'))
    flow.append(paso(4, FUCHSIA, 'Guardar',
                     'La factura queda registrada y aparece en el listado.'))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Opción B — Importar Excel', S_H2))
    flow.append(Paragraph(
        'Si recibís facturas en lote, podés descargar la plantilla Excel desde la página de OCR, '
        'completarla con tus datos y subir el archivo. El sistema valida y carga todo en un solo paso.',
        S_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Opción C — Carga manual', S_H2))
    flow.append(Paragraph(
        'Para facturas que no tienen foto o cuando preferís escribir directamente. '
        'Botón "Factura manual" en el dashboard, completás los campos y listo.',
        S_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('ojo', 'IVA paraguayo',
        'Sólo 0%, 5% o 10%. El sistema te muestra esas tres opciones, no escribas otro número. '
        'Si la factura tiene varios IVAs, cargá una línea por tasa.'))

    flow.append(PageBreak())

    # ── 04 — COBROS Y PAGOS ─────────────────────────────────────────────────
    flow.append(seccion_header(4, 'Cobros y pagos', 'El dinero que entra y sale', EMERALD))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        'Cada factura tiene un saldo pendiente. Cuando cobrás (cliente te paga) o pagás '
        '(le pagás al proveedor), ese saldo baja.',
        S_BODY,
    ))
    flow.append(Paragraph('Registrar un cobro', S_H2))
    flow.append(paso(1, EMERALD, 'Dashboard → "Cargar cobro" (o /movimientos)',
                     'También podés cobrar desde la página de la factura o pedirle a Aurora.'))
    flow.append(paso(2, EMERALD, 'Elegí la factura del cliente',
                     'El sistema te muestra las pendientes ordenadas por antigüedad.'))
    flow.append(paso(3, EMERALD, 'Monto + medio de pago',
                     'Efectivo, transferencia, cheque, tarjeta u otro. La fecha por default es hoy.'))
    flow.append(paso(4, EMERALD, 'Confirmar',
                     'El saldo de la factura baja. Si era la última cuota, queda como Pagada.'))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Página "Cobros y pagos"', S_H2))
    flow.append(Paragraph(
        'Listado de todos los movimientos con filtros: tipo (cobro/pago), fechas, búsqueda libre. '
        'Total de ingresos, total de egresos y balance en la parte de arriba. '
        'Botón "Descargar Excel" para llevar al contador.',
        S_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('tip', 'Deshacer un cobro mal registrado',
        'Sólo el rol admin puede eliminar un pago. Va a /movimientos, encuentra la fila, '
        'tacho rojo a la derecha. El saldo de la factura se restaura automáticamente.'))

    flow.append(PageBreak())

    # ── 05 — CLIENTES Y PROVEEDORES ─────────────────────────────────────────
    flow.append(seccion_header(5, 'Clientes y proveedores', 'Ficha + análisis histórico', BLUE))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        'Cada cliente y cada proveedor tiene su ficha y su cuenta corriente. Andá a la '
        'cuenta tocando el nombre desde cualquier listado.',
        S_BODY,
    ))
    flow.append(Paragraph('Qué ves en una cuenta', S_H2))
    flow.append(Paragraph(
        'La pantalla es <b>una sola página scrolleable</b> — todo de arriba a abajo, sin pestañas:',
        S_BODY,
    ))
    for x in [
        '<b>Score 🟢 🟡 🔴</b> al lado del nombre — semáforo de salud de la cuenta. Tocá para ver por qué.',
        '<b>Resumen del negocio</b> — total facturado, ya cobrado, saldo pendiente, devoluciones, cargos extra.',
        '<b>Hábitos de pago</b> — días promedio en pagar, última compra, medio favorito.',
        '<b>Devoluciones</b> (sólo si tiene) — productos más devueltos + modal con lista completa.',
        '<b>Top 5 productos</b> que más te compra.',
        '<b>Lista de facturas</b> y <b>lista de pagos</b> al final.',
    ]:
        flow.append(Paragraph(f'•  {x}', S_LISTA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('info', 'El score se calcula automáticamente',
        'Verde = saludable. Amarillo = revisar. Rojo = riesgo. La regla es transparente — '
        'el popover te dice las razones (devoluciones altas, pagos atrasados, sin compras hace mucho).'))

    flow.append(PageBreak())

    # ── 06 — INVENTARIO Y LOTES ─────────────────────────────────────────────
    flow.append(seccion_header(6, 'Inventario y lotes', 'Stock, vencimientos, CPP', AMBER))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Stock', S_H2))
    flow.append(Paragraph(
        'Página principal: lista de productos y materias primas con cantidad actual, costo unitario y categoría. '
        'Tocás un item para editarlo o ver sus lotes.',
        S_BODY,
    ))
    flow.append(Paragraph('Lotes — qué son y para qué', S_H2))
    flow.append(Paragraph(
        'Un lote es una <b>partida</b> de mercadería con un número único y una fecha de vencimiento opcional. '
        'Por ejemplo, recibís una caja de 100 cremas del lote <i>L-2026-05-A</i> que vence en agosto. '
        'Eso es un lote.',
        S_BODY,
    ))
    flow.append(Paragraph('Para qué sirve', S_H2))
    for x in [
        '<b>Trazabilidad</b>: si algún lote sale defectuoso, sabés exactamente a qué clientes les vendiste de ese lote.',
        '<b>Vencimientos</b>: el sistema te avisa cuando algo está por vencer (default 30 días antes).',
        '<b>FEFO</b>: al vender, el sistema descuenta automáticamente el lote que vence antes — minimizás pérdidas.',
        '<b>CPP — Costo Promedio Ponderado</b>: el costo unitario se recalcula con cada ingreso. Más fiel al margen real.',
    ]:
        flow.append(Paragraph(f'•  {x}', S_LISTA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Página /inventario/lotes', S_H2))
    flow.append(Paragraph(
        'Lista de todos los lotes activos. Card destacado arriba para los que vencen pronto o ya vencieron. '
        'Buscador por producto, código de lote o proveedor. Filtro "sólo lotes con vencimiento" para excluir '
        'los lotes INICIAL que no tienen fecha.',
        S_BODY,
    ))
    flow.append(callout('info', 'Lote "INICIAL"',
        'Al activar el módulo de lotes, todo el stock que ya tenías quedó marcado como lote <b>INICIAL</b> '
        'sin fecha de vencimiento. Eso es normal — los lotes nuevos los vas creando al recibir mercadería.'))

    flow.append(PageBreak())

    # ── 07 — ASISTENTE AURORA ───────────────────────────────────────────────
    flow.append(seccion_header(7, 'Asistente Aurora', 'Chat con IA, atajo Ctrl+J', VIOLET))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        'Aurora es un asistente que entiende lenguaje natural y consulta tu propia base de datos. '
        'Lo abrís desde cualquier pantalla con el botón flotante violeta abajo a la derecha, o con '
        + kbd('Ctrl+J') + '.',
        S_BODY,
    ))
    flow.append(Paragraph('Qué le podés preguntar', S_H2))
    for x in [
        '¿Cuánto me deben en total?',
        '¿Quién es el cliente que menos debe?',
        '¿Qué stock tengo de bronceador FPS 30?',
        '¿Qué facturas vencen este mes?',
        '¿Cómo está el negocio hoy? Dame un resumen.',
    ]:
        flow.append(Paragraph(f'•  <i>{x}</i>', S_LISTA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Cobros y pagos por chat', S_H2))
    flow.append(Paragraph(
        'También podés <b>registrar un cobro</b> escribiéndolo:',
        S_BODY,
    ))
    flow.append(Paragraph(
        '<i>"Cobrá G. 500.000 de la factura 001-001-1234 en efectivo"</i>',
        ParagraphStyle('ej', parent=S_BODY, leftIndent=14, fontSize=10.5,
                       textColor=SLATE),
    ))
    flow.append(Paragraph(
        'Aurora prepara una <b>tarjeta de confirmación</b> con todos los datos. '
        'Apretás <b>Confirmar</b> dentro de 60 segundos y el cobro se registra. '
        'Si pasan los 60s o cancelás, no se hace nada.',
        S_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('ojo', 'Aurora nunca inventa números',
        'Si te da un saldo, una factura o un cliente, salió de la base de datos. '
        'Si dice "no encontré nada", confiá — no hay. Y si te pide aclarar entre varios clientes con '
        'nombres parecidos, decile cuál es el correcto.'))

    flow.append(PageBreak())

    # ── 08 — REPORTES ───────────────────────────────────────────────────────
    flow.append(seccion_header(8, 'Reportes', 'Para entender el negocio', INDIGO))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        'Cuatro reportes principales, accesibles desde el menú Reportes:',
        S_BODY,
    ))
    for label, desc in [
        ('Resumen IVA del mes',
         'Liquidación simplificada: IVA débito (ventas), IVA crédito (compras), saldo a favor o a pagar. '
         'Exportable a Excel para el contador.'),
        ('Aging — Cobros vencidos',
         'Antigüedad de tus cuentas por cobrar. Buckets: al día, 1-30 días, 31-60, 61-90, +90. '
         'Identificás de un vistazo qué clientes son problema.'),
        ('Estado de resultados (P&L)',
         'Ventas, costo de mercadería vendida, utilidad bruta, gastos, resultado neto. '
         'Cambiá el período arriba y los números se ajustan.'),
        ('Forecast de caja',
         'Proyección de cuánto vas a tener en caja a 30, 60 y 90 días si todos pagan según lo pactado.'),
    ]:
        flow.append(Paragraph(f'•  <b>{label}.</b> {desc}', S_LISTA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Exportación', S_H2))
    flow.append(Paragraph(
        'Casi todo se exporta a Excel: comprobantes, IVA ventas/compras, cuentas corrientes, '
        'movimientos, inventario. El botón "Descargar Excel" está en la barra superior de cada listado.',
        S_BODY,
    ))

    flow.append(PageBreak())

    # ── 09 — BUENAS PRÁCTICAS ───────────────────────────────────────────────
    flow.append(seccion_header(9, 'Buenas prácticas', 'Cómo no romperlo, qué hacer si falla', ROSE))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('A diario', S_H2))
    for x in [
        'Cargá las facturas <b>el mismo día</b> que llegan — evita acumulación.',
        'Registrá los cobros <b>cuando suceden</b> — el dashboard se actualiza al instante.',
        'Una sola persona usa el sistema en simultáneo si trabajan en la misma factura — para evitar pisar cambios.',
    ]:
        flow.append(Paragraph(f'•  {x}', S_LISTA))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Atajos de teclado', S_H2))
    flow.append(tabla_atajos([
        ('Ctrl+J',          'Abrir / cerrar el asistente Aurora (cualquier pantalla)'),
        ('Esc',             'Cerrar modales y pop-ups'),
        ('Enter en chat',   'Enviar mensaje a Aurora'),
        ('Shift+Enter',     'Salto de línea en el chat'),
    ]))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph('Si algo no funciona', S_H2))
    flow.append(paso(1, ROSE, 'Recargá la página con Ctrl+Shift+R',
                     'Esto fuerza al navegador a pedir la versión más nueva. Soluciona el 80% de cosas raras.'))
    flow.append(paso(2, ROSE, 'Probá en modo incógnito',
                     'Si en incógnito anda, es problema de caché del navegador normal.'))
    flow.append(paso(3, ROSE, 'Si sigue sin andar, contactá al admin',
                     'Decile qué hiciste justo antes del problema y mostrale la pantalla.'))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(callout('ok', 'El sistema guarda todo',
        'Cada cambio queda registrado: quién lo hizo, cuándo, qué cambió. '
        'Si pasa algo raro, se puede rastrear y deshacer.'))

    # Cierre
    flow.append(Spacer(1, 0.4 * cm))
    flow.append(Paragraph(
        '<font color="' + SLATE_3.hexval() + '" size="9">'
        'Manual de uso · ERP Universal v7.0-rc1 · '
        'Última actualización: mayo 2026'
        '</font>',
        ParagraphStyle('fin', parent=ss['Normal'], alignment=TA_CENTER),
    ))

    doc.build(flow)
    print(f'OK -> {out_path.relative_to(out_path.parent.parent.parent)} '
          f'({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    construir()
