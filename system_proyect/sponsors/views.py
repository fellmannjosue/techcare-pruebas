from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
# <--- hecho por claude code: el módulo manejaba datos de donantes SIN autenticación
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (City, Country, Directed, Title, Sponsor, Correspondence,
                     Income, Godfather, Sponsored, Descr_Godfather)
from .forms import (CityForm, CountryForm, DirectedForm, TitleForm, SponsorForm,
                    CorrespondenceForm, IncomeForm, GodfatherForm, SponsoredForm,
                    DescrGodfatherForm)

# <--- hecho por claude code: topes (antes: sin límite ni paginación)
_SEARCH_LIMIT = 20
_PER_PAGE = 50


@login_required
def sponsors_dashboard(request):
    """Panel principal del módulo con accesos y conteos."""
    stats = {
        'sponsors':   Sponsor.objects.count(),
        'godfathers': Godfather.objects.count(),
        'sponsored':  Sponsored.objects.count(),
        'incomes':    Income.objects.count(),
    }
    return render(request, 'sponsors/dashboard.html', {'stats': stats})


# ══════════════════════ Catálogos simples ══════════════════════

def _catalogo(request, form_class, queryset, template, ctx_name, etiqueta, url_name):
    """<--- hecho por claude code: crea+lista de catálogos (evita 5 vistas calcadas)."""
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'{etiqueta} agregado correctamente.')
            return redirect(url_name)
        messages.error(request, f'Error al agregar. Revisa los campos.')
    else:
        form = form_class()
    return render(request, template, {'form': form, ctx_name: queryset})


@login_required
def add_city(request):
    return _catalogo(request, CityForm, City.objects.select_related('country').order_by('name'),
                     'sponsors/form_city.html', 'city_list', 'Ciudad', 'sponsors:add_city')


@login_required
def add_country(request):
    return _catalogo(request, CountryForm, Country.objects.order_by('name'),
                     'sponsors/form_country.html', 'countries', 'País', 'sponsors:add_country')


@login_required
def add_directed(request):
    return _catalogo(request, DirectedForm, Directed.objects.order_by('description'),
                     'sponsors/form_directed.html', 'directed_list', 'Registro', 'sponsors:add_directed')


@login_required
def add_title(request):
    return _catalogo(request, TitleForm, Title.objects.order_by('description'),
                     'sponsors/form_title.html', 'title_list', 'Título', 'sponsors:add_title')


@login_required
def add_descr_godfather(request):
    return _catalogo(request, DescrGodfatherForm, Descr_Godfather.objects.order_by('name'),
                     'sponsors/form_descr_godfather.html', 'descr_list',
                     'Descripción', 'sponsors:add_descr_godfather')


# ══════════════════════ Sponsors ══════════════════════

@login_required
def sponsor_list(request):
    """Lista paginada + buscador (antes cargaba los ~3,500 registros de golpe)."""
    q = (request.GET.get('q') or '').strip()
    qs = Sponsor.objects.select_related('city', 'city__country')
    if q:
        cond = (Q(first_name_1__icontains=q) | Q(last_name_1__icontains=q) |
                Q(first_name_2__icontains=q) | Q(last_name_2__icontains=q) |
                Q(email__icontains=q))
        if q.isdigit():
            cond |= Q(id=int(q))
        qs = qs.filter(cond)
    qs = qs.order_by('last_name_1', 'first_name_1')
    total = qs.count()
    page = Paginator(qs, _PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'sponsors/sponsor_list.html',
                  {'page_obj': page, 'sponsors': page.object_list, 'q': q, 'total': total})


@login_required
def get_sponsor_data(request):
    sponsor_id = request.GET.get('id', None)
    if not sponsor_id:
        return JsonResponse({'error': 'ID no proporcionado'}, status=400)
    try:
        sponsor = Sponsor.objects.select_related('city', 'city__country').get(id=sponsor_id)
    except Sponsor.DoesNotExist:
        return JsonResponse({'error': 'Sponsor no encontrado'}, status=404)

    def f(d):
        return d.strftime('%Y-%m-%d') if d else ''

    data = {
        'id': sponsor.id,
        'title_id': sponsor.title_id or '', 'directed_id': sponsor.directed_id or '',
        'last_name_1': sponsor.last_name_1 or '', 'last_name_2': sponsor.last_name_2 or '',
        'first_name_1': sponsor.first_name_1 or '', 'first_name_2': sponsor.first_name_2 or '',
        'free_union': sponsor.free_union, 'profession': sponsor.profession or '',
        'address': sponsor.address or '', 'street': sponsor.street or '',
        'phone_1': sponsor.phone_1 or '', 'phone_2': sponsor.phone_2 or '', 'fax': sponsor.fax or '',
        'email': sponsor.email or '', 'email_2': sponsor.email_2 or '', 'email_3': sponsor.email_3 or '',
        'report_email': sponsor.report_email, 'only_email': sponsor.only_email,
        'only_easter_rep': sponsor.only_easter_rep, 'financial_report': sponsor.financial_report,
        'language': sponsor.language or '', 'annex': sponsor.annex or '', 'contact': sponsor.contact or '',
        'addressed_to': sponsor.addressed_to or '', 'addressed_to_2': sponsor.addressed_to_2 or '',
        'visitor': sponsor.visitor, 'visitor_date': f(sponsor.visitor_date),
        'sponsor_bool': sponsor.sponsor, 'godfather': sponsor.godfather, 'member': sponsor.member,
        'former_volunteer': sponsor.former_volunteer, 'volunt_dep_date': f(sponsor.volunt_dep_date),
        'no_correspondence': sponsor.no_correspondence, 'deceased': sponsor.deceased,
        'deactivated': sponsor.deactivated, 'expect_reaction': sponsor.expect_reaction,
        'bad_address': sponsor.bad_address, 'private': sponsor.private,
        'first_contact': f(sponsor.first_contact), 'last_contact': f(sponsor.last_contact),
        'note_1': sponsor.note_1 or '', 'note_2': sponsor.note_2 or '',
        'date_of_birth': f(sponsor.date_of_birth), 'date_of_birth_2': f(sponsor.date_of_birth_2),
        'gender': sponsor.gender or '', 'civil_status': sponsor.civil_status or '',
        'nationality': sponsor.nationality or '', 'imprimir': sponsor.imprimir,
        'deactivate_soon': sponsor.deactivate_soon, 'recog_2010': sponsor.recog_2010,
        'recog_2020_blanket': sponsor.recog_2020_blanket, 'recog_2020_plate': sponsor.recog_2020_plate,
        'padrino_ch_d': sponsor.padrino_ch_d or '',
        'city_id': sponsor.city_id or '',
        'zip_code': (sponsor.city.zip_code or '') if sponsor.city else '',
        'country': (sponsor.city.country.name if sponsor.city and sponsor.city.country else ''),
    }
    return JsonResponse(data, safe=False)


