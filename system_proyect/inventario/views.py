# ==============================================================
# INVENTARIO – VISTAS COMPLETAS Y COMPATIBLES CON AJAX + MODALES
# ==============================================================

import datetime
import json   # <--- hecho por claude code (13-oct-2026): alta de categorías por JSON
import io
import qrcode
from PIL import Image

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import F, Value, CharField
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps as _wraps


# <--- hecho por claude code (seguridad): las vistas solo tenían @login_required, así que
# CUALQUIER usuario autenticado (p. ej. un maestro) entraba a /inventario/ por URL directa
# aunque el menú no se lo mostrara. Este candado usa el MISMO criterio que `nav_inventory`
# del context processor: superusuario, permiso inventario.view_item, o grupo 'inventario'.
def _inventario_required(view):
    @_wraps(view)
    @login_required
    def _w(request, *args, **kwargs):
        u = request.user
        if u.is_superuser or u.has_perm('inventario.view_item') or u.groups.filter(name='inventario').exists():
            return view(request, *args, **kwargs)
        raise PermissionDenied('No tiene acceso al módulo de Inventario.')
    return _w


from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import cm

from .models import (
    InventoryItem,
    Computadora, Televisor, Impresora, Router, DataShow, Monitor,
    ModeloMonitor,
    ModeloTelevisor, GradoTelevisor, AreaTelevisor,
    ModeloComputadora, SerieComputadora, AsignadoAComputadora,
    ItemGeneral, CategoriaGeneral, AREAS_GENERAL,   # <--- hecho por claude code (13-oct-2026)
    AreaComputadora, GradoComputadora, SubtipoGradoComputadora, EdificioComputadora,
)

from .forms import (
    CategoryUpdateForm,
    ComputadoraForm,
    TelevisorForm,
    ImpresoraForm,
    RouterForm,
    DataShowForm,
    ComputadoraFilterForm,
    MonitorForm
)

# ==============================================================
# QR PARA FICHAS
# ==============================================================

def _get_asset_id(tipo, pk):
    tipo = tipo.lower()
    mapa = {
        'computadora': Computadora,
        'televisor':   Televisor,
        'impresora':   Impresora,
        'router':      Router,
        'datashow':    DataShow,
        'monitor':     Monitor,
    }
    modelo = mapa.get(tipo)
    if modelo:
        obj = modelo.objects.filter(pk=pk).first()
        if obj:
            return obj.asset_id
    return f"{tipo.upper()}-{pk}"


def descargar_qr(request, tipo, pk):
    from PIL import ImageDraw, ImageFont

    path    = reverse("inventario:download_model_pdf", args=[tipo.lower(), pk])
    pdf_url = f"https://servicios.ana-hn.org:437{path}"
    asset_id = _get_asset_id(tipo, pk)

    qr_img = qrcode.make(pdf_url).convert("RGB")
    qr_w, qr_h = qr_img.size

    # Barra inferior con el asset_id
    bar_h    = 48
    total_h  = qr_h + bar_h
    canvas   = Image.new("RGB", (qr_w, total_h), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), asset_id, font=font)
    text_w = bbox[2] - bbox[0]
    x = (qr_w - text_w) // 2
    y = qr_h + (bar_h - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), asset_id, fill="black", font=font)

    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)

    return HttpResponse(
        buffer.read(),
        content_type="image/jpeg",
        headers={"Content-Disposition": f'attachment; filename="qr_{asset_id}.jpg"'}
    )

# ==============================================================
# DASHBOARD
# ==============================================================

@_inventario_required
def dashboard(request):
    # <--- hecho por claude code (28-sep-2026): el Panel de Inventario (8 tiles) se retiró; lo reemplaza el hub
    # Control y Servicio Técnico. La URL se conserva como redirección para enlaces guardados.
    return redirect('servicio_tecnico:hub')

# ==============================================================
# POR CATEGORÍA
# ==============================================================

@_inventario_required
def inventario_por_categoria(request):
    year = datetime.datetime.now().year

    if request.method == "POST":
        form = CategoryUpdateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada con éxito.")
            return redirect("inventario:inventario_por_categoria")
        messages.error(request, "Error al actualizar la categoría.")
    else:
        form = CategoryUpdateForm()

    from django.db.models import Q as _Q
    mapping = [
        (Computadora, "Computadora", "modelo",  "computadora"),
        (Televisor,   "Televisor",   "modelo",  "televisor"),
        (Impresora,   "Impresora",   "nombre",  "impresora"),
        (Router,      "Router",      "modelo",  "router"),
        (DataShow,    "DataShow",    "serie",   "datashow"),
        (Monitor,     "Monitor",     "modelo",  "monitor"),
    ]

    grupos = []
    sin_cat = []
    for Model, label, field, tipo_key in mapping:
        qs = list(Model.objects.annotate(
            tipo=Value(label, output_field=CharField()),
            tipo_key=Value(tipo_key, output_field=CharField()),
            descripcion=F(field),
            categoria=F("category"),
        ).values("tipo", "tipo_key", "id", "descripcion", "categoria"))
        categorized = [i for i in qs if i["categoria"]]
        uncategorized = [i for i in qs if not i["categoria"]]
        if categorized:
            grupos.append({"tipo": label, "tipo_key": tipo_key, "items": categorized})
        sin_cat.extend(uncategorized)

    return render(request, "inventario/inventario_por_categoria.html", {
        "grupos":   grupos,
        "sin_cat":  sin_cat,
        "form":     form,
        "year":     year,
        "category_choices": InventoryItem.CATEGORY_CHOICES,
    })

# ==============================================================
# INVENTARIOS (CREATE + LIST)
# ==============================================================

_PREFIJOS_COMP = {
    'estandar': 'IDANACOMP',
    'lab_bl':   'IDANALABBL',
    'lab_col':  'IDANALABCOL',
    'informatica': 'IDCFPLAB',
}

def _siguiente_asset_id_computadora(prefijo_key='estandar'):
    prefix = _PREFIJOS_COMP.get(prefijo_key, 'IDANACOMP')
    ultimo = Computadora.objects.filter(
        asset_id__startswith=prefix
    ).order_by('-asset_id').values_list('asset_id', flat=True).first()
    if ultimo:
        try:
            n = int(ultimo[len(prefix):])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{prefix}{n+1:03d}"


