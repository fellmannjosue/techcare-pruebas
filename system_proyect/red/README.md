# ANA Network Manager — Informe ejecutivo para 00-1 (Líder)

> Módulo **`red`** de TechCare · publicado en **v7.6.0** (25-ago-2026), refinado en **v7.6.1**.
> Estado: **operativo en producción**, acceso **solo superadministrador**. Este documento describe
> qué es, qué hace, cómo está construido, qué datos tiene cargados y qué falta.

---

## 1. Qué es y para qué sirve
**ANA Network Manager** es el sistema de **documentación y operación de la red institucional** de
ANA, integrado dentro de TechCare (no es un programa aparte). Reemplaza la información dispersa
(hojas, memoria de una persona, diagramas sueltos) por una **fuente única, auditable y visual** de:

- **Direccionamiento IP (IPAM):** VLANs, subredes, IPs asignadas/libres/reservadas/DHCP, capacidad.
- **Inventario de equipos de red:** dispositivos, switches, puertos y enlaces.
- **Ubicación física:** campus → edificios → ubicaciones → gabinetes, con **racks** por unidades (U).
- **Mapas y topología:** planos con marcadores y cables, y diagrama lógico de la red.
- **Operación:** pruebas de conectividad (ping), planificación de migraciones de VLAN, buscador
  global y exportación a Excel.
- **Auditoría:** bitácora de cada cambio (quién, qué, cuándo, desde qué IP).

**Valor para la institución:** menos tiempo buscando información, menos fallos por cambios
improvisados, respuesta más rápida ante caídas, decisiones de capacidad con datos, y **continuidad**
(la red queda documentada aunque cambie el personal de soporte).

## 2. Alcance construido (Fases 1–5, todas entregadas)

| Fase | Contenido | Estado |
|---|---|---|
| **1 · IPAM y catálogo** | Campus/Edificio/Ubicación/Gabinete · VLANs con capacidad real · IPs · Dispositivos e interfaces | ✅ |
| **2 · Switches y enlaces** | Switches, puertos (modo acceso/trunk, VLAN nativa/tagged, PoE), enlaces entre equipos, detección de bucles | ✅ |
| **3 · Mapas y topología** | Planos con marcadores (figuras de red), líneas/cables, zoom/rotación, topología Cytoscape, **racks** por gabinete | ✅ |
| **4 · Operación y análisis** | Panel avanzado (KPIs + gráficas), **pruebas de conectividad (ping)**, **planificador de migración VLAN** (análisis de impacto) | ✅ |
| **5 · Productividad** | **Buscador global** (IP/MAC/equipo/switch/VLAN), **exportar a Excel**, endpoint JSON de búsqueda | ✅ |

## 3. Cómo está construido (técnico, resumido)
- **Django app `red`**, 16 modelos, tablas **`red_*`** en la base principal MySQL `sponsors2`.
  18 migraciones. ~2 360 líneas de Python (modelos/vistas/servicios/formularios), 28 plantillas,
  6 archivos JS y 5 CSS propios (JS/CSS siempre en archivos separados, nunca inline).
- **Seguridad:** todas las vistas pasan por `_gate()` = **solo `is_superuser`**. Existe un grupo
  `red` y permisos (`ver_red`, `administrar_red`…) listos para abrir el acceso a más personas cuando
  se decida. Cada acción escribe en **`RedAuditLog`** (usuario, IP, módulo, registro, antes/después).
  Los modelos clave llevan historial (`django-simple-history`).
- **Lógica dura en `services.py`** (no en las vistas): validación de CIDR/rangos, cálculo de
  capacidad por VLAN, duplicados de IP/MAC, asignar/reservar/liberar IP, validación de puertos y
  enlaces, detección de ciclos, y `ping_host()`.
- **Frontend:** Tabler (misma identidad visual del portal), Chart.js para gráficas, Cytoscape para
  topología, SVG propio para líneas en planos. Todo responsive y con modo oscuro.
- **68 rutas** bajo `/red/`. Dashboard con tarjetas de acceso a cada módulo.

## 4. Funcionalidades en detalle

### 4.1 IPAM — VLANs y direcciones
- Cada **VLAN** define subred, gateway, **rango asignable**, **rango reservado** y **rango DHCP**,
  límite de dispositivos y **umbral de alerta**. La capacidad se calcula sobre el **rango asignable
  configurado** (no sobre las 254 direcciones), y el estado pasa a *advertencia / crítico / agotado*
  automáticamente, con notificación cuando quedan ≤10 IP.
