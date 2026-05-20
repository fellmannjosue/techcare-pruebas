from django.db import models
from django.conf import settings


# ─────────────────────────────────────────────────────────────
# HORARIOS POR PLANTILLAS
# ─────────────────────────────────────────────────────────────

class ScheduleTemplate(models.Model):
    nombre = models.CharField("Nombre de plantilla", max_length=120, unique=True)
    descripcion = models.TextField("Descripción", blank=True)

    class Meta:
        db_table = "reloj_schedule_template"
        verbose_name = "Plantilla de horario"
        verbose_name_plural = "Plantillas de horario"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ScheduleRule(models.Model):
    WEEKDAYS = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]
    template = models.ForeignKey(ScheduleTemplate, on_delete=models.CASCADE, related_name="reglas")
    weekday  = models.IntegerField("Día", choices=WEEKDAYS)
    trabaja  = models.BooleanField("Trabaja este día", default=True)

    # Soporte de turno partido
    entrada_manana = models.TimeField("Entrada mañana", null=True, blank=True)
    salida_manana  = models.TimeField("Salida mañana",  null=True, blank=True)
    entrada_tarde  = models.TimeField("Entrada tarde",  null=True, blank=True)
    salida_tarde   = models.TimeField("Salida tarde",   null=True, blank=True)

    class Meta:
        db_table = "reloj_schedule_rule"
        verbose_name = "Regla de día"
        verbose_name_plural = "Reglas de día"
        unique_together = ("template", "weekday")
        ordering = ["template", "weekday"]

    def __str__(self):
        return f"{self.template} - {self.get_weekday_display()}"


class EmployeeScheduleAssignment(models.Model):
    emp_code = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado (cache)", max_length=200, blank=True)

    template = models.ForeignKey(ScheduleTemplate, on_delete=models.PROTECT, related_name="asignaciones")
    fecha_inicio = models.DateField("Vigente desde")
    fecha_fin    = models.DateField("Vigente hasta", null=True, blank=True)  # null = indefinida
    activo       = models.BooleanField("Activo", default=True)

    class Meta:
        db_table = "reloj_employee_schedule_assignment"
        verbose_name = "Asignación de plantilla"
        verbose_name_plural = "Asignaciones de plantilla"
        indexes = [
            models.Index(fields=["emp_code", "fecha_inicio", "fecha_fin"]),
        ]
        ordering = ["-activo", "emp_code", "-fecha_inicio"]

    def __str__(self):
        fin = self.fecha_fin.isoformat() if self.fecha_fin else "∞"
        return f"{self.emp_code} → {self.template} [{self.fecha_inicio} → {fin}]"


# ─────────────────────────────────────────────────────────────
# OVERTIME (autorización staff) — por día/empleado
# ─────────────────────────────────────────────────────────────