@_inventario_required
def inventario_computadoras(request):
    if request.method == "POST":
        form = ComputadoraForm(request.POST)
        if form.is_valid():
            comp = form.save(commit=False)
            prefijo_key = request.POST.get('id_prefix', 'estandar')
            if prefijo_key not in _PREFIJOS_COMP:
                prefijo_key = 'estandar'
            comp.asset_id = _siguiente_asset_id_computadora(prefijo_key)
            ip_post = request.POST.get('ip', '').strip()
            comp.ip = ip_post if ip_post and ip_post != '0.0.0.0' else '0.0.0.0'
            serie_post = request.POST.get('serie', '').strip()
            comp.serie = serie_post if serie_post and serie_post != '—' else ''
            if prefijo_key == 'estandar':
                comp.edificio = request.POST.get('edificio', '').strip() or None
            else:
                comp.edificio = None
            grado_subtipo = request.POST.get('grado_subtipo', '').strip()
            if comp.grado == 'Otros' and grado_subtipo:
                comp.grado = f'Otros/{grado_subtipo}'
            comp.save()
            return redirect("inventario:inventario_computadoras")
    else:
        form = ComputadoraForm()

    total_comp = Computadora.objects.count()
    prefijos_tabs = [
        {"key": "IDANACOMP",   "label": "General",   "count": Computadora.objects.filter(asset_id__startswith="IDANACOMP").count()},
        {"key": "IDANALABBL",  "label": "Lab BL",    "count": Computadora.objects.filter(asset_id__startswith="IDANALABBL").count()},
        {"key": "IDANALABCOL", "label": "Lab COL",   "count": Computadora.objects.filter(asset_id__startswith="IDANALABCOL").count()},
        {"key": "IDCFPLAB",    "label": "Lab CFP",   "count": Computadora.objects.filter(asset_id__startswith="IDCFPLAB").count()},
    ]

    return render(request, "inventario/inventario_computadoras.html", {
        "form":              form,
        "next_id":           _siguiente_asset_id_computadora('estandar'),
        "next_id_bl":        _siguiente_asset_id_computadora('lab_bl'),
        "next_id_col":       _siguiente_asset_id_computadora('lab_col'),
        "next_id_inf":       _siguiente_asset_id_computadora('informatica'),
        "computadoras":      Computadora.objects.order_by("-id"),
        "edificios":         EdificioComputadora.objects.all(),
        "subtipos_otros":    SubtipoGradoComputadora.objects.all(),
        "total_comp":        total_comp,
        "prefijos_tabs":     prefijos_tabs,
    })


@_inventario_required
def computadoras_list(request):
    year = datetime.datetime.now().year
    form = ComputadoraFilterForm(request.GET or None)
    qs = Computadora.objects.order_by("-fecha_instalado")

    if form.is_valid():
        cd = form.cleaned_data
        for field, val in cd.items():
            if val:
                qs = qs.filter(**{f"{field}__icontains": val})

    return render(request, "inventario/filtro_computadoras.html", {
        "form": form,
        "computadoras": qs,
        "year": year
    })


def _siguiente_asset_id_televisor():
    prefix = 'IDANATV'
    ultimo = Televisor.objects.filter(
        asset_id__startswith=prefix
    ).order_by('-asset_id').values_list('asset_id', flat=True).first()
    if ultimo:
        try:
            n = int(ultimo[len(prefix):])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{prefix}{n+1:03d}"


@_inventario_required
def inventario_televisores(request):
    if request.method == "POST":
        form = TelevisorForm(request.POST)
        if form.is_valid():
            tv = form.save(commit=False)
            tv.asset_id = _siguiente_asset_id_televisor()
            tv.serie    = 'Pendiente'
            tv.ip       = '0.0.0.0'
            tv.save()
            return redirect("inventario:inventario_televisores")
    else:
        form = TelevisorForm()

    return render(request, "inventario/inventario_televisores.html", {
        "form":       form,
        "next_id":    _siguiente_asset_id_televisor(),
        "televisores": Televisor.objects.order_by("-id"),
    })


# <--- hecho por claude code: Asset ID autoincremental de impresoras (ANAIMP-001), mirror de _siguiente_asset_id_televisor
def _siguiente_asset_id_impresora():
    prefix = 'ANAIMP-'
    ultimo = Impresora.objects.filter(
        asset_id__startswith=prefix
    ).order_by('-asset_id').values_list('asset_id', flat=True).first()
    if ultimo:
        try:
            n = int(ultimo[len(prefix):])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{prefix}{n+1:03d}"


@_inventario_required
def inventario_impresoras(request):
    year = datetime.datetime.now().year

    if request.method == "POST":
        form = ImpresoraForm(request.POST)
        if form.is_valid():
            imp = form.save(commit=False)
            imp.asset_id = _siguiente_asset_id_impresora()  # <--- hecho por claude code: ID auto en el servidor
            imp.save()
            return redirect("inventario:inventario_impresoras")
    else:
        form = ImpresoraForm()

    return render(request, "inventario/inventario_impresoras.html", {
        "form": form,
        "year": year,
        "next_id": _siguiente_asset_id_impresora(),  # <--- hecho por claude code: mostrar el próximo ID
        "impresoras": Impresora.objects.order_by("-id")
    })


@_inventario_required
def inventario_routers(request):
    year = datetime.datetime.now().year

    if request.method == "POST":
        form = RouterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("inventario:inventario_routers")
    else:
        form = RouterForm()

    return render(request, "inventario/inventario_routers.html", {
        "form": form,
        "year": year,
        "routers": Router.objects.order_by("-id")
    })


@_inventario_required
def inventario_datashows(request):
    year = datetime.datetime.now().year

    if request.method == "POST":
        form = DataShowForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("inventario:inventario_datashows")
    else:
        form = DataShowForm()

    return render(request, "inventario/inventario_datashows.html", {
        "form": form,
        "year": year,
        "datashows": DataShow.objects.order_by("-id")
    })


@_inventario_required
def inventario_monitores(request):
    import re as _re
    year = datetime.datetime.now().year

    if request.method == "POST":
        form = MonitorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("inventario:inventario_monitores")
    else:
        form = MonitorForm()

    # Prefijos de ID y siguiente número disponible
    prefijos = [
        ("ANAMONI",    "General"),
        ("LABBLMONI",  "Lab BL"),
        ("LABCOLMONI", "Lab COL"),
        ("CFPINFO",    "Lab Informática"),
    ]
    next_ids = {}
    for prefix, _ in prefijos:
        existing = Monitor.objects.filter(asset_id__startswith=prefix).values_list('asset_id', flat=True)
        nums = [int(m.group()) for aid in existing for m in [_re.search(r'\d+$', aid)] if m]
        next_ids[prefix] = f"{prefix}{(max(nums) + 1 if nums else 1):03d}"

    # Modelos de monitores desde catálogo admin
    modelos_monitor = list(ModeloMonitor.objects.values_list('nombre', flat=True))

    # Computadoras para selects
    computadoras = list(Computadora.objects.order_by('asset_id').values('id', 'asset_id', 'modelo', 'serie', 'asignado_a', 'area', 'grado'))

    # Asset IDs de computadoras ya vinculadas a un monitor (para advertencia de duplicado)
    labs_usados    = set(Monitor.objects.exclude(laboratorio='').exclude(laboratorio__isnull=True).values_list('laboratorio', flat=True))
    asignados_usados = set(Monitor.objects.exclude(asignado_a='').exclude(asignado_a__isnull=True).values_list('asignado_a', flat=True))

    return render(request, "inventario/inventario_monitores.html", {
        "form":              form,
        "year":              year,
        "monitores":         Monitor.objects.order_by("-id"),
        "prefijos":          prefijos,
        "next_ids":          next_ids,
        "modelos_monitor":   modelos_monitor,
        "computadoras":      computadoras,
        "labs_usados":       list(labs_usados),
        "asignados_usados":  list(asignados_usados),
    })


# ==============================================================
# INVENTARIO REGISTROS (TABS CONSOLIDADOS)
# ==============================================================

