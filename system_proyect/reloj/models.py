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
    # <--- hecho por claude code: horas que se suman al total mensual de los
    # MAESTROS POR HORA asignados a este sábado (no aplica al resto del personal).
    horas = models.DecimalField("Horas (maestros por hora)", max_digits=5, decimal_places=2, default=5)
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

    # Factor de conversión días → horas para días adeudados
    factor_horas_dia = models.DecimalField("Horas por día (factor)", max_digits=4, decimal_places=1, default=8.0)

    # Calculados y guardados
    minutos_total           = models.PositiveIntegerField("Minutos a compensar", default=0)
    dias_habiles_necesarios = models.PositiveIntegerField("Días hábiles necesarios", default=0)
    fecha_fin               = models.DateField("Fecha fin estimada", null=True, blank=True)

    # Override manual para empleados con seguimiento especial
    minutos_compensados_manual = models.PositiveIntegerField("Compensado manual (min)", null=True, blank=True)

    # Tiempo extra autorizado registrado manualmente
    minutos_tiempo_extra = models.PositiveIntegerField("Tiempo extra autorizado (min)", null=True, blank=True)

    # Permisos extras en horas (nuevo campo para nueva estructura)
    permisos_extras_horas = models.DecimalField(
        "Permisos extras (h)", max_digits=6, decimal_places=2, null=True, blank=True,
    )

    # Horas adeudadas capturadas directamente (reemplaza días × factor)  <--- hecho por claude code
    horas_adeudadas_manual = models.DecimalField(
        "Horas adeudadas", max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Horas adeudadas capturadas directamente. Si está vacío, usa días × 8.",
    )

    # Tiempo extra tomado (override). Si es null, se calcula del permiso compensatorio.
    horas_tiempo_extra_tomado_manual = models.DecimalField(
        "Tiempo extra tomado (h, override)", max_digits=7, decimal_places=2, null=True, blank=True,
    )

    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        db_table = "reloj_compensatorio_calculo"
        verbose_name = "Cálculo compensatorio"
        verbose_name_plural = "Cálculos compensatorios"
        ordering = ["nombre_empleado"]

    def __str__(self):
        return f"{self.nombre_empleado} → {self.fecha_fin}"


class CompensatorioTomadoManual(models.Model):
    """Entradas manuales de tiempo tomado para un CompensatorioCalculo (tab Adeudados 2).
    Se suman al permiso compensatorio para el 'Tiempo tomado' total."""
    calculo    = models.ForeignKey(
        'CompensatorioCalculo', on_delete=models.CASCADE, related_name='tomados_manual')
    fecha      = models.DateField("Fecha")
    horas      = models.DecimalField("Horas", max_digits=6, decimal_places=2, default=0)
    razon      = models.CharField("Razón / comentario", max_length=300, blank=True)
    creado_en  = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_compensatorio_tomado_manual"
        verbose_name = "Tiempo tomado manual"
        verbose_name_plural = "Tiempos tomados manuales"
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.calculo.emp_code} {self.fecha} {self.horas}h"


class DiaNoLaborableANA(models.Model):
    """Entrada de horas no laborables ANA para cálculo compensatorio."""
    calculo     = models.ForeignKey(
        CompensatorioCalculo, on_delete=models.CASCADE, related_name='dias_no_laborables',
    )
    descripcion = models.CharField("Descripción", max_length=200, blank=True)
    horas       = models.DecimalField("Horas", max_digits=6, decimal_places=2, default=8.8)

    @property
    def total_horas(self):
        return round(float(self.horas), 2)

    class Meta:
        db_table  = "reloj_dia_no_laborable_ana"
        verbose_name = "Día no laborable ANA"
        verbose_name_plural = "Días no laborables ANA"
        ordering  = ["pk"]

    def __str__(self):
        return f"{self.calculo.nombre_empleado} – {self.descripcion}"


# ── Compensatorio: matriz mensual (Horas Trabajadas / Horas Tomadas) ──────────
# <--- hecho por claude code: tabs 3 y 4 comparten lista de empleados (manual,
# desde ZKBio). Cada empleado tiene valores por mes/año, editables.
class CompensatorioMensualEmpleado(models.Model):
    """Empleado agregado manualmente a la matriz mensual (tabs Horas Trabajadas/Tomadas)."""
    emp_code        = models.CharField("Código empleado", max_length=20, unique=True, db_index=True)
    nombre_empleado = models.CharField("Nombre empleado", max_length=200)
    comentario_trab = models.TextField("Comentario (Horas Trabajadas)", blank=True, default="")
    comentario_tom  = models.TextField("Comentario (Horas Tomadas)", blank=True, default="")
    creado_en       = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_compensatorio_mensual_empleado"
        verbose_name = "Empleado compensatorio mensual"
        verbose_name_plural = "Empleados compensatorio mensual"
        ordering = ["nombre_empleado"]

    def __str__(self):
        return f"{self.nombre_empleado} ({self.emp_code})"


