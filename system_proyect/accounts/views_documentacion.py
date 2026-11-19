# accounts/views_documentacion.py
# <--- hecho por claude code (09-nov-2026, pedido del usuario: "las guías súbelas siempre en TechCare, en Configuración")
"""Configuración → Documentación: visor de SOLO LECTURA de la carpeta `docs/` del repositorio.

- Solo superusuario: incluye la matriz de riesgos y los procedimientos de seguridad.
- Lista los .md (y .conf/.txt de `docs/`), agrupados por carpeta. Toda guía nueva que se agregue a
  `docs/` aparece sola, sin tocar código.
- Seguridad del visor:
  * el documento se elige SOLO de la lista armada al recorrer `docs/` (nunca se abre una ruta que
    mande el navegador → sin path traversal);
  * Markdown con `markdown-it-py` y `html=False`: el HTML crudo dentro del .md se muestra como texto
    (sin XSS); los enlaces `javascript:` los descarta markdown-it;
  * los enlaces relativos a otro .md se convierten en enlaces de este visor.
"""
import posixpath
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

DOCS_DIR = Path(settings.BASE_DIR).parent / 'docs'
_EXT = ('.md', '.conf', '.txt')
_TAM_MAX = 2 * 1024 * 1024


def _listar():
    """{ruta_relativa_posix: Path} de los documentos visibles."""
    docs = {}
    if not DOCS_DIR.is_dir():
        return docs
    raiz = DOCS_DIR.resolve()
    for p in sorted(DOCS_DIR.rglob('*')):
        try:
            real = p.resolve()
        except OSError:
            continue
        if not p.is_file() or p.suffix.lower() not in _EXT or raiz not in real.parents:
            continue   # fuera de docs/ (enlaces simbólicos) o tipo no permitido
        docs[p.relative_to(DOCS_DIR).as_posix()] = p
    return docs


def _titulo(path):
    if path.suffix.lower() == '.md':
        try:
            with path.open(encoding='utf-8', errors='replace') as f:
                for linea in f:
                    if linea.startswith('# '):
                        return linea[2:].strip()
        except OSError:
            pass
    return path.name


def _ancla(rel):
    return 'doc-' + ''.join(c if c.isalnum() else '-' for c in rel)


def _render(rel, path, docs, pdf=None):
    """pdf=None → visor web; pdf='uno' → sin enlaces internos; pdf='todos' → enlaces a anclas del PDF combinado."""
    from markdown_it import MarkdownIt
    texto = path.read_text(encoding='utf-8', errors='replace')
    if path.suffix.lower() != '.md':
        texto = '```\n' + texto.replace('```', "'''") + '\n```'
    md = MarkdownIt('commonmark', {'html': False, 'linkify': False}).enable('table').enable('strikethrough')
    env = {}
    tokens = md.parse(texto, env)
    base = posixpath.dirname(rel)
    url = reverse('settings_documentacion')

    def _ajustar(toks):
        for t in toks:
            if t.type == 'link_open':
                href = t.attrGet('href') or ''
                if href and '://' not in href and not href.startswith(('#', 'mailto:', '/')):
                    destino = href.split('#', 1)[0]
                    destino = posixpath.normpath(posixpath.join(base, destino)) if destino else rel
                    if destino.endswith('/'):
                        destino = destino.rstrip('/')
                    if destino not in docs and destino + '/README.md' in docs:
                        destino = destino + '/README.md'
                    if destino in docs:
                        if pdf == 'todos':
                            t.attrSet('href', '#' + _ancla(destino))
                        elif pdf:
                            t.attrs.pop('href', None)
                        else:
                            t.attrSet('href', url + '?' + urlencode({'doc': destino}))
                elif '://' in href:
                    t.attrSet('target', '_blank')
                    t.attrSet('rel', 'noopener noreferrer')
            if t.children:
                _ajustar(t.children)
    _ajustar(tokens)
    return md.renderer.render(tokens, md.options, env)


from django.contrib.auth.decorators import login_required   # noqa: E402