@_inventario_required
def inventario_registros(request):
    year = datetime.datetime.now().year

    prefijos_comp = [
        {"key": "IDANACOMP",   "label": "General",  "count": Computadora.objects.filter(asset_id__startswith="IDANACOMP").count()},
        {"key": "IDANALABBL",  "label": "Lab BL",   "count": Computadora.objects.filter(asset_id__startswith="IDANALABBL").count()},
        {"key": "IDANALABCOL", "label": "Lab COL",  "count": Computadora.objects.filter(asset_id__startswith="IDANALABCOL").count()},
        {"key": "IDCFPLAB",    "label": "Lab CFP",  "count": Computadora.objects.filter(asset_id__startswith="IDCFPLAB").count()},
    ]

    return render(request, "inventario/inventario_registros.html", {
        "computadoras":  Computadora.objects.order_by("id"),
        "impresoras":    Impresora.objects.order_by("id"),
        "televisores":   Televisor.objects.order_by("id"),
        "routers":       Router.objects.order_by("id"),
        "datashows":     DataShow.objects.order_by("id"),
        "monitores":     Monitor.objects.order_by("id"),
        "year":          year,
        "prefijos_comp": prefijos_comp,
        "total_comp":    Computadora.objects.count(),
    })

# ==============================================================
# Asignar / cambiar grupo de computadora(s)
# ==============================================================

@_inventario_required
def asignar_grupo_computadora(request, pk):
    comp = get_object_or_404(Computadora, pk=pk)
    if request.method == 'POST':
        valor = request.POST.get('grupo', '').strip()
        comp.grupo = int(valor) if valor.isdigit() else None
        comp.save(update_fields=['grupo'])
        return JsonResponse({'ok': True, 'grupo': comp.grupo})
    return JsonResponse({'ok': True, 'grupo': comp.grupo})


@_inventario_required
def asignar_grupo_bulk(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    ids   = request.POST.getlist('ids')
    valor = request.POST.get('grupo', '').strip()
    grupo = int(valor) if valor.isdigit() else None
    updated = Computadora.objects.filter(pk__in=ids).update(grupo=grupo)
    return JsonResponse({'ok': True, 'grupo': grupo, 'count': updated})


@_inventario_required
def asignar_categoria_televisor(request, pk):
    from .models import Televisor
    tv = get_object_or_404(Televisor, pk=pk)
    if request.method == 'POST':
        valor = request.POST.get('categoria', '').strip()
        tv.category = valor if valor else None
        tv.save(update_fields=['category'])
        return JsonResponse({'ok': True, 'categoria': tv.category or ''})
    return JsonResponse({'ok': True, 'categoria': tv.category or ''})


@_inventario_required
def asignar_categoria_router(request, pk):
    from .models import Router
    rt = get_object_or_404(Router, pk=pk)
    if request.method == 'POST':
        valor = request.POST.get('categoria', '').strip()
        rt.category = valor if valor else None
        rt.save(update_fields=['category'])
        return JsonResponse({'ok': True, 'categoria': rt.category or ''})
    return JsonResponse({'ok': True, 'categoria': rt.category or ''})


@_inventario_required
def asignar_categoria_impresora(request, pk):
    from .models import Impresora
    obj = get_object_or_404(Impresora, pk=pk)
    if request.method == 'POST':
        valor = request.POST.get('categoria', '').strip()
        obj.category = valor if valor else None
        obj.save(update_fields=['category'])
        return JsonResponse({'ok': True, 'categoria': obj.category or ''})
    return JsonResponse({'ok': True, 'categoria': obj.category or ''})


@_inventario_required
def asignar_categoria_datashow(request, pk):
    from .models import DataShow
    obj = get_object_or_404(DataShow, pk=pk)
    if request.method == 'POST':
        valor = request.POST.get('categoria', '').strip()
        obj.category = valor if valor else None
        obj.save(update_fields=['category'])
        return JsonResponse({'ok': True, 'categoria': obj.category or ''})
    return JsonResponse({'ok': True, 'categoria': obj.category or ''})


@_inventario_required
def asignar_categoria_monitor(request, pk):
    from .models import Monitor
    obj = get_object_or_404(Monitor, pk=pk)
    if request.method == 'POST':
        valor = request.POST.get('categoria', '').strip()
        obj.category = valor if valor else None
        obj.save(update_fields=['category'])
        return JsonResponse({'ok': True, 'categoria': obj.category or ''})
    return JsonResponse({'ok': True, 'categoria': obj.category or ''})


@_inventario_required
def asignar_categoria_bulk(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    tipo = request.POST.get('tipo', '').strip()
    categoria = request.POST.get('categoria', '').strip()
    ids = request.POST.getlist('ids')
    if not ids:
        return JsonResponse({'ok': False, 'error': 'Sin IDs'})
    mapa = {
        'computadora': Computadora,
        'televisor':   Televisor,
        'router':      Router,
        'impresora':   Impresora,
        'datashow':    DataShow,
        'monitor':     Monitor,
    }
    modelo = mapa.get(tipo)
    if not modelo:
        return JsonResponse({'ok': False, 'error': 'Tipo inválido'})
    modelo.objects.filter(pk__in=ids).update(category=categoria or None)
    return JsonResponse({'ok': True, 'categoria': categoria})


# ==============================================================
# GET (Cargar formulario en el modal)
# ==============================================================

@_inventario_required
def get_computadora(request, pk):
    obj = get_object_or_404(Computadora, pk=pk)
    form = ComputadoraForm(instance=obj)
    grado_val = obj.grado or ''
    grado_subtipo = grado_val.split('/', 1)[1] if grado_val.startswith('Otros/') else ''
    return render(request, "inventario/edit_computadora.html", {
        "form": form, "obj": obj,
        "edificios": EdificioComputadora.objects.all(),
        "grado_subtipo": grado_subtipo,
        "subtipos_otros": SubtipoGradoComputadora.objects.all(),
    })

@_inventario_required
def computadora_json(request, pk):
    obj = get_object_or_404(Computadora, pk=pk)
    return JsonResponse({
        'asset_id':   obj.asset_id,
        'modelo':     obj.modelo,
        'serie':      obj.serie,
        'asignado_a': obj.asignado_a,
        'area':       obj.area,
        'grado':      obj.grado,
    })

@_inventario_required
def get_televisor(request, pk):
    obj = get_object_or_404(Televisor, pk=pk)
    form = TelevisorForm(instance=obj)
    return render(request, "inventario/edit_televisor.html", {"form": form, "obj": obj})

@_inventario_required
def get_impresora(request, pk):
    obj = get_object_or_404(Impresora, pk=pk)
    form = ImpresoraForm(instance=obj)
    return render(request, "inventario/edit_impresora.html", {"form": form, "obj": obj})

@_inventario_required
def get_router(request, pk):
    obj = get_object_or_404(Router, pk=pk)
    form = RouterForm(instance=obj)
    return render(request, "inventario/edit_router.html", {"form": form, "obj": obj})

@_inventario_required
def get_datashow(request, pk):
    obj = get_object_or_404(DataShow, pk=pk)
    form = DataShowForm(instance=obj)
    return render(request, "inventario/edit_datashow.html", {"form": form, "obj": obj})

@_inventario_required
def get_monitor(request, pk):
    obj  = get_object_or_404(Monitor, pk=pk)
    form = MonitorForm(instance=obj)
    prefijos = [
        ("ANAMONI",    "General"),
        ("LABBLMONI",  "Lab BL"),
        ("LABCOLMONI", "Lab COL"),
        ("CFPINFO",    "Lab Informática"),
    ]
    computadoras = list(Computadora.objects.order_by('asset_id').values('id', 'asset_id', 'modelo', 'serie', 'asignado_a', 'area', 'grado'))
    labs_usados      = list(Monitor.objects.exclude(pk=pk).exclude(laboratorio='').exclude(laboratorio__isnull=True).values_list('laboratorio', flat=True))
    asignados_usados = list(Monitor.objects.exclude(pk=pk).exclude(asignado_a='').exclude(asignado_a__isnull=True).values_list('asignado_a', flat=True))
    return render(request, "inventario/edit_monitor.html", {
        "form": form, "obj": obj, "prefijos": prefijos,
        "computadoras": computadoras,
        "labs_usados": labs_usados,
        "asignados_usados": asignados_usados,
    })

# ==============================================================
# UPDATE (Guardar cambios vía AJAX)
# ==============================================================

@_inventario_required
def update_computadora(request, pk):
    obj = get_object_or_404(Computadora, pk=pk)
    form = ComputadoraForm(request.POST, instance=obj)
    if form.is_valid():
        comp = form.save(commit=False)
        new_ip = request.POST.get('ip', '').strip()
        if new_ip:
            comp.ip = new_ip
        new_serie = request.POST.get('serie', '').strip()
        if new_serie:
            comp.serie = new_serie
        new_asset_id = request.POST.get('asset_id', '').strip()
        if new_asset_id:
            comp.asset_id = new_asset_id
        comp.edificio = request.POST.get('edificio', '').strip() or None
        grado_subtipo = request.POST.get('grado_subtipo', '').strip()
        if comp.grado == 'Otros' and grado_subtipo:
            comp.grado = f'Otros/{grado_subtipo}'
        comp.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors})