class CompensatorioMensualValor(models.Model):
    """Valor por mes/año de un empleado en la matriz mensual.
    horas_trabajadas = manual (compensatorio hecho).
    horas_tomadas    = override; si es null se toma del permiso compensatorio del mes."""
    empleado         = models.ForeignKey(
        CompensatorioMensualEmpleado, on_delete=models.CASCADE, related_name='valores',
    )
    anio             = models.PositiveIntegerField("Año")
    mes              = models.PositiveSmallIntegerField("Mes")  # 1-12
    horas_trabajadas = models.DecimalField("Horas trabajadas", max_digits=7, decimal_places=2, default=0)
    horas_tomadas    = models.DecimalField("Horas tomadas (override)", max_digits=7, decimal_places=2,
                                           null=True, blank=True)

    class Meta:
        db_table = "reloj_compensatorio_mensual_valor"
        verbose_name = "Valor compensatorio mensual"
        verbose_name_plural = "Valores compensatorio mensual"
        unique_together = ("empleado", "anio", "mes")
        ordering = ["anio", "mes"]

    def __str__(self):
        return f"{self.empleado.emp_code} {self.anio}-{self.mes:02d}"


class CompensatorioMensualDetalle(models.Model):
    """Entradas con horas + comentario por empleado (tabs Horas Trabajadas/Tomadas).
    tipo: 'trab' | 'tom'. El total se muestra como suma de horas (estilo Tiempo extra)."""
    empleado   = models.ForeignKey(
        CompensatorioMensualEmpleado, on_delete=models.CASCADE, related_name='detalles')
    anio       = models.PositiveIntegerField("Año")
    tipo       = models.CharField("Tipo", max_length=4)  # 'trab' | 'tom'
    fecha      = models.DateField("Fecha")
    horas      = models.DecimalField("Horas", max_digits=6, decimal_places=2, default=0)
    comentario = models.CharField("Comentario", max_length=300, blank=True)
    creado_en  = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_compensatorio_mensual_detalle"
        verbose_name = "Detalle compensatorio mensual"
        verbose_name_plural = "Detalles compensatorio mensual"
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.empleado.emp_code} {self.tipo} {self.fecha} {self.horas}h"


class CompensatorioInstructor(models.Model):
    """Tab 5 — instructores (lista aparte, manual desde ZKBio).
    Solo 'minutos_tiempo_extra' y el override de permiso tomado son manuales;
    el resto (horario, compensado, total, saldo) se calcula en la vista."""
    emp_code            = models.CharField("Código empleado", max_length=20, unique=True, db_index=True)
    nombre_empleado     = models.CharField("Nombre empleado", max_length=200)
    fecha_inicio        = models.DateField("Fecha de inicio", null=True, blank=True)
    fecha_fin           = models.DateField("Fecha fin", null=True, blank=True)  # manual
    minutos_tiempo_extra = models.PositiveIntegerField("Tiempo extra autorizado (min)", default=0)
    # Override del permiso tomado (h). Si es null, se calcula del permiso compensatorio.
    permiso_tomado_horas = models.DecimalField(
        "Permiso tomado (h, override)", max_digits=7, decimal_places=2, null=True, blank=True,
    )
    creado_en           = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_compensatorio_instructor"
        verbose_name = "Compensatorio instructor"
        verbose_name_plural = "Compensatorio instructores"
        ordering = ["nombre_empleado"]

    def __str__(self):
        return f"{self.nombre_empleado} ({self.emp_code})"


class CompensatorioInstructorTE(models.Model):
    """Entradas de tiempo extra autorizado de un instructor (Fecha + Minutos + Comentario)."""
    instructor = models.ForeignKey(
        CompensatorioInstructor, on_delete=models.CASCADE, related_name='te_entradas')
    fecha      = models.DateField("Fecha")
    minutos    = models.PositiveIntegerField("Minutos", default=0)
    comentario = models.CharField("Comentario", max_length=300, blank=True)
    creado_en  = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_compensatorio_instructor_te"
        verbose_name = "Tiempo extra instructor"
        verbose_name_plural = "Tiempos extra instructor"
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.instructor.emp_code} {self.fecha} {self.minutos}min"


