from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reloj', '0005_add_reporte_nota'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReporteComentario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emp_code', models.CharField(db_index=True, max_length=20, verbose_name='Código empleado')),
                ('fecha', models.DateField(db_index=True, verbose_name='Fecha')),
                ('texto', models.TextField(verbose_name='Texto')),
                ('creado_en', models.DateTimeField(auto_now_add=True, verbose_name='Creado en')),
                ('creado_por', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reporte_comentarios',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Creado por'
                )),
            ],
            options={
                'verbose_name': 'Comentario de reporte',
                'verbose_name_plural': 'Comentarios de reporte',
                'db_table': 'reloj_reporte_comentario',
                'ordering': ['creado_en'],
            },
        ),
    ]
