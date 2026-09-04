# <--- hecho por claude code: rediseño tabs 1-2 — override manual de "Vacación acumulada"
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reloj', '0060_compensatorioperiodoanual'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompensatorioVacacionManual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emp_code', models.CharField(db_index=True, max_length=20, unique=True, verbose_name='Código empleado')),
                ('acumulada', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Vacación acumulada (manual)')),
            ],
            options={
                'verbose_name': 'Vacación acumulada manual',
                'verbose_name_plural': 'Vacaciones acumuladas manuales',
                'db_table': 'reloj_compensatorio_vacacion_manual',
                'ordering': ['emp_code'],
            },
        ),
    ]
