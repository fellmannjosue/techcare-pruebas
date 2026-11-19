# accounts/views_auditoria_rol.py
# <--- hecho por claude code (10-nov-2026): Configuración → Permisos → Rol Auditoría (solo superusuario real)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render

from core import auditoria
from core.programas import PROGRAMAS


@login_required
def settings_auditoria_rol(request):
    # El auditor nunca llega aquí (core.auditoria.PROHIBIDAS); se valida igual.
    if not request.user.is_superuser or auditoria.es_auditor(request.user):
        return redirect('settings_perfil')
    if request.method == 'POST':
        claves = set(request.POST.getlist('editar'))
        auditoria.guardar_editables(claves)
        from core.seguridad_eventos import evento
        evento('auditoria_permisos', request, objetivo='rol_auditoria', editar=sorted(claves))
        messages.success(request, 'Permisos del rol Auditoría guardados.')
        return redirect('settings_auditoria_rol')
    editables = auditoria.programas_editables()
    grupo = Group.objects.filter(name=auditoria.GRUPO).first()
    from .views import _settings_ctx
    ctx = _settings_ctx(request, 'auditoria_rol')
    ctx.update({
        'filas': [{**p, 'editar': p['key'] in editables} for p in PROGRAMAS],
        'miembros': list(grupo.user_set.order_by('username')) if grupo else [],
        'n_editar': len(editables),
    })
    return render(request, 'accounts/settings_auditoria_rol.html', ctx)