class OvertimeRequest(models.Model):
    """
    Registro diario de tiempo extra por empleado.
    - minutos_calculados: lo que calcula el sistema (post-proceso en la vista).
    - minutos_autorizados: lo que aprueba el staff desde el modal.
    - approved_by / approved_at: quién y cuándo autorizó (columna 'Autorizado por').
    """
    STATUS_CHOICES = [
        ("PEND", "Pendiente"),
        ("APPR", "Aprobado"),
        ("REJC", "Rechazado"),
    ]

    emp_code = models.CharField("Código empleado", max_length=20, db_index=True)
    fecha = models.DateField("Fecha", db_index=True)

    minutos_calculados  = models.PositiveIntegerField("Minutos extra calculados", default=0)
    minutos_autorizados = models.PositiveIntegerField("Minutos extra autorizados", default=0)

    comentario = models.CharField("Comentario", max_length=255, blank=True)
    status     = models.CharField("Estado", max_length=4, choices=STATUS_CHOICES, default="PEND")

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Autorizado por",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="overtime_aprobados"
    )
    approved_at = models.DateTimeField("Fecha de autorización", null=True, blank=True)

    created_at  = models.DateTimeField("Creado en", auto_now_add=True)
    updated_at  = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_overtime_request"
        verbose_name = "Tiempo extra"
        verbose_name_plural = "Tiempos extra"
        unique_together = ("emp_code", "fecha")
        indexes = [
            models.Index(fields=["emp_code", "fecha"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-fecha", "emp_code"]

    def __str__(self):
        return f"{self.emp_code} {self.fecha} - {self.get_status_display()}"

    @property
    def approver_display(self) -> str:
        """Nombre bonito para mostrar en la columna 'Autorizado por'."""
        if self.approved_by:
            full = (self.approved_by.get_full_name() or "").strip()
            return full or self.approved_by.username
        return ""


# ─────────────────────────────────────────────────────────────
# EXCEPCIONES / REGISTROS AUXILIARES
# ─────────────────────────────────────────────────────────────

class Feriado(models.Model):
    fecha_inicio = models.DateField("Fecha inicio")
    fecha_fin    = models.DateField("Fecha fin")
    descripcion  = models.CharField("Descripción", max_length=255)
    creado_por   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="feriados_creados", verbose_name="Creado por"
    )
    creado_en = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_feriado"
        verbose_name = "Feriado"
        verbose_name_plural = "Feriados"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        if self.fecha_inicio == self.fecha_fin:
            return f"{self.fecha_inicio} - {self.descripcion}"
        return f"{self.fecha_inicio} → {self.fecha_fin} - {self.descripcion}"


class FeriadoAsignacion(models.Model):
    """Asignación de un feriado a un empleado específico."""
    feriado        = models.ForeignKey(Feriado, on_delete=models.CASCADE, related_name="asignaciones")
    emp_code       = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=200, blank=True)
    asignado_por   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="feriados_asignados", verbose_name="Asignado por"
    )
    asignado_en = models.DateTimeField("Asignado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_feriado_asignacion"
        verbose_name = "Asignación de feriado"
        verbose_name_plural = "Asignaciones de feriado"
        unique_together = ("feriado", "emp_code")
        ordering = ["emp_code"]

    def __str__(self):
        return f"{self.feriado} → {self.emp_code}"


class SabadoEspecial(models.Model):
    fecha = models.DateField("Fecha", unique=True)
    descripcion = models.CharField("Descripción", max_length=255, default="Escuela para padres")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sabados_creados", verbose_name="Creado por"
    )
    creado_en = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_sabado_especial"
        verbose_name = "Sábado especial"
        verbose_name_plural = "Sábados especiales"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.descripcion}"


