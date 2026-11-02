# datashow/views.py
# <--- hecho por claude code (02-nov-2026): Solicitud de DataShow — calendario de reservas + autorización de Soporte.
import calendar as _cal
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils_notifications import crear_notificacion
from .forms import ReservaForm
from .models import ReservaDataShow
from .services import reservas_en_conflicto

MESES_ES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
DIAS_ES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def _es_soporte(user):
    # <--- por ahora SOLO superusuario revisa/autoriza (decisión del usuario, 02-nov-2026)
    return user.is_superuser


def _mes_valido(anio, mes):
    try:
        anio = int(anio); mes = int(mes)
        if 1 <= mes <= 12 and 2000 <= anio <= 2100:
            return anio, mes
    except (TypeError, ValueError):
        pass
    hoy = timezone.now().date()
    return hoy.year, hoy.month


def _construir_calendario(anio, mes, reservas):
    """Matriz de semanas (lunes→domingo) con las reservas activas por día."""
    hoy = timezone.now().date()
    por_dia = {}
    for r in reservas:
        por_dia.setdefault(r.fecha, []).append(r)

    cal = _cal.Calendar(firstweekday=0)  # lunes
    semanas = []
    for semana in cal.monthdatescalendar(anio, mes):
        fila = []
        for d in semana:
            fila.append({
                'dia': d.day,
                'fecha': d,
                'iso': d.isoformat(),
                'en_mes': (d.month == mes),
                'es_hoy': (d == hoy),
                'es_pasado': (d < hoy),
                'reservas': sorted(por_dia.get(d, []), key=lambda x: x.hora_inicio),
            })
        semanas.append(fila)
    return semanas


@login_required
def index(request):
    hoy = timezone.now().date()
    anio, mes = _mes_valido(request.GET.get('anio'), request.GET.get('mes'))

    # Reservas activas del mes (para el calendario; todos ven la disponibilidad)
    primero = datetime.date(anio, mes, 1)
    ult_dia = _cal.monthrange(anio, mes)[1]
    ultimo = datetime.date(anio, mes, ult_dia)
    activas_mes = (ReservaDataShow.objects
                   .filter(estado__in=ReservaDataShow.ESTADOS_ACTIVOS,
                           fecha__gte=primero, fecha__lte=ultimo)
                   .select_related('datashow', 'solicitante'))
    semanas = _construir_calendario(anio, mes, activas_mes)

    # Navegación de mes
    mes_prev = (primero - datetime.timedelta(days=1))
    mes_sig = (ultimo + datetime.timedelta(days=1))

    es_soporte = _es_soporte(request.user)

    # Mis solicitudes (o todas, si es soporte y lo pide)
    ver_todas = es_soporte and request.GET.get('todas') == '1'
    mis = ReservaDataShow.objects.select_related('datashow', 'solicitante', 'revisado_por')
    if not ver_todas:
        mis = mis.filter(solicitante=request.user)
    mis = mis.order_by('-fecha', 'hora_inicio')[:100]

    # Cola de pendientes (solo soporte)
    pendientes = []
    if es_soporte:
        pendientes = (ReservaDataShow.objects
                      .filter(estado=ReservaDataShow.ESTADO_PENDIENTE)
                      .select_related('datashow', 'solicitante')
                      .order_by('fecha', 'hora_inicio'))

    from django.shortcuts import render
    return render(request, 'datashow/index.html', {
        'form': ReservaForm(),
        'semanas': semanas,
        'dias_cabecera': DIAS_ES,
        'anio': anio, 'mes': mes,
        'mes_nombre': MESES_ES[mes].capitalize(),
        'nav_prev': {'anio': mes_prev.year, 'mes': mes_prev.month},
        'nav_sig': {'anio': mes_sig.year, 'mes': mes_sig.month},
        'hoy': hoy,
        'hoy_iso': hoy.isoformat(),
        'es_soporte': es_soporte,
        'ver_todas': ver_todas,
        'mis': mis,
        'pendientes': pendientes,
        'n_pendientes': len(pendientes),
    })


@login_required
@require_POST
def crear(request):
    form = ReservaForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            reserva = form.save(commit=False)
            reserva.solicitante = request.user
            reserva.estado = ReservaDataShow.ESTADO_PENDIENTE
            reserva.creado_por = request.user
            reserva.modificado_por = request.user
            reserva.save()
        # Avisar a los que autorizan (superusuarios)
        _avisar_soporte_nueva(reserva)
        messages.success(request, 'Solicitud enviada. Soporte la revisará y la autorizará.')
    else:
        errores = '; '.join(
            f'{form.fields[c].label or c}: {e[0]}' for c, e in form.errors.items()
        ) or 'Revisa los datos del formulario.'
        messages.error(request, f'No se pudo enviar la solicitud. {errores}')
    destino = reverse('datashow:index')
    if form.is_valid() and form.cleaned_data.get('fecha'):
        f = form.cleaned_data['fecha']
        destino += f'?anio={f.year}&mes={f.month}'
    return redirect(destino)