@login_required
def settings_documentacion(request):
    if not request.user.is_superuser:
        return redirect('settings_perfil')
    from .views import _settings_ctx
    docs = _listar()
    grupos = {}
    for rel, p in docs.items():
        carpeta = posixpath.dirname(rel) or 'docs'
        grupos.setdefault(carpeta, []).append({'rel': rel, 'titulo': _titulo(p)})
    elegido = request.GET.get('doc') or ('seguridad/README.md' if 'seguridad/README.md' in docs else next(iter(docs), ''))
    html = ''
    if elegido:
        if elegido not in docs:
            raise Http404('Documento no encontrado')
        p = docs[elegido]
        if p.stat().st_size > _TAM_MAX:
            raise Http404('Documento demasiado grande')
        html = _render(elegido, p, docs)
    ctx = _settings_ctx(request, 'documentacion')
    ctx.update({
        'doc_grupos': sorted(grupos.items(), key=lambda kv: ({'manuales': 0, 'seguridad': 1}.get(kv[0].split('/')[0], 2), kv[0])),
        'doc_actual': elegido,
        'doc_titulo': _titulo(docs[elegido]) if elegido else '',
        'doc_html': html,
        'doc_total': len(docs),
        'doc_carpeta_actual': posixpath.dirname(elegido) or 'docs',
        'doc_carpeta_raiz': elegido.split('/', 1)[0] if '/' in elegido else '',
    })
    return render(request, 'accounts/settings_documentacion.html', ctx)


# <--- hecho por claude code (10-nov-2026, pedido del usuario: "agrega una opción para descargar en PDF"):
# ?doc=<rel> → PDF de ese documento; ?carpeta=<carpeta> → todos los de la carpeta en un solo PDF (README primero).
# WeasyPrint con el CSS y el logo del DISCO (finders), nunca por HTTP (ver AGENTS.md, trampa de WeasyPrint).
@login_required
def settings_documentacion_pdf(request):
    if not request.user.is_superuser:
        return redirect('settings_perfil')
    import datetime
    from django.contrib.staticfiles import finders
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from weasyprint import CSS, HTML
    docs = _listar()
    rel = request.GET.get('doc') or ''
    carpeta = request.GET.get('carpeta') or ''
    if rel:
        if rel not in docs:
            raise Http404('Documento no encontrado')
        elegidos, modo = [rel], 'uno'
        nombre = posixpath.splitext(rel)[0].replace('/', '_')
        titulo = _titulo(docs[rel])
    elif carpeta:
        elegidos = sorted((r for r in docs if r == carpeta + '/README.md' or r.startswith(carpeta + '/')),
                          key=lambda r: (posixpath.dirname(r) != carpeta, posixpath.dirname(r),
                                         posixpath.basename(r) != 'README.md', r))
        if not elegidos:
            raise Http404('Carpeta sin documentos')
        modo, nombre = 'todos', carpeta.replace('/', '_') + '_completo'
        titulo = _titulo(docs[elegidos[0]]) if elegidos[0].endswith('README.md') else carpeta
    else:
        raise Http404('Falta el documento')
    secciones = []
    for r in elegidos:
        p = docs[r]
        if p.stat().st_size > _TAM_MAX:
            continue
        secciones.append({'rel': r, 'ancla': _ancla(r), 'titulo': _titulo(p), 'html': _render(r, p, docs, pdf=modo)})
    logo = finders.find('mantenimiento_mecanico/logo_ana.png')
    html = render_to_string('accounts/documentacion_pdf.html', {
        'titulo': titulo, 'secciones': secciones, 'varios': modo == 'todos',
        'logo': ('file://' + logo) if logo else '', 'fecha': datetime.date.today().strftime('%d/%m/%Y'),
    })
    hoja = finders.find('accounts/css/documentacion_pdf.css')
    pdf = HTML(string=html).write_pdf(stylesheets=[CSS(filename=hoja)] if hoja else None)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="TechCare_%s.pdf"' % ''.join(c for c in nombre if c.isalnum() or c in '_-')
    return resp