- Las IPs se **generan en bloque** por VLAN (idempotente) y se gestionan desde una **grilla IPAM**
  (asignar, reservar, liberar). Se rechazan IP fuera de rango y **duplicados de IP o MAC**.
- Estados de IP: libre, reservada, asignada, dhcp, conflicto, pendiente, no utilizable.

### 4.2 Dispositivos, switches, puertos y enlaces
- **Dispositivo**: código interno, nombre, hostname, tipo (21 tipos: servidor, router, switch,
  AP, cámara, NVR, teléfono IP, impresora, reloj, UPS, PBX…), fabricante/modelo/serie, MAC, ubicación,
  gabinete, VLAN, IP, método de direccionamiento, responsable, estado, criticidad, garantía.
- **Switch**: IP/MAC de administración, administrable/PoE, cantidad de puertos y SFP, firmware,
  URL de administración, fecha de último respaldo. **Puertos** con modo (acceso/trunk), VLAN de
  acceso/nativa/tagged, PoE, estado físico, dispositivo conectado, cable/etiqueta física.
- **Enlaces** entre equipos (RJ45, fibra, radio, virtual) con VLAN nativa/permitidas y validación
  de coherencia. **Detección de bucles** en la topología.

### 4.3 Mapa de campus (planos)
- Se suben **planos** (imágenes de cada edificio/planta) y se colocan **marcadores** con
  **figuras de red** (router, switch, servidor, AP, firewall, cámara, PC, impresora, gabinete,
  nube/Internet, teléfono IP, reloj marcador, reloj de acceso).
- Cada marcador se edita en un **panel flotante** (nombre, tipo, vínculo a gabinete/dispositivo/
  switch, color, figura, **tamaño** y **giro**; el giro rota ícono y texto). **Selección múltiple**
  para cambiar tamaño/giro o eliminar en lote.
- **Líneas/cables** entre marcadores: recta u **ortogonal** (ángulos rectos) con **punto de
  referencia** arrastrable, nombre y color; si un extremo es un gabinete, la línea puede apuntar a
  **un equipo concreto del rack** (ej. "Switch 1"). **Zoom, orientación y paneo** del plano,
  recordados por plano.
- Un marcador de gabinete abre directamente **su rack**.

### 4.4 Racks (elevación tipo draw.io)
- Cada **gabinete** tiene su **rack por unidades (U)** con numeración estándar (**U1 abajo → U42
  arriba**), **frente y atrás**, y equipos apilables: switch, patch panel, servidor, firewall,
  router, **NVR**, **media converter**, **bandeja**, PDU, organizador, KVM, UPS, espacio libre.
- Los equipos se **arrastran** para cambiar de U, se editan con clic, y pueden **vincularse al
  inventario** (Device/Switch). Acceso desde *Dashboard de Red → Racks*.

### 4.5 Topología
- Diagrama **Cytoscape** de dispositivos y enlaces (color por tipo o por VLAN, posiciones que se
  guardan al arrastrar, info del enlace al clic, filtros por edificio/VLAN/tipo).
- También puede dibujar **el diagrama de un plano** (marcadores + líneas). Export **PNG** y **Mermaid**.
  Avisa nodos sueltos y posibles bucles.

### 4.6 Panel avanzado (Fase 4)
KPIs (VLANs, dispositivos, switches, enlaces, planos, % IPs en uso) y **6 gráficas**: dispositivos
por tipo y por edificio, IPs usadas/libres por VLAN, capacidad de VLANs, enlaces por tipo,
ocupación de puertos por switch.

### 4.7 Pruebas de conectividad (Fase 4)
Ping desde el servidor a cada dispositivo/switch con IP (individual o **"Probar todos"** en
secuencia). Guarda **en línea / caído / latencia / fecha** en el propio registro. Nota operativa:
un equipo que bloquea ICMP puede aparecer "caído" aunque esté encendido.

### 4.8 Migración de VLAN (Fase 4)
Elige VLAN origen → destino y muestra el **análisis de impacto**: cuántos dispositivos se moverían,
si el destino tiene IPs suficientes y la nueva subred. **Solo análisis** (no aplica cambios) por
seguridad en producción.