class CompensatorioInstructorTomado(models.Model):
    """Entradas manuales de permiso tomado de un instructor (solo superuser)."""
    instructor = models.ForeignKey(
        CompensatorioInstructor, on_delete=models.CASCADE, related_name='tomados_manual')
    fecha      = models.DateField("Fecha")
    horas      = models.DecimalField("Horas", max_digits=6, decimal_places=2, default=0)
    razon      = models.CharField("Razón / comentario", max_length=300, blank=True)
    creado_en  = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_compensatorio_instructor_tomado"
        verbose_name = "Permiso tomado instructor"
        verbose_name_plural = "Permisos tomados instructor"
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.instructor.emp_code} {self.fecha} {self.horas}h"


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


class MaestroHoraEntrada(models.Model):
    """Horas trabajadas (sin fecha) de un maestro por hora, por mes.
    Solo aplica a los maestros por hora; se suman para el total mensual."""
    emp_code   = models.CharField("Código empleado", max_length=20, db_index=True)
    mes        = models.DateField("Mes (primer día)")
    horas      = models.DecimalField("Horas", max_digits=5, decimal_places=2, default=0)
    comentario = models.CharField("Comentario", max_length=300, blank=True, default="")
    creado_en  = models.DateTimeField("Creado en", auto_now_add=True)

    class Meta:
        db_table = "reloj_maestro_hora_entrada"
        verbose_name = "Horas maestro por hora"
        verbose_name_plural = "Horas maestros por hora"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.emp_code} {self.mes:%Y-%m} {self.horas}h"


