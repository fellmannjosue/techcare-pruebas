# <--- hecho por claude code: ANA Network Manager — lógica de negocio (IPAM/capacidad/validaciones)
import ipaddress
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import VLAN, IPAddress


# ── Utilidades de red ──────────────────────────────────────────────────────
def red_de(cidr):
    try:
        return ipaddress.ip_network(str(cidr), strict=False)
    except (ValueError, TypeError):
        return None


def ip_valida(txt):
    try:
        return ipaddress.ip_address(str(txt))
    except (ValueError, TypeError):
        return None


def a_int(txt):
    ip = ip_valida(txt)
    return int(ip) if ip is not None else None


def _en_red(ip, red):
    return ip is not None and red is not None and ip in red


# ── Validación de VLAN ─────────────────────────────────────────────────────
def validar_vlan(vlan):
    """Devuelve lista de errores (vacía = ok). No guarda nada."""
    errores = []
    if not (1 <= int(vlan.vlan_id) <= 4094):
        errores.append('El VLAN ID debe estar entre 1 y 4094.')
    red = red_de(vlan.subred)
    if red is None:
        errores.append('La subred (CIDR) no es válida. Ej: 192.168.60.0/24')
        return errores  # sin red no se puede validar el resto

    net, bcast = red.network_address, red.broadcast_address

    def chk(campo, etiqueta, permitir_borde=False):
        val = getattr(vlan, campo, None)
        if not val:
            return None
        ip = ip_valida(val)
        if ip is None:
            errores.append(f'{etiqueta}: dirección inválida.')
            return None
        if ip not in red:
            errores.append(f'{etiqueta} ({val}) está fuera de la subred {vlan.subred}.')
        elif not permitir_borde and ip in (net, bcast):
            errores.append(f'{etiqueta} no puede ser la dirección de red ni el broadcast.')
        return ip

    chk('gateway', 'Gateway')
    ini_a = chk('ip_inicial_asignable', 'IP inicial asignable')
    fin_a = chk('ip_final_asignable', 'IP final asignable')
    ini_r = chk('ip_inicio_reservado', 'Inicio reservado')
    fin_r = chk('ip_fin_reservado', 'Fin reservado')
    ini_d = chk('ip_inicio_dhcp', 'Inicio DHCP')
    fin_d = chk('ip_fin_dhcp', 'Fin DHCP')

    def orden(a, b, etq):
        if a and b and int(a) > int(b):
            errores.append(f'{etq}: el inicio no puede ser mayor que el fin.')

    orden(ini_a, fin_a, 'Rango asignable')
    orden(ini_r, fin_r, 'Rango reservado')
    orden(ini_d, fin_d, 'Rango DHCP')

    # reservado y DHCP NO deben superponerse
    if all([ini_r, fin_r, ini_d, fin_d]):
        if int(ini_r) <= int(fin_d) and int(ini_d) <= int(fin_r):
            errores.append('El rango reservado y el rango DHCP se superponen.')
    return errores


def subredes_solapadas(cidr, exclude_pk=None):
    """VLANs cuya subred se solapa con 'cidr' (para avisar al crear/editar)."""
    red = red_de(cidr)
    if red is None:
        return []
    out = []
    qs = VLAN.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    for v in qs:
        r = red_de(v.subred)
        if r is not None and red.overlaps(r):
            out.append(v)
    return out


# ── Capacidad (usa el RANGO configurado, no las 254 completas) ─────────────
def _rango_asignable(vlan):
    """(inicio_int, fin_int) del rango asignable; si no está configurado, usa los hosts de la subred."""
    ini = a_int(vlan.ip_inicial_asignable)
    fin = a_int(vlan.ip_final_asignable)
    if ini and fin and ini <= fin:
        return ini, fin
    red = red_de(vlan.subred)
    if red is None:
        return None, None
    hosts = list(red.hosts())
    if not hosts:
        return None, None
    return int(hosts[0]), int(hosts[-1])


