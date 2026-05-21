"""
Genera la guía visual del ERP Universal v4.0 en PDF.
Salida: docs/Guia_ERP_Universal.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Frame, PageTemplate, BaseDocTemplate, KeepTogether, NextPageTemplate
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfgen import canvas

# ── paleta corporativa ───────────────────────────────────────────────────────
VERDE        = HexColor('#10b981')
VERDE_OSCURO = HexColor('#047857')
VERDE_CLARO  = HexColor('#d1fae5')
AZUL         = HexColor('#3b82f6')
AZUL_OSCURO  = HexColor('#1e40af')
AZUL_CLARO   = HexColor('#dbeafe')
GRIS         = HexColor('#475569')
GRIS_CLARO   = HexColor('#f1f5f9')
GRIS_BORDE   = HexColor('#e2e8f0')
NEGRO        = HexColor('#0f172a')
ROJO         = HexColor('#ef4444')
AMBAR        = HexColor('#f59e0b')
PURPURA      = HexColor('#a855f7')

# ── estilos ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

S_TITULO_PORTADA = ParagraphStyle(
    'TituloPortada', parent=styles['Title'],
    fontName='Helvetica-Bold', fontSize=42, leading=48,
    alignment=TA_CENTER, textColor=white, spaceAfter=10,
)
S_SUBT_PORTADA = ParagraphStyle(
    'SubtPortada', parent=styles['Normal'],
    fontName='Helvetica', fontSize=16, leading=22,
    alignment=TA_CENTER, textColor=white,
)
S_VERSION_PORTADA = ParagraphStyle(
    'VersionPortada', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=11, leading=14,
    alignment=TA_CENTER, textColor=VERDE_CLARO, spaceAfter=4,
)

S_H1 = ParagraphStyle(
    'H1', parent=styles['Heading1'],
    fontName='Helvetica-Bold', fontSize=22, leading=26,
    textColor=AZUL_OSCURO, spaceBefore=2, spaceAfter=14,
)
S_H2 = ParagraphStyle(
    'H2', parent=styles['Heading2'],
    fontName='Helvetica-Bold', fontSize=14, leading=18,
    textColor=VERDE_OSCURO, spaceBefore=14, spaceAfter=6,
)
S_BODY = ParagraphStyle(
    'Body', parent=styles['Normal'],
    fontName='Helvetica', fontSize=10.5, leading=15,
    textColor=NEGRO, alignment=TA_JUSTIFY, spaceAfter=6,
)
S_BODY_W = ParagraphStyle(  # body sobre fondo de color
    'BodyW', parent=S_BODY, textColor=white,
)
S_PEQUE = ParagraphStyle(
    'Peque', parent=styles['Normal'],
    fontName='Helvetica', fontSize=9, leading=12,
    textColor=GRIS,
)
S_CITA = ParagraphStyle(
    'Cita', parent=styles['Normal'],
    fontName='Helvetica-Oblique', fontSize=10, leading=14,
    textColor=GRIS, alignment=TA_CENTER,
)
S_MOD_TIT = ParagraphStyle(
    'ModTit', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=11, leading=14,
    textColor=NEGRO, spaceAfter=2,
)
S_MOD_DESC = ParagraphStyle(
    'ModDesc', parent=styles['Normal'],
    fontName='Helvetica', fontSize=9, leading=12,
    textColor=GRIS,
)
S_PASO_NUM = ParagraphStyle(
    'PasoNum', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=20, leading=24,
    textColor=white, alignment=TA_CENTER,
)
S_PASO_TIT = ParagraphStyle(
    'PasoTit', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=11, leading=14,
    textColor=NEGRO, spaceAfter=3,
)
S_PASO_DESC = ParagraphStyle(
    'PasoDesc', parent=styles['Normal'],
    fontName='Helvetica', fontSize=9.5, leading=13,
    textColor=GRIS,
)


# ── decoración: portada ──────────────────────────────────────────────────────
def fondo_portada(canv, doc):
    """Pinta el fondo verde→azul de la portada."""
    canv.saveState()
    w, h = A4
    # banda principal verde
    canv.setFillColor(VERDE_OSCURO)
    canv.rect(0, 0, w, h, fill=1, stroke=0)
    # diagonal azul decorativa
    canv.setFillColor(AZUL_OSCURO)
    p = canv.beginPath()
    p.moveTo(0, h)
    p.lineTo(w, h)
    p.lineTo(w, h * 0.55)
    p.lineTo(0, h * 0.75)
    p.close()
    canv.drawPath(p, fill=1, stroke=0)
    # acento verde claro
    canv.setFillColor(VERDE)
    p2 = canv.beginPath()
    p2.moveTo(0, h * 0.3)
    p2.lineTo(w, h * 0.18)
    p2.lineTo(w, h * 0.05)
    p2.lineTo(0, h * 0.12)
    p2.close()
    canv.drawPath(p2, fill=1, stroke=0)
    canv.restoreState()


def fondo_pagina(canv, doc):
    """Encabezado y pie de página de las páginas internas."""
    canv.saveState()
    w, h = A4

    # franja superior
    canv.setFillColor(VERDE_OSCURO)
    canv.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
    # título de la guía
    canv.setFillColor(white)
    canv.setFont('Helvetica-Bold', 10)
    canv.drawString(2 * cm, h - 0.78 * cm, 'ERP UNIVERSAL  v4.0')
    canv.setFont('Helvetica', 9)
    canv.drawRightString(w - 2 * cm, h - 0.78 * cm, 'Guía rápida de uso')

    # pie de página
    canv.setStrokeColor(GRIS_BORDE)
    canv.setLineWidth(0.5)
    canv.line(2 * cm, 1.2 * cm, w - 2 * cm, 1.2 * cm)
    canv.setFillColor(GRIS)
    canv.setFont('Helvetica', 8)
    canv.drawString(2 * cm, 0.7 * cm, 'Sistema de gestión empresarial — Paraguay')
    canv.drawRightString(w - 2 * cm, 0.7 * cm, f'Página {doc.page - 1}')
    canv.restoreState()


# ── helpers de layout ────────────────────────────────────────────────────────
def caja_modulo(emoji, titulo, descripcion, color):
    """Tarjeta de módulo: barra de color con ícono + título, descripción debajo."""
    cabecera = Paragraph(
        f'<font size="18" color="white">{emoji}</font>  '
        f'<font size="12" color="white"><b>{titulo}</b></font>',
        styles['Normal']
    )
    desc_p = Paragraph(descripcion, S_MOD_DESC)

    inner = Table(
        [[cabecera], [desc_p]],
        colWidths=[7.8 * cm],
    )
    inner.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0), color),
        ('BACKGROUND',   (0, 1), (-1, 1), white),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (0, 0), 8),
        ('BOTTOMPADDING',(0, 0), (0, 0), 8),
        ('TOPPADDING',   (0, 1), (-1, 1), 10),
        ('BOTTOMPADDING',(0, 1), (-1, 1), 10),
        ('BOX',          (0, 0), (-1, -1), 0.5, GRIS_BORDE),
    ]))
    return inner


def paso_circular(numero, titulo, desc, color):
    """Paso numerado: círculo con número + texto al costado."""
    num_p = Paragraph(str(numero), S_PASO_NUM)
    num_cell = Table([[num_p]], colWidths=[1.5 * cm], rowHeights=[1.5 * cm])
    num_cell.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',  (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))

    text_cell = [
        Paragraph(f'<b>{titulo}</b>', S_PASO_TIT),
        Paragraph(desc, S_PASO_DESC),
    ]

    fila = Table(
        [[num_cell, text_cell]],
        colWidths=[2 * cm, 13 * cm],
    )
    fila.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 4),
        ('TOPPADDING',   (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
    ]))
    return fila


def chip_rol(emoji, nombre, descripcion, color_fondo, color_texto):
    """Chip de rol: emoji + nombre destacado + descripción."""
    cab = Paragraph(
        f'<font size="16">{emoji}</font>  <font size="13" color="{color_texto.hexval()}"><b>{nombre}</b></font>',
        styles['Normal']
    )
    desc = Paragraph(descripcion, S_MOD_DESC)
    t = Table([[cab], [desc]], colWidths=[5.2 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color_fondo),
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 12),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def consejo(emoji, texto):
    """Línea de consejo con bullet de color."""
    p = Paragraph(
        f'<font size="13">{emoji}</font>  <font color="{NEGRO.hexval()}">{texto}</font>',
        ParagraphStyle('Cons', parent=S_BODY, alignment=TA_LEFT, leading=16)
    )
    t = Table([[p]], colWidths=[16.5 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), GRIS_CLARO),
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LINEBEFORE',   (0, 0), (0, -1), 4, VERDE),
    ]))
    return t


# ── construcción del documento ───────────────────────────────────────────────
def construir():
    salida = r'C:\Users\gfcar\Desktop\IA\Empresa 1\docs\Guia_ERP_Universal.pdf'

    doc = BaseDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2 * cm,
        title='Guía ERP Universal v4.0',
        author='ERP Universal',
        subject='Guía rápida de uso',
    )

    # frame portada (ocupa toda la página)
    frame_portada = Frame(
        0, 0, A4[0], A4[1],
        leftPadding=2.5 * cm, rightPadding=2.5 * cm,
        topPadding=2 * cm, bottomPadding=2 * cm,
        showBoundary=0, id='portada'
    )
    # frame interno (deja espacio para header/footer)
    frame_interno = Frame(
        2 * cm, 1.5 * cm,
        A4[0] - 4 * cm, A4[1] - 3.5 * cm,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
        showBoundary=0, id='interno'
    )

    doc.addPageTemplates([
        PageTemplate(id='Portada', frames=[frame_portada], onPage=fondo_portada),
        PageTemplate(id='Interno', frames=[frame_interno], onPage=fondo_pagina),
    ])

    story = []

    # ─── PORTADA ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph('●  v4.0', S_VERSION_PORTADA))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph('ERP UNIVERSAL', S_TITULO_PORTADA))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph('Guía rápida de uso', S_SUBT_PORTADA))
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph(
        '<font color="#d1fae5" size="11">Sistema integral de gestión empresarial<br/>'
        'diseñado para PyMEs paraguayas</font>',
        ParagraphStyle('p', parent=styles['Normal'], alignment=TA_CENTER, leading=16)
    ))
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(
        '<font color="#d1fae5" size="9">Comprobantes  ·  Cuentas Corrientes  ·  Inventario  ·  '
        'Contabilidad  ·  Bancos  ·  Reportes IVA  ·  IA</font>',
        ParagraphStyle('p2', parent=styles['Normal'], alignment=TA_CENTER)
    ))

    # Cambiar a la plantilla 'Interno' para el resto del documento
    story.append(NextPageTemplate('Interno'))
    story.append(PageBreak())
    # ─── PÁGINA 2 — QUÉ ES + ROLES ───────────────────────────────────────────
    story.append(Paragraph('¿Qué es el ERP Universal?', S_H1))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE, spaceBefore=0, spaceAfter=14))

    story.append(Paragraph(
        'El <b>ERP Universal v4.0</b> es un sistema de gestión empresarial completo, '
        'diseñado para que pequeñas y medianas empresas paraguayas lleven sus operaciones '
        'comerciales y contables de forma <b>centralizada, automatizada y auditable</b>.',
        S_BODY,
    ))
    story.append(Paragraph(
        'Combina <b>OCR con inteligencia artificial</b> (lectura automática de facturas), '
        '<b>contabilidad de partida doble</b>, control de stock, manejo de cuentas corrientes, '
        'reportes fiscales (IVA RG90) y un <b>asistente IA</b> integrado que responde '
        'preguntas sobre tus números en lenguaje natural.',
        S_BODY,
    ))
    story.append(Spacer(1, 0.4 * cm))

    # destacado
    destacado = Table([[Paragraph(
        '<b>Acceso multi-plataforma:</b>  funciona como aplicación de escritorio (Windows .exe) '
        'y desde cualquier navegador moderno conectado a tu base de datos en la nube.',
        S_BODY_W
    )]], colWidths=[16.5 * cm])
    destacado.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), AZUL_OSCURO),
        ('LEFTPADDING',  (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING',   (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 12),
    ]))
    story.append(destacado)

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph('Roles de usuario', S_H2))
    story.append(Paragraph(
        'Cada usuario tiene un rol que determina qué puede hacer dentro del sistema:',
        S_BODY
    ))
    story.append(Spacer(1, 0.3 * cm))

    roles_tabla = Table(
        [[
            chip_rol('🛡️', 'Administrador',
                     'Control total: usuarios, configuración, datos maestros, eliminación, auditoría completa.',
                     AZUL_CLARO, AZUL_OSCURO),
            chip_rol('✏️', 'Operador',
                     'Carga y validación diaria: comprobantes, pagos, stock, clientes y proveedores.',
                     VERDE_CLARO, VERDE_OSCURO),
            chip_rol('👁️', 'Viewer',
                     'Solo lectura: dashboard, reportes y cuentas corrientes — ideal para gerencia.',
                     HexColor('#fef3c7'), HexColor('#92400e')),
        ]],
        colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm],
    )
    roles_tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(roles_tabla)

    story.append(PageBreak())
    # ─── PÁGINA 3 — MÓDULOS ──────────────────────────────────────────────────
    story.append(Paragraph('Módulos principales', S_H1))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE, spaceBefore=0, spaceAfter=14))

    story.append(Paragraph(
        'El sistema se organiza en módulos accesibles desde la barra lateral. '
        'Cada uno cubre un área operativa concreta del negocio:',
        S_BODY
    ))
    story.append(Spacer(1, 0.4 * cm))

    modulos = [
        ('📊', 'Dashboard',         'KPIs, gráficos y selector de período (este mes, último año, todo). Vista general de la salud financiera.', VERDE),
        ('📄', 'Comprobantes / OCR','Carga manual o por foto/PDF. La IA extrae proveedor, fecha, montos e IVA automáticamente.', AZUL),
        ('👥', 'Cuentas Corrientes','Saldos por cliente y proveedor, historial de movimientos, aging de antigüedad.', VERDE),
        ('📦', 'Inventario',        'Productos, categorías, ajustes de stock, alertas de punto de reorden.', AZUL),
        ('📚', 'Contabilidad',      'Plan de cuentas, libro diario, libro mayor, balance de comprobación, estados financieros.', VERDE),
        ('🏦', 'Bancos',            'Cuentas bancarias, depósitos, transferencias, conciliación de movimientos.', AZUL),
        ('📋', 'Reportes IVA',      'Libro de Compras, Libro de Ventas y Liquidación según RG90 — exportables a Excel.', VERDE),
        ('🤖', 'Asistente IA',      'Chatbot que responde sobre tus datos: "¿Cuánto le debo a X?", "Top clientes del mes", etc.', AZUL),
    ]

    # render en grilla 2 columnas × 4 filas (más legible)
    filas = [
        [caja_modulo(*modulos[i][:3], color=modulos[i][3]),
         caja_modulo(*modulos[i+1][:3], color=modulos[i+1][3])]
        for i in range(0, 8, 2)
    ]
    grilla = Table(
        filas,
        colWidths=[8.2 * cm, 8.2 * cm],
    )
    grilla.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(grilla)

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        '<i>Además: módulo de <b>Empresa</b> para tu logo y datos fiscales, '
        '<b>Auditoría</b> que registra cada cambio, '
        '<b>Exportar Excel</b> con un clic para todos los reportes.</i>',
        S_CITA
    ))

    story.append(PageBreak())
    # ─── PÁGINA 4 — INICIO + FLUJO ───────────────────────────────────────────
    story.append(Paragraph('Cómo iniciar el sistema', S_H1))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE, spaceBefore=0, spaceAfter=14))

    pasos_inicio = [
        ('1', 'Instalar',
         'Ejecutar <b>ERP Universal Setup 4.0.0.exe</b> y seguir el asistente. Si Windows muestra '
         'una advertencia, hacer clic en "Más información" → "Ejecutar de todas formas".', AZUL),
        ('2', 'Configurar (solo primera vez)',
         'En el primer arranque se piden: URL de base de datos (Supabase), clave de Gemini IA, '
         'datos del administrador y nombre de la empresa.', VERDE),
        ('3', 'Iniciar sesión',
         'Ingresar con el correo y contraseña del administrador. El sistema redirige al '
         'Dashboard automáticamente.', AZUL),
    ]
    for num, tit, d, col in pasos_inicio:
        story.append(paso_circular(num, tit, d, col))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph('Flujo típico de uso diario', S_H1))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE, spaceBefore=0, spaceAfter=14))

    flujo = [
        ('1', 'Cargar factura recibida',
         'Ir a <b>Cargar Factura</b>, subir foto/PDF. La IA llena los campos en segundos.', VERDE),
        ('2', 'Validar datos extraídos',
         'Revisar proveedor, fecha, monto e IVA. Corregir si hace falta y confirmar.', AZUL),
        ('3', 'Registrar el pago',
         'En <b>Comprobantes</b>, abrir la factura y registrar el pago (efectivo, transferencia, etc).', VERDE),
        ('4', 'Consultar la cuenta corriente',
         'En <b>Cuentas Corrientes</b> ver el saldo actualizado del proveedor o cliente.', AZUL),
    ]
    for num, tit, d, col in flujo:
        story.append(paso_circular(num, tit, d, col))

    story.append(PageBreak())
    # ─── PÁGINA 5 — CONSEJOS + CIERRE ────────────────────────────────────────
    story.append(Paragraph('Consejos rápidos', S_H1))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE, spaceBefore=0, spaceAfter=14))

    consejos = [
        ('💡', '<b>Usa el OCR siempre que puedas.</b>  Cargar facturas con foto reduce errores '
               'de digitación y ahorra tiempo. La IA detecta timbrado, RUC, fecha y montos.'),
        ('🔍', '<b>Filtros del Dashboard.</b>  El selector de período (Este mes, Últimos 6 meses, '
               'Este año, Todo) afecta a todos los gráficos y KPIs simultáneamente.'),
        ('💬', '<b>Pregúntale al Asistente.</b>  Ejemplos: <i>"¿Cuánto vendí en marzo?"</i>, '
               '<i>"Lista los proveedores con saldo pendiente"</i>, <i>"Top 5 clientes del año"</i>.'),
        ('📤', '<b>Exporta a Excel.</b>  Casi todos los reportes (IVA, aging, libro diario) tienen '
               'botón de exportar — útil para enviar al contador o al banco.'),
        ('🔐', '<b>Roles y seguridad.</b>  Crea usuarios <b>Operador</b> para la carga diaria '
               'y <b>Viewer</b> para gerencia. Solo el <b>Admin</b> puede borrar o modificar configuración.'),
        ('💾', '<b>Backups.</b>  En Administración → Sistema podés bajar un backup ZIP con todo '
               '(datos + adjuntos). Hacelo periódicamente.'),
        ('📎', '<b>Adjuntá comprobantes.</b>  Cada factura y recibo puede tener su imagen/PDF '
               'asociado — quedan disponibles para auditoría y consulta.'),
    ]
    for emo, txt in consejos:
        story.append(consejo(emo, txt))
        story.append(Spacer(1, 0.18 * cm))

    story.append(Spacer(1, 0.6 * cm))

    # caja final de soporte
    cierre = Table([[Paragraph(
        '<font color="white" size="13"><b>¿Necesitás ayuda?</b></font><br/><br/>'
        '<font color="#d1fae5" size="10">'
        'Consultá el <b>Asistente IA</b> dentro del sistema o revisá la documentación técnica '
        'en la carpeta <b>docs/</b> del proyecto. Para soporte avanzado, contactá al equipo de implementación.'
        '</font>',
        ParagraphStyle('cierre', parent=styles['Normal'], alignment=TA_CENTER, leading=15)
    )]], colWidths=[16.5 * cm])
    cierre.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), VERDE_OSCURO),
        ('LEFTPADDING',  (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING',   (0, 0), (-1, -1), 18),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 18),
    ]))
    story.append(cierre)

    doc.build(story)
    print(f'OK -> {salida}')


if __name__ == '__main__':
    construir()
