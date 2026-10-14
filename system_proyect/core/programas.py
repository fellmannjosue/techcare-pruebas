# core/programas.py
# <--- hecho por claude code (10-sep-2026): programas que el superusuario puede OCULTAR a todos
"""Registro de los programas (módulos) del sistema que se pueden desactivar desde
Configuración → Seguridad.

Ocultar un programa significa, para TODOS los usuarios (menos el superusuario):
  - desaparece de los menús (sidebar, Panel Principal, dashboards por rol);
  - sus rutas quedan bloqueadas por el middleware (pantalla "Programa desactivado"),
    así tampoco se entra con la URL guardada.
El superusuario lo sigue viendo en su Panel Principal con la etiqueta "Oculto" y
puede entrar por URL para revisarlo.

Se guarda en constance `PROGRAMAS_OCULTOS` como lista JSON de claves.
`flags` son las variables de contexto (nav_* / show_*) que se apagan al ocultarlo.
"""
import json

PROGRAMAS = [
    {'key': 'tickets',       'label': 'Sistema de Tickets',           'icon': 'ti-ticket',
     'prefijos': ('/tickets/',),
     'flags': ('nav_tickets', 'nav_tickets_tecnico', 'show_tickets')},
    {'key': 'servicio_tecnico', 'label': 'Control y Servicio Técnico', 'icon': 'ti-headset',   # <--- hecho por claude code (28-sep-2026)
     'prefijos': ('/servicio-tecnico/',),
     'flags': ('nav_servicio', 'show_servicio')},
    {'key': 'mantenimiento_mecanico', 'label': 'Mantenimiento Mecánico', 'icon': 'ti-engine',   # <--- hecho por claude code (01-oct-2026; 12-oct-2026 incluye vehículos)
     'prefijos': ('/mantenimiento-mecanico/', '/mantenimiento-vehiculos/'),
     'flags': ('nav_mant_mecanico', 'nav_mm_insumos', 'nav_vehiculos', 'show_mant_mecanico', 'show_vehiculos')},
    {'key': 'inventario',    'label': 'Inventario',                   'icon': 'ti-package',
     'prefijos': ('/inventario/',),
     'flags': ('nav_inventory', 'show_inventory')},
    {'key': 'mantenimiento', 'label': 'Mantenimiento',                'icon': 'ti-tool',
     'prefijos': ('/mantenimiento/',),
     'flags': ('nav_maintenance', 'show_maintenance')},
    {'key': 'camaras',       'label': 'Inventario y Mant. de Cámaras', 'icon': 'ti-camera',
     'prefijos': ('/inventario-camaras/',),
     'flags': ('show_camaras_inv',)},
    {'key': 'desarrollo',    'label': 'Gestión de Desarrollo',        'icon': 'ti-clipboard-list',
     'prefijos': ('/desarrollo/',),
     'flags': ('nav_desarrollo',)},
    {'key': 'agendas',       'label': 'Agendas',                      'icon': 'ti-calendar-week',
     'prefijos': ('/agendas/',),
     'flags': ('show_agendas',)},
    {'key': 'tutorias',      'label': 'Tutorías (convocatorias)',     'icon': 'ti-school',
     'prefijos': ('/conducta/tutorias/',),
     'flags': ()},
    {'key': 'progress',      'label': 'Progress Report',              'icon': 'ti-chart-line',
     'prefijos': ('/conducta/progress_report/', '/conducta/progress-report/'),
     'flags': ('nav_solo_progress',)},
    {'key': 'notas_parcial', 'label': 'Notas Mitad de Parcial',       'icon': 'ti-file-certificate',
     'prefijos': ('/notas-parcial/',),
     'flags': ()},
    {'key': 'ingresos_notas', 'label': 'Ingresos de Notas',           'icon': 'ti-list-numbers',
     'prefijos': ('/ingresos-notas/',),
     'flags': ('nav_ingresos_notas',)},
    {'key': 'ruteo',         'label': 'Ruteo Reportes BL',            'icon': 'ti-route',
     'prefijos': ('/conducta/routing-bl/',),
     'flags': ('nav_ruteo_bl',)},
    {'key': 'salidas',       'label': 'Salidas al baño (Colegio y CFP)', 'icon': 'ti-door-exit',
     'prefijos': ('/salidas-bano/',),
     'flags': ('nav_salidas_bano', 'nav_salidas_bano_cfp', 'show_salidas_bano', 'show_salidas_bano_cfp')},
    {'key': 'enfermeria',    'label': 'Enfermería',                   'icon': 'ti-stethoscope',
     'prefijos': ('/enfermeria/',),
     'excepto':  ('/enfermeria/directorio/',),    # el Directorio lo usan los coordinadores
     'flags': ('nav_enfermeria', 'show_enfermeria')},
    {'key': 'reloj',         'label': 'Reloj',                        'icon': 'ti-clock',
     'prefijos': ('/reloj/',),
     'flags': ('nav_reloj', 'show_reloj')},
    {'key': 'sponsors',      'label': 'Sponsors',                     'icon': 'ti-heart-handshake',
     'prefijos': ('/sponsors/',),
     'flags': ('nav_sponsors', 'show_sponsors')},
    {'key': 'contabilidad',  'label': 'Contabilidad',                 'icon': 'ti-report-money',
     'prefijos': ('/contabilidad/',),
     'flags': ('nav_contabilidad',)},
    {'key': 'red',           'label': 'Red (ANA Network Manager)',    'icon': 'ti-network',
     'prefijos': ('/red/',),
     'flags': ('nav_red', 'nav_red_admin')},
    {'key': 'cfp',           'label': 'CFP (Contabilidad y Notas)',   'icon': 'ti-school',
     'prefijos': ('/cfp/',),
     'flags': ('nav_cfp', 'show_cfp')},
    {'key': 'calculadoras',  'label': 'Calculadoras',                 'icon': 'ti-calculator',
     'prefijos': ('/calculadoras/',),
     'flags': ('nav_calculadoras', 'show_calculadoras')},
]

