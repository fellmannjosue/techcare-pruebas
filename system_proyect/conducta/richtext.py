# conducta/richtext.py
# <--- hecho por claude code (03-nov-2026): comentario con formato LIMITADO (negrita + 2 tamaños).
# Subconjunto permitido, tanto para guardar como para mostrar y para el PDF.
#   negrita  -> <b>…</b>
#   grande   -> <span class="tc-fs-lg">…</span>
#   pequeño  -> <span class="tc-fs-sm">…</span>
#   salto    -> <br>
# Nada más. Así evitamos XSS y que se rompa el PDF.
import html as _html
import re
from html.parser import HTMLParser

_SPAN_CLASES = {'tc-fs-lg', 'tc-fs-sm'}


class _Sanitizador(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.pila = []   # etiquetas que SÍ abrimos (para cerrar bien)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ('b', 'strong'):
            self.out.append('<b>'); self.pila.append('b')
        elif tag == 'br':
            self.out.append('<br>')
        elif tag == 'span':
            clase = dict(attrs).get('class', '') or ''
            clases = set(clase.split())
            elegido = next((c for c in ('tc-fs-lg', 'tc-fs-sm') if c in clases), None)
            if elegido:
                self.out.append('<span class="%s">' % elegido); self.pila.append('span')
            else:
                self.pila.append('')   # span sin clase válida: no emite, pero marca para cerrar
        else:
            self.pila.append('')       # etiqueta no permitida: se ignora, se conserva el texto

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'br':
            return
        # cerrar la última etiqueta que abrimos realmente
        while self.pila:
            abierta = self.pila.pop()
            if abierta == 'b':
                self.out.append('</b>'); return
            if abierta == 'span':
                self.out.append('</span>'); return
            # abierta == '' (ignorada): seguir buscando
            return

    def handle_data(self, data):
        self.out.append(_html.escape(data))

    def resultado(self):
        # cerrar lo que quedara abierto
        for abierta in reversed(self.pila):
            if abierta == 'b':
                self.out.append('</b>')
            elif abierta == 'span':
                self.out.append('</span>')
        self.pila = []
        return ''.join(self.out)


def sanitizar(valor):
    """Deja solo <b>, <span class="tc-fs-lg|tc-fs-sm"> y <br>. Devuelve '' si queda vacío."""
    if not valor:
        return valor or ''
    valor = valor.replace('\r\n', '\n').replace('\r', '\n')
    p = _Sanitizador()
    p.feed(valor)
    p.close()
    limpio = p.resultado().strip()
    # si al quitar el formato no queda texto, devolver vacío
    if not a_texto_plano(limpio).strip():
        return ''
    return limpio


def a_texto_plano(valor):
    """Quita todo el formato y devuelve texto plano (para PNG/WhatsApp y comparaciones)."""
    if not valor:
        return ''
    t = re.sub(r'<br\s*/?>', '\n', valor, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    return _html.unescape(t)


def a_markup_pdf(valor):
    """Convierte el subconjunto al marcado de reportlab Paragraph (<b>, <font size=…>, <br/>)."""
    if not valor:
        return ''
    t = valor
    t = t.replace('<span class="tc-fs-lg">', '<font size="13">')
    t = t.replace('<span class="tc-fs-sm">', '<font size="8">')
    t = t.replace('</span>', '</font>')
    t = re.sub(r'<br\s*/?>', '<br/>', t, flags=re.I)
    return t


def tiene_formato(valor):
    """True si el comentario usa alguna etiqueta de formato (para decidir cómo dibujarlo)."""
    return bool(valor) and bool(re.search(r'<(b|span|font|br)\b', valor, flags=re.I))
