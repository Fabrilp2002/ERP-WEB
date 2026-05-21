"""
Genera el instructivo paso a paso de instalación del ERP Universal.
Salida: docs/Instalacion_ERP_Universal.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether
)

# ── paleta (igual al manual) ─────────────────────────────────────────────────
SLATE     = HexColor('#0f172a')
SLATE_2   = HexColor('#334155')
SLATE_3   = HexColor('#64748b')
SLATE_4   = HexColor('#cbd5e1')
SLATE_BG  = HexColor('#f8fafc')
VERDE     = HexColor('#10b981')
VERDE_BG  = HexColor('#d1fae5')
AMBAR     = HexColor('#f59e0b')
AMBAR_BG  = HexColor('#fef3c7')
ROSA      = HexColor('#ec4899')
ROSA_BG   = HexColor('#fce7f3')
AZUL      = HexColor('#3b82f6')
AZUL_BG   = HexColor('#dbeafe')
BORDE     = HexColor('#e2e8f0')

ss = getSampleStyleSheet()
S_BODY = ParagraphStyle('B', parent=ss['Normal'],
    fontName='Helvetica', fontSize=10, leading=14,
    textColor=SLATE_2, alignment=TA_LEFT, spaceAfter=4)
S_PASO_T = ParagraphStyle('PT', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=SLATE)
S_PASO_D = ParagraphStyle('PD', parent=ss['Normal'],
    fontName='Helvetica', fontSize=10, leading=14, textColor=SLATE_2)
S_NUM = ParagraphStyle('N', parent=ss['Normal'],
    fontName='Helvetica-Bold', fontSize=14, leading=16,
    textColor=white, alignment=1)
S_TIP_D = ParagraphStyle('TD', parent=ss['Normal'],
    fontName='Helvetica', fontSize=9, leading=12, textColor=SLATE_2)


# ── header / footer ──────────────────────────────────────────────────────────
def encabezado(canv, doc):
    canv.saveState()
    w, h = A4
    canv.setFillColor(SLATE)
    canv.rect(0, h - 0.6 * cm, w, 0.6 * cm, fill=1, stroke=0)
    canv.setFillColor(VERDE)
    canv.rect(0, h - 0.6 * cm, 1.5 * cm, 0.6 * cm, fill=1, stroke=0)
    canv.setFillColor(white)
    canv.setFont('Helvetica-Bold', 8)
    canv.drawString(2 * cm, h - 0.4 * cm, '⏵  ERP UNIVERSAL  ·  instalación paso a paso')
    canv.setFont('Helvetica', 8)
    canv.setFillColor(SLATE_4)
    canv.drawRightString(w - 2 * cm, h - 0.4 * cm, f'/ pág {doc.page:02d}')
    canv.setStrokeColor(BORDE); canv.setLineWidth(0.4)
    canv.line(2 * cm, 1 * cm, w - 2 * cm, 1 * cm)
    canv.setFillColor(SLATE_3); canv.setFont('Helvetica', 7.5)
    canv.drawString(2 * cm, 0.55 * cm,
        'v4.0  ·  de archivo .exe a sistema corriendo en menos de 5 minutos')
    canv.drawRightString(w - 2 * cm, 0.55 * cm, 'docs/Instalacion_ERP_Universal.pdf')
    canv.restoreState()


# ── helpers ──────────────────────────────────────────────────────────────────
def paso(num, color, titulo, descripcion):
    num_box = Table([[Paragraph(str(num), S_NUM)]],
                    colWidths=[1.1 * cm], rowHeights=[1.1 * cm])
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
    fila = Table([[num_box, texto]], colWidths=[1.4 * cm, 15.1 * cm])
    fila.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
    ]))
    return fila


def callout(tipo, titulo, texto):
    config = {
        'tip':  ('TIP',  AMBAR, AMBAR_BG),
        'ojo':  ('OJO',  ROSA,  ROSA_BG),
        'info': ('NOTA', AZUL,  AZUL_BG),
    }[tipo]
    label, color, bg = config
    cab = Paragraph(
        f'<font face="Helvetica-Bold" size="8" color="{white.hexval()}">  {label}  </font>'
        f'  <font face="Helvetica-Bold" size="9.5" color="{SLATE.hexval()}">{titulo}</font>',
        ss['Normal'])
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


def fase_header(num, titulo, color):
    p = Paragraph(
        f'<font color="{color.hexval()}" face="Helvetica-Bold" size="9">FASE {num}</font>'
        f'<br/><font color="{SLATE.hexval()}" face="Helvetica-Bold" size="16">{titulo}</font>',
        ParagraphStyle('fh', parent=ss['Normal'], leading=20)
    )
    t = Table([[p]], colWidths=[16.5 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), SLATE_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',(0, 0), (-1, -1), 14),
        ('TOPPADDING',  (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 12),
        ('LINEBEFORE',  (0, 0), (0, -1), 4, color),
    ]))
    return t


def lista_check(items):
    """Lista de check con cuadrito verde."""
    flowables = []
    for it in items:
        check = Paragraph(
            f'<font color="{VERDE.hexval()}" face="Helvetica-Bold" size="11">▪</font>',
            ss['Normal'])
        texto = Paragraph(it, S_BODY)
        fila = Table([[check, texto]], colWidths=[0.5 * cm, 16 * cm])
        fila.setStyle(TableStyle([
            ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',(0, 0), (-1, -1), 0),
            ('TOPPADDING',  (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 2),
        ]))
        flowables.append(fila)
    return flowables


def encabezado_doc():
    estilo_titulo = ParagraphStyle('docT', parent=ss['Normal'],
        fontName='Helvetica-Bold', fontSize=26, leading=32, textColor=SLATE)
    estilo_sub = ParagraphStyle('docS', parent=ss['Normal'],
        fontName='Helvetica', fontSize=10, leading=14, textColor=SLATE_3)
    titulo = Paragraph(
        f'Instalación <font color="{VERDE.hexval()}">/</font> ERP Universal',
        estilo_titulo)
    sub = Paragraph(
        'Cómo instalar el sistema en una PC nueva.<br/>'
        'Solo necesitás el archivo .exe, conexión a internet y 5 minutos.',
        estilo_sub)
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


# ── construcción ─────────────────────────────────────────────────────────────
def construir():
    salida = r'C:\Users\gfcar\Desktop\IA\Empresa 1\docs\Instalacion_ERP_Universal.pdf'

    doc = BaseDocTemplate(salida, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.5 * cm,
        title='Instalación ERP Universal')
    frame = Frame(2 * cm, 1.3 * cm, A4[0] - 4 * cm, A4[1] - 2.9 * cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                  showBoundary=0)
    doc.addPageTemplates([PageTemplate(id='I', frames=[frame], onPage=encabezado)])

    s = []

    # ─── PORTADA + REQUISITOS ────────────────────────────────────────────────
    s.append(encabezado_doc())
    s.append(Spacer(1, 0.3 * cm))

    s.append(Paragraph(
        'Esta guía te lleva de la mano desde tener el archivo <font face="Courier-Bold">'
        'ERP Universal Setup 4.0.0.exe</font> hasta tener el sistema corriendo, con tu '
        'usuario admin creado y la primera factura cargable. Pensado para que cualquier '
        'persona — no técnica — pueda hacerlo.', S_BODY))

    s.append(Spacer(1, 0.4 * cm))
    s.append(Paragraph('<b>Antes de empezar, asegurate de tener:</b>', S_PASO_T))
    s.append(Spacer(1, 0.2 * cm))

    requisitos = [
        '<b>Windows 10 u 11</b> (64 bits). En versiones anteriores no fue probado.',
        '<b>Conexión a internet</b> activa. La base de datos vive en la nube (Supabase) y '
        'la IA de OCR consulta a Google.',
        '<b>4 GB de RAM libres</b> y <b>2 GB de disco</b> para la instalación.',
        '<b>Permisos de instalación</b> en la PC (no hace falta admin si elegís la carpeta '
        'del usuario, pero sí si querés instalar en C:\\Program Files).',
        '<b>Datos a mano:</b> URL de la base de datos Supabase, clave de API de Gemini, '
        'y el correo + contraseña con la que vas a entrar.',
    ]
    for r in lista_check(requisitos):
        s.append(r)

    s.append(Spacer(1, 0.4 * cm))
    s.append(callout('info', '¿No tenés la URL de la DB ni la clave de Gemini?',
        'Pediselos a quien hizo la instalación original (gfcar). Si vas a estrenar todo el sistema '
        'desde cero, necesitás crear una cuenta en <b>supabase.com</b> (DB) y otra en '
        '<b>aistudio.google.com</b> (Gemini). Ambas tienen plan gratis suficiente para empezar.'))

    s.append(Spacer(1, 0.4 * cm))
    s.append(Paragraph('<b>Tiempo total estimado:</b>', S_PASO_T))
    s.append(Spacer(1, 0.15 * cm))

    timing = Table([
        ['Descargar el .exe',          '1 min'],
        ['Ejecutar instalador NSIS',   '2 min'],
        ['Primera config (DB + Gemini + admin)', '2 min'],
        ['Iniciar y verificar',        '30 seg'],
        ['', ''],
        ['Total',                      '≈ 5–6 min'],
    ], colWidths=[12 * cm, 4 * cm])
    timing.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME',  (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -2), SLATE_2),
        ('TEXTCOLOR', (0, -1), (-1, -1), SLATE),
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('LINEBELOW',    (0, 0), (-1, -3), 0.4, BORDE),
        ('LINEABOVE',    (0, -1), (-1, -1), 1, VERDE),
        ('BACKGROUND',   (0, -1), (-1, -1), VERDE_BG),
        ('ALIGN',        (1, 0), (1, -1), 'RIGHT'),
    ]))
    s.append(timing)

    s.append(PageBreak())
    # ─── FASE 1: CONSEGUIR Y EJECUTAR EL INSTALADOR ──────────────────────────
    s.append(fase_header('1', 'Conseguir y ejecutar el instalador', VERDE))
    s.append(Spacer(1, 0.3 * cm))

    s.append(paso(1, VERDE, 'Conseguir el archivo .exe',
        'Te lo van a pasar por: pendrive, WeTransfer, Google Drive o lo bajás del repositorio. '
        'El archivo se llama <b>ERP Universal Setup 4.0.0.exe</b> y pesa cerca de <b>258 MB</b>. '
        'Guardalo en cualquier carpeta — ej. tu Escritorio o Descargas.'))

    s.append(paso(2, VERDE, 'Doble clic para ejecutar',
        'Hacé doble clic en <b>ERP Universal Setup 4.0.0.exe</b>. Windows puede tardar '
        'unos segundos en abrirlo (está verificando el archivo).'))

    s.append(paso(3, VERDE, 'Pasar la advertencia de Windows SmartScreen',
        'Como el .exe no está firmado con certificado de empresa, Windows muestra una pantalla azul: '
        '<b>"Windows protegió su PC"</b>. Es <i>normal</i> en software interno. Hacé clic en '
        '<b>"Más información"</b> y después en <b>"Ejecutar de todas formas"</b>.'))

    s.append(callout('ojo', '¿No aparece "Más información"?',
        'En algunas configuraciones corporativas el botón está oculto. Probá: clic derecho sobre '
        'el .exe → <b>Propiedades</b> → tildá <b>"Desbloquear"</b> al pie → <b>Aceptar</b>. '
        'Volvé a hacer doble clic y ya no aparece la advertencia.'))

    s.append(Spacer(1, 0.3 * cm))
    s.append(paso(4, VERDE, 'Aceptar el acuerdo de licencia',
        'Aparece la ventana del instalador NSIS. Marcá la casilla de aceptación y clic en '
        '<b>Siguiente</b>.'))

    s.append(paso(5, VERDE, 'Elegir carpeta de instalación',
        'Por defecto sugiere <font face="Courier-Bold">C:\\Users\\&lt;usuario&gt;\\AppData\\Local\\Programs\\ERP Universal</font>. '
        'Podés cambiarla con <b>Examinar</b> si querés instalarlo en otra parte. Para uso personal '
        'la opción por defecto está perfecta. Clic en <b>Instalar</b>.'))

    s.append(paso(6, VERDE, 'Esperar a que copie los archivos',
        'La barra de progreso tarda <b>1–2 minutos</b>. Está descomprimiendo el backend Python '
        '(~30 MB), el frontend Next.js (~150 MB) y librerías auxiliares.'))

    s.append(paso(7, VERDE, 'Finalizar',
        'Cuando termina, dejá tildada la casilla <b>"Ejecutar ERP Universal"</b> y clic en '
        '<b>Terminar</b>. Se crearon también un acceso directo en el Escritorio y otro en el '
        'Menú Inicio.'))

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('tip', 'Atajo en el escritorio',
        'Si cerraste el instalador sin tildar "Ejecutar", buscá en el Escritorio el ícono '
        '<b>ERP Universal</b> y hacé doble clic. Misma historia.'))

    s.append(PageBreak())
    # ─── FASE 2: PRIMERA CONFIG ──────────────────────────────────────────────
    s.append(fase_header('2', 'Configuración inicial (solo la primera vez)', AZUL))
    s.append(Spacer(1, 0.3 * cm))

    s.append(Paragraph(
        'Al abrir por primera vez, antes de la pantalla de login te aparece una ventana de '
        'configuración con 4 secciones. Completá los datos y clic en <b>Guardar</b> al final. '
        'Esto se hace UNA sola vez — la próxima vez que abras la app va directo al login.',
        S_BODY))
    s.append(Spacer(1, 0.4 * cm))

    s.append(paso(1, AZUL, 'Base de datos (DATABASE_URL)',
        'Pegar la URL que te pasó el responsable. Tiene este formato:<br/>'
        '<font face="Courier-Bold" size="9">'
        'postgresql+asyncpg://postgres.xxxx:&lt;PASS&gt;@aws-0-us-east-1.pooler.supabase.com:6543/postgres'
        '</font><br/>'
        'Es la dirección donde viven los datos de tu empresa (clientes, comprobantes, etc).'))

    s.append(paso(2, AZUL, 'URL y clave de Supabase (opcional)',
        'Si te las pasaron, completalas — son las dos URL+anon-key del panel de Supabase. '
        'Si no, dejalas vacías; el sistema funciona igual usando solo DATABASE_URL.'))

    s.append(paso(3, AZUL, 'Clave de Gemini API (GEMINI_API_KEY)',
        'Es la clave que activa el OCR (lectura automática de facturas) y el chatbot. '
        'Empieza con <font face="Courier-Bold">AIza...</font> y mide unos 39 caracteres. '
        'Pegala en el campo <b>Clave Gemini</b>.'))

    s.append(callout('info', '¿De dónde sale la clave de Gemini?',
        'Se obtiene en <b>aistudio.google.com</b>: iniciar sesión con cuenta Google → '
        'menú <b>Get API key</b> → <b>Create API key in new project</b> → copiar. La clave es '
        'gratis para uso moderado (varios miles de facturas por mes). Si ya tenés un proyecto '
        'compartido te la pueden mandar.'))

    s.append(Spacer(1, 0.2 * cm))
    s.append(paso(4, AZUL, 'Datos del usuario administrador',
        '<b>Email:</b> con el que vas a iniciar sesión todos los días. '
        '<b>Contraseña:</b> mínimo 8 caracteres, mezclá letras y números. '
        '<b>Nombre:</b> tu nombre o "Administrador" si querés. '
        'Este usuario tiene acceso total al sistema.'))

    s.append(paso(5, AZUL, 'Nombre de la empresa',
        'El nombre que se va a mostrar en el sidebar y en los reportes. Lo podés cambiar '
        'después desde <b>Administración → Empresa</b>.'))

    s.append(paso(6, AZUL, 'Guardar',
        'Clic en <b>Guardar</b>. La ventana se cierra y el sistema empieza a arrancar el '
        'backend y el frontend. Tarda <b>10–30 segundos</b> la primera vez. No cierres '
        'la ventana negra de consola que aparece — es el backend trabajando.'))

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('ojo', 'Los datos se guardan localmente',
        'Todo lo que pusiste en esta ventana queda en '
        '<font face="Courier-Bold">%APPDATA%\\ERP Universal\\backend.env</font>. '
        'No se sube a ningún servidor. Si querés cambiarlos después, editá ese archivo o '
        'borralo y se vuelve a abrir la ventana de config al próximo inicio.'))

    s.append(PageBreak())
    # ─── FASE 3: PRIMER LOGIN + VERIFICACIÓN ─────────────────────────────────
    s.append(fase_header('3', 'Primer login y verificación', AMBAR))
    s.append(Spacer(1, 0.3 * cm))

    s.append(paso(1, AMBAR, 'Esperá la pantalla de login',
        'Después de Guardar, el sistema arranca solo. Vas a ver una ventana llamada '
        '<b>ERP Universal</b> con un formulario de login. Si tarda más de un minuto, mirá '
        'la sección <b>"Si algo falla"</b> al final.'))

    s.append(paso(2, AMBAR, 'Iniciar sesión',
        'Email y contraseña son los que pusiste en la fase anterior. Clic en <b>Ingresar</b>. '
        'Te lleva al <b>Dashboard</b> automáticamente.'))

    s.append(paso(3, AMBAR, 'Verificación rápida',
        'Para confirmar que todo funciona:'))

    chequeos = [
        'El <b>Dashboard</b> abre y muestra los KPIs (aunque estén en cero, eso es OK en una DB nueva).',
        'En el sidebar izquierdo aparecen <b>Cargar Factura, Comprobantes, Cuentas Corrientes…</b>',
        'Andá a <b>Cargar Factura</b> → la pantalla del OCR debe mostrar la zona para subir archivo.',
        'Andá a <b>Asistente</b> → escribí <i>"hola"</i>; el chatbot debe responder.',
        'Andá a <b>Administración → Empresa</b> y verificá que el nombre quedó como pusiste.',
    ]
    for c in lista_check(chequeos):
        s.append(c)

    s.append(Spacer(1, 0.3 * cm))
    s.append(callout('tip', 'Listo. Ya podés trabajar.',
        'Si los 5 puntos de arriba se cumplen, la instalación es un éxito. Cualquier dato que '
        'cargue otra PC con el mismo DATABASE_URL aparece acá automáticamente — todas las PCs '
        'comparten la misma base.'))

    s.append(Spacer(1, 0.6 * cm))
    # ─── 4. SI ALGO FALLA ────────────────────────────────────────────────────
    s.append(fase_header('!', 'Si algo falla', ROSA))
    s.append(Spacer(1, 0.3 * cm))

    fallas = [
        ('La ventana de la app no aparece después de Guardar.',
         'Esperá 60 seg más. Si sigue sin aparecer, cerrá la app desde la barra de tareas, '
         'volvé a abrirla. Si reincide, abrí la consola de logs (Ctrl+Shift+I dentro de la app) '
         'y mirá si hay error rojo.'),
        ('"Backend no encontrado" al iniciar.',
         'La instalación quedó incompleta. Desinstalá desde Panel de control → Programas, '
         'borrá la carpeta donde lo instalaste y volvé a correr el instalador.'),
        ('"Error al conectar con base de datos".',
         'El DATABASE_URL está mal o la DB Supabase está pausada. Borrá '
         '<font face="Courier-Bold">%APPDATA%\\ERP Universal\\backend.env</font>, abrí la app '
         'de nuevo y volvé a poner los datos.'),
        ('OCR no detecta nada / dice "clave de Gemini inválida".',
         'La GEMINI_API_KEY es incorrecta o expiró. Andá a '
         '<b>Administración → Sistema → Configurar Gemini</b> y pegá una clave nueva.'),
        ('"El puerto 8000 está en uso".',
         'Otro programa lo usa. Cerrá la app, abrí PowerShell y ejecutá '
         '<font face="Courier-Bold">Get-Process python | Stop-Process -Force</font>, '
         'volvé a abrir.'),
        ('Quiero desinstalar todo y empezar de cero.',
         'Panel de control → Programas → <b>ERP Universal</b> → Desinstalar. '
         'Después borrá <font face="Courier-Bold">%APPDATA%\\ERP Universal</font> para limpiar '
         'también la config personal.'),
    ]
    for problema, solucion in fallas:
        bloque = Table([
            [Paragraph(f'<b>{problema}</b>', S_PASO_T)],
            [Paragraph(solucion, S_PASO_D)],
        ], colWidths=[16.5 * cm])
        bloque.setStyle(TableStyle([
            ('BACKGROUND',  (0, 0), (-1, -1), SLATE_BG),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING',(0, 0), (-1, -1), 12),
            ('TOPPADDING',  (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
            ('LINEBEFORE',  (0, 0), (0, -1), 3, ROSA),
        ]))
        s.append(bloque)
        s.append(Spacer(1, 0.15 * cm))

    s.append(Spacer(1, 0.4 * cm))

    # caja final
    cierre_p = Paragraph(
        '<font face="Helvetica-Bold" size="11" color="' + white.hexval() + '">'
        '✓  Lo lograste</font><br/>'
        '<font face="Helvetica" size="9" color="' + SLATE_4.hexval() + '">'
        'El ERP ya está listo en esta PC. Para el siguiente paso, leé '
        '<b>Manual_ERP_Universal.pdf</b> en la misma carpeta — explica cómo cargar facturas, '
        'registrar pagos, ver cuentas corrientes y todas las funciones.</font>',
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