POR_KEY = {p['key']: p for p in PROGRAMAS}


def ocultos(config):
    """Conjunto de claves ocultas (ignora claves que ya no existen)."""
    crudo = getattr(config, 'PROGRAMAS_OCULTOS', '') or ''
    try:
        data = json.loads(crudo) if crudo.strip() else []
    except ValueError:
        data = []
    return {k for k in data if k in POR_KEY} if isinstance(data, list) else set()


def guardar_ocultos(config, claves):
    limpio = sorted(k for k in set(claves or ()) if k in POR_KEY)
    config.PROGRAMAS_OCULTOS = json.dumps(limpio)
    return set(limpio)


def programa_de_ruta(ruta):
    """Programa al que pertenece una ruta (respetando sus excepciones), o None."""
    for p in PROGRAMAS:
        if any(ruta.startswith(e) for e in p.get('excepto', ())):
            continue
        if any(ruta.startswith(pref) for pref in p['prefijos']):
            return p
    return None


def programa_oculto_de_ruta(ruta, config):
    """El programa OCULTO de esa ruta, o None si la ruta no toca ninguno oculto."""
    p = programa_de_ruta(ruta)
    return p if (p and p['key'] in ocultos(config)) else None


def aplicar_ocultos(ctx, claves_ocultas):
    """Apaga en `ctx` las variables nav_*/show_* de los programas ocultos y agrega
    `programas_ocultos` ({clave: True}) para condicionar enlaces sueltos en plantillas."""
    for k in claves_ocultas:
        for f in POR_KEY[k]['flags']:
            if f in ctx:
                ctx[f] = False
    ctx['programas_ocultos'] = {k: True for k in claves_ocultas}
    return ctx


def programas_para_ui(config):
    oc = ocultos(config)
    return [{**p, 'oculto': p['key'] in oc} for p in PROGRAMAS]
