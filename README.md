# TechCare – Sistema de Gestión Institucional

Sistema web desarrollado en Django para la **Asociación Nuevo Amanecer**. Centraliza la gestión de tickets, asistencia, conducta estudiantil, inventario, citas, enfermería, seguridad y más.

- **URL de producción:** https://servicios.ana-hn.org:437
- **Servidor:** Apache + mod_wsgi · Django 5.0.14 · Python 3.11
- **Base de datos principal:** MySQL (`sponsors2` en `192.168.10.6`)
- **Base de datos secundaria:** SQL Server (módulo Reloj)
- **UI:** Tabler UI v1.0.0-beta19

---

## Estructura del repositorio

```
techcare_project/
├── system_proyect/       # Proyecto Django de producción
│   ├── accounts/         # Autenticación, menú principal, registro
│   ├── tickets/          # Sistema de tickets de soporte
│   ├── conducta/         # Reportes conductuales y académicos
│   ├── reloj/            # Control de asistencia (SQL Server)
│   ├── inventario/       # Inventario de equipos y activos
│   ├── mantenimiento/    # Registro de mantenimientos
│   ├── citas_billingue/  # Citas – departamento bilingüe
│   ├── citas_colegio/    # Citas – colegio/vocacional
│   ├── enfermeria/       # Atención médica e inventario medicamentos
│   ├── sponsors/         # Gestión de patrocinadores
│   ├── seguridad/        # Control de cámaras y contabilidad
│   └── core/             # Utilidades compartidas y notificaciones
├── django_test/          # Entorno de pruebas (copia del proyecto)
└── datos/                # Scripts SQL y CSV de datos de ejemplo
```

---

## Módulos

### Accounts — Autenticación y Panel Principal
Login unificado con redirección automática según rol (maestro, técnico, coordinador, admin).

| Ruta | Descripción |
|------|-------------|
| `/accounts/login/` | Inicio de sesión |
| `/accounts/logout/` | Cierre de sesión |
| `/accounts/register/` | Registro de usuarios (maestros / staff) |
| `/accounts/menu/` | Panel principal con tarjetas por módulo |
| `/accounts/password_reset/` | Recuperar contraseña (envío de enlace) |
| `/accounts/reenviar-bienvenida/` | Reenvío de correo de bienvenida (solo superuser) |

**Roles y grupos:**
- `maestros_bilingue` / `maestros_colegio` → dashboard de maestro
- `coordinador_bilingue` / `coordinador_colegio` → dashboard de coordinador
- `admin_bilingue` / `admin_colegio` / `administracion` → acceso administrativo
- `tecnicos` → dashboard de tickets
- Superusuario → acceso completo + herramientas de admin

---

### Tickets — Soporte Técnico
Gestión de solicitudes de soporte con seguimiento, comentarios y notificaciones por correo.

| Ruta | Descripción |
|------|-------------|
| `/tickets/submit_ticket/` | Crear ticket |
| `/tickets/technician_dashboard/` | Panel para técnicos |
| `/tickets/<id>/comments/` | Conversación / chat del ticket |

---

### Conducta — Reportes Académicos y de Conducta
Sistema de reportes para maestros con revisión por coordinadores.

**Tipos de reportes:**
- **Reporte Informativo** — comunicación académica general
- **Reporte Conductual** — faltas de conducta (genera PDF individual y "3 Strikes")
- **Progress Report** — seguimiento académico (solo área bilingüe)

**Áreas:** Bilingüe y Colegio/CFP (flujos independientes)

| Ruta | Descripción |
|------|-------------|
| `/conducta/dashboard/maestro/` | Dashboard del maestro |
| `/conducta/historial/bilingue/` | Historial de reportes – maestro bilingüe |
| `/conducta/historial/colegio/` | Historial de reportes – maestro colegio |
| `/conducta/coordinador/<area>/` | Dashboard del coordinador |
| `/conducta/reenviar-reportes/` | Reenviar notificaciones a coordinadores (solo superuser) |
| `/conducta/pdf/informativo/<id>/` | Descargar PDF informativo |
| `/conducta/pdf/conductual/<id>/` | Descargar PDF conductual |
| `/conducta/pdf/conductual/3strikes/<id>/` | Descargar PDF 3 Strikes |

**Notificaciones automáticas:** Al crear cualquier reporte, se envía correo HTML a los 4 coordinadores (`ialcerro`, `druiz`, `jmartinez`, `acruz` @ana-hn.org).

**Evidencias:** Cada reporte admite hasta 2 imágenes de evidencia.

---