class SabadoAsignacion(models.Model):
    """Asignación de un sábado especial a un empleado específico."""
    sabado          = models.ForeignKey(SabadoEspecial, on_delete=models.CASCADE, related_name="asignaciones")
    emp_code        = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=200, blank=True)
    asignado_por    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sabados_asignados", verbose_name="Asignado por"
    )
    asignado_en = models.DateTimeField("Asignado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_sabado_asignacion"
        verbose_name = "Asignación de sábado especial"
        verbose_name_plural = "Asignaciones de sábados especiales"
        unique_together = ("sabado", "emp_code")
        ordering = ["emp_code"]

    def __str__(self):
        return f"{self.sabado} → {self.emp_code}"


class TiempoCompensatorio(models.Model):
    """
    Solicitudes de tiempo extra registradas por usuario (vía Google Form o UI).
    No autoriza: solo captura y queda en estado PEND hasta que staff apruebe minutos.
    """
    STATUS_CHOICES = [
        ("PEND", "Pendiente"),
        ("APPR", "Aprobado"),
        ("REJC", "Rechazado"),
    ]

    emp_code = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=120)
    fecha = models.DateField("Fecha", db_index=True)
    minutos_registrados = models.PositiveIntegerField("Minutos registrados", default=0)
    motivo = models.TextField("Motivo", blank=True)

    # Auditoría / autorización (opcional)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tiempos_compensatorio_creados", verbose_name="Registrado por"
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tiempos_compensatorio_autorizados", verbose_name="Autorizado por"
    )
    autorizado_en = models.DateTimeField("Autorizado en", null=True, blank=True)
    estado = models.CharField("Estado", max_length=4, choices=STATUS_CHOICES, default="PEND")

    creado_en = models.DateTimeField("Creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_tiempo_compensatorio"
        verbose_name = "Tiempo compensatorio"
        verbose_name_plural = "Tiempos compensatorios"
        indexes = [
            models.Index(fields=["emp_code", "fecha"]),
            models.Index(fields=["estado"]),
        ]
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        return f"{self.emp_code} - {self.nombre_empleado} - {self.fecha} ({self.minutos_registrados} min)"


class ReporteNota(models.Model):
    """
    Comentario/nota por empleado y fecha en el Generar Reporte.
    Un registro por (emp_code, fecha).
    """
    emp_code  = models.CharField("Código empleado", max_length=20, db_index=True)
    fecha     = models.DateField("Fecha", db_index=True)
    comentario = models.TextField("Comentario", blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Creado por",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reporte_notas"
    )
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_reporte_nota"
        verbose_name = "Nota de reporte"
        verbose_name_plural = "Notas de reporte"
        unique_together = ("emp_code", "fecha")
        ordering = ["-fecha", "emp_code"]

    def __str__(self):
        return f"{self.emp_code} {self.fecha}"


class ReporteComentario(models.Model):
    """
    Múltiples comentarios por (emp_code, fecha) en el Generar Reporte.
    Máximo 5 por registro, controlado en la vista.
    """
    emp_code   = models.CharField("Código empleado", max_length=20, db_index=True)
    fecha      = models.DateField("Fecha", db_index=True)
    texto      = models.TextField("Texto")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Creado por",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reporte_comentarios"
    )
    creado_en = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_reporte_comentario"
        verbose_name = "Comentario de reporte"
        verbose_name_plural = "Comentarios de reporte"
        ordering = ["creado_en"]

    def __str__(self):
        return f"{self.emp_code} {self.fecha}: {self.texto[:40]}"


