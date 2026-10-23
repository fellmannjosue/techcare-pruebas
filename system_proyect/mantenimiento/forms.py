from django import forms
from .models import MaintenanceRecord, TipoFalla


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model  = MaintenanceRecord
        # <--- hecho por claude code: + campos de impresora (variante en el mismo formulario)
        fields = ['tipo_equipo', 'computadora', 'impresora', 'model', 'serie',
                  'teacher_name', 'grade', 'area', 'tipo_falla',
                  'tipo_mant_impresora', 'estado_tinta',
                  'tinta_negra', 'tinta_magenta', 'tinta_amarillo', 'tinta_cyan', 'tipo_tinta',
                  # <--- hecho por claude code: campos del Control de equipo
                  'eval_trabajo', 'eval_fallas', 'eval_fallas_detalle', 'obs_auditora', 'obs_tecnico', 'estado_equipo',
                  'insp_limpio', 'insp_ordenado', 'insp_cables', 'insp_alimentos',
                  # <--- hecho por claude code (17-sep-2026): Entrega / Recogida de equipo
                  'ent_equipo', 'ent_mouse_teclado', 'ent_televisor', 'ent_control_tv',
                  'televisor', 'firma_nombre', 'fecha_hora', 'control_origen',
                  'modelo_anterior', 'serie_anterior', 'ip_anterior', 'modelo_nuevo', 'serie_nuevo', 'ip_nuevo',
                  'date', 'status', 'solucion', 'observaciones']
        widgets = {
            'tipo_equipo':  forms.HiddenInput(),
            'computadora':  forms.Select(attrs={'class': 'form-select'}),
            'impresora':    forms.Select(attrs={'class': 'form-select'}),
            'model':        forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'serie':        forms.TextInput(attrs={'class': 'form-control bg-light text-muted', 'readonly': 'readonly'}),
            'teacher_name': forms.Select(attrs={'class': 'form-select'}),
            'grade':        forms.Select(attrs={'class': 'form-select'}),
            'area':         forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_falla':   forms.Select(attrs={'class': 'form-select'}),
            'tipo_mant_impresora': forms.Select(attrs={'class': 'form-select'}),
            'estado_tinta': forms.Select(attrs={'class': 'form-select'}),
            'tipo_tinta':   forms.Select(attrs={'class': 'form-select'}),
            'tinta_negra':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tinta_magenta':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tinta_amarillo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tinta_cyan':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'eval_trabajo':        forms.Select(attrs={'class': 'form-select'}),
            'eval_fallas':         forms.Select(attrs={'class': 'form-select'}),
            'eval_fallas_detalle': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Describe las fallas que ha presentado…'}),
            'obs_auditora':        forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'obs_tecnico':         forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'estado_equipo':       forms.Select(attrs={'class': 'form-select'}),
            'insp_limpio':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insp_ordenado':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insp_cables':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insp_alimentos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ent_equipo':        forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ent_mouse_teclado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ent_televisor':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ent_control_tv':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'televisor':         forms.Select(attrs={'class': 'form-select'}),
            'firma_nombre':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba su nombre completo', 'autocomplete': 'off'}),
            'fecha_hora':        forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'date':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':       forms.Select(attrs={'class': 'form-select'}),
            'solucion':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones':forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import MaestroMantenimiento, GradoMantenimiento
        from inventario.models import Computadora, Impresora

        # Solo computadoras de general (excluye laboratorios: IDANALAB*, IDCFPLAB*)
        self.fields['computadora'].queryset = (
            Computadora.objects.exclude(asset_id__icontains='LAB').order_by('asset_id'))
        self.fields['computadora'].empty_label = '— Seleccionar computadora —'
        # Mostrar también el nombre del asignado para identificar mejor
        self.fields['computadora'].label_from_instance = (
            lambda o: f"{o.asset_id} – {o.modelo}" + (f" · {o.asignado_a}" if o.asignado_a else ""))

        # <--- hecho por claude code: dropdown de impresoras (asset_id — nombre · asignado)
        self.fields['impresora'].queryset = Impresora.objects.order_by('asset_id')
        self.fields['impresora'].empty_label = '— Seleccionar impresora —'
        self.fields['impresora'].label_from_instance = (
            lambda o: f"{o.asset_id} – {o.modelo}" + (f" · {o.asignado_a}" if o.asignado_a else ""))

        # Campos que dependen del tipo de equipo: no obligatorios a nivel de widget;
        # la validación real se hace en clean() según tipo_equipo.
        for f in ('computadora', 'impresora', 'model', 'serie', 'teacher_name',
                  'grade', 'area', 'tipo_falla', 'tipo_mant_impresora',
                  'estado_tinta', 'tipo_tinta',
                  'eval_trabajo', 'eval_fallas', 'eval_fallas_detalle', 'obs_auditora', 'obs_tecnico',
                  'estado_equipo', 'status',
                  # <--- hecho por claude code (17-sep-2026): entrega/recogida; `date` la pone fecha_hora en clean()
                  'televisor', 'firma_nombre', 'fecha_hora', 'date', 'control_origen',
                  'modelo_anterior', 'serie_anterior', 'ip_anterior', 'modelo_nuevo', 'serie_nuevo', 'ip_nuevo'):
            self.fields[f].required = False
        # <--- hecho por claude code (28-sep-2026): el origen de un caso especial solo puede ser un Control de equipo
        self.fields['control_origen'].queryset = MaintenanceRecord.objects.filter(tipo_equipo='control')
        self.fields['control_origen'].widget = forms.HiddenInput()
        from inventario.models import Televisor
        self.fields['televisor'].queryset = Televisor.objects.order_by('asset_id')
        self.fields['televisor'].empty_label = '— Seleccionar televisor —'
        self.fields['televisor'].label_from_instance = (
            lambda t: ' · '.join(x for x in [t.asset_id, t.modelo or '', t.grado or t.area or ''] if x))
        self.fields['fecha_hora'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']
        self.fields['estado_equipo'].choices = [('', '— Seleccionar —')] + list(MaintenanceRecord.ESTADO_EQUIPO_CHOICES)
        # Los selects de evaluación arrancan sin opción elegida
        self.fields['eval_trabajo'].choices = [('', '— Seleccionar —')] + list(MaintenanceRecord.EVAL_TRABAJO_CHOICES)
        self.fields['eval_fallas'].choices  = [('', '— Seleccionar —')] + list(MaintenanceRecord.EVAL_FALLAS_CHOICES)

        self.fields['teacher_name'].widget = forms.HiddenInput()
        self.fields['grade'].widget        = forms.HiddenInput()

    def clean(self):
        # <--- hecho por claude code: validación condicional por tipo de equipo
        cleaned = super().clean()
        tipo = cleaned.get('tipo_equipo') or 'computadora'
        if tipo == 'impresora':
            if not cleaned.get('impresora'):
                self.add_error('impresora', 'Selecciona una impresora.')
            if not cleaned.get('tipo_mant_impresora'):
                self.add_error('tipo_mant_impresora', 'Selecciona el tipo de mantenimiento.')
            if not cleaned.get('estado_tinta'):
                self.add_error('estado_tinta', 'Indica el estado de la tinta.')
        elif tipo == 'control':
            # <--- hecho por claude code: el control se hace sobre la computadora del maestro
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona la computadora del maestro.')
            # <--- hecho por claude code (28-sep-2026): con "caso especial" las dos preguntas se reemplazan por el checklist de recogida
            if self.data.get('reasignacion'):
                # <--- hecho por claude code (12-oct-2026): reasignación — la computadora pasa del maestro A al B
                nuevo = (self.data.get('asignado_nuevo') or '').strip()
                comp = cleaned.get('computadora')
                if not nuevo:
                    self.add_error('computadora', 'Reasignación: indica a qué maestro pasa la computadora.')
                elif comp and nuevo.lower() == (comp.asignado_a or '').strip().lower():
                    self.add_error('computadora', f'Reasignación: la computadora ya está asignada a {nuevo}.')
            elif self.data.get('cambio_equipo'):
                # <--- hecho por claude code (28-sep-2026): cambio de equipo — equipo anterior (computadora) → equipo nuevo
                if not ((cleaned.get('modelo_nuevo') or '').strip() or (cleaned.get('serie_nuevo') or '').strip()):
                    self.add_error('modelo_nuevo', 'Registra el equipo nuevo (modelo o serie).')
            elif self.data.get('mantenimiento'):
                # <--- hecho por claude code (21-oct-2026): mantenimiento (solo comentario) o reparación (preguntas); no exige las 2 preguntas del control
                if self.data.get('es_reparacion'):
                    if not (self.data.get('rep_que_danado') or '').strip():
                        self.add_error('computadora', 'Reparación: indica qué tiene dañado.')
                    if not (self.data.get('rep_que_reparacion') or '').strip():
                        self.add_error('computadora', 'Reparación: indica qué reparación se realizará.')
                elif not (self.data.get('mant_comentario') or '').strip():
                    self.add_error('computadora', 'Mantenimiento: escribe el comentario.')
            elif self.data.get('caso_especial'):
                if not (cleaned.get('firma_nombre') or '').strip():
                    self.add_error('firma_nombre', 'Elige quién firma la recogida.')
                if not cleaned.get('fecha_hora'):
                    self.add_error('fecha_hora', 'Indica la fecha y la hora de la recogida.')
                if cleaned.get('ent_televisor') and not cleaned.get('televisor'):
                    self.add_error('televisor', 'Indica qué televisor.')
                if not any(cleaned.get(c) for c in ('ent_equipo', 'ent_mouse_teclado', 'ent_televisor', 'ent_control_tv')):
                    self.add_error('ent_equipo', 'Marca al menos una cosa que se recibe.')
                if not cleaned.get('ent_televisor'):
                    cleaned['televisor'] = None
            elif not (self.instance.pk and self.instance.casos_especiales.filter(
                    tipo_equipo__in=('caso_especial', 'cambio_equipo', 'reasignacion', 'mantenimiento', 'reparacion')).exists()):
                # <--- hecho por claude code (16-oct-2026): un control que YA generó un cambio de equipo / reasignación /
                # caso especial no tiene las dos preguntas (se reemplazaron) y al editarlo el interruptor va bloqueado
                # (no se envía): antes exigía las preguntas y no dejaba ni agregar fotos.
                if not cleaned.get('eval_trabajo'):
                    self.add_error('eval_trabajo', 'Responde cómo ha trabajado el equipo.')
                if not cleaned.get('eval_fallas'):
                    self.add_error('eval_fallas', 'Indica si el equipo ha presentado fallas.')
            if not cleaned.get('estado_equipo'):
                self.add_error('estado_equipo', 'Indica el estado del equipo.')
            # El control queda registrado como trámite completado (el "estado" real es el del equipo)
            cleaned['status'] = 'Completado'
        elif tipo in ('entrega', 'recogida', 'caso_especial'):
            # <--- hecho por claude code (17-sep-2026): entrega/recogida — equipo + checklist + firma escrita + fecha y hora
            # <--- hecho por claude code (28-sep-2026): el caso especial valida igual que una recogida y exige el control de origen
            if tipo == 'caso_especial' and not cleaned.get('control_origen'):
                self.add_error('control_origen', 'El caso especial debe nacer de un Control de equipo.')
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona la computadora.')
            if not (cleaned.get('firma_nombre') or '').strip():
                self.add_error('firma_nombre', 'El usuario debe escribir su nombre como firma.')
            if not cleaned.get('fecha_hora'):
                self.add_error('fecha_hora', 'Indica la fecha y la hora.')
            if cleaned.get('ent_televisor') and not cleaned.get('televisor'):
                self.add_error('televisor', 'Indica qué televisor.')
            if not any(cleaned.get(c) for c in ('ent_equipo', 'ent_mouse_teclado', 'ent_televisor', 'ent_control_tv')):
                self.add_error('ent_equipo', 'Marca al menos una cosa.')
            if not cleaned.get('ent_televisor'):
                cleaned['televisor'] = None
            if cleaned.get('fecha_hora'):
                cleaned['date'] = cleaned['fecha_hora'].date()
            cleaned['status'] = 'Completado'
        elif tipo == 'prestamo':
            # <--- hecho por claude code (16-oct-2026): préstamo de equipo. Sus campos (prest_*) NO son del ModelForm: los
            # aplica la vista solo cuando llegan, así editar otra ficha nunca los borra. Aquí solo se validan.
            import datetime as _dt
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona la computadora que se presta.')
            d = self.data
            if not (d.get('prest_solicitante') or '').strip():
                self.add_error('computadora', 'Préstamo: indica quién solicita el equipo.')
            if not (d.get('prest_motivo') or '').strip():
                self.add_error('computadora', 'Préstamo: indica el motivo o la actividad.')
            try:
                desde = _dt.date.fromisoformat(d.get('prest_desde') or '')
                hasta = _dt.date.fromisoformat(d.get('prest_hasta') or '')
                if hasta < desde:
                    self.add_error('computadora', 'Préstamo: la devolución no puede ser antes de la entrega.')
            except ValueError:
                self.add_error('computadora', 'Préstamo: indica la fecha de entrega y la de devolución.')
            if not cleaned.get('status'):
                cleaned['status'] = 'Pendiente'   # nace pendiente de firmas
            if not cleaned.get('date'):
                cleaned['date'] = _dt.date.today()
        elif tipo == 'inspeccion':
            # <--- hecho por claude code: la inspección es del equipo del maestro; queda completada al registrarse
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona la computadora del maestro.')
            cleaned['status'] = 'Completado'
        else:
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona una computadora.')
            if not cleaned.get('status'):
                self.add_error('status', 'Selecciona el estado.')
        # `date` dejó de ser obligatoria a nivel de campo (entrega/recogida la derivan de fecha_hora)
        if not cleaned.get('date'):
            self.add_error('date', 'Selecciona la fecha.')
        return cleaned


class FirmaMaestroForm(forms.Form):
    """Formulario público (sin login) para que el maestro firme por link."""
    firma_data = forms.CharField(widget=forms.HiddenInput, required=True)

    def clean_firma_data(self):
        data = (self.cleaned_data.get('firma_data') or '').strip()
        if not data or not data.startswith('data:image'):
            raise forms.ValidationError("Debes firmar antes de enviar.")
        return data
