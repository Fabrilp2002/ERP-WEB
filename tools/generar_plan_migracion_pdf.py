"""
Genera un PDF que explica el Plan de Migración v5.0 (ERP a la nube).
Salida: %USERPROFILE%/Desktop/Plan_Migracion_v5.pdf
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable

# ── paleta ──────────────────────────────────────────────────────────────────
SLATE    = HexColor('#0f172a')
SLATE_2  = HexColor('#334155')
SLATE_3  = HexColor('#64748b')
SLATE_BG = HexColor('#f8fafc')
VERDE    = HexColor('#10b981')
VERDE_BG = HexColor('#d1fae5')
AMBAR    = HexColor('#f59e0b')
AMBAR_BG = HexColor('#fef3c7')
ROJO     = HexColor('#ef4444')
ROJO_BG  = HexColor('#fee2e2')
AZUL     = HexColor('#3b82f6')
AZUL_BG  = HexColor('#dbeafe')
BORDE    = HexColor('#e2e8f0')

ss = getSampleStyleSheet()

S_TITULO = ParagraphStyle('T', parent=ss['Normal'], fontName='Helvetica-Bold',
    fontSize=22, leading=26, textColor=SLATE, spaceAfter=4)
S_SUBT = ParagraphStyle('ST', parent=ss['Normal'], fontName='Helvetica',
    fontSize=11, leading=14, textColor=SLATE_3, spaceAfter=14)
S_H2 = ParagraphStyle('H2', parent=ss['Normal'], fontName='Helvetica-Bold',
    fontSize=15, leading=19, textColor=SLATE, spaceBefore=14, spaceAfter=6)
S_H3 = ParagraphStyle('H3', parent=ss['Normal'], fontName='Helvetica-Bold',
    fontSize=11, leading=14, textColor=SLATE, spaceBefore=8, spaceAfter=3)
S_BODY = ParagraphStyle('B', parent=ss['Normal'], fontName='Helvetica',
    fontSize=10, leading=14, textColor=SLATE_2, alignment=TA_LEFT, spaceAfter=4)
S_BODY_W = ParagraphStyle('BW', parent=S_BODY, textColor=white)
S_KBD = ParagraphStyle('K', parent=ss['Normal'], fontName='Courier',
    fontSize=9, leading=12, textColor=SLATE)
S_PEQUE = ParagraphStyle('P', parent=ss['Normal'], fontName='Helvetica',
    fontSize=8.5, leading=11, textColor=SLATE_3)


def encabezado(canv, doc):
    canv.saveState()
    canv.setFillColor(SLATE)
    canv.rect(0, A4[1] - 1.6 * cm, A4[0], 1.6 * cm, fill=1, stroke=0)
    canv.setFillColor(white)
    canv.setFont('Helvetica-Bold', 11)
    canv.drawString(2 * cm, A4[1] - 1.0 * cm, 'ERP Universal v5.0 — Plan de Migración a la Nube')
    canv.setFont('Helvetica', 9)
    canv.drawRightString(A4[0] - 2 * cm, A4[1] - 1.0 * cm, f'Página {doc.page}')
    canv.setStrokeColor(BORDE)
    canv.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canv.setFillColor(SLATE_3)
    canv.setFont('Helvetica', 8)
    canv.drawString(2 * cm, 1.0 * cm, 'Documento técnico para PM (gfcar) — preparado por Claude Sonnet 4.6')
    canv.drawRightString(A4[0] - 2 * cm, 1.0 * cm, '2026-04-30')
    canv.restoreState()


def callout(titulo, texto, color_borde, color_fondo):
    t = Table([[Paragraph(f'<b>{titulo}</b><br/>{texto}', S_BODY)]],
              colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color_fondo),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBEFORE', (0, 0), (0, -1), 3, color_borde),
    ]))
    return t


def tabla(headers, rows, anchos):
    data = [headers] + rows
    t = Table(data, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SLATE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), SLATE_2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDE),
    ]))
    return t


def construir(story):
    # ── PORTADA ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph('Plan de Migración v5.0', S_TITULO))
    story.append(Paragraph('De aplicación de escritorio a sistema en la nube', S_SUBT))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDE, spaceAfter=14))

    story.append(Paragraph('¿Qué se quiere lograr?', S_H2))
    story.append(Paragraph(
        'Hoy el ERP corre como aplicación de escritorio (un .exe que se instala en cada PC). '
        'La idea de la versión 5.0 es transformarlo en un <b>sistema accesible desde el navegador</b>, '
        'con la base de datos en la nube y una interfaz amigable también para celulares.', S_BODY))
    story.append(Paragraph(
        'Esto se hará en una <b>carpeta separada</b> del proyecto actual — el sistema actual sigue '
        'funcionando intacto durante todo el proceso. No se toca <i>Empresa 1</i> en ningún momento.', S_BODY))

    story.append(Spacer(1, 0.3 * cm))
    story.append(callout(
        'Lo importante en una frase',
        'Pasar el ERP de PC de escritorio a una página web que también sirva en el teléfono, '
        'sin perder ninguna funcionalidad y sin afectar la versión que se usa hoy.',
        AZUL, AZUL_BG))

    # ── SECCIÓN 1 ───────────────────────────────────────────────────────────
    story.append(Paragraph('1. ¿Qué cambia y qué se mantiene?', S_H2))
    story.append(tabla(
        ['Componente', 'Hoy (desktop)', 'Mañana (cloud)'],
        [
            ['Base de datos', 'PostgreSQL local en la PC', 'Supabase (nube)'],
            ['Backend (motor)', 'FastAPI en la PC', 'FastAPI en Railway o Render'],
            ['Frontend (pantallas)', 'Electron (.exe)', 'Vercel (página web)'],
            ['Adjuntos / Logos', 'Carpeta en la PC', 'Supabase Storage'],
            ['OCR (Gemini)', 'Sin cambios', 'Sin cambios'],
            ['Chatbot (Gemini)', 'Sin cambios', 'Sin cambios'],
            ['Login / contraseñas', 'JWT propio', 'JWT propio (no se toca)'],
            ['Modo offline', 'Funciona', 'Funciona igual'],
        ],
        [4.5 * cm, 6 * cm, 6 * cm]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(callout(
        'Lo que NO se toca',
        'El sistema actual (Empresa 1) sigue funcionando. La cuenta Gemini es la misma. '
        'Las contraseñas siguen funcionando igual. El modo sin internet sigue activo.',
        VERDE, VERDE_BG))

    # ── SECCIÓN 2 ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('2. Estrategia: trabajo en paralelo', S_H2))
    story.append(Paragraph(
        'La regla de oro: el proyecto actual <b>no se modifica</b>. Todo el trabajo de v5 ocurre en '
        'una carpeta separada, hermana de la actual:', S_BODY))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Table([[Paragraph(
        'C:\\Users\\gfcar\\Desktop\\IA\\<b>Empresa 1</b> &nbsp;&nbsp;'
        '<font color="#64748b">(actual, no se toca)</font><br/>'
        'C:\\Users\\gfcar\\Desktop\\IA\\<b>ERP_v5_Cloud</b> &nbsp;&nbsp;'
        '<font color="#10b981">(nuevo, ahí se trabaja)</font>',
        S_KBD)]], colWidths=[17 * cm], style=TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), SLATE_BG),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDE),
        ])))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        'Ambos proyectos pueden correr al mismo tiempo en la misma PC durante el desarrollo, '
        'cada uno en su puerto. Solo cuando v5 esté probado y aprobado, se reemplaza al actual.', S_BODY))

    # ── SECCIÓN 3 ───────────────────────────────────────────────────────────
    story.append(Paragraph('3. Pasos de la migración', S_H2))
    pasos = [
        ('1', 'Copiar la carpeta', 'Duplicar Empresa 1 → ERP_v5_Cloud y configurar las claves de Supabase.'),
        ('2', 'Crear la base de datos en la nube', 'Proyecto en Supabase + correr las 10 migraciones SQL existentes + 1 nueva.'),
        ('3', 'Probar la conexión', 'Levantar el backend localmente apuntando a Supabase y testear los endpoints básicos.'),
        ('4', 'Migrar los datos productivos', 'pg_dump del PostgreSQL local → restaurar en Supabase. Verificar conteos.'),
        ('5', 'Auditar Notas de Crédito', 'Confirmar que las NC vinculadas (Fase I) siguen consistentes en la nueva DB.'),
        ('6', 'Adjuntos a la nube', 'Reescribir el módulo de adjuntos para que use Supabase Storage en vez del disco.'),
        ('7', 'Logo de empresa a la nube', 'Mismo patrón que adjuntos.'),
        ('8', 'Limpiar el backend', 'Quitar las rutas estáticas locales y los archivos del build de escritorio.'),
        ('9', 'Frontend al aire', 'Desplegar el frontend a Vercel apuntando al backend.'),
        ('10', 'Backend al aire', 'Desplegar el backend a Railway o Render con un endpoint /health.'),
        ('11', 'Pruebas end-to-end', 'Verificar checklist completo en navegador y celular.'),
        ('12', 'Limpieza final', 'Eliminar todos los archivos del build de escritorio (Electron, NSIS, .bat, .vbs).'),
    ]
    for num, titulo, desc in pasos:
        burbuja = Table([[Paragraph(num, ParagraphStyle('N', parent=S_BODY,
            fontName='Helvetica-Bold', textColor=white, alignment=TA_CENTER))]],
            colWidths=[0.9 * cm], rowHeights=[0.9 * cm])
        burbuja.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), AZUL),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        contenido = Table([[burbuja, Paragraph(f'<b>{titulo}</b><br/>{desc}', S_BODY)]],
                          colWidths=[1.2 * cm, 15.8 * cm])
        contenido.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(KeepTogether(contenido))

    # ── SECCIÓN 4 ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('4. Costos estimados', S_H2))
    story.append(tabla(
        ['Servicio', 'Plan gratuito', 'Plan paga', 'Cuándo conviene pagar'],
        [
            ['Supabase', '500 MB DB + 1 GB Storage', '$25/mes (Pro)', 'Cuando los adjuntos crecen'],
            ['Vercel', 'Hobby (suficiente)', '$20/mes (Pro)', 'Solo si hay mucho tráfico'],
            ['Railway / Render', 'Free con cold start', '$5–7/mes always-on', 'Si molesta el delay del primer request'],
        ],
        [4 * cm, 5 * cm, 4 * cm, 4 * cm]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(callout(
        'Punto de partida: $0/mes',
        'Se puede arrancar sin pagar nada. Si crece la empresa o aparece la incomodidad del cold start, '
        'recién ahí se evalúa pagar (~$5–7/mes en total para tener todo always-on).',
        VERDE, VERDE_BG))

    # ── SECCIÓN 5 ───────────────────────────────────────────────────────────
    story.append(Paragraph('5. Riesgos a tener en cuenta', S_H2))
    story.append(tabla(
        ['Riesgo', 'Probabilidad', 'Mitigación'],
        [
            ['Free tier de Supabase se queda corto', 'Media', 'Monitorear espacio. Pasar a Pro si hace falta.'],
            ['Cold start del backend (1ª request lenta)', 'Alta', 'Plan paga $5/mes o ping cada 5 min.'],
            ['JWT_SECRET reutilizada del local', 'Media', 'Generar una nueva antes del primer deploy.'],
            ['URLs de adjuntos viejos rotas', 'Alta', 'Script de migración + UPDATE SQL.'],
        ],
        [7 * cm, 3 * cm, 7 * cm]))

    # ── SECCIÓN 6 ───────────────────────────────────────────────────────────
    story.append(Paragraph('6. Esfuerzo y cronograma', S_H2))
    story.append(Paragraph(
        'Estimación total: <b>25 a 35 horas de trabajo</b> de desarrollo, distribuidas así:', S_BODY))
    story.append(tabla(
        ['Bloque', 'Horas estimadas'],
        [
            ['Reescritura de adjuntos a Storage', '~8 h'],
            ['Migración de datos productivos', '~4 h'],
            ['Deploy + smoke test', '~4 h'],
            ['Limpieza de archivos desktop', '~3 h'],
            ['UI mobile-first (Bottom Tab Bar + badges)', '~6 h'],
            ['Contingencia / imprevistos', '~10 h'],
        ],
        [12 * cm, 5 * cm]))

    # ── SECCIÓN 7 ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('7. ¿Cómo sabemos que está terminado?', S_H2))
    story.append(Paragraph(
        'La migración se considera <b>completada</b> cuando todos estos puntos pasan:', S_BODY))
    checks = [
        'El backend en Railway/Render responde a /health.',
        'El frontend en Vercel carga en menos de 3 segundos.',
        'Login + JWT funcionan desde un celular real.',
        'Crear una factura + un pago muestra el estado_pago actualizado.',
        'Se puede subir un adjunto y descargarlo desde la nube.',
        'OCR de una factura real funciona end-to-end.',
        'El chatbot devuelve datos reales de la base migrada.',
        'El modo offline (Dexie) sigue encolando sin internet.',
        'Los conteos de filas en Supabase = los del local.',
        'La bitácora del proyecto queda actualizada.',
    ]
    for c in checks:
        story.append(Paragraph(f'☐ &nbsp;&nbsp;{c}', S_BODY))

    # ── SECCIÓN 8 ───────────────────────────────────────────────────────────
    story.append(Paragraph('8. Decisión pendiente', S_H2))
    story.append(callout(
        'Estado actual: PLAN APROBADO, EJECUCIÓN PENDIENTE',
        'El plan ya pasó la revisión técnica (Ultraplan) y está documentado completo en '
        'PLAN_MIGRACION_V5.md. Falta tu decisión de cuándo arrancar la ejecución. '
        'Mientras tanto, todo el trabajo registrado en v4 (instalador, fixes, etc.) '
        'sigue funcionando sin cambios.',
        AMBAR, AMBAR_BG))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph('Documentos relacionados', S_H3))
    story.append(Paragraph(
        '• <b>PLAN_MIGRACION_V5.md</b> — Plan técnico completo con todas las secciones.<br/>'
        '• <b>BITACORA_COLABORATIVA.md</b> — Registro de turnos del equipo.<br/>'
        '• <b>docs/roadmap/PLAN_MIGRACION_V5_PENDIENTE.md</b> — Registro de este plan como tarea futura.',
        S_BODY))


def main():
    desktop = Path(os.path.expanduser('~')) / 'Desktop'
    desktop.mkdir(parents=True, exist_ok=True)
    out = desktop / 'Plan_Migracion_v5.pdf'

    doc = BaseDocTemplate(str(out), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.2 * cm, bottomMargin=1.8 * cm)

    frame = Frame(2 * cm, 1.8 * cm,
        A4[0] - 4 * cm, A4[1] - 4 * cm,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
        showBoundary=0)
    doc.addPageTemplates([PageTemplate(id='P', frames=[frame], onPage=encabezado)])

    story = []
    construir(story)
    doc.build(story)
    print(f'PDF generado: {out}')


if __name__ == '__main__':
    main()
