# <--- hecho por claude code: Ingreso de Notas — bitácora propia de escrituras al legacy
from django.conf import settings
from django.db import models


class EscrituraNota(models.Model):
    """Registro de CADA celda que TechCare escribe en el sistema académico legacy.

    El legacy ya tiene sus propios triggers de auditoría, pero solo cubren
    `AFTER UPDATE` (`trg_Audit_tblEdcEvalBL`). Esta tabla vive en MySQL, guarda
    también los INSERT y deja el rastro del lado de TechCare: quién, cuándo, qué
    celda y el valor anterior. Es lo que permite deshacer un error sin depender
    de la base ajena.
    """
    # <--- hecho por claude code: `delete` para las asistencias. Quitar una ausencia
    # puesta por error borra la fila del legacy, y ese rastro no lo guarda nadie más
    # (sus triggers solo cubren UPDATE). Las notas siguen sin borrarse nunca.
    ACCIONES = [('insert', 'Creó la fila'), ('update', 'Actualizó'),
                ('delete', 'Quitó la fila')]

    usuario     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name='notas_escritas')
    area        = models.CharField('Área', max_length=30)
    rama        = models.CharField('Rama legacy', max_length=10)      # bl | acad
    tabla       = models.CharField('Tabla', max_length=40)
    materia_id  = models.IntegerField('ID materia (legacy)', db_index=True)
    eval_id     = models.IntegerField('ID evaluación (legacy)', null=True, blank=True)
    parcial     = models.PositiveSmallIntegerField('Parcial')
    columna     = models.CharField('Columna', max_length=30)
    valor_antes = models.CharField('Valor anterior', max_length=30, blank=True, default='')
    valor_nuevo = models.CharField('Valor nuevo', max_length=30, blank=True, default='')
    accion      = models.CharField('Acción', max_length=10, choices=ACCIONES, default='update')
    alumno      = models.CharField('Alumno', max_length=200, blank=True, default='')
    creado      = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ingresos_notas_escritura'
        ordering = ['-creado']
        verbose_name = 'Escritura de nota'
        verbose_name_plural = 'Bitácora de ingreso de notas'

    def __str__(self):
        return f'{self.alumno or self.materia_id} · {self.columna} → {self.valor_nuevo}'