@login_required
def add_sponsor(request):
    if request.method == "POST":
        form = SponsorForm(request.POST)
        if form.is_valid():
            # 'city' ahora viene en el form; antes se excluía y quedaba NULL → IntegrityError
            form.save()
            messages.success(request, "Sponsor agregado correctamente.")
            return redirect("sponsors:sponsor_list")
        messages.error(request, "Error al agregar el sponsor. Revisa los campos.")
    else:
        form = SponsorForm()
    return render(request, "sponsors/form_sponsor.html", {'form': form, 'edit_mode': False})


@login_required
def edit_sponsor(request, sponsor_id):
    sponsor = get_object_or_404(Sponsor, id=sponsor_id)
    if request.method == "POST":
        form = SponsorForm(request.POST, instance=sponsor)
        if form.is_valid():
            form.save()
            messages.success(request, "Sponsor actualizado correctamente.")
            return redirect("sponsors:sponsor_list")
        messages.error(request, "Error al actualizar el sponsor.")
    else:
        form = SponsorForm(instance=sponsor)
    return render(request, "sponsors/form_sponsor.html",
                  {'form': form, 'edit_mode': True, 'sponsor': sponsor})


@login_required
@require_POST
def delete_sponsor(request, sponsor_id):
    """Elimina un sponsor. Solo POST: antes se borraba con un GET sin confirmación."""
    sponsor = get_object_or_404(Sponsor, id=sponsor_id)
    sponsor.delete()
    messages.success(request, "Sponsor eliminado correctamente.")
    return redirect("sponsors:sponsor_list")


# ══════════════════════ Relacionados con el sponsor ══════════════════════

@login_required
def add_godfather(request):
    if request.method == "POST":
        form = GodfatherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Padrinazgo agregado correctamente.")
            return redirect('sponsors:add_godfather')
        messages.error(request, "Error al agregar el padrinazgo.")
    else:
        form = GodfatherForm()
    lista = Godfather.objects.select_related('sponsor').order_by('-id')[:_PER_PAGE]
    return render(request, 'sponsors/form_godfather.html',
                  {'form': form, 'godfather_list': lista, 'total': Godfather.objects.count()})


@login_required
def add_correspondence(request):
    if request.method == "POST":
        form = CorrespondenceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Correspondencia agregada correctamente.")
            return redirect('sponsors:add_correspondence')
        messages.error(request, "Error al agregar la correspondencia.")
    else:
        form = CorrespondenceForm()
    lista = Correspondence.objects.select_related('sponsor').order_by('-date', '-id')[:_PER_PAGE]
    return render(request, 'sponsors/form_correspondence.html',
                  {'form': form, 'correspondence_list': lista,
                   'total': Correspondence.objects.count()})


@login_required
def add_income(request):
    if request.method == "POST":
        form = IncomeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ingreso agregado correctamente.")
            return redirect('sponsors:add_income')
        messages.error(request, "Error al agregar el ingreso.")
    else:
        form = IncomeForm()
    qs = Income.objects.select_related('sponsor').order_by('-date', '-id')
    page = Paginator(qs, _PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'sponsors/form_income.html',
                  {'form': form, 'page_obj': page, 'income_list': page.object_list,
                   'total': Income.objects.count()})


@login_required
def add_sponsored(request):
    if request.method == "POST":
        form = SponsoredForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Apadrinado agregado correctamente.")
            return redirect('sponsors:add_sponsored')
        messages.error(request, "Error al agregar el apadrinado.")
    else:
        form = SponsoredForm()
    lista = Sponsored.objects.order_by('last_name_1', 'first_name_1')
    return render(request, 'sponsors/form_sponsored.html',
                  {'form': form, 'sponsored_list': lista, 'total': lista.count()})


# ══════════════════════ Autocompletar ══════════════════════

def _sugerencias(campo, query):
    """Valores distintos y acotados (antes: sin límite y con duplicados)."""
    if not query:
        return []
    qs = (Sponsor.objects.filter(**{f'{campo}__icontains': query})
          .values_list(campo, flat=True).distinct()[:_SEARCH_LIMIT])
    return [v for v in qs if v]


@login_required
def search_name(request):
    return JsonResponse(_sugerencias('first_name_1', request.GET.get('q', '').strip()), safe=False)


@login_required
def search_lastname(request):
    return JsonResponse(_sugerencias('last_name_1', request.GET.get('q', '').strip()), safe=False)


@login_required
def search_id(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)
    ids = (Sponsor.objects.filter(id__icontains=q)
           .values_list('id', flat=True).order_by('id')[:_SEARCH_LIMIT])
    return JsonResponse(list(ids), safe=False)
