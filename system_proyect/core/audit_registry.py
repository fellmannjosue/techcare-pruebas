"""
Registro centralizado de django-simple-history para todos los modelos del proyecto.
Se llama desde core/apps.py ready() para no modificar cada models.py individualmente.
Excluye: sponsors, auth, contenttypes, sessions, simple_history internas y AuditLog propio.
"""
from simple_history import register as _register


def _safe_register(model):
    try:
        _register(model)
    except Exception:
        pass  # Ya registrado o no compatible


def register_all():
    # ── accounts ──
    from accounts.models import CoordPermiso, DestinatarioEmail, PerfilUsuario, RegistroAcceso
    for m in (CoordPermiso, DestinatarioEmail, PerfilUsuario, RegistroAcceso):
        _safe_register(m)

    # ── agendas ──
    from agendas.models import Agenda, GradoAgenda, ImagenAgenda
    for m in (Agenda, GradoAgenda, ImagenAgenda):
        _safe_register(m)

    # ── calculadoras ──
    from calculadoras.models import TasaCambio
    _safe_register(TasaCambio)

    # ── conducta ──
    from conducta.models import (
        ConfiguracionCoordinador, ConfiguracionNotificacion, EvidenciaReporte,
        IncisoConductual, MateriaDocenteBilingue, MateriaDocenteColegio,
        ProgressReport, ReporteConductual, ReporteInformativo,
    )
    for m in (
        ConfiguracionCoordinador, ConfiguracionNotificacion, EvidenciaReporte,
        IncisoConductual, MateriaDocenteBilingue, MateriaDocenteColegio,
        ProgressReport, ReporteConductual, ReporteInformativo,
    ):
        _safe_register(m)

    # ── core ──
    from core.models import Notificacion
    _safe_register(Notificacion)

    # ── enfermeria ──
    from enfermeria.models import (
        AtencionMedica, Grado, InventarioMedicamento, Medico,
        Presentacion, Proveedor, Responsable, UsoMedicamento,
    )
    for m in (
        AtencionMedica, Grado, InventarioMedicamento, Medico,
        Presentacion, Proveedor, Responsable, UsoMedicamento,
    ):
        _safe_register(m)

    # ── inventario ──
    from inventario.models import (
        AreaComputadora, AreaTelevisor, AsignadoAComputadora, CategoriaInventario,
        Computadora, DataShow, EdificioComputadora, GradoComputadora, GradoTelevisor,
        Impresora, InventoryItem, ModeloComputadora, ModeloMonitor, ModeloTelevisor,
        Monitor, Router, SerieComputadora, SubtipoGradoComputadora, Televisor,
    )
    for m in (
        AreaComputadora, AreaTelevisor, AsignadoAComputadora, CategoriaInventario,
        Computadora, DataShow, EdificioComputadora, GradoComputadora, GradoTelevisor,
        Impresora, InventoryItem, ModeloComputadora, ModeloMonitor, ModeloTelevisor,
        Monitor, Router, SerieComputadora, SubtipoGradoComputadora, Televisor,
    ):
        _safe_register(m)

    # ── mantenimiento ──
    from mantenimiento.models import (
        FotoMantenimiento, GradoMantenimiento, MaestroMantenimiento,
        MaintenanceRecord, TipoFalla,
    )
    for m in (
        FotoMantenimiento, GradoMantenimiento, MaestroMantenimiento,
        MaintenanceRecord, TipoFalla,
    ):
        _safe_register(m)

    # ── notas_parcial ──
    from notas_parcial.models import AsignacionMaestro, NotaComentario, RevisionFinalizada
    for m in (AsignacionMaestro, NotaComentario, RevisionFinalizada):
        _safe_register(m)

    # ── reloj ──
    from reloj.models import (
        CompensatorioCalculo, CompensatorioInstructor, CompensatorioMensualEmpleado,
        CompensatorioMensualValor, DiaNoLaborableANA, EmployeeScheduleAssignment,
        Feriado, FeriadoAsignacion, OvertimeRequest, PermisoEmpleado, PermisoReporte,
        RelojConfigGlobal, RelojPermiso, ReporteComentario, ReporteNota,
        ReportePermisoMensual, SabadoAsignacion, SabadoEspecial, ScheduleRule,
        ScheduleTemplate, TiempoCompensatorio, TiempoExtraDia, VacacionConfig,
    )
    for m in (
        CompensatorioCalculo, CompensatorioInstructor, CompensatorioMensualEmpleado,
        CompensatorioMensualValor, DiaNoLaborableANA, EmployeeScheduleAssignment,
        Feriado, FeriadoAsignacion, OvertimeRequest, PermisoEmpleado, PermisoReporte,
        RelojConfigGlobal, RelojPermiso, ReporteComentario, ReporteNota,
        ReportePermisoMensual, SabadoAsignacion, SabadoEspecial, ScheduleRule,
        ScheduleTemplate, TiempoCompensatorio, TiempoExtraDia, VacacionConfig,
    ):
        _safe_register(m)

    # ── salidas_bano ──
    from salidas_bano.models import MaestroClase, NotificacionSalida, PeriodoEscolar, SalidaBano
    for m in (MaestroClase, NotificacionSalida, PeriodoEscolar, SalidaBano):
        _safe_register(m)

    # ── tickets ──
    from tickets.models import Ticket, TicketComment
    for m in (Ticket, TicketComment):
        _safe_register(m)