@_inventario_required
def update_televisor(request, pk):
    obj = get_object_or_404(Televisor, pk=pk)
    form = TelevisorForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors})


@_inventario_required
def update_impresora(request, pk):
    obj = get_object_or_404(Impresora, pk=pk)
    form = ImpresoraForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors})


@_inventario_required
def update_router(request, pk):
    obj = get_object_or_404(Router, pk=pk)
    form = RouterForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors})


@_inventario_required
def update_datashow(request, pk):
    obj = get_object_or_404(DataShow, pk=pk)
    form = DataShowForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors})


@_inventario_required
def update_monitor(request, pk):
    obj = get_object_or_404(Monitor, pk=pk)
    form = MonitorForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors})

# ==============================================================
# DELETE (JSON)
# ==============================================================

@_inventario_required
def eliminar_computadora(request, pk):
    get_object_or_404(Computadora, pk=pk).delete()
    return JsonResponse({"ok": True})

@_inventario_required
def eliminar_televisor(request, pk):
    get_object_or_404(Televisor, pk=pk).delete()
    return JsonResponse({"ok": True})

@_inventario_required
def eliminar_impresora(request, pk):
    get_object_or_404(Impresora, pk=pk).delete()
    return JsonResponse({"ok": True})

@_inventario_required
def eliminar_router(request, pk):
    get_object_or_404(Router, pk=pk).delete()
    return JsonResponse({"ok": True})

@_inventario_required
def eliminar_datashow(request, pk):
    get_object_or_404(DataShow, pk=pk).delete()
    return JsonResponse({"ok": True})

@_inventario_required
def eliminar_monitor(request, pk):
    get_object_or_404(Monitor, pk=pk).delete()
    return JsonResponse({"ok": True})


# ==============================================================
# PDF GENERATOR
# ==============================================================