### 4.9 Buscador global y exportación (Fase 5)
Una sola caja para **IP, MAC, equipo, switch o VLAN** con resultados agrupados y enlace directo.
**Exportar Excel** (`.xlsx`) con hojas *Dispositivos, Switches, VLANs, IPs asignadas* (incluye
estado de conectividad). Endpoint JSON `/red/api/buscar/?q=` para integraciones.

## 5. Datos actualmente cargados (producción, 26-ago-2026)

| Entidad | Cantidad | Comentario |
|---|---|---|
| Campus / Edificios / Ubicaciones | 1 / 5 / 20 | Administración, Bilingüe, CFP, Colegio (+"Por confirmar") |
| **VLANs** | **13** | 15 AP-Relojes · 25 Sonido · 30 Teléfonos · 35 Routers · 40 Impresoras · 45 Equipos mixtos · 50 Cámaras · 60 Dirección-Coordinación · 61 Docentes BL · 62 Docentes Colegio · 65 Administrativos · 70 Televisores · 80 Invitados — **todas en estado "creada"** (aún no "producción") |
| **IPs generadas** | **3 289** | Todas **libres** todavía (sin asignaciones cargadas) |
| Dispositivos / Switches / Puertos | 6 / 7 / 4 | Backbone real: Meraki MX84, Cisco C1200, SF350 ×2, MikroTik, switches Datacenter |
| Enlaces | 0 | Pendiente documentar cableado lógico |
| **Planos** | **2** | Admin planta baja y planta alta |
| Marcadores / Líneas en planos | **73 / 84** | Puntos de red y cableado del edificio Admin |
| **Gabinetes** | **20** | **Datacenter · Rack 1** (internet/red general, 42U, 20 equipos frente/atrás) y **Rack 2** (cámaras/CCTV, 42U, 22 equipos) modelados desde fotos reales; Casa Azul y Aula 22 (12U); **16 gabinetes placeholder** (24U, "por ubicar") |
| Equipos en racks | 43 | |
| Registros de auditoría | 480 | |

## 6. Cómo se usa (flujo recomendado)
1. **Ubicaciones** → verificar edificios/ubicaciones y **renombrar/ubicar los 16 gabinetes** pendientes.
2. **VLANs** → confirmar rangos y pasar de "creada" a **"producción"** cuando estén validadas.
3. **Dispositivos** → cargar equipos con IP/MAC/VLAN (el sistema asigna la IP en el IPAM).
4. **Switches → Puertos** → documentar qué va en cada puerto; **Enlaces** entre switches.
5. **Planos** → colocar marcadores y cables por edificio; **Racks** → llenar cada gabinete.
6. **Pruebas de red** periódicas y **Panel avanzado** para capacidad; **Exportar Excel** para informes.

## 7. Pendientes y recomendaciones
- **Carga de datos:** los **16 gabinetes** están como placeholders (nombre, ubicación y tamaño real
  por confirmar: se estima 20–25U); **0 enlaces** y las 3 289 IPs aún sin asignar; solo 2 planos
  (faltan CFP, Colegio y Bilingüe, cuyas imágenes ya se identificaron).
- **Acceso:** hoy solo superadmin. Existe el grupo `red` y permisos para abrir a soporte/TI cuando
  Dirección lo autorice (recomendado: lectura para soporte, administración para el responsable).
- **Migración de VLAN** está en modo análisis; aplicar cambios reales requeriría una decisión
  explícita (y se haría equipo por equipo).
- **Ping** corre bajo demanda; si se quiere monitoreo continuo con alertas, sería un proceso
  programado (cron) — no se implementó para no cargar el servidor sin aprobación.
- **Dependencias:** el repo reporta vulnerabilidades en dependencias (Dependabot en GitHub); no
  son de este módulo pero conviene una revisión general.
- Export SVG/PDF de topología y API REST completa (DRF) quedaron como mejoras opcionales.

## 8. Rutas principales
`/red/` dashboard · `/red/panel/` · `/red/vlans/` · `/red/ubicaciones/` · `/red/dispositivos/` ·
`/red/switches/` · `/red/enlaces/` · `/red/planos/` · `/red/topologia/` · `/red/racks/` ·
`/red/gabinete/<id>/rack/` · `/red/pruebas/` · `/red/migracion/` · `/red/buscar/` ·
`/red/export/excel/` · `/red/auditoria/`.
