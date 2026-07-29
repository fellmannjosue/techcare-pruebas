# <--- hecho por claude code: emojis a color en el PDF de notas de mitad de parcial.
"""Soporte de emojis para los PDF generados con reportlab.

Helvetica es una fuente Type1 con codificacion WinAnsi: no tiene glifos de emoji,
asi que un comentario como "...compromiso con la clase. :)" con un emoji real
salia en el PDF como un cuadro negro (■).

Aqui cada emoji se dibuja como una IMAGEN a color recortada de NotoColorEmoji.ttf
(la misma familia que se ve en pantalla) y se exponen versiones "conscientes de
emoji" de stringWidth/drawString, para que el ajuste de linea del comentario siga
cuadrando con lo que de verdad se pinta.

Degradacion elegante: si falta Pillow o la fuente no esta instalada, `_imagen()`
devuelve None, el emoji ocupa 0 y simplemente no se dibuja (el PDF sale sin
emojis, pero nunca con el cuadro negro ni con el texto descuadrado).
"""
import re
from functools import lru_cache

from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

# Lo instala el paquete fonts-noto-color-emoji.
RUTA_FUENTE = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'

# NotoColorEmoji es un font CBDT (bitmap): FreeType solo acepta su rejilla de
# 109 px, cualquier otro tamano lanza "invalid pixel size".
_PX_FUENTE = 109
# Tamano al que se guarda el PNG. 64 px sobra para un emoji de 9 pt impreso a
# 300 dpi (~38 px) y pesa la cuarta parte que el original de 109 px.
_PX_IMAGEN = 64

# Ancho que se le reserva a un emoji, en multiplos del tamano de letra.
_FACTOR_ANCHO = 1.18
# Cuanto baja el cuadro del emoji respecto de la linea base, para que quede
# alineado con las minusculas y no "flotando".
_FACTOR_BASE = 0.22

# Bloques de pictogramas. Se dejan fuera a proposito (c) (r) (tm), que SI existen
# en WinAnsi y deben seguir siendo texto normal.
_BASE = (
    '\U0001F000-\U0001FAFF'   # emoticones, transporte, simbolos y pictogramas
    '☀-➿'           # simbolos misc. + dingbats
    '⬀-⯿'           # estrellas, flechas gruesas, cuadros
    '‼⁉ℹ〰〽㊗㊙'
)
_VS16  = '️'         # selector de presentacion "emoji"
_ZWJ   = '‍'         # zero width joiner (une familias, profesiones...)
_TECLA = '⃣'         # combinador de tecla (1 + esto = 1 con recuadro)
# Modificadores que se pegan al emoji base: VS16, tecla y tonos de piel.
_MOD = f'{_VS16}{_TECLA}\U0001F3FB-\U0001F3FF'

# Un "cluster" = lo que el usuario percibe como UN emoji. Hay que tratarlo como
# unidad indivisible o una bandera/familia se partiria a la mitad al ajustar linea.
_CLUSTER = re.compile(
    '[\U0001F1E6-\U0001F1FF]{2}'                                    # banderas
    f'|[0-9#*]{_VS16}?{_TECLA}'                                     # teclas
    f'|[{_BASE}][{_MOD}]*(?:{_ZWJ}[{_BASE}][{_MOD}]*)*'             # base (+ZWJ)
)


def hay_emoji(texto):
    """True si el texto trae al menos un emoji."""
    return bool(texto) and _CLUSTER.search(texto) is not None


def partir(texto):
    """Trocea el texto en [(es_emoji, trozo), ...] conservando el orden."""
    texto = texto or ''
    partes, i = [], 0
    for m in _CLUSTER.finditer(texto):
        if m.start() > i:
            partes.append((False, texto[i:m.start()]))
        partes.append((True, m.group()))
        i = m.end()
    if i < len(texto):
        partes.append((False, texto[i:]))
    return partes


def unidades(texto):
    """Recorre el texto en unidades indivisibles: un emoji completo o un caracter."""
    for es_emoji, trozo in partir(texto):
        if es_emoji:
            yield trozo
        else:
            yield from trozo


@lru_cache(maxsize=1)
def _fuente():
    """La fuente de emojis, cargada una sola vez (el .ttf pesa ~10 MB)."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    try:
        return ImageFont.truetype(RUTA_FUENTE, _PX_FUENTE)
    except OSError:
        return None


@lru_cache(maxsize=256)
def _imagen(cluster):
    """PNG cuadrado y transparente del emoji, listo para drawImage. None si no se puede."""
    fuente = _fuente()
    if fuente is None:
        return None
    try:
        from PIL import Image, ImageDraw
        lienzo = Image.new('RGBA', (_PX_FUENTE * 2, _PX_FUENTE * 2), (0, 0, 0, 0))
        ImageDraw.Draw(lienzo).text((0, 0), cluster, font=fuente, embedded_color=True)
        caja = lienzo.getbbox()
        if not caja:                      # el font no conoce ese emoji
            return None
        recorte = lienzo.crop(caja)
        # Se centra en un cuadrado para que todos los emojis ocupen igual y no
        # se deformen al escalarlos al tamano de la letra.
        lado = max(recorte.size)
        cuadro = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
        cuadro.paste(recorte, ((lado - recorte.width) // 2, (lado - recorte.height) // 2))
        return ImageReader(cuadro.resize((_PX_IMAGEN, _PX_IMAGEN), Image.LANCZOS))
    except Exception:
        return None


def _ancho_emoji(cluster, size):
    # Si no se va a poder dibujar, tampoco se le reserva ancho: asi medir y
    # pintar siempre coinciden.
    return size * _FACTOR_ANCHO if _imagen(cluster) is not None else 0.0


def ancho(texto, fuente, size):
    """stringWidth consciente de emojis."""
    if not hay_emoji(texto):
        return stringWidth(texto or '', fuente, size)
    total = 0.0
    for es_emoji, trozo in partir(texto):
        total += _ancho_emoji(trozo, size) if es_emoji else stringWidth(trozo, fuente, size)
    return total


def dibujar(pdf, x, y, texto, fuente, size):
    """drawString consciente de emojis. Devuelve la x final."""
    if not hay_emoji(texto):
        pdf.setFont(fuente, size)
        pdf.drawString(x, y, texto or '')
        return x + stringWidth(texto or '', fuente, size)
    for es_emoji, trozo in partir(texto):
        if es_emoji:
            img = _imagen(trozo)
            if img is not None:
                pdf.drawImage(img, x, y - size * _FACTOR_BASE,
                              width=size, height=size, mask='auto')
                x += size * _FACTOR_ANCHO
        else:
            pdf.setFont(fuente, size)
            pdf.drawString(x, y, trozo)
            x += stringWidth(trozo, fuente, size)
    return x