### Reloj — Control de Asistencia
Conecta con SQL Server para leer marcas del reloj biométrico. Gestiona horarios, compensatorios, permisos, feriados y genera reportes.

| Ruta | Descripción |
|------|-------------|
| `/reloj/` | Dashboard principal |
| `/reloj/tiempo-por-hora/` | Tabla detallada de marcas por empleado/día |
| `/reloj/reporte/` | Reporte de asistencia con filtros |
| `/reloj/feriados/` | Listado de feriados |
| `/reloj/feriados/nuevo/` | Crear feriado (rango de fechas) |
| `/reloj/feriados/<id>/editar/` | Editar feriado y asignar empleados |
| `/reloj/feriados/asignacion/bulk/` | Guardar asignación masiva de empleados |
| `/reloj/solicitudes/` | Solicitudes de compensatorio / permiso |

**Feriados:** Soportan rango de fechas (`fecha_inicio` → `fecha_fin`) y asignación individual por empleado mediante checkboxes.

**Columnas en Tiempo por Hora:** Horario Programado · Feriado · Marcas del Día · Compensatorio · Ausencias · Otro Pagado · Vacaciones · Enfermedad.

---

### Inventario — Activos y Equipos
Control de equipos institucionales con QR, PDF y categorías.

| Ruta | Descripción |
|------|-------------|
| `/inventario/` | Panel general |
| `/inventario/computadoras/` | Listado de computadoras |
| `/inventario/televisores/` | Listado de televisores |
| `/inventario/impresoras/` | Listado de impresoras |
| `/inventario/routers/` | Listado de routers |
| `/inventario/datashows/` | Listado de datashows |
| `/inventario/por_categoria/` | Consulta unificada por categoría |
| `/inventario/download_item_pdf/<id>/` | Ficha en PDF |
| `/registros/qr/<tipo>/<pk>/` | Código QR del equipo |

---

### Mantenimiento
Registro y descarga de reportes de mantenimiento.

| Ruta | Descripción |
|------|-------------|
| `/mantenimiento/` | Listado y formulario |
| `/mantenimiento/download/<id>/` | Reporte en PDF |

---

### Citas Bilingüe / Colegio
Agendamiento de citas para padres de familia.

| Ruta | Descripción |
|------|-------------|
| `/citas_billingue/dashboard_bl/` | Gestión de citas bilingüe |
| `/citas_colegio/dashboard_col/` | Gestión de citas colegio |

---

### Enfermería
Atención médica, inventario de medicamentos e historial en PDF o correo.

| Ruta | Descripción |
|------|-------------|
| `/enfermeria/` | Dashboard principal |
| `/enfermeria/atencion/` | Registrar atención médica |
| `/enfermeria/inventario/` | Inventario de medicamentos |
| `/enfermeria/historial/` | Historial médico |

---

### Sponsors — Patrocinadores
Gestión de padrinos y patrocinadores institucionales.

| Ruta | Descripción |
|------|-------------|
| `/sponsors/dashboard/` | Vista principal |

---

### Seguridad
Control de cámaras, registros contables e identificación de equipos.

| Ruta | Descripción |
|------|-------------|
| `/seguridad/` | Dashboard de seguridad |

---

## Variables de entorno (`.env`)

```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False

# MySQL (base de datos principal)
DB_NAME=sponsors2
DB_USER=admin3
DB_PASSWORD=...
DB_HOST=192.168.10.6
DB_PORT=3306

# SQL Server (módulo Reloj)
MSSQL_DB_NAME=...
MSSQL_DB_USER=...
MSSQL_DB_PASSWORD=...
MSSQL_DB_HOST=...
MSSQL_DB_PORT=1433

# Correo (Gmail SMTP)
EMAIL_HOST_USER=techcare.app2024@gmail.com
EMAIL_HOST_PASSWORD=...
```

---

## Comandos frecuentes

```bash
# Conectar al servidor
ssh admin2@192.168.10.6

# Activar entorno virtual
cd techcare_project
source venv/bin/activate
cd system_proyect

# Aplicar cambios en producción
python manage.py collectstatic --noinput
sudo systemctl restart apache2

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Servidor de desarrollo
python manage.py runserver

# Shell interactiva
python manage.py shell

# Crear superusuario
python manage.py createsuperuser
```

---

## Despliegue

El proyecto corre con **Apache + mod_wsgi**. Después de cualquier cambio en código Python o archivos estáticos:

```bash
sudo systemctl restart apache2
```

Si se modifican templates o archivos estáticos:

```bash
python manage.py collectstatic --noinput
sudo systemctl restart apache2
```

---

*© 2025 Soporte Técnico – Asociación Nuevo Amanecer*