class PermisoEmpleado(models.Model):
    """
    Permisos (ausencias justificadas): médico, personal, etc.
    Se verán en una ventana/listado y pueden excluirse del cálculo de faltantes.
    """
    emp_code = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=120)

    fecha_inicio = models.DateField("Desde")
    fecha_fin    = models.DateField("Hasta")
    motivo       = models.CharField("Motivo", max_length=255)

    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="permisos_autorizados", verbose_name="Autorizado por"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="permisos_registrados", verbose_name="Registrado por"
    )
    aprobado = models.BooleanField("Aprobado", default=False)
    comentario_autorizacion = models.TextField("Comentario autorización", blank=True)

    creado_en = models.DateTimeField("Creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_permiso_empleado"
        verbose_name = "Permiso de empleado"
        verbose_name_plural = "Permisos de empleados"
        indexes = [
            models.Index(fields=["emp_code", "fecha_inicio", "fecha_fin"]),
            models.Index(fields=["aprobado"]),
        ]
        ordering = ["-fecha_inicio", "emp_code"]

    def __str__(self):
        return f"{self.emp_code} - {self.nombre_empleado} ({self.fecha_inicio}→{self.fecha_fin})"


class CompensatorioCalculo(models.Model):
    """
    Cálculo de fecha fin para acumular tiempo compensatorio.
    47 min/día hábil × días hábiles necesarios = días adeudados × 480 min.
    """
    emp_code         = models.CharField("Código empleado", max_length=20, unique=True, db_index=True)
    nombre_empleado  = models.CharField("Nombre empleado", max_length=200)
    dias_adeudados   = models.DecimalField("Días adeudados", max_digits=6, decimal_places=2)
    fecha_inicio     = models.DateField("Fecha de inicio")

    # Minutos que el empleado está autorizado a compensar por día hábil
    minutos_autorizados_dia = models.PositiveIntegerField("Min. autorizados/día", default=47)

    # Calculados y guardados
    minutos_total           = models.PositiveIntegerField("Minutos a compensar", default=0)
    dias_habiles_necesarios = models.PositiveIntegerField("Días hábiles necesarios", default=0)
    fecha_fin               = models.DateField("Fecha fin estimada", null=True, blank=True)

    # Override manual para empleados con seguimiento especial
    minutos_compensados_manual = models.PositiveIntegerField("Compensado manual (min)", null=True, blank=True)

    # Tiempo extra autorizado registrado manualmente
    minutos_tiempo_extra = models.PositiveIntegerField("Tiempo extra autorizado (min)", null=True, blank=True)

    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_compensatorio_calculo"
        verbose_name = "Cálculo compensatorio"
        verbose_name_plural = "Cálculos compensatorios"
        ordering = ["nombre_empleado"]

    def __str__(self):
        return f"{self.nombre_empleado} → {self.fecha_fin}"


class TiempoExtraDia(models.Model):
    """
    Tiempo extra autorizado por día para un empleado.
    Registrado manualmente por superuser o glorenzo.
    """
    emp_code       = models.CharField("Código empleado", max_length=20, db_index=True)
    fecha          = models.DateField("Fecha", db_index=True)
    minutos        = models.PositiveIntegerField("Minutos extra autorizados", default=0)
    razon          = models.CharField("Razón", max_length=300, blank=True)
    comentario     = models.TextField("Comentario", blank=True)
    autorizado_por = models.CharField("Autorizado por", max_length=200, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tiempos_extra_dia", verbose_name="Registrado por"
    )
    creado_en      = models.DateTimeField("Creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_tiempo_extra_dia"
        unique_together = [("emp_code", "fecha")]
        verbose_name = "Tiempo extra por día"
        verbose_name_plural = "Tiempos extra por día"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.emp_code} {self.fecha} – {self.minutos}m"


class ReportePermisoMensual(models.Model):
    """
    Reporte mensual de permisos por empleado.
    Una fila por empleado por mes con los 8 tipos de permiso en días.
    Los minutos tarde y horas rebaja se calculan en la vista desde zkbio_sqlserver.
    """
    emp_code        = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=200)
    mes             = models.DateField("Mes (primer día del mes)")

    ausencias_dias   = models.DecimalField("Ausencias",        max_digits=5, decimal_places=2, default=0)
    otro_pagado_dias = models.DecimalField("Otro Pagado",       max_digits=5, decimal_places=2, default=0)
    vacaciones_dias  = models.DecimalField("Vacaciones",        max_digits=5, decimal_places=2, default=0)
    enfermedad_dias  = models.DecimalField("Enfermedad",        max_digits=5, decimal_places=2, default=0)
    pct25_dias       = models.DecimalField("25%",               max_digits=5, decimal_places=2, default=0)
    pct50_dias       = models.DecimalField("50%",               max_digits=5, decimal_places=2, default=0)
    pct75_dias       = models.DecimalField("75%",               max_digits=5, decimal_places=2, default=0)
    pct100_dias          = models.DecimalField("100%",              max_digits=5, decimal_places=2, default=0)
    compensatorio_dias   = models.DecimalField("Compensatorio",    max_digits=5, decimal_places=2, default=0)
    pierde_bono          = models.BooleanField("Pierde bono",       default=False)
    rebaja_activa        = models.BooleanField("Rebaja activa",     default=False)

    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_reporte_permiso_mensual"
        verbose_name = "Reporte de permiso mensual"
        verbose_name_plural = "Reportes de permisos mensuales"
        unique_together = ("emp_code", "mes")
        ordering = ["nombre_empleado"]

    def __str__(self):
        return f"{self.nombre_empleado} – {self.mes.strftime('%m/%Y')}"