def download_model_pdf(request, tipo, pk):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader

    model_map = {
        "computadora": Computadora,
        "televisor":   Televisor,
        "impresora":   Impresora,
        "router":      Router,
        "datashow":    DataShow,
        "monitor":     Monitor,
    }

    fields_map = {
        "computadora": [
            ("ID",              "asset_id"),
            ("Modelo",          "modelo"),
            ("Serie",           "serie"),
            ("IP",              "ip"),
            ("Categoría",       "category"),
            ("Asignado a",      "asignado_a"),
            ("Área",            "area"),
            ("Grado",           "grado"),
            ("Edificio",        "edificio"),
            ("Fecha Instalación","fecha_instalado"),
            ("Observaciones",   "observaciones"),
        ],
        "televisor": [
            ("ID",              "asset_id"),
            ("Modelo",          "modelo"),
            ("Serie",           "serie"),
            ("IP",              "ip"),
            ("Categoría",       "category"),
            ("Grado",           "grado"),
            ("Área",            "area"),
            ("Observaciones",   "observaciones"),
        ],
        "impresora": [
            ("ID",              "asset_id"),
            ("Nombre",          "nombre"),
            ("Modelo",          "modelo"),
            ("Serie",           "serie"),
            ("Categoría",       "category"),
            ("Asignado a",      "asignado_a"),
            ("Nivel Tinta",     "nivel_tinta"),
            ("Últ. Llenado",    "ultima_vez_llenado"),
            ("Impresiones",     "cantidad_impresiones"),
            ("A Color",         "a_color"),
            ("Observaciones",   "observaciones"),
        ],
        "router": [
            ("ID",              "asset_id"),
            ("Modelo",          "modelo"),
            ("Serie",           "serie"),
            ("Categoría",       "category"),
            ("Nombre Router",   "nombre_router"),
            ("Clave Router",    "clave_router"),
            ("IP Asignada",     "ip_asignada"),
            ("IP de Uso",       "ip_uso"),
            ("Ubicado",         "ubicado"),
            ("Observaciones",   "observaciones"),
        ],
        "datashow": [
            ("ID",              "asset_id"),
            ("Nombre",          "nombre"),
            ("Modelo",          "modelo"),
            ("Serie",           "serie"),
            ("Categoría",       "category"),
            ("Estado",          "estado"),
            ("Cable Corriente", "cable_corriente"),
            ("HDMI",            "hdmi"),
            ("VGA",             "vga"),
            ("Extensión",       "extension"),
            ("Observaciones",   "observaciones"),
        ],
        "monitor": [
            ("ID",              "asset_id"),
            ("Modelo",          "modelo"),
            ("Serie",           "serie"),
            ("Tipo Ubicación",  "ubicacion_tipo"),
            ("Laboratorio",     "laboratorio"),
            ("Asignado a",      "asignado_a"),
            ("Categoría",       "category"),
            ("Observaciones",   "observaciones"),
        ],
    }

    # Color de acento por tipo de equipo
    color_map = {
        "computadora": "#1971c2",
        "televisor":   "#0c8599",
        "impresora":   "#d9480f",
        "router":      "#2f9e44",
        "datashow":    "#7048e8",
        "monitor":     "#495057",
    }

    tipo = tipo.lower()
    if tipo not in model_map:
        return HttpResponse("Modelo inválido", status=404)

    Model  = model_map[tipo]
    campos = fields_map[tipo]
    obj    = get_object_or_404(Model, pk=pk)

    accent_hex = color_map.get(tipo, "#0056b3")
    accent     = colors.HexColor(accent_hex)
    grey_line  = colors.HexColor("#dee2e6")
    label_bg   = colors.HexColor("#f1f3f5")
    label_fg   = colors.HexColor("#343a40")
    alt_row    = colors.HexColor("#f8f9fa")

    # QR code apuntando a este mismo PDF
    pdf_path = reverse("inventario:download_model_pdf", args=[tipo, pk])
    pdf_url  = f"https://servicios.ana-hn.org:437{pdf_path}"
    qr_pil   = qrcode.make(pdf_url).convert("RGB")
    qr_buf   = io.BytesIO()
    qr_pil.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    # Canvas (portrait Letter: 612 x 792 pts)
    page_w, page_h = letter
    buffer = io.BytesIO()
    pdf    = canvas.Canvas(buffer, pagesize=letter)
    margin = 1.5 * cm

    today_str = datetime.date.today().strftime("%d/%m/%Y")
    asset_id  = getattr(obj, "asset_id", "")
    titulo    = f"Ficha de {tipo.capitalize()}"

    pdf.setTitle(f"Ficha {tipo.capitalize()} – {asset_id}")
    pdf.setAuthor("TechCare – Instituto ANA Honduras")
    pdf.setSubject(f"Reporte de inventario: {asset_id}")

    # ── CABECERA ──────────────────────────────────────────────
    band_h = 105

    # Banda principal de color
    pdf.setFillColor(accent)
    pdf.rect(0, page_h - band_h, page_w, band_h, fill=1, stroke=0)

    # Banda inferior oscurecida (efecto sombra)
    pdf.setFillColor(colors.HexColor("#00000022"))
    pdf.rect(0, page_h - band_h, page_w, 6, fill=1, stroke=0)

    # Texto blanco
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(margin, page_h - 16, "INSTITUTO EDUCATIVO ANA HONDURAS · TechCare")

    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(margin, page_h - 50, titulo)

    # Pastilla Asset ID
    badge_x, badge_y, badge_w, badge_h = margin, page_h - 85, 160, 20
    pdf.setFillColor(colors.HexColor("#ffffff33"))
    pdf.roundRect(badge_x, badge_y, badge_w, badge_h, 4, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(badge_x + 8, badge_y + 5, f"Asset ID: {asset_id}")

    # Fecha en cabecera
    pdf.setFont("Helvetica", 8.5)
    pdf.drawRightString(page_w - 100, page_h - 80, today_str)

    # QR code incrustado en la cabecera
    qr_size = 88
    qr_x = page_w - qr_size - 10
    qr_y = page_h - band_h + 8
    pdf.drawImage(ImageReader(qr_buf), qr_x, qr_y,
                  width=qr_size, height=qr_size, preserveAspectRatio=True)

    # Línea separadora debajo de la cabecera
    sep_y = page_h - band_h - 8
    pdf.setStrokeColor(accent)
    pdf.setLineWidth(1.5)
    pdf.line(margin, sep_y, page_w - margin, sep_y)

    # ── TABLA ─────────────────────────────────────────────────
    data = [["Campo", "Valor"]]
    for label, attr in campos:
        val = getattr(obj, attr, None)
        if val is None:
            val = "—"
        elif isinstance(val, bool):
            val = "Sí" if val else "No"
        elif isinstance(val, datetime.date):
            val = val.strftime("%d/%m/%Y")
        else:
            # Usar display label si el campo tiene choices
            display_method = f"get_{attr}_display"
            if hasattr(obj, display_method):
                val = getattr(obj, display_method)() or "—"
            else:
                val = str(val) if str(val) else "—"
        data.append([label, val])

    col1_w = 5.2 * cm
    col2_w = page_w - 2 * margin - col1_w
    n = len(data)

    tstyles = [
        # Fila de encabezado
        ("BACKGROUND",    (0, 0), (-1, 0), accent),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("TOPPADDING",    (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        # Todas las celdas
        ("FONTSIZE",      (0, 1), (-1, -1), 10),
        ("TOPPADDING",    (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Columna de etiquetas — fondo gris, negrita
        ("BACKGROUND",    (0, 1), (0, -1), label_bg),
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (0, 1), (0, -1), label_fg),
        # Columna de valores
        ("FONTNAME",      (1, 1), (1, -1), "Helvetica"),
        ("TEXTCOLOR",     (1, 1), (1, -1), colors.HexColor("#212529")),
        # Bordes
        ("LINEBELOW",     (0, 0), (-1, -2), 0.4, grey_line),
        ("BOX",           (0, 0), (-1, -1), 0.6, grey_line),
        ("LINEAFTER",     (0, 0), (0, -1),  0.4, grey_line),
    ]

    # Filas alternas en columna de valor
    for i in range(1, n):
        if i % 2 == 0:
            tstyles.append(("BACKGROUND", (1, i), (1, i), alt_row))

    table = Table(data, colWidths=[col1_w, col2_w])
    table.setStyle(TableStyle(tstyles))

    tw, th = table.wrap(col1_w + col2_w, 0)
    table_y = sep_y - 14 - th
    table.drawOn(pdf, margin, table_y)

    current_y = table_y  # rastrea la Y más baja usada

    # ── SECCIÓN MONITOR (solo para computadoras) ───────────────
    if tipo == "computadora":
        monitor = Monitor.objects.filter(laboratorio=obj.asset_id).first()
        if monitor:
            mon_accent = colors.HexColor("#495057")
            gap = 18
            subband_h = 26

            # Sub-cabecera del monitor
            sub_y = current_y - gap
            pdf.setFillColor(mon_accent)
            pdf.rect(margin, sub_y - subband_h, col1_w + col2_w, subband_h, fill=1, stroke=0)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(margin + 8, sub_y - subband_h + 8,
                           f"Monitor Asignado  —  {monitor.asset_id}")

            # Tabla del monitor
            mon_campos = [
                ("Asset ID",       monitor.asset_id or "—"),
                ("Modelo",         monitor.modelo or "—"),
                ("Serie",          monitor.serie or "—"),
                ("Tipo Ubicación", monitor.get_ubicacion_tipo_display() if monitor.ubicacion_tipo else "—"),
                ("Categoría",      monitor.category or "—"),
                ("Observaciones",  monitor.observaciones or "—"),
            ]
            mon_data = [["Campo", "Valor"]] + [[lbl, val] for lbl, val in mon_campos]
            nm = len(mon_data)

            mon_tstyles = [
                ("BACKGROUND",    (0, 0), (-1, 0), mon_accent),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, 0), 10),
                ("TOPPADDING",    (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
                ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
                ("FONTSIZE",      (0, 1), (-1, -1), 10),
                ("TOPPADDING",    (0, 1), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND",    (0, 1), (0, -1), label_bg),
                ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR",     (0, 1), (0, -1), label_fg),
                ("FONTNAME",      (1, 1), (1, -1), "Helvetica"),
                ("TEXTCOLOR",     (1, 1), (1, -1), colors.HexColor("#212529")),
                ("LINEBELOW",     (0, 0), (-1, -2), 0.4, grey_line),
                ("BOX",           (0, 0), (-1, -1), 0.6, grey_line),
                ("LINEAFTER",     (0, 0), (0, -1),  0.4, grey_line),
            ]
            for i in range(1, nm):
                if i % 2 == 0:
                    mon_tstyles.append(("BACKGROUND", (1, i), (1, i), alt_row))

            mon_table = Table(mon_data, colWidths=[col1_w, col2_w])
            mon_table.setStyle(TableStyle(mon_tstyles))
            _, mon_th = mon_table.wrap(col1_w + col2_w, 0)
            mon_table_y = sub_y - subband_h - mon_th
            mon_table.drawOn(pdf, margin, mon_table_y)
            current_y = mon_table_y

    # ── PIE DE PÁGINA ─────────────────────────────────────────
    pdf.setFillColor(accent)
    pdf.rect(0, 0, page_w, 5, fill=1, stroke=0)

    pdf.setFillColor(colors.HexColor("#6c757d"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(margin, 13, "TechCare — Sistema de Gestión de Inventario · Instituto ANA Honduras")
    pdf.drawRightString(page_w - margin, 13, f"Generado el {today_str}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = f"Ficha_{tipo.capitalize()}_{asset_id}.pdf"
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


# ===================== EXPORTAR EXCEL =====================
@_inventario_required
def exportar_excel_inventario(request, categoria):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center")

    def estilizar_cabecera(ws, cols):
        ws.append(cols)
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
        ws.row_dimensions[1].height = 22

    if categoria == 'computadoras':
        ws.title = "Computadoras"
        estilizar_cabecera(ws, ["Asset ID", "Modelo", "Serie", "IP", "Asignado a", "Área", "Grado", "Grupo", "Fecha Instalación", "Observaciones"])
        # <--- hecho por claude code (17-sep-2026): respeta el filtro activo (General / Lab BL / …) con ?prefijo=
        for c in _comp_por_prefijo(request).order_by('asset_id'):
            ws.append([c.asset_id, c.modelo, c.serie, c.ip, c.asignado_a, c.area, c.grado,
                        c.grupo or '', str(c.fecha_instalado) if c.fecha_instalado else '', c.observaciones or ''])

    elif categoria == 'impresoras':
        ws.title = "Impresoras"
        estilizar_cabecera(ws, ["Asset ID", "Nombre", "Modelo", "Serie", "Asignado a", "Nivel Tinta", "Última vez llenado", "Cant. Impresiones", "A Color", "Observaciones"])
        for i in Impresora.objects.all().order_by('asset_id'):
            ws.append([i.asset_id, i.nombre, i.modelo, i.serie, i.asignado_a, i.nivel_tinta,
                        str(i.ultima_vez_llenado) if i.ultima_vez_llenado else '', i.cantidad_impresiones,
                        'Sí' if i.a_color else 'No', i.observaciones or ''])

    elif categoria == 'televisores':
        ws.title = "Televisores"
        estilizar_cabecera(ws, ["Asset ID", "Modelo", "Serie", "IP", "Grado", "Área", "Observaciones"])
        for t in Televisor.objects.all().order_by('asset_id'):
            ws.append([t.asset_id, t.modelo, t.serie, t.ip, t.grado, t.area, t.observaciones or ''])

    elif categoria == 'routers':
        ws.title = "Routers"
        estilizar_cabecera(ws, ["Asset ID", "Modelo", "Serie", "Nombre Router", "IP Asignada", "IP Uso", "Ubicado", "Observaciones"])
        for r in Router.objects.all().order_by('asset_id'):
            ws.append([r.asset_id, r.modelo, r.serie, r.nombre_router, r.ip_asignada, r.ip_uso, r.ubicado, r.observaciones or ''])

    elif categoria == 'datashows':
        ws.title = "DataShows"
        estilizar_cabecera(ws, ["Asset ID", "Nombre", "Modelo", "Serie", "Estado", "Cable Corriente", "HDMI", "VGA", "Extensión", "Observaciones"])
        for d in DataShow.objects.all().order_by('asset_id'):
            ws.append([d.asset_id, d.nombre, d.modelo, d.serie, d.estado,
                        'Sí' if d.cable_corriente else 'No', 'Sí' if d.hdmi else 'No',
                        'Sí' if d.vga else 'No', 'Sí' if d.extension else 'No', d.observaciones or ''])

    elif categoria == 'monitores':
        ws.title = "Monitores"
        estilizar_cabecera(ws, ["Asset ID", "Modelo", "Serie", "Tipo Ubicación", "Laboratorio", "Asignado a", "Observaciones"])
        for m in Monitor.objects.all().order_by('asset_id'):
            ws.append([m.asset_id, m.modelo, m.serie,
                        m.get_ubicacion_tipo_display() if m.ubicacion_tipo else '',
                        m.laboratorio or '', m.asignado_a or '', m.observaciones or ''])
    else:
        return HttpResponse("Categoría no válida", status=400)

    # Ajustar anchos de columna automáticamente
    for col in ws.columns:
        max_len = max((len(str(cell.value)) if cell.value else 0) for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="inventario_{categoria}.xlsx"'
    return response


# ===================== EXPORTAR PDF =====================
# <--- hecho por claude code (17-sep-2026): PDF de cada pestaña de "Registros de inventario".
_PREFIJOS_EXPORT = {'IDANACOMP': 'General', 'IDANALABBL': 'Lab BL', 'IDANALABCOL': 'Lab COL', 'IDCFPLAB': 'Lab CFP'}


def _comp_por_prefijo(request):
    """Computadoras filtradas por el prefijo de Asset ID que viene en ?prefijo= (solo valores conocidos)."""
    pref = (request.GET.get('prefijo') or '').strip()
    qs = Computadora.objects.all()
    return qs.filter(asset_id__startswith=pref) if pref in _PREFIJOS_EXPORT else qs


def _inventario_export_datos(request, categoria):
    """(título, encabezados, filas) de una pestaña; None si la categoría no existe."""
    sn = lambda b: 'Sí' if b else 'No'
    f = lambda d: d.strftime('%d/%m/%Y') if d else ''
    if categoria == 'computadoras':
        pref = (request.GET.get('prefijo') or '').strip()
        titulo = 'Computadoras' + (f' — {_PREFIJOS_EXPORT[pref]}' if pref in _PREFIJOS_EXPORT else '')
        cols = ["Asset ID", "Modelo", "Serie", "IP", "Asignado a", "Área", "Grado", "Grupo", "Categoría", "Fecha inst.", "Observaciones"]
        filas = [[c.asset_id, c.modelo, c.serie, c.ip, c.asignado_a, c.area, c.grado, c.grupo or '', c.category or '',
                  f(c.fecha_instalado), c.observaciones or ''] for c in _comp_por_prefijo(request).order_by('asset_id')]
    elif categoria == 'impresoras':
        titulo, cols = 'Impresoras', ["Asset ID", "Nombre", "Modelo", "Serie", "Asignado a", "Nivel tinta", "Últ. llenado", "Impresiones", "A color", "Observaciones"]
        filas = [[i.asset_id, i.nombre, i.modelo, i.serie, i.asignado_a, i.nivel_tinta, f(i.ultima_vez_llenado),
                  i.cantidad_impresiones, sn(i.a_color), i.observaciones or ''] for i in Impresora.objects.order_by('asset_id')]
    elif categoria == 'televisores':
        titulo, cols = 'Televisores', ["Asset ID", "Modelo", "Serie", "IP", "Grado", "Área", "Observaciones"]
        filas = [[t.asset_id, t.modelo, t.serie, t.ip, t.grado, t.area, t.observaciones or ''] for t in Televisor.objects.order_by('asset_id')]
    elif categoria == 'routers':
        titulo, cols = 'Routers', ["Asset ID", "Modelo", "Serie", "Nombre router", "IP asignada", "IP uso", "Ubicado", "Observaciones"]
        filas = [[r.asset_id, r.modelo, r.serie, r.nombre_router, r.ip_asignada, r.ip_uso, r.ubicado, r.observaciones or ''] for r in Router.objects.order_by('asset_id')]
    elif categoria == 'datashows':
        titulo, cols = 'DataShows', ["Asset ID", "Nombre", "Modelo", "Serie", "Estado", "Cable corriente", "HDMI", "VGA", "Extensión", "Observaciones"]
        filas = [[d.asset_id, d.nombre, d.modelo, d.serie, d.estado, sn(d.cable_corriente), sn(d.hdmi), sn(d.vga), sn(d.extension),
                  d.observaciones or ''] for d in DataShow.objects.order_by('asset_id')]
    elif categoria == 'monitores':
        titulo, cols = 'Monitores', ["Asset ID", "Modelo", "Serie", "Tipo ubicación", "Laboratorio", "Asignado a", "Observaciones"]
        filas = [[m.asset_id, m.modelo, m.serie, m.get_ubicacion_tipo_display() if m.ubicacion_tipo else '', m.laboratorio or '',
                  m.asignado_a or '', m.observaciones or ''] for m in Monitor.objects.order_by('asset_id')]
    else:
        return None
    return titulo, cols, [[('' if v is None else str(v)) for v in fila] for fila in filas]


@_inventario_required
def exportar_pdf_inventario(request, categoria):
    """PDF apaisado con la tabla completa de la pestaña (en Computadoras respeta ?prefijo=)."""
    datos = _inventario_export_datos(request, categoria)
    if datos is None:
        return HttpResponse("Categoría no válida", status=400)
    titulo, cols, filas = datos
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from xml.sax.saxutils import escape as _esc
    AZUL = colors.HexColor("#1F4E79"); GRIS = colors.HexColor("#eeeeee")
    st_t = ParagraphStyle("t", fontSize=15, leading=18, fontName="Helvetica-Bold", textColor=AZUL, spaceAfter=3)
    st_s = ParagraphStyle("s", fontSize=9, fontName="Helvetica", textColor=colors.gray)
    st_c = ParagraphStyle("c", fontSize=7, fontName="Helvetica", leading=8.5)
    st_h = ParagraphStyle("h", fontSize=7.5, fontName="Helvetica-Bold", leading=9, textColor=colors.white)
    # Anchos proporcionales al contenido (acotados), ajustados al ancho útil de carta apaisada (25.5 cm)
    pesos = []
    for k, col in enumerate(cols):
        largo = max([len(col)] + [len(f[k]) for f in filas[:400]])
        pesos.append(min(max(largo, 6), 34))
    anchos = [25.5 * cm * w / sum(pesos) for w in pesos]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), leftMargin=1.2*cm, rightMargin=1.2*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm, title=f"Inventario — {titulo}")
    story = [Paragraph(f"Inventario — {_esc(titulo)}", st_t),
             Paragraph(f"Asociación Nuevo Amanecer – Sistema TechCare · Generado el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} · {len(filas)} registros", st_s),
             Spacer(1, 0.3*cm)]
    data = [[Paragraph(_esc(c), st_h) for c in cols]] + [[Paragraph(_esc(v), st_c) for v in f] for f in filas]
    tabla = Table(data, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(tabla)
    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/pdf')
    nombre = titulo.lower().replace(' — ', '_').replace(' ', '_')
    resp['Content-Disposition'] = f'inline; filename="inventario_{nombre}.pdf"'
    return resp


# ==============================================================
# INVENTARIO GENERAL — hecho por claude code (13-oct-2026)
# Código automático ANAGEN-0001, descripción, ubicación, estado, foto, comentario y firma de la auditora.
# Registra/edita: quien tiene Inventario. Comenta: solo la auditora (grupo `mantenimiento`) o el superusuario.
# ==============================================================
from django.db import transaction as _tx
from django.contrib import messages as _msg
from django.views.decorators.http import require_POST as _require_POST
from .forms import ItemGeneralForm

FIRMA_AUDITORA_INV = ('Yeny Lagos', 'Auditora')   # misma firma fija que Mantenimiento


def _es_auditora_inv(u):
    return u.is_superuser or u.groups.filter(name='mantenimiento').exists()


def _siguiente_codigo_general():
    """Correlativo ANAGEN-0001 con bloqueo para no repetir en guardados simultáneos."""
    with _tx.atomic():
        ult = (ItemGeneral.objects.select_for_update().filter(codigo__startswith=ItemGeneral.PREFIJO)
               .order_by('-codigo').values_list('codigo', flat=True).first())
        try:
            n = int(ult[len(ItemGeneral.PREFIJO):]) if ult else 0
        except ValueError:
            n = ItemGeneral.objects.count()
        return f"{ItemGeneral.PREFIJO}{n + 1:04d}"


def _reducir_foto(f):
    """Las fotos del celular pesan 3-5 MB: se guardan a máx. 1600 px en JPEG."""
    try:
        from PIL import Image, ImageOps
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile
        im = ImageOps.exif_transpose(Image.open(f)).convert('RGB')
        im.thumbnail((1600, 1600))
        buf = BytesIO(); im.save(buf, 'JPEG', quality=82, optimize=True); buf.seek(0)
        nombre = (f.name.rsplit('.', 1)[0] or 'foto') + '.jpg'
        return InMemoryUploadedFile(buf, 'foto', nombre, 'image/jpeg', buf.getbuffer().nbytes, None)
    except Exception:
        return f


@_inventario_required
def inventario_general(request):
    edit = ItemGeneral.objects.filter(pk=request.GET.get('editar')).first() if request.GET.get('editar', '').isdigit() else None
    if request.method == 'POST':
        edit = ItemGeneral.objects.filter(pk=request.POST.get('edit_id')).first() if request.POST.get('edit_id', '').isdigit() else None
        form = ItemGeneralForm(request.POST, request.FILES, instance=edit)
        if form.is_valid():
            obj = form.save(commit=False)
            if 'foto' in request.FILES:
                obj.foto = _reducir_foto(request.FILES['foto'])
            if not obj.pk:
                obj.codigo = _siguiente_codigo_general()
                obj.creado_por = request.user
            obj.modificado_por = request.user
            obj.save()
            _msg.success(request, f'{obj.codigo} {"actualizado" if edit else "registrado"}.')
            return redirect('inventario:inventario_general')
    else:
        form = ItemGeneralForm(instance=edit)
    items, f_area, f_cat = _items_general_filtrados(request)
    por_estado = {k: 0 for k, _ in ItemGeneral.ESTADOS}
    for e in items.values_list('estado', flat=True):
        por_estado[e] = por_estado.get(e, 0) + 1
    return render(request, 'inventario/inventario_general.html', {
        'form': form, 'edit': edit, 'items': items,
        'next_codigo': None if edit else _siguiente_codigo_general(),
        'ubicaciones': sorted(set(ItemGeneral.objects.values_list('ubicacion', flat=True))),
        'kpi_estados': [(k, l, por_estado.get(k, 0)) for k, l in ItemGeneral.ESTADOS],
        'es_auditora': _es_auditora_inv(request.user),
        'auditora': FIRMA_AUDITORA_INV,
        # <--- área y categoría (filtro + select agregable)
        'areas': AREAS_GENERAL,
        'categorias': CategoriaGeneral.objects.all(),
        'f_area': f_area, 'f_cat': f_cat,
        'filtro_qs': request.GET.urlencode(),
        'cat_sel': (form['categoria'].value() or '') if form is not None else '',
    })


def _items_general_filtrados(request):
    """Filtro por ÁREA y luego por SU categoría (?f_area=&f_cat=). Lo usan la página, el PDF y el Excel."""
    f_area = request.GET.get('f_area', '') if request.GET.get('f_area', '') in dict(AREAS_GENERAL) else ''
    f_cat = request.GET.get('f_cat', '') if request.GET.get('f_cat', '').isdigit() else ''
    qs = ItemGeneral.objects.select_related('creado_por', 'categoria').order_by('-id')
    if f_area:
        qs = qs.filter(area=f_area)
    if f_cat:
        qs = qs.filter(categoria_id=int(f_cat))
    return qs, f_area, f_cat


@_inventario_required
@_require_POST
def categoria_general_add(request):
    """Agrega una categoría al área (desde el botón + del formulario). JSON."""
    try:
        data = json.loads(request.body or b'{}')
    except ValueError:
        data = {}
    area = data.get('area', '')
    nombre = ' '.join((data.get('nombre') or '').split())[:80]
    if area not in dict(AREAS_GENERAL):
        return JsonResponse({'ok': False, 'error': 'Elige primero el área.'}, status=400)
    if len(nombre) < 2:
        return JsonResponse({'ok': False, 'error': 'Escribe el nombre de la categoría.'}, status=400)
    cat = CategoriaGeneral.objects.filter(area=area, nombre__iexact=nombre).first() or \
          CategoriaGeneral.objects.create(area=area, nombre=nombre[:1].upper() + nombre[1:])
    return JsonResponse({'ok': True, 'id': cat.id, 'nombre': cat.nombre, 'area': cat.area})


@_inventario_required
@_require_POST
def item_general_comentario(request, pk):
    if not _es_auditora_inv(request.user):
        raise PermissionDenied('Solo la auditora deja comentarios.')
    obj = get_object_or_404(ItemGeneral, pk=pk)
    obj.comentario_auditora = (request.POST.get('comentario') or '').strip()[:2000]
    obj.modificado_por = request.user
    obj.save(update_fields=['comentario_auditora', 'modificado_por', 'fecha_modificado'])
    _msg.success(request, f'Comentario de auditoría guardado en {obj.codigo}.')
    return redirect('inventario:inventario_general')


@_inventario_required
@_require_POST
def item_general_eliminar(request, pk):
    obj = get_object_or_404(ItemGeneral, pk=pk)
    cod = obj.codigo
    if obj.foto:
        obj.foto.delete(save=False)
    obj.delete()
    _msg.success(request, f'{cod} eliminado.')
    return redirect('inventario:inventario_general')


def _pdf_item_general(pdf, it, w, h):
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    from django.contrib.staticfiles import finders
    logo = finders.find('mantenimiento_mecanico/logo_ana.png') or finders.find('inventario/img/ana-transformed.png')   # logo de 256 px: el original hacía PDFs de 2.7 MB
    if logo:
        pdf.drawImage(logo, 15 * mm, h - 32 * mm, width=20 * mm, height=20 * mm, mask='auto', preserveAspectRatio=True)
    pdf.setFont('Helvetica-Bold', 13); pdf.drawCentredString(w / 2, h - 18 * mm, 'Asociación Nuevo Amanecer')
    pdf.setFont('Helvetica', 10);       pdf.drawCentredString(w / 2, h - 24 * mm, 'Inventario General · Ficha de artículo')
    pdf.setFont('Helvetica-Bold', 14);  pdf.drawRightString(w - 15 * mm, h - 18 * mm, it.codigo)
    pdf.setLineWidth(0.6); pdf.line(15 * mm, h - 36 * mm, w - 15 * mm, h - 36 * mm)
    y = h - 46 * mm
    filas = [('Área', it.get_area_display()), ('Categoría', it.categoria.nombre if it.categoria_id else '—'),
             ('Descripción', it.descripcion), ('Ubicación', it.ubicacion), ('Estado', it.get_estado_display()),
             ('Registrado', f"{it.fecha_creado:%d/%m/%Y} por {(it.creado_por.get_full_name() or it.creado_por.username) if it.creado_por else '—'}")]
    for etq, val in filas:
        pdf.setFont('Helvetica-Bold', 10); pdf.drawString(15 * mm, y, etq + ':')
        pdf.setFont('Helvetica', 10)
        for i, ln in enumerate(simpleSplit(str(val), 'Helvetica', 10, 95 * mm) or ['']):
            pdf.drawString(45 * mm, y - i * 5 * mm, ln)
        y -= max(1, len(simpleSplit(str(val), 'Helvetica', 10, 95 * mm))) * 5 * mm + 3 * mm
    # foto a la derecha
    if it.foto:
        try:
            pdf.drawImage(it.foto.path, w - 75 * mm, h - 110 * mm, width=60 * mm, height=65 * mm, preserveAspectRatio=True, anchor='c')
            pdf.rect(w - 75 * mm, h - 110 * mm, 60 * mm, 65 * mm)
        except Exception:
            pass
    y = min(y, h - 120 * mm)
    pdf.setFont('Helvetica-Bold', 10); pdf.drawString(15 * mm, y, 'Comentario de la auditora:')
    y -= 6 * mm; pdf.setFont('Helvetica', 10)
    for ln in (simpleSplit(it.comentario_auditora, 'Helvetica', 10, w - 30 * mm) or ['—'])[:14]:
        pdf.drawString(15 * mm, y, ln); y -= 5 * mm
    # firmas: quien registró y la auditora (fija)
    yf = 45 * mm
    pdf.line(20 * mm, yf, 90 * mm, yf); pdf.line(w - 90 * mm, yf, w - 20 * mm, yf)
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawCentredString(55 * mm, yf - 5 * mm, (it.creado_por.get_full_name() or it.creado_por.username) if it.creado_por else '')
    pdf.drawCentredString(w - 55 * mm, yf - 5 * mm, FIRMA_AUDITORA_INV[0])
    pdf.setFont('Helvetica', 9)
    pdf.drawCentredString(55 * mm, yf - 10 * mm, 'Responsable de inventario')
    pdf.drawCentredString(w - 55 * mm, yf - 10 * mm, FIRMA_AUDITORA_INV[1])
    pdf.setFont('Helvetica', 7)
    pdf.drawString(15 * mm, 12 * mm, f'Generado el {datetime.datetime.now():%d/%m/%Y %H:%M}')


@_inventario_required
def item_general_pdf(request, pk=None):
    """Ficha PDF de un artículo (pk) o de todos los filtrados (sin pk) — una página por artículo."""
    from reportlab.lib.pagesizes import letter as _letter
    items = [get_object_or_404(ItemGeneral, pk=pk)] if pk else list(_items_general_filtrados(request)[0].order_by('codigo'))
    resp = HttpResponse(content_type='application/pdf')
    nombre = items[0].codigo if pk else 'inventario_general'
    resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
    pdf = canvas.Canvas(resp, pagesize=_letter)
    w, h = _letter
    for i, it in enumerate(items):
        _pdf_item_general(pdf, it, w, h)
        if i < len(items) - 1:
            pdf.showPage()
    if not items:
        pdf.drawString(72, h - 72, 'Sin artículos.')
    pdf.save()
    return resp


@_inventario_required
def item_general_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = 'Inventario general'
    ws.append(['Código', 'Área', 'Categoría', 'Descripción', 'Ubicación', 'Estado', 'Comentario de la auditora', 'Registrado por', 'Fecha'])
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='206BC4')
    for it in _items_general_filtrados(request)[0].order_by('codigo'):
        ws.append([it.codigo, it.get_area_display(), it.categoria.nombre if it.categoria_id else '', it.descripcion, it.ubicacion, it.get_estado_display(), it.comentario_auditora,
                   (it.creado_por.get_full_name() or it.creado_por.username) if it.creado_por else '', it.fecha_creado.date()])
        ws.cell(row=ws.max_row, column=9).number_format = 'DD/MM/YYYY'
    for col, an in zip('ABCDEFGHI', (13, 16, 20, 40, 24, 14, 45, 24, 12)):
        ws.column_dimensions[col].width = an
    ws.freeze_panes = 'A2'
    resp = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="inventario_general_{datetime.date.today():%Y%m%d}.xlsx"'
    wb.save(resp)
    return resp
