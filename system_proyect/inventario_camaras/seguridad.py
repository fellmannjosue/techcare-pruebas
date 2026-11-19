# <--- hecho por claude code (seguridad 05-nov-2026): validaciones del módulo de cámaras (firma remota, firmas en PNG, fotos, texto del PDF).
import base64
import os
import uuid
from datetime import timedelta
from io import BytesIO
from xml.sax.saxutils import escape as _xml_escape

from django.core.files.base import ContentFile
from django.utils import timezone

# ── Link de firma remota del técnico ─────────────────────────────────────────
# Sin migración: el link solo sirve si la ficha se marcó como enviada (firma_solicitada, lo pone el botón
# "Enviar link") y durante FIRMA_LINK_DIAS desde la última vez que se envió o se modificó la ficha
# (marcar_firma_solicitada refresca fecha_modificado, así que volver a enviar el link lo renueva).
FIRMA_LINK_DIAS = 7


def link_firma_vigente(rec, ahora=None):
    if rec.firmado or not rec.firma_solicitada:
        return False
    ref = rec.fecha_modificado or rec.fecha_creado
    if ref is None:
        return False
    ahora = ahora or timezone.now()
    return ahora - ref <= timedelta(days=FIRMA_LINK_DIAS)


# ── Firmas dibujadas en el canvas (PNG en data URL) ──────────────────────────
FIRMA_PREFIJO = 'data:image/png;base64,'
FIRMA_MAX_CHARS = 700_000        # ~500 KB de PNG; un canvas de firma real ocupa 10-60 KB
FIRMA_LADO_MAX = 4000            # px; evita "bombas" de descompresión


def validar_firma_png(data):
    """Devuelve la firma como data URL PNG RE-CODIFICADA por Pillow. Lanza ValueError con el motivo.
    Solo acepta lo que manda el canvas (image/png en base64): ni SVG, ni otros formatos, ni texto."""
    from PIL import Image
    data = (data or '').strip()
    if not data.startswith(FIRMA_PREFIJO):
        raise ValueError('Debes firmar antes de enviar.')
    if len(data) > FIRMA_MAX_CHARS:
        raise ValueError('La firma es demasiado grande.')
    try:
        raw = base64.b64decode(data[len(FIRMA_PREFIJO):], validate=True)
        img = Image.open(BytesIO(raw))
        if img.format != 'PNG':
            raise ValueError
        ancho, alto = img.size
        if not (0 < ancho <= FIRMA_LADO_MAX and 0 < alto <= FIRMA_LADO_MAX):
            raise ValueError
        img.verify()
        img = Image.open(BytesIO(raw))
        img.load()
    except Exception:
        raise ValueError('La firma no es una imagen válida.')
    if img.getbbox() is None:   # canvas vacío (todo transparente / negro)
        raise ValueError('Debes firmar antes de enviar.')
    out = BytesIO()
    img.save(out, format='PNG', optimize=True)
    return FIRMA_PREFIJO + base64.b64encode(out.getvalue()).decode('ascii')


# ── Fotos de evidencia ───────────────────────────────────────────────────────
FOTO_EXT_OK = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
FOTO_FORMATOS_OK = ('JPEG', 'MPO', 'PNG', 'WEBP', 'GIF')
FOTO_MAX_BYTES = 10 * 1024 * 1024
FOTO_MAX_POR_ENVIO = 5
FOTO_MAX_PIXELES = 60_000_000    # 48 MP de un celular caben; más es sospechoso
FOTO_LADO_MAX = 1600             # se reduce a 1600 px y se guarda como JPEG


def procesar_foto(f):
    """Valida extensión, tamaño y que sea una imagen real (Pillow) y la re-codifica a JPEG <= 1600 px
    con nombre aleatorio. Devuelve un ContentFile para el ImageField. Lanza ValueError con el motivo."""
    from PIL import Image, ImageOps
    nombre = os.path.basename(getattr(f, 'name', '') or 'foto')
    if os.path.splitext(nombre.lower())[1] not in FOTO_EXT_OK:
        raise ValueError(f'«{nombre}»: formato no permitido (usa JPG, PNG o WEBP).')
    if (getattr(f, 'size', 0) or 0) > FOTO_MAX_BYTES:
        raise ValueError(f'«{nombre}» pesa más de {FOTO_MAX_BYTES // (1024 * 1024)} MB.')
    try:
        f.seek(0)
        img = Image.open(f)
        if img.format not in FOTO_FORMATOS_OK:
            raise ValueError
        ancho, alto = img.size
        if ancho * alto > FOTO_MAX_PIXELES:
            raise ValueError
        img.verify()
        f.seek(0)
        img = Image.open(f)
        img.thumbnail((FOTO_LADO_MAX, FOTO_LADO_MAX))
        img = ImageOps.exif_transpose(img)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
            fondo = Image.new('RGB', img.size, (255, 255, 255))
            fondo.paste(img, mask=img.split()[3])
            img = fondo
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        out = BytesIO()
        img.save(out, format='JPEG', quality=85, optimize=True)
    except Exception:
        raise ValueError(f'«{nombre}» no es una imagen válida.')
    return ContentFile(out.getvalue(), name=f'{uuid.uuid4().hex}.jpg')


def procesar_fotos(archivos):
    """Lista de UploadedFile -> lista de ContentFile ya validados. Lanza ValueError (nada se guarda)."""
    archivos = list(archivos or [])
    if len(archivos) > FOTO_MAX_POR_ENVIO:
        raise ValueError(f'Puedes subir hasta {FOTO_MAX_POR_ENVIO} fotos por vez.')
    return [procesar_foto(f) for f in archivos]


# ── Texto del usuario dentro de un Paragraph de reportlab ────────────────────
# Paragraph interpreta marcado (<img src=...>, <a href=...>, <font>): sin escapar, un texto podía incrustar
# en el PDF cualquier imagen del disco o hacer que el servidor pidiera una URL interna.
def texto_pdf(valor, multilinea=False):
    s = _xml_escape(str(valor))
    return s.replace('\r\n', '\n').replace('\n', '<br/>') if multilinea else s
