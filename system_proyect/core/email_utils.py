# <--- hecho por claude code: helpers para SMTP multi-cuenta por módulo
"""
email_utils.py — conexiones SMTP por módulo con fallback automático a Gmail.

Módulos:
  - Enfermería  →  No Reply <enfermeria@ana-hn.org>   (mail.ana-hn.org)
  - Conducta BL, Notas Parcial BL
                →  coordinacion_bl@ana-hn.org          (mail.ana-hn.org)
  - Conducta Colegio, Notas Parcial Colegio
                →  coordinacion_col@ana-hn.org         (mail.ana-hn.org)
  - Resto       →  Gmail fallback (settings.DEFAULT_FROM_EMAIL)

Uso típico:
    from core.email_utils import (
        get_enfermeria_connection, get_enfermeria_from,
        get_coord_bl_connection,   get_coord_bl_from,
        get_coord_col_connection,  get_coord_col_from,
        get_coord_connection,      get_coord_from,   # auto BL/Colegio por área
    )

    conn = get_coord_bl_connection()          # None → Gmail si sin clave
    msg  = EmailMessage(..., from_email=get_coord_bl_from(), connection=conn)
    msg.send()
"""
from django.core.mail import get_connection
from django.conf import settings


# ─────────────────────────────────────────────────────────────
# Interno
# ─────────────────────────────────────────────────────────────
def _make_connection(cfg: dict, fail_silently: bool = False):
    """
    Crea un SMTPEmailBackend con la config dada.
    Retorna None si falta USER o PASSWORD → el llamador usa Django default (Gmail).
    """
    user     = cfg.get('USER', '').strip()
    password = cfg.get('PASSWORD', '').strip()
    if not user or not password:
        return None
    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=cfg.get('HOST', 'mail.ana-hn.org'),
        port=int(cfg.get('PORT', 587)),
        username=user,
        password=password,
        use_tls=cfg.get('USE_TLS', True),
        use_ssl=cfg.get('USE_SSL', False),
        fail_silently=fail_silently,
    )


# ─────────────────────────────────────────────────────────────
# Módulo: Enfermería  →  No Reply <enfermeria@ana-hn.org>
# ─────────────────────────────────────────────────────────────
def get_enfermeria_connection(fail_silently: bool = False):
    cfg = getattr(settings, 'EMAIL_ENFERMERIA', {})
    return _make_connection(cfg, fail_silently=fail_silently)


def get_enfermeria_from() -> str:
    """FROM para enfermería: 'No Reply <enfermeria@ana-hn.org>'."""
    cfg  = getattr(settings, 'EMAIL_ENFERMERIA', {})
    user = cfg.get('USER', '').strip()
    if user:
        return f'No Reply <{user}>'
    return settings.DEFAULT_FROM_EMAIL


# ─────────────────────────────────────────────────────────────
# Módulo: Coordinación Bilingüe
# ─────────────────────────────────────────────────────────────
def get_coord_bl_connection(fail_silently: bool = False):
    cfg = getattr(settings, 'EMAIL_COORD_BL', {})
    return _make_connection(cfg, fail_silently=fail_silently)


def get_coord_bl_from() -> str:
    cfg  = getattr(settings, 'EMAIL_COORD_BL', {})
    user = cfg.get('USER', '').strip()
    return user or settings.DEFAULT_FROM_EMAIL


def get_coord_bl_inbox() -> str:
    """Dirección de bandeja BL (TO para notificaciones del módulo)."""
    return get_coord_bl_from()


# ─────────────────────────────────────────────────────────────
# Módulo: Coordinación Colegio
# ─────────────────────────────────────────────────────────────
def get_coord_col_connection(fail_silently: bool = False):
    cfg = getattr(settings, 'EMAIL_COORD_COL', {})
    return _make_connection(cfg, fail_silently=fail_silently)


def get_coord_col_from() -> str:
    cfg  = getattr(settings, 'EMAIL_COORD_COL', {})
    user = cfg.get('USER', '').strip()
    return user or settings.DEFAULT_FROM_EMAIL


def get_coord_col_inbox() -> str:
    """Dirección de bandeja Colegio (TO para notificaciones del módulo)."""
    return get_coord_col_from()


# ─────────────────────────────────────────────────────────────
# Helper auto: selecciona BL o Colegio según clave de área
# ─────────────────────────────────────────────────────────────
_AREAS_BL = {'bl', 'colegio_bl'}   # mismas claves que notas_parcial/views.py AREAS_BL


def _es_area_bl(area: str) -> bool:
    return area in _AREAS_BL


def get_coord_connection(area: str, fail_silently: bool = False):
    """Retorna la conexión SMTP correcta según área ('bl'/'colegio_bl' → BL, resto → Colegio)."""
    if _es_area_bl(area):
        return get_coord_bl_connection(fail_silently=fail_silently)
    return get_coord_col_connection(fail_silently=fail_silently)


def get_coord_from(area: str) -> str:
    """Retorna el FROM correcto según área."""
    if _es_area_bl(area):
        return get_coord_bl_from()
    return get_coord_col_from()


def get_coord_inbox(area: str) -> str:
    """Retorna la bandeja (TO) correcta según área."""
    if _es_area_bl(area):
        return get_coord_bl_inbox()
    return get_coord_col_inbox()
