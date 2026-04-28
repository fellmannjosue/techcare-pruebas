# TechCare – Sistema de Gestión Institucional

Sistema web desarrollado en Django para la **Asociación Nuevo Amanecer**. Centraliza la gestión de tickets, asistencia, conducta estudiantil, inventario, citas, enfermería, seguridad, agendas docentes y más.

- **URL de producción:** https://servicios.ana-hn.org:437
- **Servidor:** Apache + mod_wsgi · Django 5.0.14 · Python 3.11
- **Base de datos principal:** MySQL (`sponsors2` en `192.168.10.6`)
- **Bases de datos secundarias:** SQL Server (módulo Reloj y datos de alumnos/padres)
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
│   ├── enfermeria/       # Atención médica, medicamentos y directorio
│   ├── agendas/          # Agendas semanales docentes (BL y Colegio)
│   ├── sponsors/         # Gestión de patrocinadores
│   ├── seguridad/        # Control de cámaras y contabilidad
│   └── core/             # Utilidades compartidas y notificaciones
├── django_test/          # Entorno de pruebas (copia del proyecto)
└── datos/                # Scripts SQL y CSV de datos de ejemplo
```

---

## Módulos

### Accounts — Autenticación y Panel Principal
Login unificado con redirección automática según rol (maestro, técnico, coordinador, admin). Sidebar unificado compartido por todos los módulos vía `accounts/templates/accounts/_sidebar.html`.

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
- `coordinador_bilingue` → dashboard coordinador BL + acceso a enfermería, agendas y directorio BL
- `coordinadores_colegio` / `coordinadores` → dashboard coordinador Colegio + directorio Colegio
- `administracion` → acceso administrativo
- `tecnicos` → dashboard de tickets
- Superusuario → acceso completo + herramientas de admin

**Sidebar unificado:** todas las apps usan `{% include 'accounts/_sidebar.html' %}`. Los ítems visibles se controlan con variables `nav_*` inyectadas por `core/context_processors.py`.

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
| `/conducta/directorio/` | Directorio de teléfonos (coordinadores) |
| `/conducta/reenviar-reportes/` | Reenviar notificaciones a coordinadores (solo superuser) |
| `/conducta/pdf/informativo/<id>/` | Descargar PDF informativo |
| `/conducta/pdf/conductual/<id>/` | Descargar PDF conductual |
| `/conducta/pdf/conductual/3strikes/<id>/` | Descargar PDF 3 Strikes |

**Notificaciones automáticas:** Al crear cualquier reporte, se envía correo HTML a los coordinadores correspondientes (`ialcerro`, `druiz`, `jmartinez`, `cvarela` @ana-hn.org).

**Evidencias:** Cada reporte admite hasta 2 imágenes de evidencia.

---

### Agendas — Agendas Semanales Docentes
Permite a los maestros registrar y a los coordinadores revisar las agendas semanales de cada grado.

**Áreas y materias:**
- **Primaria Bilingüe** (`primaria`) → Math, Phonics, Reading, Language, Science, Español, CCSS, Asociadas
- **Colegio Bilingüe** (`colegio_bl`) → Math, Spelling, Reading, Language, Science, Español, CCSS, Cívica, Asociadas
- **Colegio 7mo–9no** (`colegio_7_9`) → Matemática, Dibujo Técnico, Español, Ciencias Naturales, Cívica, Estudios Sociales, Inglés, Tecnología, Artística, Computación, Orientación, E. Física
- **Colegio 10mo** (`colegio_10`) → Matemática, Física Elemental, Robótica, Español, Química, Biología, Sociología, Psicología, Historia de Honduras, Inglés Básico, Inglés Avanzado, Educ. Física, Informática
- **Colegio 11mo** (`colegio_11`) → Matemática, Física Elemental, Dibujo Téc., Robótica, Química, Biología, Español, Historia Universal, Economía, Antropología, Artística, Filosofía, Inglés, Educ. Física

**Filtrado por rol:** BL (coordinador/maestro) ve solo grados BL; Colegio ve solo grados Colegio.

**Descarga:**
- Área BL → genera **PPTX** con fondo de plantilla (`plantilla agendas.png`)
- Área Colegio → genera **DOCX** (Word, A4 horizontal, tabla con cabecera azul)

| Ruta | Descripción |
|------|-------------|
| `/agendas/form/` | Registrar agenda (maestros) |
| `/agendas/historial/` | Historial de agendas propias |
| `/agendas/coordinador/` | Dashboard coordinador (todas las agendas del área) |
| `/agendas/<id>/editar/` | Editar agenda |
| `/agendas/<id>/pptx/` | Descargar agenda (PPTX para BL, DOCX para Colegio) |
| `/agendas/modo/toggle/` | Alternar modo maestro/coordinador (coord-maestros) |

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
| `/reloj/solicitudes/` | Solicitudes de compensatorio / permiso |

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
Atención médica, inventario de medicamentos, historial y directorio de teléfonos de alumnos.

| Ruta | Descripción |
|------|-------------|
| `/enfermeria/` | Dashboard principal |
| `/enfermeria/atencion/` | Registrar atención médica |
| `/enfermeria/inventario/` | Inventario de medicamentos |
| `/enfermeria/historial/` | Historial médico |
| `/enfermeria/directorio/` | Directorio de teléfonos con links WhatsApp |

**Directorio de teléfonos:** Consulta SQL Server (`tblPrsDtosGen`) para obtener `Tel1`/`Tel2` de cada alumno. Filtrado por área: coordinador BL ve alumnos BL, coordinador Colegio ve alumnos Colegio, admin ve todos. Genera links directos a WhatsApp (`wa.me/504XXXXXXXX`). También accesible desde conducta en `/conducta/directorio/`.

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

# SQL Server (módulo Reloj y datos de alumnos)
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

# Recargar sin reiniciar Apache (mod_wsgi)
touch system_proyect/wsgi.py

# Aplicar cambios estáticos en producción
python manage.py collectstatic --noinput

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

El proyecto corre con **Apache + mod_wsgi**. Para recargar el código Python sin reiniciar Apache:

```bash
touch system_proyect/wsgi.py
```

Para cambios en archivos estáticos:

```bash
python manage.py collectstatic --noinput
touch system_proyect/wsgi.py
```

---

*© 2025 Soporte Técnico – Asociación Nuevo Amanecer*