def capacidad_vlan(vlan):
    """Dict con capacidad, usadas, libres y % — SIEMPRE sobre el rango configurado."""
    ini, fin = _rango_asignable(vlan)
    if not ini or not fin:
        return {'capacidad': 0, 'usadas': 0, 'libres': 0, 'pct_ocupacion': 0, 'pct_libre': 100, 'estado': 'normal'}
    capacidad = fin - ini + 1
    if vlan.limite_dispositivos:
        capacidad = min(capacidad, int(vlan.limite_dispositivos))
    usadas = (IPAddress.objects
              # <--- hecho por claude code: una IP en 'conflicto' está ocupada (no disponible) → cuenta como usada
              .filter(vlan=vlan, estado__in=['asignada', 'reservada', 'dhcp', 'conflicto'],
                      direccion_int__gte=ini, direccion_int__lte=fin)
              .count())
    libres = max(0, capacidad - usadas)
    pct_ocup = round(usadas / capacidad * 100, 1) if capacidad else 0
    pct_libre = round(100 - pct_ocup, 1)
    umbral = int(vlan.porcentaje_alerta or 20)
    if libres <= 0:
        estado = 'agotado'
    elif pct_libre <= 10:
        estado = 'critico'
    elif pct_libre <= umbral:
        estado = 'advertencia'
    else:
        estado = 'normal'
    return {'capacidad': capacidad, 'usadas': usadas, 'libres': libres,
            'pct_ocupacion': pct_ocup, 'pct_libre': pct_libre, 'estado': estado}


def recalcular_capacidad(vlan, guardar=True, notificar=True):
    """Actualiza cache (cantidad_ip_disponibles, estado_capacidad) y avisa si quedan ≤10 IP."""
    cap = capacidad_vlan(vlan)
    antes = vlan.cantidad_ip_disponibles
    vlan.cantidad_ip_disponibles = cap['libres']
    vlan.estado_capacidad = cap['estado']
    if guardar:
        VLAN.objects.filter(pk=vlan.pk).update(
            cantidad_ip_disponibles=cap['libres'], estado_capacidad=cap['estado'])
    # Notificación cuando quedan solamente ≤10 IP (al cruzar el umbral)
    if notificar and cap['libres'] <= 10 and (antes is None or antes > 10):
        _notificar(f'VLAN {vlan.vlan_id} ({vlan.nombre}) con solo {cap["libres"]} IP disponibles.')
    return cap


def _notificar(mensaje):
    try:
        from core.utils_notifications import crear_notificacion
        from django.contrib.auth import get_user_model
        U = get_user_model()
        for u in U.objects.filter(is_superuser=True):
            crear_notificacion(u, 'Red · Capacidad', mensaje, tipo='warning')
    except Exception:
        pass   # nunca romper el flujo por la notificación


# ── Generación de IPs de una VLAN (bajo demanda) ───────────────────────────
@transaction.atomic
def generar_ips_vlan(vlan):
    """Crea las filas IPAddress del rango asignable que aún no existan. Idempotente."""
    ini, fin = _rango_asignable(vlan)
    if not ini or not fin:
        return 0
    existentes = set(IPAddress.objects.filter(vlan=vlan).values_list('direccion_int', flat=True))
    ini_r = a_int(vlan.ip_inicio_reservado); fin_r = a_int(vlan.ip_fin_reservado)
    ini_d = a_int(vlan.ip_inicio_dhcp);      fin_d = a_int(vlan.ip_fin_dhcp)
    creadas = 0
    nuevas = []
    for n in range(ini, fin + 1):
        if n in existentes:
            continue
        dirs = str(ipaddress.ip_address(n))
        estado = 'libre'
        if ini_d and fin_d and ini_d <= n <= fin_d:
            estado = 'dhcp'
        elif ini_r and fin_r and ini_r <= n <= fin_r:
            estado = 'reservada'
        nuevas.append(IPAddress(vlan=vlan, direccion=dirs, direccion_int=n, estado=estado))
        creadas += 1
    IPAddress.objects.bulk_create(nuevas, batch_size=500)
    recalcular_capacidad(vlan)
    return creadas


# ── Reglas de IP: rango, duplicados ────────────────────────────────────────
def dentro_rango_asignable(vlan, ip_txt):
    n = a_int(ip_txt)
    ini, fin = _rango_asignable(vlan)
    return bool(n and ini and fin and ini <= n <= fin)


def ip_duplicada(vlan, ip_txt, exclude_pk=None):
    n = a_int(ip_txt)
    if n is None:
        return False
    qs = IPAddress.objects.filter(vlan=vlan, direccion_int=n)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def mac_duplicada(mac, exclude_pk=None):
    mac = (mac or '').strip()
    if not mac:
        return False
    qs = IPAddress.objects.filter(mac__iexact=mac)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