class PermisoReporte(models.Model):
    """Registro individual de permiso desde el reporte de asistencia.
    Soporta edición/eliminación y sincroniza ReportePermisoMensual."""
    emp_code        = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=200, blank=True)
    fecha           = models.DateField("Fecha inicio")
    fecha_fin       = models.DateField("Fecha fin", null=True, blank=True)
    tipo            = models.CharField("Tipo de permiso", max_length=30)
    dias            = models.DecimalField("Días", max_digits=5, decimal_places=2, default=1)
    horas           = models.DecimalField("Horas", max_digits=6, decimal_places=2, null=True, blank=True)
    razon           = models.CharField("Razón", max_length=300, blank=True)
    comentario      = models.TextField("Comentario", blank=True)
    registrado_por  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name="Registrado por"
    )
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reloj_permiso_reporte"
        verbose_name = "Permiso en reporte"
        verbose_name_plural = "Permisos en reporte"
        unique_together = ("emp_code", "fecha", "tipo")
        ordering = ["-fecha", "emp_code"]

    def __str__(self):
        return f"{self.nombre_empleado} – {self.fecha} – {self.tipo}"


class VacacionConfig(models.Model):
    emp_code             = models.CharField("Código empleado", max_length=20, unique=True, db_index=True)
    nombre_empleado      = models.CharField("Nombre empleado", max_length=200, blank=True)
    es_docente           = models.BooleanField("Es docente (60 días)", default=False)
    fecha_inicio_labores = models.DateField("Fecha inicio de labores", null=True, blank=True)
    registrado_por       = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='vacacion_configs',
    )
    creado_en      = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = "reloj_vacacion_config"
        verbose_name = "Configuración de vacaciones"
        verbose_name_plural = "Configuraciones de vacaciones"
        ordering  = ["nombre_empleado"]

    def __str__(self):
        return f"{self.nombre_empleado} ({self.emp_code})"


class RelojPermiso(models.Model):
    """Permisos de edición/eliminación por módulo del reloj para usuarios staff."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reloj_permiso', verbose_name='Usuario',
    )
    # Generar Reporte
    reporte_editar        = models.BooleanField("Reporte – Editar",   default=False)
    reporte_eliminar      = models.BooleanField("Reporte – Eliminar", default=False)
    # Plantilla de Horario
    plantilla_editar      = models.BooleanField("Plantilla – Editar",   default=False)
    plantilla_eliminar    = models.BooleanField("Plantilla – Eliminar", default=False)
    # Asignación de Horario
    asignacion_editar     = models.BooleanField("Asignación – Editar",   default=False)
    asignacion_eliminar   = models.BooleanField("Asignación – Eliminar", default=False)
    # Tiempo Compensatorio
    compensatorio_editar  = models.BooleanField("Compensatorio – Editar",   default=False)
    compensatorio_eliminar= models.BooleanField("Compensatorio – Eliminar", default=False)
    # Feriados
    feriado_editar        = models.BooleanField("Feriados – Editar",   default=False)
    feriado_eliminar      = models.BooleanField("Feriados – Eliminar", default=False)
    # Sábados Especiales
    sabado_editar         = models.BooleanField("Sábados – Editar",   default=False)
    sabado_eliminar       = models.BooleanField("Sábados – Eliminar", default=False)
    # Cálculo Compensatorio
    calculo_comp_editar   = models.BooleanField("Cálculo Comp. – Editar",   default=False)
    calculo_comp_eliminar = models.BooleanField("Cálculo Comp. – Eliminar", default=False)
    # Vacaciones
    vacaciones_editar     = models.BooleanField("Vacaciones – Editar",   default=False)
    vacaciones_eliminar   = models.BooleanField("Vacaciones – Eliminar", default=False)

    class Meta:
        db_table         = 'reloj_permiso_usuario'
        verbose_name     = 'Permiso de módulo reloj'
        verbose_name_plural = 'Permisos de módulos reloj'

    def __str__(self):
        return f'Permisos reloj – {self.user}'