@login_required
@require_POST
def revisar(request, pk):
    if not _es_soporte(request.user):
        messages.error(request, 'No tienes permiso para autorizar solicitudes.')
        return redirect('datashow:index')

    reserva = get_object_or_404(ReservaDataShow, pk=pk)
    accion = request.POST.get('accion')
    comentario = (request.POST.get('comentario') or '').strip()

    if reserva.estado != ReservaDataShow.ESTADO_PENDIENTE:
        messages.warning(request, 'Esa solicitud ya no está pendiente.')
        return redirect('datashow:index')

    if accion == 'autorizar':
        # Re-chequear conflicto al autorizar (pudo autorizarse otra entre tanto)
        conflicto = reservas_en_conflicto(
            reserva.datashow_id, reserva.fecha, reserva.hora_inicio,
            reserva.hora_fin, excluir_id=reserva.pk
        ).filter(estado=ReservaDataShow.ESTADO_AUTORIZADA).first()
        if conflicto:
            messages.error(request, (
                f'No se puede autorizar: {reserva.datashow.asset_id} ya está '
                f'autorizado el {reserva.fecha:%d/%m/%Y} de {conflicto.rango_horario}.'
            ))
            return redirect('datashow:index')
        reserva.estado = ReservaDataShow.ESTADO_AUTORIZADA
        msg_user = (f'Tu reserva del DataShow {reserva.datashow.asset_id} para el '
                    f'{reserva.fecha:%d/%m/%Y} ({reserva.rango_horario}) fue AUTORIZADA.')
        tipo_notif = 'success'
        messages.success(request, 'Solicitud autorizada.')
    elif accion == 'rechazar':
        reserva.estado = ReservaDataShow.ESTADO_RECHAZADA
        extra = f' Motivo: {comentario}' if comentario else ''
        msg_user = (f'Tu reserva del DataShow {reserva.datashow.asset_id} para el '
                    f'{reserva.fecha:%d/%m/%Y} ({reserva.rango_horario}) fue RECHAZADA.{extra}')
        tipo_notif = 'warning'
        messages.success(request, 'Solicitud rechazada.')
    else:
        messages.error(request, 'Acción no válida.')
        return redirect('datashow:index')

    reserva.comentario_soporte = comentario
    reserva.revisado_por = request.user
    reserva.revisado_en = timezone.now()
    reserva.modificado_por = request.user
    reserva.save()

    crear_notificacion(reserva.solicitante, msg_user, modulo='datashow', tipo=tipo_notif)
    return redirect('datashow:index')


@login_required
@require_POST
def cancelar(request, pk):
    reserva = get_object_or_404(ReservaDataShow, pk=pk)
    if not reserva.puede_cancelar(request.user):
        messages.error(request, 'No puedes cancelar esa reserva.')
        return redirect('datashow:index')

    era_autorizada = (reserva.estado == ReservaDataShow.ESTADO_AUTORIZADA)
    reserva.estado = ReservaDataShow.ESTADO_CANCELADA
    reserva.modificado_por = request.user
    reserva.save()
    messages.success(request, 'Reserva cancelada.')

    # Si un superusuario cancela la de otro, avisar al solicitante
    if request.user.id != reserva.solicitante_id:
        crear_notificacion(
            reserva.solicitante,
            (f'Tu reserva del DataShow {reserva.datashow.asset_id} para el '
             f'{reserva.fecha:%d/%m/%Y} ({reserva.rango_horario}) fue CANCELADA por Soporte.'),
            modulo='datashow', tipo='warning'
        )
    return redirect('datashow:index')


def _avisar_soporte_nueva(reserva):
    """Notifica a los superusuarios activos que hay una nueva solicitud por revisar."""
    try:
        url = reverse('datashow:index')
    except Exception:
        url = '/datashow/'
    destinatarios = User.objects.filter(is_superuser=True, is_active=True)
    mensaje = (f'{reserva.solicitante.get_full_name() or reserva.solicitante.username} '
               f'solicitó el DataShow {reserva.datashow.asset_id} para el '
               f'{reserva.fecha:%d/%m/%Y} ({reserva.rango_horario}). Revisar y autorizar.')
    for u in destinatarios:
        crear_notificacion(u, mensaje, modulo='datashow', tipo='info',
                           extra={'url': url}, enviar_correo=False)