# ── Operaciones IPAM (con histórico, liberar SIN borrar) ───────────────────
@transaction.atomic
def asignar_ip(ip_obj, *, dispositivo=None, hostname='', mac='', tipo='estatica',
               responsable='', descripcion='', usuario=None):
    """Punto 1: bloquea fuera del rango. Punto 2: bloquea duplicados."""
    if not dentro_rango_asignable(ip_obj.vlan, ip_obj.direccion):
        raise ValidationError('La dirección está fuera del rango autorizado de la VLAN.')
    if mac and mac_duplicada(mac, exclude_pk=ip_obj.pk):
        raise ValidationError(f'La MAC {mac} ya está registrada en otra IP.')
    ip_obj.estado = 'asignada'
    ip_obj.tipo = tipo
    ip_obj.dispositivo = dispositivo
    ip_obj.hostname = hostname
    ip_obj.mac = mac
    ip_obj.responsable = responsable
    ip_obj.descripcion = descripcion
    ip_obj.fecha_asignacion = timezone.now()
    ip_obj.fecha_liberacion = None
    ip_obj.modificado_por = usuario
    ip_obj.save()
    recalcular_capacidad(ip_obj.vlan)
    return ip_obj


@transaction.atomic
def reservar_ip(ip_obj, *, motivo='', usuario=None):
    ip_obj.estado = 'reservada'
    ip_obj.descripcion = motivo or ip_obj.descripcion
    ip_obj.modificado_por = usuario
    ip_obj.save()
    recalcular_capacidad(ip_obj.vlan)
    return ip_obj


@transaction.atomic
def liberar_ip(ip_obj, *, usuario=None):
    """Libera SIN borrar: conserva el registro y su historial (simple_history)."""
    ip_obj.estado = 'libre'
    ip_obj.dispositivo = None
    ip_obj.interfaz = None
    ip_obj.hostname = ''
    ip_obj.mac = ''
    ip_obj.tipo = ''
    ip_obj.fecha_liberacion = timezone.now()
    ip_obj.modificado_por = usuario
    ip_obj.save()
    recalcular_capacidad(ip_obj.vlan)
    return ip_obj


# ═══════════════════════ FASE 2 · Switches / Puertos / Enlaces ═══════════════════════
from django.db.models import Q as _Q
from .models import Switch, SwitchPort, NetworkLink   # noqa: E402


def color_puerto(p):
    """Color del puerto para el mapa frontal del switch."""
    if p.estado_fisico == 'bloqueado':
        return '#d63939'                       # rojo: bloqueado/error
    if p.modo_vlan == 'trunk':
        return '#206bc4'                       # azul: trunk
    if p.modo_vlan == 'access' and p.vlan_access_id and p.vlan_access:
        return p.vlan_access.color or '#2fb344'  # color de la VLAN access
    if p.estado_fisico == 'up':
        return '#2fb344'                       # verde: activo
    return '#adb5bd'                           # gris: libre/desconocido


def validar_puerto(p):
    """Reglas: Access solo 1 VLAN; Trunk con nativa + tagged; PoE coherente."""
    errores = []
    if p.modo_vlan == 'access' and p.vlans_tagged.strip():
        errores.append('Un puerto Access no puede tener VLAN tagged (solo su VLAN principal).')
    if p.poe_habilitado and not p.poe_disponible:
        errores.append('El puerto tiene PoE habilitado pero no dispone de PoE (requiere inyector).')
    return errores


def validar_link(link):
    """Devuelve (errores, avisos). Errores bloquean; avisos solo alertan."""
    errores, avisos = [], []
    # puerto consigo mismo
    if (link.puerto_origen_id and link.puerto_destino_id
            and link.puerto_origen_id == link.puerto_destino_id):
        errores.append('Un puerto no puede conectarse consigo mismo.')
    if (link.dispositivo_origen_id and link.dispositivo_destino_id
            and link.dispositivo_origen_id == link.dispositivo_destino_id
            and not (link.puerto_origen_id and link.puerto_destino_id)):
        avisos.append('Origen y destino son el mismo dispositivo.')
    # enlace duplicado (mismo par de puertos, cualquier sentido)
    if link.puerto_origen_id and link.puerto_destino_id:
        dup = NetworkLink.objects.filter(
            _Q(puerto_origen_id=link.puerto_origen_id, puerto_destino_id=link.puerto_destino_id) |
            _Q(puerto_origen_id=link.puerto_destino_id, puerto_destino_id=link.puerto_origen_id))
        if link.pk:
            dup = dup.exclude(pk=link.pk)
        if dup.exists():
            avisos.append('Ya existe un enlace entre esos mismos puertos (posible duplicado).')
    # trunk hacia switch NO administrable
    if link.modo == 'trunk':
        for dev in (link.dispositivo_origen, link.dispositivo_destino):
            sw = getattr(dev, 'switch', None) if dev else None
            if sw and not sw.administrable:
                avisos.append(f'Trunk hacia un switch NO administrable ({sw.nombre}).')
    return errores, avisos


def alertas_switch(switch):
    """Avisos a nivel switch: trunk en no administrable, PoE incoherente."""
    avisos = []
    puertos = list(switch.puertos.all())
    if not switch.administrable and any(p.modo_vlan == 'trunk' for p in puertos):
        avisos.append('Switch NO administrable con puertos en modo trunk (no soportado).')
    for p in puertos:
        avisos.extend(validar_puerto(p))
    return avisos


