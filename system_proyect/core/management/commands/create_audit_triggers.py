"""
Management command: crea (o recrea) los triggers MySQL de auditoría para todas las tablas.

Uso:
    python manage.py create_audit_triggers           # crea todos
    python manage.py create_audit_triggers --drop    # elimina triggers existentes primero
    python manage.py create_audit_triggers --dry-run # imprime el SQL sin ejecutar

Los triggers escriben en core_audit_log (INSERT/UPDATE/DELETE).
Excluye: tablas de sponsors, simple_history, constance, y la propia core_audit_log.
"""
from django.core.management.base import BaseCommand
from django.db import connection

# Tablas a excluir de triggers
_EXCLUIR = {
    'core_audit_log',
    'tblPrsDtosGen',           # legacy enfermeria
    'constance_config',
    'django_migrations',
    'django_content_type',
    'django_session',
    'django_admin_log',
    'auth_permission',
    'auth_group',
    'auth_group_permissions',
    'auth_user',
    'auth_user_groups',
    'auth_user_user_permissions',
}

# Prefijos de tablas de simple_history (se detectan por patrón)
_HISTORY_PREFIX = 'historical'


class Command(BaseCommand):
    help = 'Crea triggers MySQL de auditoría en todas las tablas del proyecto'

    def add_arguments(self, parser):
        parser.add_argument('--drop', action='store_true', help='Elimina triggers existentes antes de crear')
        parser.add_argument('--dry-run', action='store_true', help='Imprime SQL sin ejecutar')

    def handle(self, *args, **options):
        drop    = options['drop']
        dry_run = options['dry_run']

        with connection.cursor() as cursor:
            # Obtener todas las tablas de la BD
            cursor.execute("SHOW TABLES")
            all_tables = [row[0] for row in cursor.fetchall()]

        tables = [
            t for t in all_tables
            if t not in _EXCLUIR
            and not t.startswith(_HISTORY_PREFIX)
        ]

        total_sql = []

        for table in sorted(tables):
            # Detectar columna PK
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = %s
                      AND COLUMN_KEY = 'PRI'
                    LIMIT 1
                """, [table])
                row = cursor.fetchone()
                pk_col = row[0] if row else 'id'

            for op, timing, ref in [
                ('INSERT', 'AFTER', f'NEW.`{pk_col}`'),
                ('UPDATE', 'AFTER', f'NEW.`{pk_col}`'),
                ('DELETE', 'AFTER', f'OLD.`{pk_col}`'),
            ]:
                tname   = f'tc_{table[:40]}_{op[:3].lower()}'
                drop_sql = f"DROP TRIGGER IF EXISTS `{tname}`;"
                create_sql = (
                    f"CREATE TRIGGER `{tname}` {timing} {op} ON `{table}` "
                    f"FOR EACH ROW "
                    f"INSERT INTO `core_audit_log` "
                    f"(`table_name`,`operation`,`record_pk`,`changed_at`) "
                    f"VALUES ('{table}','{op}',{ref},NOW());"
                )
                total_sql.append((drop_sql, create_sql, tname))

        created = 0
        errors  = 0
        for drop_sql, create_sql, tname in total_sql:
            if dry_run:
                self.stdout.write(drop_sql)
                self.stdout.write(create_sql)
                self.stdout.write('')
                continue
            try:
                with connection.cursor() as cursor:
                    cursor.execute(drop_sql)
                    if drop:
                        pass  # ya eliminado
                    cursor.execute(create_sql)
                created += 1
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(f'ERROR {tname}: {e}'))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'Triggers creados: {created}  |  Errores: {errors}  |  Tablas: {len(tables)}'
            ))
        else:
            self.stdout.write(self.style.WARNING(f'DRY RUN — {len(total_sql)} triggers generados'))
