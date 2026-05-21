"""
Preprocesado de imagen para mejorar la extracción de datos por Gemini Vision.

Pipeline:
  1. Decodificar bytes → ndarray
  2. Convertir a escala de grises
  3. Deskew (corregir rotación)
  4. CLAHE (realza contraste en manuscritos con tinta clara)
  5. Denoise ligero (quita compresión JPEG / sombras CamScanner)
  6. Re-encodear a PNG

Todo con OpenCV (opencv-python-headless) + NumPy. Sin GPU, ~150ms por factura A4.
El pipeline es tolerante a errores: si algo falla, devuelve la imagen original
intacta para no bloquear el flujo OCR.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


# ── Pipeline ─────────────────────────────────────────────────────────────────

def mejorar_imagen(imagen_bytes: bytes) -> bytes:
    """
    Aplica deskew + CLAHE + denoise suave a una imagen.

    Args:
        imagen_bytes: imagen codificada (PNG/JPEG/WebP).

    Returns:
        PNG codificado (más procesable por Gemini).
        Si algún paso falla, devuelve los bytes originales.
    """
    try:
        arr = np.frombuffer(imagen_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            log.warning("preprocesado: cv2.imdecode devolvió None, uso imagen original")
            return imagen_bytes

        # 1) gris
        gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2) deskew
        gris = _deskew(gris)

        # 3) CLAHE (realza trazos manuscritos claros sin quemar papel)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        gris = clahe.apply(gris)

        # 4) denoise suave — h=10 preserva detalle fino de letras
        gris = cv2.fastNlMeansDenoising(gris, h=10, templateWindowSize=7, searchWindowSize=21)

        # 5) re-encode a PNG (lossless, ideal para Gemini Vision)
        ok, buf = cv2.imencode(".png", gris, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        if not ok:
            log.warning("preprocesado: cv2.imencode falló, uso imagen original")
            return imagen_bytes

        return buf.tobytes()

    except Exception as e:
        # En producción nunca bloqueamos el flujo por un fallo de limpieza
        log.warning("preprocesado falló (%s); devuelvo imagen sin procesar", e)
        return imagen_bytes


# ── Deskew ───────────────────────────────────────────────────────────────────

def _deskew(gris: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """
    Corrige la rotación de un documento fotografiado.

    Usa minAreaRect sobre los píxeles de tinta para estimar el ángulo dominante.
    Si el ángulo detectado supera ±max_angle (probablemente ruido), no rota.
    """
    try:
        # Binarizamos invertido: tinta = 255, papel = 0
        _, bw = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        coords = cv2.findNonZero(bw)
        if coords is None or len(coords) < 500:
            return gris  # Imagen casi vacía, no arriesgamos

        angle = cv2.minAreaRect(coords)[-1]
        # minAreaRect devuelve en [-90, 0); normalizamos a [-45, 45]
        if angle < -45:
            angle = 90 + angle

        if abs(angle) < 0.3 or abs(angle) > max_angle:
            return gris  # Ya está derecho, o el ángulo es probablemente basura

        h, w = gris.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(
            gris, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception as e:
        log.debug("deskew falló (%s); devuelvo imagen sin rotar", e)
        return gris