class MaestroHoraDia(models.Model):
    """Horas que un maestro por hora trabaja en cada día de la semana (fijo, manual).
    weekday: 0=Lunes .. 6=Domingo. El permiso se rebaja con las horas del día."""
    emp_code  = models.CharField("Código empleado", max_length=20, db_index=True)
    weekday   = models.PositiveSmallIntegerField("Día de la semana")  # 0-6
    horas     = models.DecimalField("Horas", max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = "reloj_maestro_hora_dia"
        verbose_name = "Horas por día (maestro por hora)"
        verbose_name_plural = "Horas por día (maestros por hora)"
        unique_together = ("emp_code", "weekday")
        ordering = ["emp_code", "weekday"]

    def __str__(self):
        return f"{self.emp_code} d{self.weekday} {self.horas}h"


class RecesoAjuste(models.Model):
    """Ajuste manual del receso (almuerzo) de un empleado en un día.
    Si existe, reemplaza a las marcas detectadas automáticamente del reloj."""
    emp_code  = models.CharField("Código empleado", max_length=20, db_index=True)
    fecha     = models.DateField("Fecha")
    m2        = models.CharField("Salida (HH:MM)", max_length=5, blank=True, default="")
    m3        = models.CharField("Regreso (HH:MM)", max_length=5, blank=True, default="")
    creado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reloj_receso_ajuste"
        verbose_name = "Ajuste de receso"
        verbose_name_plural = "Ajustes de receso"
        unique_together = ("emp_code", "fecha")

    def __str__(self):
        return f"{self.emp_code} {self.fecha} {self.m2}-{self.m3}"


class RazonPermiso(models.Model):
    """Catálogo de razones/motivos de permiso (select editable en el reporte)."""
    texto     = models.CharField("Razón", max_length=200, unique=True)
    activo    = models.BooleanField("Activo", default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reloj_razon_permiso"
        verbose_name = "Razón de permiso"
        verbose_name_plural = "Razones de permiso"
        ordering = ["texto"]

    def __str__(self):
        return self.texto


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
    compensatorio_dias        = models.DecimalField("Compensatorio",           max_digits=5, decimal_places=2, default=0)
    horas_diarias_laboradas   = models.DecimalField("Horas diarias laboradas", max_digits=4, decimal_places=1, default=8.0)
    dias_laborables           = models.CharField("Días laborables", max_length=20, default="L,M,X,J,V", blank=True)
    horario_comentario        = models.CharField("Comentario horario", max_length=200, blank=True, default="")
    pierde_bono          = models.BooleanField("Pierde bono",       default=False)
    # Override manual del superusuario sobre el cálculo automático del bono:
    # '' = automático · 'si' = forzar pierde · 'no' = forzar conserva
    bono_override        = models.CharField("Override bono", max_length=3, blank=True, default='')
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


# ── Bono por Asistencia: configuración de reglas ──  <--- hecho por claude code
class BonoConfig(models.Model):
    """Configuración global de las reglas fijas del Bono por Asistencia."""
    from datetime import time as _t
    hora_limite        = models.TimeField("Hora máxima de entrada", default=_t(6, 58))
    intentos_tarde     = models.PositiveSmallIntegerField(
        "Entradas tarde toleradas (pierde al siguiente)", default=2)
    regla_otro_pagado  = models.BooleanField("Regla: Otro Pagado activa", default=True)
    regla_enfermedad   = models.BooleanField("Regla: Enfermedad activa", default=True)
    regla_hora_activa  = models.BooleanField("Regla: Hora de entrada activa", default=True)
    # Vigilancia: dos turnos. Turno 1 (19:00) → a tiempo hasta 18:45.
    # Turno 2 (00:00) → a tiempo hasta 23:45. El turno se decide por la hora de entrada.
    hora_vigilancia       = models.TimeField("Vigilancia turno 19:00 — entrada máx", default=_t(18, 45))
    hora_vigilancia_2     = models.TimeField("Vigilancia turno 00:00 — entrada máx", default=_t(23, 45))
    regla_vigilancia      = models.BooleanField("Regla: Vigilancia activa", default=True)

    class Meta:
        db_table = "reloj_bono_config"
        verbose_name = "Configuración de Bono"
        verbose_name_plural = "Configuración de Bono"

    def __str__(self):
        return f"Bono — entrada máx {self.hora_limite}"

    @classmethod
    def get(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class BonoReglaExtra(models.Model):
    """Reglas adicionales configurables del bono."""
    TIPO_CHOICES = [('permiso', 'Por tipo de permiso'), ('hora', 'Por hora de entrada')]
    tipo         = models.CharField("Tipo de regla", max_length=10, choices=TIPO_CHOICES)
    permiso_tipo = models.CharField("Tipo de permiso", max_length=40, blank=True, default='')
    hora         = models.TimeField("Hora máxima", null=True, blank=True)
    descripcion  = models.CharField("Descripción", max_length=160, blank=True, default='')
    activa       = models.BooleanField("Activa", default=True)
    creado_en    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reloj_bono_regla_extra"
        verbose_name = "Regla extra de Bono"
        verbose_name_plural = "Reglas extra de Bono"
        ordering = ["pk"]

    def __str__(self):
        return self.descripcion or f"{self.get_tipo_display()}"


class BonoHorarioEmpleado(models.Model):
    """Hora máxima de entrada especial por empleado y día (maestros por hora).
    Si existe, reemplaza la hora límite global del bono ese día."""
    WEEKDAYS = [(0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'),
                (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')]
    emp_code = models.CharField("Código empleado", max_length=20, db_index=True)
    nombre   = models.CharField("Nombre", max_length=120, blank=True, default='')
    weekday  = models.PositiveSmallIntegerField("Día", choices=WEEKDAYS)
    hora     = models.TimeField("Hora máxima de entrada")
    activa   = models.BooleanField("Activa", default=True)

    class Meta:
        db_table = "reloj_bono_horario_empleado"
        verbose_name = "Horario especial de bono"
        verbose_name_plural = "Horarios especiales de bono"
        unique_together = ("emp_code", "weekday")
        ordering = ["nombre", "weekday"]

    def __str__(self):
        return f"{self.nombre or self.emp_code} {self.get_weekday_display()} {self.hora}"


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
    GRUPO_DOCENTE = [('bl', 'BL'), ('colegio', 'Colegio')]
    grupo_docente        = models.CharField(
        "Grupo docente (BL/Colegio)", max_length=10, blank=True, default='',
        choices=GRUPO_DOCENTE,
    )
    fecha_inicio_labores = models.DateField("Fecha inicio de labores", null=True, blank=True)
    dias_usados_manual   = models.DecimalField(
        "Días usados (manual)", max_digits=5, decimal_places=2, null=True, blank=True,
    )
    dias_fijos           = models.IntegerField(
        "Días fijos (caso especial)", null=True, blank=True,
        help_text="Si se establece, sobreescribe el cálculo automático de días que corresponden."
    )
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
    # Visualización: ver todos los empleados (True) o solo los asignados (False)
    ver_todos = models.BooleanField('Ver todos los empleados', default=False)
    # Generar Reporte
    reporte_ver           = models.BooleanField("Reporte – Ver",      default=False)
    reporte_editar        = models.BooleanField("Reporte – Editar",   default=False)
    reporte_eliminar      = models.BooleanField("Reporte – Eliminar", default=False)
    # Plantilla de Horario
    plantilla_ver         = models.BooleanField("Plantilla – Ver",      default=False)
    plantilla_editar      = models.BooleanField("Plantilla – Editar",   default=False)
    plantilla_eliminar    = models.BooleanField("Plantilla – Eliminar", default=False)
    # Asignación de Horario
    asignacion_ver        = models.BooleanField("Asignación – Ver",      default=False)
    asignacion_editar     = models.BooleanField("Asignación – Editar",   default=False)
    asignacion_eliminar   = models.BooleanField("Asignación – Eliminar", default=False)
    # Tiempo Compensatorio
    compensatorio_ver     = models.BooleanField("Compensatorio – Ver",      default=False)
    compensatorio_editar  = models.BooleanField("Compensatorio – Editar",   default=False)
    compensatorio_eliminar= models.BooleanField("Compensatorio – Eliminar", default=False)
    # Feriados
    feriado_ver           = models.BooleanField("Feriados – Ver",      default=False)
    feriado_editar        = models.BooleanField("Feriados – Editar",   default=False)
    feriado_eliminar      = models.BooleanField("Feriados – Eliminar", default=False)
    # Sábados Especiales
    sabado_ver            = models.BooleanField("Sábados – Ver",      default=False)
    sabado_editar         = models.BooleanField("Sábados – Editar",   default=False)
    sabado_eliminar       = models.BooleanField("Sábados – Eliminar", default=False)
    # Cálculo Compensatorio (tabs 1-2: adeudados)
    calculo_comp_ver      = models.BooleanField("Cálculo Comp. – Ver",      default=False)
    calculo_comp_editar   = models.BooleanField("Cálculo Comp. – Editar",   default=False)
    calculo_comp_eliminar = models.BooleanField("Cálculo Comp. – Eliminar", default=False)
    # Compensatorio Mensual / Instructores (tabs 3-4-5)  <--- hecho por claude code
    comp_mensual_ver      = models.BooleanField("Comp. Mensual – Ver",      default=False)
    comp_mensual_editar   = models.BooleanField("Comp. Mensual – Editar",   default=False)
    comp_mensual_eliminar = models.BooleanField("Comp. Mensual – Eliminar", default=False)
    # Vacaciones
    vacaciones_ver        = models.BooleanField("Vacaciones – Ver",      default=False)
    vacaciones_editar     = models.BooleanField("Vacaciones – Editar",   default=False)
    vacaciones_eliminar   = models.BooleanField("Vacaciones – Eliminar", default=False)
    # Permisos Empleados (solo visualizar)
    permisos_ver          = models.BooleanField("Permisos – Ver",        default=False)
    # Permiso PROVISIONAL para registrar permisos fuera de fecha (tras el cierre de mes).
    # Si está a futuro, el usuario puede registrar permisos hasta esa fecha/hora; luego expira solo.
    permisos_registrar_hasta = models.DateTimeField("Permisos – Registrar hasta", null=True, blank=True)
    # Vigilancia
    vigilancia_ver        = models.BooleanField("Vigilancia – Ver",      default=False)
    # Instructores CFP
    cfp_ver               = models.BooleanField("Instructores CFP – Ver", default=False)
    # Reportes PDF (vista previa y descarga)
    reportes_pdf_ver      = models.BooleanField("Reportes PDF – Ver",     default=False)

    class Meta:
        db_table         = 'reloj_permiso_usuario'
        verbose_name     = 'Permiso de módulo reloj'
        verbose_name_plural = 'Permisos de módulos reloj'

    def __str__(self):
        return f'Permisos reloj – {self.user}'


class RelojConfigGlobal(models.Model):
    """Configuración global del módulo reloj (singleton pk=1)."""
    factor_horas_visible = models.BooleanField(
        'Factor H/Día visible para todos', default=True,
        help_text='Si False, la columna solo la ve el superusuario.'
    )
    horas_diarias_visible = models.BooleanField(
        'Horas Diarias Lab. visible para todos', default=True,
        help_text='Si False, la columna solo la ve el superusuario.'
    )
    # Reglas configurables de rebaja por tardanza (minutos → horas).
    # Cada regla: {"min": int, "max": int, "horas": float}. El último tramo
    # también aplica a valores por encima de su "max".
    tarde_reglas = models.JSONField('Reglas de rebaja por tardanza', blank=True, default=list)

    class Meta:
        db_table = 'reloj_config_global'
        verbose_name = 'Configuración global Reloj'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