def detectar_ciclos():
    """Detección simple de ciclos en el grafo de enlaces (por dispositivo)."""
    from collections import defaultdict
    ady = defaultdict(set)
    for l in NetworkLink.objects.all():
        if l.dispositivo_origen_id and l.dispositivo_destino_id:
            ady[l.dispositivo_origen_id].add(l.dispositivo_destino_id)
            ady[l.dispositivo_destino_id].add(l.dispositivo_origen_id)
    visitados, en_ciclo = set(), set()

    def dfs(nodo, padre):
        visitados.add(nodo)
        for v in ady[nodo]:
            if v == padre:
                continue
            if v in visitados:
                en_ciclo.add(nodo); en_ciclo.add(v)
            elif dfs(v, nodo):
                return True
        return False

    for n in list(ady):
        if n not in visitados:
            dfs(n, None)
    return en_ciclo


# ═══════════════════════ FASE 4 · Pruebas de conectividad ═══════════════════════
# <--- hecho por claude code: ping ICMP (una petición, timeout corto) sin bloquear de más.
import subprocess as _subprocess
import re as _re


def ping_host(ip, timeout=1):
    """Devuelve (ok: bool, latencia_ms: float|None). No lanza excepciones."""
    if not ip:
        return (False, None)
    try:
        out = _subprocess.run(['ping', '-c', '1', '-W', str(timeout), str(ip)],
                              capture_output=True, text=True, timeout=timeout + 2)
        if out.returncode != 0:
            return (False, None)
        m = _re.search(r'time[=<]\s*([\d.]+)', out.stdout)
        return (True, float(m.group(1)) if m else None)
    except Exception:
        return (False, None)


# ═══════════════════════ FASE 4 · Migración REAL de VLAN ═══════════════════════
# <--- hecho por claude code: mueve dispositivos a otra VLAN asignándoles una IP libre del
# rango asignable de destino y liberando la IP anterior en el IPAM. Cada equipo va en su
# propia transacción: si uno falla, se revierte SOLO ese y se continúa con el siguiente.
def _ip_libre_en(vlan):
    """Primera IP 'libre' dentro del rango asignable de la VLAN (o None)."""
    ini, fin = _rango_asignable(vlan)
    if ini is None:
        return None
    return (IPAddress.objects
            .filter(vlan=vlan, estado='libre', direccion_int__gte=ini, direccion_int__lte=fin)
            .order_by('direccion_int').first())


def migrar_dispositivos_vlan(dispositivos, destino, *, usuario=None, motivo=''):
    """Devuelve {'ok': [...], 'error': [...]} con el detalle por dispositivo."""
    ok, error = [], []
    for d in dispositivos:
        try:
            with transaction.atomic():
                ip_antes = d.ip
                candidata = _ip_libre_en(destino)
                if candidata is None:
                    raise ValidationError(f'La VLAN {destino.vlan_id} no tiene IP libres en su rango asignable.')
                # bloqueo de fila: evita que dos migraciones simultáneas tomen la misma IP
                nueva = IPAddress.objects.select_for_update().get(pk=candidata.pk)
                if nueva.estado != 'libre':
                    raise ValidationError(f'La IP {nueva.direccion} fue tomada por otro proceso; reintenta.')
                # 1) liberar la IP anterior en el IPAM (si estaba registrada)
                if ip_antes:
                    for vieja in IPAddress.objects.filter(direccion=ip_antes).exclude(estado='libre'):
                        liberar_ip(vieja, usuario=usuario)
                # 2) asignar la nueva IP al dispositivo (valida rango y MAC duplicada)
                asignar_ip(nueva, dispositivo=d, hostname=(d.hostname or ''), mac=(d.mac_principal or ''),
                           tipo='estatica', responsable=(d.responsable or ''),
                           descripcion=f'Migración VLAN: {motivo}'[:200], usuario=usuario)
                # 3) actualizar el dispositivo
                d.vlan = destino
                d.ip = nueva.direccion
                d.modificado_por = usuario
                d.save(update_fields=['vlan', 'ip', 'modificado_por', 'fecha_modificado'])
            ok.append({'dispositivo': d.nombre, 'ip_antes': ip_antes, 'ip_despues': nueva.direccion})
        except Exception as e:  # noqa: BLE001 — se registra y se sigue con el siguiente equipo
            msg = '; '.join(getattr(e, 'messages', None) or [str(e)])
            error.append({'dispositivo': d.nombre, 'error': msg[:200]})
    return {'ok': ok, 'error': error}
