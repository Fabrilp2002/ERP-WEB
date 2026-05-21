"""
Genera el manual práctico del ERP Universal — formato más casual,
enfocado en CÓMO se usa cada cosa.
Salida: docs/Manual_ERP_Universal.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable, Flowable

# ── paleta tipo dev/modern ───────────────────────────────────────────────────
SLATE       = HexColor('#0f172a')   # casi negro
SLATE_2     = HexColor('#334155')   # gris azul oscuro
SLATE_3     = HexColor('#64748b')   # gris medio
SLATE_4     = HexColor('#cbd5e1')   # gris claro
SLATE_BG    = HexColor('#f8fafc')   # fondo casi blanco
VERDE       = HexColor('#10b981')
VERDE_BG    = HexColor('#d1fae5')
AMBAR       = HexColor('#f59e0b')
AMBAR_BG    = HexColor('#fef3c7')
ROSA        = HexColor('#ec4899')
ROSA_BG     = HexColor('#fce7f3')
AZUL        = HexColor('#3b82f6')
AZUL_BG     = HexColor('#dbeafe')
LILA        = HexColor('#a855f7')
LILA_BG     = HexColor('#f3e8ff')
BORDE       = HexColor('#e2e8f0')

# ── estilos ──────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

S_H1 = ParagraphStyle('H1', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=20, leading=24,
    textColor=SLATE, spaceBefore=4, spaceAfter=2,
)
S_H1_SUB = ParagraphStyle('H1sub', parent=ss['Normal'],
    fontName='Helvetica', fontSize=10, leading=12,
    textColor=SLATE_3, spaceAfter=12,
)
S_SECCION = ParagraphStyle('Sec', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=14, leading=18,
    textColor=SLATE, spaceBefore=14, spaceAfter=6,
)
S_BODY = ParagraphStyle('Body', parent=ss['Normal'],
    fontName='Helvetica', fontSize=10, leading=14,
    textColor=SLATE_2, alignment=TA_LEFT, spaceAfter=4,
)
S_BODY_W = ParagraphStyle('BodyW', parent=S_BODY, textColor=white)
S_PEQUE = ParagraphStyle('Peq', parent=ss['Normal'],
    fontName='Helvetica', fontSize=8.5, leading=11, textColor=SLATE_3,
)
S_PASO_T = ParagraphStyle('PasoT', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=SLATE,
)
S_PASO_D = ParagraphStyle('PasoD', parent=ss['Normal'],
    fontName='Helvetica', fontSize=9.5, leading=13, textColor=SLATE_2,
)
S_NUM = ParagraphStyle('Num', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=11, leading=13,
    textColor=white, alignment=TA_CENTER,
)
S_KBD = ParagraphStyle('Kbd', parent=ss['Normal'],
    fontName='Courier-Bold', fontSize=9, leading=12, textColor=SLATE,
)
S_TIP_T = ParagraphStyle('TipT', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=SLATE,
)
S_TIP_D = ParagraphStyle('TipD', parent=ss['Normal'],
    fontName='Helvetica', fontSize=9, leading=12, textColor=SLATE_2,
)


# ── header / footer ──────────────────────────────────────────────────────────
def encabezado(canv, doc):
    canv.saveState()
    w, h = A4
    # franja superior negra delgada
    canv.setFillColor(SLATE)
    canv.rect(0, h - 0.6 * cm, w, 0.6 * cm, fill=1, stroke=0)
    # acento verde a la izquierda
    canv.setFillColor(VERDE)
    canv.rect(0, h - 0.6 * cm, 1.5 * cm, 0.6 * cm, fill=1, stroke=0)
    # título minimalista
    canv.setFillColor(white)
    canv.setFont('Helvetica-Bold', 8)
    canv.drawString(2 * cm, h - 0.4 * cm, '⏵  ERP UNIVERSAL  ·  manual práctico')
    canv.setFont('Helvetica', 8)
    canv.setFillColor(SLATE_4)
    canv.drawRightString(w - 2 * cm, h - 0.4 * cm, f'/ pág {doc.page:02d}')

    # pie
    canv.setStrokeColor(BORDE)
    canv.setLineWidth(0.4)
    canv.line(2 * cm, 1 * cm, w - 2 * cm, 1 * cm)
    canv.setFillColor(SLATE_3)
    canv.setFont('Helvetica', 7.5)
    canv.drawString(2 * cm, 0.55 * cm, 'v4.0  ·  guía rápida — leélo una vez y olvidate del manual')
    canv.drawRightString(w - 2 * cm, 0.55 * cm, 'docs/Manual_ERP_Universal.pdf')
    canv.restoreState()


# ── helpers visuales ─────────────────────────────────────────────────────────
def chip(texto, color_fondo, color_texto):
    """Pequeña etiqueta inline tipo tag."""
    return f'<font color="{color_texto.hexval()}" size="8" face="Helvetica-Bold">' \
           f'<span style="background:{color_fondo.hexval()};">  {texto}  </span></font>'


def kbd(s):
    """Texto tipo tecla/UI en monospace."""
    return f'<font face="Courier-Bold" color="{SLATE.hexval()}" size="9" backcolor="{SLATE_BG.hexval()}">  {s}  </font>'


def paso(num, color, titulo, descripcion, ancho=16.0):
    """Fila numerada: cuadrito de color con número + texto."""
    num_box = Table([[Paragraph(str(num), S_NUM)]],
                    colWidths=[0.9 * cm], rowHeights=[0.9 * cm])
    num_box.setStyle(TableStyle([
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
    fila = Table([[num_box, texto]],
                 colWidths=[1.2 * cm, (ancho - 1.2) * cm])
    fila.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    return fila


def callout(tipo, titulo, texto):
    """Caja de aviso — tipo: 'tip', 'ojo', 'info'."""
    config = {
        'tip':  ('TIP',  AMBAR,  AMBAR_BG),
        'ojo':  ('OJO',  ROSA,   ROSA_BG),
        'info': ('NOTA', AZUL,   AZUL_BG),
    }[tipo]
    label, color, bg = config

    cab = Paragraph(
        f'<font face="Helvetica-Bold" size="8" color="{white.hexval()}">  {label}  </font>'
        f'  <font face="Helvetica-Bold" size="9.5" color="{SLATE.hexval()}">{titulo}</font>',
        ss['Normal']
    )
    body = Paragraph(texto, S_TIP_D)

    inner = Table([[cab], [body]], colWidths=[16.5 * cm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), color),
        ('BACKGROUND', (0, 1), (0, 1), bg),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',(0, 0), (-1, -1), 10),
        ('TOPPADDING',  (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
        ('LINEBEFORE',  (0, 0), (0, -1), 3, color),
    ]))
    return inner


def seccion_header(emoji, titulo, color):
    """Header de sección: barra de color + emoji + título."""
    p = Paragraph(
        f'<font color="{color.hexval()}" face="Helvetica-Bold" size="16">{emoji}  {titulo}</font>',
        ss['Normal']
    )
    t = Table([[p]], colWidths=[16.5 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), SLATE_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',(0, 0), (-1, -1), 12),
        ('TOPPADDING',  (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LINEBEFORE',  (0, 0), (0, -1), 4, color),
    ]))
    return t


def encabezado_doc():
    """Bloque grande de apertura del documento."""
    estilo_titulo = ParagraphStyle(
        'docTit', parent=ss['Normal'],
        fontName='Helvetica-Bold', fontSize=26, leading=32,
        textColor=SLATE,
    )
    estilo_sub = ParagraphStyle(
        'docSub', parent=ss['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=SLATE_3,
    )
    titulo = Paragraph(
        f'Manual <font color="{VERDE.hexval()}">/</font> ERP Universal',
        estilo_titulo,
    )
    sub = Paragraph(
        'Cómo usar el sistema sin morir en el intento.<br/>'
        'Una hoja por tema, todo lo que necesitás para arrancar.',
        estilo_sub,
    )
    bloque = Table([[titulo], [sub]], colWidths=[16.5 * cm])
    bloque.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (0, 0), 4),
        ('BOTTOMPADDING',(0, 0), (0, 0), 6),
        ('TOPPADDING',   (0, 1), (0, 1), 0),
        ('BOTTOMPADDING',(0, 1), (0, 1), 14),
        ('LINEBELOW',    (0, 1), (0, 1), 1.5, VERDE),
    ]))
    return bloque


def linea_tema(emoji, tema, descripcion, color):
    """Mini-card del índice."""
    contenido = Paragraph(
        f'<font face="Helvetica-Bold" size="11" color="{SLATE.hexval()}">'
        f'{emoji}  {tema}</font><br/>'
        f'<font face="Helvetica" size="9" color="{SLATE_3.hexval()}">{descripcion}</font>',
        ParagraphStyle('lt', parent=ss['Normal'], leading=14)
    )
    t = Table([[contenido]], colWidths=[8 * cm])
    t.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LINEBEFORE',   (0, 0), (0, -1), 3, color),
        ('BACKGROUND',   (0, 0), (-1, -1), SLATE_BG),
    ]))
    return t


# ── construcción ─────────────────────────────────────────────────────────────
def construir():
    salida = r'C:\Users\gfcar\Desktop\IA\Empresa 1\docs\Manual_ERP_Universal.pdf'

    doc = BaseDocTemplate(
        salida, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.5 * cm,
        title='Manual ERP Universal',
    )
    frame = Frame(2 * cm, 1.3 * cm, A4[0] - 4 * cm, A4[1] - 2.9 * cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                  showBoundary=0)
    doc.addPageTemplates([PageTemplate(id='M', frames=[frame], onPage=encabezado)])

    s = []  # story

    # ─── PORTADA / ÍNDICE ────────────────────────────────────────────────────
    s.append(encabezado_doc())
    s.append(Spacer(1, 0.4 * cm))

    intro = Paragraph(
        'Este manual asume que ya tenés el ERP instalado y la sesión iniciada. '
        'Si no, abrí <font face="Courier-Bold">ERP Universal Setup 4.0.0.exe</font>, '
        'completá la config inicial (DB + clave Gemini + admin) y volvé acá. '
        'Cada sección de abajo es independiente — saltá a lo que necesites.',
        S_BODY
    )
    s.append(intro)
    s.append(Spacer(1, 0.5 * cm))

    s.append(Paragraph('<b>¿Qué hay adentro?</b>', S_PASO_T))
    s.append(Spacer(1, 0.2 * cm))

    temas = [
        ('▸', 'Cargar una factura con OCR',     'Foto/PDF, la IA llena los campos. 30 seg.', VERDE),
        ('▸', 'Validar y confirmar',            'Revisar lo que extrajo la IA antes de guardar.', AZUL),
        ('▸', 'Registrar un pago / cobro',      'Marcar facturas como pagadas, total o parcial.', AMBAR),
        ('▸', 'Ver cuentas corrientes',         'Saldos por cliente y proveedor, historial.', LILA),
        ('▸', 'Dashboard y filtros',            'Cambiar período, leer KPIs, encontrar problemas.', VERDE),
        ('▸', 'Asistente IA',                   'Preguntarle al chatbot sobre tus datos.', ROSA),
        ('▸', 'Reportes e Excel',               'IVA, aging, libro diario — exportable.', AZUL),
        ('▸', 'Tareas de admin',                'Usuarios, empresa, backup, auditoría.', AMBAR),
    ]
    pares = [(temas[i], temas[i+1]) for i in range(0, len(temas), 2)]
    for a, b in pares:
        fila = Table(
            [[linea_tema(a[0], a[1], a[2], a[3]), linea_tema(b[0], b[1], b[2], b[3])]],
            colWidths=[8.2 * cm, 8.2 * cm],
        )
        fila.setStyle(TableStyle([
            ('LEFTPADDING',  (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING',   (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ]))
        s.append(fila)

    s.append(Spacer(1, 0.5 * cm))
    s.append(callout('info', 'Convenciones',
        'Cuando veas <font face="Courier-Bold">Botón gris</font> es algo de la UI; '
        'los textos en <b>negrita</b> son nombres de menú o módulo. '
        'TIP = atajo útil, OJO = no metas la pata, NOTA = info de contexto.'))

    s.append(PageBreak())
    # ─── 1. CARGAR FACTURA ───────────────────────────────────────────────────
    s.append(seccion_header('▸', '1.  Cargar una factura con OCR', VERDE))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'El camino más rápido para meter una factura al sistema. La IA hace el 90% del trabajo, '
        'vos solo confirmás.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    s.append(paso(1, VERDE, 'Abrir el módulo',
        'En la barra lateral, clic en <b>Cargar Factura</b>. Te lleva a la página del OCR.'))
    s.append(paso(2, VERDE, 'Subir el archivo',
        'Arrastrá la imagen/PDF a la zona punteada o clic en <b>Seleccionar</b>. '
        'Acepta JPG, PNG, WEBP y PDF (incluso varias páginas).'))
    s.append(paso(3, VERDE, 'Esperar a Gemini',
        'En 5–15 segundos la IA devuelve los campos: tipo, número, fecha, RUC, montos, IVA y los '
        'ítems del detalle. Te muestra el % de confianza por campo.'))
    s.append(paso(4, VERDE, 'Elegir cliente o proveedor',
        'Si el RUC ya existe en tu DB se autocompleta. Si no, clic en <b>+ Crear</b> y lo agregás '
        'al vuelo sin salir de la pantalla.'))
    s.append(paso(5, VERDE, 'Confirmar',
        'Clic en <b>Guardar comprobante</b>. Queda en estado <i>pendiente_revisión</i> '
        'hasta que un admin/operador lo valide (paso 2 del manual).'))

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('tip', 'Subí varias a la vez',
        'En la zona de drop podés tirar 5 facturas juntas. Las procesa en paralelo, una por una. '
        'Útil si tenés un fajo del mes para meter de golpe.'))
    s.append(Spacer(1, 0.2 * cm))
    s.append(callout('ojo', 'Foto borrosa = OCR malo',
        'Si la confianza baja a menos de 60%, revisá uno por uno. Pone fondo plano, buena luz, '
        'sin sombras encima del timbrado.'))

    s.append(Spacer(1, 0.6 * cm))
    # ─── 2. VALIDAR ──────────────────────────────────────────────────────────
    s.append(seccion_header('▸', '2.  Validar y confirmar comprobantes', AZUL))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Todo lo que entra por OCR queda como <i>pendiente</i>. Revisión humana antes de '
        'considerarlo definitivo y reflejarlo en cuentas corrientes.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    s.append(paso(1, AZUL, 'Ir al listado',
        'Menú <b>Comprobantes</b>. Filtrá por estado = <i>pendiente_revisión</i>.'))
    s.append(paso(2, AZUL, 'Abrir el detalle',
        'Clic en la fila → ves los datos extraídos + miniatura del archivo original al costado.'))
    s.append(paso(3, AZUL, 'Corregir si hace falta',
        'Tocá cualquier campo para editar. Las modificaciones quedan en auditoría.'))
    s.append(paso(4, AZUL, 'Confirmar o rechazar',
        '<b>Confirmar</b> = entra al sistema. <b>Rechazar</b> = se marca como inválido pero queda '
        'el archivo guardado. Ambos requieren motivo si rechazás.'))

    s.append(PageBreak())
    # ─── 3. REGISTRAR PAGO ───────────────────────────────────────────────────
    s.append(seccion_header('▸', '3.  Registrar un pago o cobro', AMBAR))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Un pago se asocia siempre a un comprobante. Puede ser total (cancela el saldo) '
        'o parcial (resta del saldo pendiente).', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    s.append(paso(1, AMBAR, 'Encontrar la factura',
        'En <b>Comprobantes</b> filtrá por la persona o número. O abrí <b>Cuentas Corrientes</b> '
        '→ entrar al cliente/proveedor → ves todas sus facturas con saldo.'))
    s.append(paso(2, AMBAR, 'Abrir el modal de pago',
        'Botón <b>Registrar pago</b> en la fila o en el detalle.'))
    s.append(paso(3, AMBAR, 'Completar los datos',
        'Fecha, monto, medio (efectivo / transferencia / cheque / tarjeta), número de recibo y '
        'notas. Opcional: subir foto del recibo en el mismo modal.'))
    s.append(paso(4, AMBAR, 'Guardar',
        'El saldo se actualiza al instante. Si pagaste el total → la factura pasa a '
        '<i>cancelado</i>. Si fue parcial → sigue activa con el saldo nuevo.'))

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('tip', 'Podés borrar un pago',
        'Si te equivocaste, andá al pago y eliminalo. El sistema revierte el asiento contable '
        'automáticamente y devuelve el saldo a la factura.'))

    s.append(Spacer(1, 0.6 * cm))
    # ─── 4. CUENTAS CORRIENTES ───────────────────────────────────────────────
    s.append(seccion_header('▸', '4.  Cuentas corrientes', LILA))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Vista panorámica de cuánto te debe cada cliente y cuánto le debés a cada proveedor. '
        'El módulo más consultado del día a día.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    s.append(paso(1, LILA, 'Listado general',
        'Menú <b>Cuentas Corrientes</b>. Dos pestañas: clientes y proveedores. Cada fila muestra '
        'saldo total y semáforo (verde = al día, ámbar = vencido, rojo = mora).'))
    s.append(paso(2, LILA, 'Detalle por persona',
        'Clic en una fila → entrás al historial. Ves todas las facturas con su estado, todos los '
        'pagos, los adjuntos y el aging.'))
    s.append(paso(3, LILA, 'Aging',
        'Pestaña <b>Aging</b> dentro del detalle: descompone el saldo en 0–30, 31–60, 61–90, +90 '
        'días. Sirve para priorizar cobros o renegociar plazos.'))

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('info', 'Movimientos consolidados',
        'Si querés ver todo (cobros + pagos) cronológico de toda la empresa, andá a '
        '<b>Movimientos</b> en la barra lateral. Filtrable por fecha, tipo y medio de pago.'))

    s.append(PageBreak())
    # ─── 5. DASHBOARD ────────────────────────────────────────────────────────
    s.append(seccion_header('▸', '5.  Dashboard y filtros de período', VERDE))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'La pantalla principal. KPIs arriba, gráficos abajo. Todo respeta el período '
        'seleccionado en la parte superior derecha.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    s.append(Paragraph('<b>Lo que vas a encontrar:</b>', S_PASO_T))
    s.append(Spacer(1, 0.15 * cm))

    items_dash = [
        ('KPIs',         'Por cobrar, por pagar, facturas pendientes, stock crítico.'),
        ('Flujo',        'Gráfico de barras: ingresos vs egresos por mes en el rango elegido.'),
        ('Resumen',      'Totales del período: ingresos, egresos y flujo neto.'),
        ('Top clientes', 'Los 5 que más te facturan en el período. Clic = detalle.'),
        ('Medios pago',  'Torta con la distribución de pagos (efectivo, transferencia, etc).'),
        ('Últimos',      'Tabla con los 6 últimos comprobantes. Clic = abrir.'),
    ]
    for tit, desc in items_dash:
        bullet = Paragraph(
            f'<font color="{VERDE.hexval()}" face="Helvetica-Bold">▪  </font>'
            f'<font face="Helvetica-Bold">{tit}.</font>  {desc}',
            S_BODY
        )
        s.append(bullet)

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('tip', 'El selector de período manda',
        'Arriba a la derecha: <i>Este mes / Mes anterior / Últimos 3 meses / Últimos 6 meses / '
        'Este año / Último año / Todo</i>. Cambiarlo refresca TODOS los componentes a la vez. '
        'Si no ves datos, probá con "Todo" para descartar que sea filtro.'))

    s.append(Spacer(1, 0.6 * cm))
    # ─── 6. ASISTENTE IA ─────────────────────────────────────────────────────
    s.append(seccion_header('▸', '6.  Asistente IA (chatbot)', ROSA))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Un Gemini con acceso de lectura a tus tablas. Le preguntás en castellano y te responde '
        'con datos reales — no inventa, ejecuta funciones internas y arma la respuesta.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    s.append(Paragraph('<b>Ejemplos que entiende perfectamente:</b>', S_PASO_T))
    s.append(Spacer(1, 0.15 * cm))

    ejemplos = [
        '"¿Cuánto le debo a Casa Esperanza?"',
        '"¿Quién es mi top cliente este año?"',
        '"Listame los proveedores con saldo pendiente mayor a 1.000.000"',
        '"¿Cuántas facturas cargué en marzo?"',
        '"¿Qué productos están bajo el punto de reorden?"',
        '"Dame el resumen del IVA del mes pasado"',
    ]
    for e in ejemplos:
        s.append(Paragraph(
            f'<font face="Courier" color="{ROSA.hexval()}">›</font>  '
            f'<font face="Helvetica-Oblique" color="{SLATE_2.hexval()}">{e}</font>',
            S_BODY
        ))

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('ojo', 'Lectura, no escritura',
        'El asistente <b>nunca</b> modifica datos — solo consulta. Si le pedís "borrá la factura X" '
        'te explica que no puede y te dice cómo hacerlo manualmente.'))

    s.append(PageBreak())
    # ─── 7. REPORTES ─────────────────────────────────────────────────────────
    s.append(seccion_header('▸', '7.  Reportes y exportación a Excel', AZUL))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Todo lo que necesite tu contador o el banco está acá. Cada reporte tiene botón '
        '<b>Exportar Excel</b> arriba a la derecha.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    reportes = [
        ('Libro de Compras (RG90)', 'Compras del período con IVA discriminado por tasa.'),
        ('Libro de Ventas (RG90)',  'Ventas del período, mismo formato — listo para SET.'),
        ('Liquidación de IVA',      'Compras vs ventas, débito y crédito fiscal del período.'),
        ('Aging de saldos',         'Antigüedad de cuentas por cobrar/pagar agrupada por tramo.'),
        ('Libro Diario',            'Asientos contables de partida doble.'),
        ('Libro Mayor',             'Movimientos por cuenta del plan de cuentas.'),
        ('Balance de comprobación', 'Saldos deudor/acreedor a una fecha.'),
        ('Estado de Resultados',    'Ingresos – egresos = utilidad del período.'),
        ('Balance General',         'Foto patrimonial: activo, pasivo, patrimonio.'),
    ]
    # tabla de 2 cols
    pares = [(reportes[i], reportes[i+1] if i+1 < len(reportes) else ('', ''))
             for i in range(0, len(reportes), 2)]
    for a, b in pares:
        celda_a = Paragraph(
            f'<font face="Helvetica-Bold" color="{SLATE.hexval()}">{a[0]}</font><br/>'
            f'<font color="{SLATE_3.hexval()}" size="9">{a[1]}</font>',
            ParagraphStyle('rep', parent=S_BODY, leading=13)
        )
        if b[0]:
            celda_b = Paragraph(
                f'<font face="Helvetica-Bold" color="{SLATE.hexval()}">{b[0]}</font><br/>'
                f'<font color="{SLATE_3.hexval()}" size="9">{b[1]}</font>',
                ParagraphStyle('rep', parent=S_BODY, leading=13)
            )
        else:
            celda_b = Paragraph('', S_BODY)
        fila = Table([[celda_a, celda_b]], colWidths=[8.2 * cm, 8.2 * cm])
        fila.setStyle(TableStyle([
            ('LEFTPADDING',  (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING',   (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW',    (0, 0), (-1, -1), 0.4, BORDE),
        ]))
        s.append(fila)

    s.append(Spacer(1, 0.6 * cm))
    # ─── 8. ADMIN ────────────────────────────────────────────────────────────
    s.append(seccion_header('▸', '8.  Tareas de administrador', AMBAR))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Solo usuarios con rol <b>admin</b>. Está todo bajo el menú <b>Administración</b>.', S_BODY))
    s.append(Spacer(1, 0.3 * cm))

    admin_tareas = [
        ('Empresa',  'Logo, RUC, dirección, teléfono, email, moneda principal.'),
        ('Usuarios', 'Crear / editar / desactivar. Cambiar rol (admin / operador / viewer).'),
        ('Sistema',  'Backup ZIP completo, estadísticas, eliminar datos de prueba.'),
        ('Auditoría','Toda acción del sistema con quién, cuándo, qué cambió. Filtrable.'),
    ]
    for tit, desc in admin_tareas:
        bullet = Paragraph(
            f'<font color="{AMBAR.hexval()}" face="Helvetica-Bold">▪  </font>'
            f'<font face="Helvetica-Bold">{tit}.</font>  {desc}',
            S_BODY
        )
        s.append(bullet)

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('tip', 'Backup periódico',
        'Andá a <b>Administración → Sistema → Descargar backup ZIP</b> al menos una vez por '
        'semana. Te lleva un ZIP con SQL + adjuntos. Guardalo afuera de la PC.'))
    s.append(Spacer(1, 0.2 * cm))
    s.append(callout('ojo', 'Wipe de datos',
        'El botón <b>Eliminar todos los datos</b> es destructivo. Pide doble confirmación. '
        'Sirve para limpiar después de las pruebas iniciales — no usar en producción.'))

    s.append(PageBreak())
    # ─── 9. ATAJOS / CHEATSHEET ──────────────────────────────────────────────
    s.append(seccion_header('▸', 'Atajos & cheatsheet', VERDE))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        'Lo que vale la pena tener a mano. Imprimí esta hoja si querés.', S_BODY))
    s.append(Spacer(1, 0.4 * cm))

    # tabla de atajos
    atajos = [
        ('Refrescar dashboard',    'F5  o el botón Actualizar arriba a la derecha'),
        ('Buscar global',          'Cada listado tiene su buscador en la cabecera'),
        ('Ver adjunto',            'Icono clip en la fila del comprobante o pago'),
        ('Anular comprobante',     'Detalle → menú …  → Anular (pide motivo)'),
        ('Cambiar período',        'Botones grises arriba en Dashboard, Cuentas y Reportes'),
        ('Cerrar sesión',          'Esquina inferior izquierda del sidebar'),
    ]
    data = [
        [Paragraph(f'<b>{a[0]}</b>', S_PASO_T),
         Paragraph(f'<font face="Courier-Bold" color="{SLATE.hexval()}">{a[1]}</font>', S_PASO_D)]
        for a in atajos
    ]
    t = Table(data, colWidths=[5.5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING',   (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND',   (0, 0), (-1, -1), SLATE_BG),
        ('LINEBELOW',    (0, 0), (-1, -2), 0.4, BORDE),
        ('LINEAFTER',    (0, 0), (0, -1), 0.4, BORDE),
    ]))
    s.append(t)

    s.append(Spacer(1, 0.6 * cm))
    s.append(Paragraph('<b>Estados del comprobante</b> (qué significa cada label):', S_PASO_T))
    s.append(Spacer(1, 0.2 * cm))

    estados = [
        ('pendiente_revisión', 'Cargado por OCR, aún no fue validado por una persona.', AMBAR),
        ('confirmado',         'Validado y activo. Suma a cuentas corrientes y reportes.',  VERDE),
        ('rechazado',          'Validado como inválido. No suma a nada pero queda el archivo.', SLATE_3),
        ('anulado',            'Estaba confirmado pero se anuló (con motivo). No suma.',    ROSA),
    ]
    for nombre, desc, color in estados:
        chip_html = (f'<font face="Helvetica-Bold" color="{white.hexval()}" size="8" '
                     f'backColor="{color.hexval()}">  {nombre}  </font>')
        p = Paragraph(
            f'{chip_html}  &nbsp; <font color="{SLATE_2.hexval()}">{desc}</font>',
            S_BODY
        )
        s.append(p)
        s.append(Spacer(1, 0.1 * cm))

    s.append(Spacer(1, 0.6 * cm))
    # caja de cierre
    cierre_p = Paragraph(
        '<font face="Helvetica-Bold" size="11" color="' + white.hexval() + '">'
        '¿Algo no anda?</font><br/>'
        '<font face="Helvetica" size="9" color="' + SLATE_4.hexval() + '">'
        'Probá lo obvio primero: F5 al browser, "Todo" en el filtro de período, '
        'cerrar y abrir sesión. Si persiste, revisá la auditoría '
        'para ver qué cambió último, o preguntale al asistente IA "¿qué hizo gfcar hoy?". '
        'Los logs del backend están en la consola que se abre al iniciar el .exe.</font>',
        ParagraphStyle('cier', parent=ss['Normal'], leading=14)
    )
    cierre = Table([[cierre_p]], colWidths=[16.5 * cm])
    cierre.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), SLATE),
        ('LEFTPADDING',  (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING',   (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 14),
        ('LINEBEFORE',   (0, 0), (0, -1), 4, VERDE),
    ]))
    s.append(cierre)

    doc.build(s)
    print(f'OK -> {salida}')


if __name__ == '__main__':
    construir()
