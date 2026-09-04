# <--- hecho por claude code: rediseño tabs 1-2 (Cálculo Compensatorio) — periodo anual configurable
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reloj', '0059_bonoexencionempleado'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompensatorioPeriodoAnual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveIntegerField(db_index=True, unique=True, verbose_name='Año')),
                ('fecha_inicio', models.DateField(verbose_name='Inicio del periodo')),
                ('fecha_fin', models.DateField(verbose_name='Fin del periodo')),
            ],
            options={
                'verbose_name': 'Periodo compensatorio anual',
                'verbose_name_plural': 'Periodos compensatorios anuales',
                'db_table': 'reloj_compensatorio_periodo_anual',
                'ordering': ['-anio'],
            },
        ),
    ]
