# <--- hecho por claude code: ANA Network Manager — modelos Fase 1
# IPAM + documentación de infraestructura. Tablas red_* en MySQL sponsors2.
# La lógica dura (validar CIDR/rangos, capacidad, alertas) vive en services.py.
import ipaddress
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords

from core.models import AuditModel


# ═══════════════════════ Ubicaciones físicas ═══════════════════════
class Campus(AuditModel):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'red_campus'
        ordering = ['nombre']
        verbose_name = 'Campus'
        verbose_name_plural = 'Campus'
        permissions = [
            ('ver_red', 'Ver Red'),
            ('administrar_red', 'Administrar Red (VLAN/IP/dispositivos)'),
            ('registrar_dispositivos', 'Registrar dispositivos y puertos'),
            ('aprobar_migracion', 'Aprobar migraciones'),
            ('exportar_red', 'Exportar informes de red'),
        ]

    def __str__(self):
        return self.nombre


class Edificio(AuditModel):
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name='edificios')
    codigo = models.CharField(max_length=30, blank=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True)
    coord_x = models.FloatField(null=True, blank=True)   # posición opcional en el plano
    coord_y = models.FloatField(null=True, blank=True)
    color = models.CharField(max_length=7, default='#206bc4', verbose_name='Color (diagramas)')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'red_edificio'
        ordering = ['nombre']
        verbose_name = 'Edificio'
        verbose_name_plural = 'Edificios'

    def __str__(self):
        return self.nombre


class Ubicacion(AuditModel):
    TIPOS = (
        ('piso', 'Piso'), ('oficina', 'Oficina'), ('aula', 'Aula'),
        ('laboratorio', 'Laboratorio'), ('datacenter', 'Datacenter'),
        ('exterior', 'Exterior'), ('otro', 'Otro'),
    )
    edificio = models.ForeignKey(Edificio, null=True, blank=True, on_delete=models.PROTECT, related_name='ubicaciones')
    padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='hijas')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='otro')
    codigo = models.CharField(max_length=30, blank=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True)
    responsable = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'red_ubicacion'
        ordering = ['nombre']
        verbose_name = 'Ubicación'
        verbose_name_plural = 'Ubicaciones'

    def __str__(self):
        return self.nombre


class Gabinete(AuditModel):
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='gabinetes')
    codigo = models.CharField(max_length=30, blank=True)
    nombre = models.CharField(max_length=120)
    unidades_rack = models.PositiveIntegerField(default=0, verbose_name='Unidades de rack (U)')
    ups = models.CharField(max_length=120, blank=True, verbose_name='UPS')
    observaciones = models.TextField(blank=True)
    fotografia = models.ImageField(upload_to='red/gabinetes/', null=True, blank=True)
    coord_x = models.FloatField(null=True, blank=True)
    coord_y = models.FloatField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'red_gabinete'
        ordering = ['nombre']
        verbose_name = 'Gabinete'
        verbose_name_plural = 'Gabinetes'

    def __str__(self):
        return self.nombre


# ═══════════════════════ VLAN ═══════════════════════
class VLAN(AuditModel):
    ESTADOS = (
        ('planificada', 'Planificada'), ('creada', 'Creada'), ('en_prueba', 'En prueba'),
        ('produccion', 'Producción'), ('suspendida', 'Suspendida'),
    )
    TIPOS_DHCP = (
        ('meraki', 'Meraki'), ('windows', 'Windows Server'),
        ('estatico', 'Estático'), ('ninguno', 'Ninguno'),
    )
    CAPACIDAD = (
        ('normal', 'Normal'), ('advertencia', 'Advertencia'),
        ('critico', 'Crítico'), ('agotado', 'Agotado'),
    )

    vlan_id = models.PositiveIntegerField(unique=True, verbose_name='VLAN ID')
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True)
    subred = models.CharField(max_length=32, verbose_name='Subred (CIDR)')       # ej. 192.168.60.0/24
    gateway = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    mascara = models.CharField(max_length=20, blank=True)
    servidor_dhcp = models.CharField(max_length=120, blank=True)
    tipo_dhcp = models.CharField(max_length=12, choices=TIPOS_DHCP, default='ninguno')
    dns_principal = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    dns_secundario = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)

    # <--- rangos configurables (se usan para capacidad, NO las 254 completas)
    ip_inicial_asignable = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    ip_final_asignable = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    ip_inicio_reservado = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    ip_fin_reservado = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    ip_inicio_dhcp = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    ip_fin_dhcp = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)

    limite_dispositivos = models.PositiveIntegerField(null=True, blank=True,
                                                      verbose_name='Límite de dispositivos')
    porcentaje_alerta = models.PositiveIntegerField(default=20,
                                                    verbose_name='% libre para alerta amarilla')
    cantidad_ip_disponibles = models.IntegerField(default=0, editable=False)   # cache, recalculado
    estado_capacidad = models.CharField(max_length=12, choices=CAPACIDAD, default='normal', editable=False)

    politica_meraki = models.CharField(max_length=120, blank=True)
    color = models.CharField(max_length=7, default='#206bc4')
    estado = models.CharField(max_length=12, choices=ESTADOS, default='planificada')
    permite_internet = models.BooleanField(default=True)
    permite_comunicacion_interna = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_vlan'
        ordering = ['vlan_id']
        verbose_name = 'VLAN'
        verbose_name_plural = 'VLANs'

    def __str__(self):
        return f'VLAN {self.vlan_id} · {self.nombre}'

    # ── Helpers de red (cálculo real en services, aquí utilidades ligeras) ──
    @property
    def red(self):
        try:
            return ipaddress.ip_network(self.subred, strict=False)
        except ValueError:
            return None

    @property
    def broadcast(self):
        r = self.red
        return str(r.broadcast_address) if r else ''

    @property
    def direccion_red(self):
        r = self.red
        return str(r.network_address) if r else ''


# ═══════════════════════ Dispositivos ═══════════════════════
class Device(AuditModel):
    TIPOS = (
        ('servidor', 'Servidor'), ('computadora', 'Computadora'), ('laptop', 'Laptop'),
        ('telefono_ip', 'Teléfono IP'), ('impresora', 'Impresora'), ('televisor', 'Televisor'),
        ('camara', 'Cámara'), ('nvr', 'NVR'), ('router', 'Router'), ('access_point', 'Access Point'),
        ('mikrotik', 'MikroTik'), ('switch_adm', 'Switch administrable'),
        ('switch_noadm', 'Switch no administrable'), ('reloj', 'Reloj ZKTeco'), ('ups', 'UPS'),
        ('pbx', 'PBX'), ('sonido', 'Equipo de sonido'), ('campana', 'Campana'),
        ('fibra_conv', 'Convertidor de fibra'), ('planta_solar', 'Planta solar'), ('otro', 'Otro'),
    )
    ESTADOS = (
        ('activo', 'Activo'), ('desconectado', 'Desconectado'), ('mantenimiento', 'Mantenimiento'),
        ('retirado', 'Retirado'), ('por_confirmar', 'Por confirmar'),
    )
    CRITICIDAD = (('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('critica', 'Crítica'))

    codigo_interno = models.CharField(max_length=40, blank=True)
    nombre = models.CharField(max_length=120)
    hostname = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='otro')
    fabricante = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    numero_serie = models.CharField(max_length=80, blank=True)
    mac_principal = models.CharField(max_length=20, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, null=True, blank=True, on_delete=models.SET_NULL, related_name='dispositivos')
    gabinete = models.ForeignKey(Gabinete, null=True, blank=True, on_delete=models.SET_NULL, related_name='dispositivos')
    vlan = models.ForeignKey(VLAN, null=True, blank=True, on_delete=models.SET_NULL, related_name='dispositivos')
    ip = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    metodo_direccionamiento = models.CharField(max_length=20, blank=True)
    sistema_operativo = models.CharField(max_length=80, blank=True)
    responsable = models.CharField(max_length=120, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='por_confirmar')
    criticidad = models.CharField(max_length=10, choices=CRITICIDAD, default='media')
    fecha_compra = models.DateField(null=True, blank=True)
    garantia = models.CharField(max_length=120, blank=True)
    fotografia = models.ImageField(upload_to='red/dispositivos/', null=True, blank=True)
    observaciones = models.TextField(blank=True)

    # <--- hecho por claude code: posición del nodo en el editor de topología (Cytoscape)
    topo_x = models.FloatField(null=True, blank=True, editable=False)
    topo_y = models.FloatField(null=True, blank=True, editable=False)
    # <--- hecho por claude code: Fase 4 — pruebas de conectividad
    CONECT = (('ok', 'En línea'), ('caido', 'Caído'), ('desconocido', 'Sin probar'))
    conectividad = models.CharField(max_length=12, choices=CONECT, default='desconocido', editable=False)
    latencia_ms = models.FloatField(null=True, blank=True, editable=False)
    probado_en = models.DateTimeField(null=True, blank=True, editable=False)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_dispositivo'
        ordering = ['nombre']
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'

    def __str__(self):
        return self.nombre or self.hostname or f'Dispositivo #{self.pk}'


class NetworkInterface(AuditModel):
    TIPOS = (('ethernet', 'Ethernet'), ('wifi', 'Wi-Fi'), ('fibra', 'Fibra'), ('virtual', 'Virtual'))
    dispositivo = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='interfaces')
    nombre = models.CharField(max_length=60, blank=True)
    tipo = models.CharField(max_length=12, choices=TIPOS, default='ethernet')
    mac = models.CharField(max_length=20, blank=True)
    vlan = models.ForeignKey(VLAN, null=True, blank=True, on_delete=models.SET_NULL, related_name='interfaces')
    ip = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    dhcp = models.BooleanField(default=False, verbose_name='DHCP (si no, estática)')
    velocidad = models.CharField(max_length=30, blank=True)
    activa = models.BooleanField(default=True)
    observaciones = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_interfaz'
        ordering = ['dispositivo', 'nombre']
        verbose_name = 'Interfaz de red'
        verbose_name_plural = 'Interfaces de red'

    def __str__(self):
        return f'{self.dispositivo} · {self.nombre or self.tipo}'


# ═══════════════════════ IPAM ═══════════════════════
class IPAddress(AuditModel):
    ESTADOS = (
        ('libre', 'Libre'), ('reservada', 'Reservada'), ('asignada', 'Asignada'),
        ('dhcp', 'DHCP'), ('conflicto', 'Conflicto'), ('pendiente', 'Pendiente'), ('no_utilizable', 'No utilizable'),
    )
    TIPOS = (('estatica', 'Estática'), ('reserva_dhcp', 'Reserva DHCP'), ('dinamica', 'Dinámica'))

    vlan = models.ForeignKey(VLAN, on_delete=models.CASCADE, related_name='ips')
    direccion = models.GenericIPAddressField(protocol='IPv4')
    direccion_int = models.BigIntegerField(editable=False, db_index=True)   # para orden/rango/duplicados
    estado = models.CharField(max_length=15, choices=ESTADOS, default='libre', db_index=True)
    tipo = models.CharField(max_length=15, choices=TIPOS, blank=True)
    dispositivo = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name='ips')
    interfaz = models.ForeignKey(NetworkInterface, null=True, blank=True, on_delete=models.SET_NULL, related_name='ips')
    mac = models.CharField(max_length=20, blank=True)
    hostname = models.CharField(max_length=120, blank=True)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_liberacion = models.DateTimeField(null=True, blank=True)
    responsable = models.CharField(max_length=120, blank=True)
    observaciones = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_ip'
        ordering = ['vlan', 'direccion_int']
        verbose_name = 'Dirección IP'
        verbose_name_plural = 'Direcciones IP'
        unique_together = ('vlan', 'direccion')
        indexes = [models.Index(fields=['vlan', 'direccion_int'])]

    def save(self, *args, **kwargs):
        try:
            self.direccion_int = int(ipaddress.ip_address(self.direccion))
        except (ValueError, TypeError):
            self.direccion_int = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.direccion} ({self.get_estado_display()})'


# ═══════════════════════ Auditoría propia (IP del usuario + motivo) ═══════════════════════
class RedAuditLog(models.Model):
    """simple_history guarda el 'antes/después' por modelo; esto añade IP del usuario y MOTIVO."""
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_usuario = models.GenericIPAddressField(null=True, blank=True)
    modulo = models.CharField(max_length=40)
    registro = models.CharField(max_length=160)          # descripción del registro afectado
    accion = models.CharField(max_length=40)             # crear / editar / liberar / cambio_rango…
    valores_antes = models.JSONField(null=True, blank=True)
    valores_despues = models.JSONField(null=True, blank=True)
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'red_auditoria'
        ordering = ['-fecha']
        verbose_name = 'Auditoría de Red'
        verbose_name_plural = 'Auditoría de Red'

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} · {self.modulo} · {self.accion}'


# ═══════════════════════ FASE 2 · Switches, Puertos, Enlaces ═══════════════════════
class Switch(AuditModel):
    ESTADOS = (('activo', 'Activo'), ('inactivo', 'Inactivo'), ('mantenimiento', 'Mantenimiento'),
               ('retirado', 'Retirado'), ('por_confirmar', 'Por confirmar'))
    device = models.OneToOneField(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name='switch')
    nombre = models.CharField(max_length=120)
    fabricante = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    ip_admin = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True, verbose_name='IP administrativa')
    mac_admin = models.CharField(max_length=20, blank=True, verbose_name='MAC administrativa')
    ubicacion = models.ForeignKey(Ubicacion, null=True, blank=True, on_delete=models.SET_NULL, related_name='switches')
    gabinete = models.ForeignKey(Gabinete, null=True, blank=True, on_delete=models.SET_NULL, related_name='switches')
    administrable = models.BooleanField(default=True)
    poe = models.BooleanField(default=False, verbose_name='PoE')
    cantidad_puertos = models.PositiveIntegerField(default=0)
    cantidad_puertos_sfp = models.PositiveIntegerField(default=0)
    firmware = models.CharField(max_length=60, blank=True)
    usuario_responsable = models.CharField(max_length=120, blank=True)
    url_admin = models.CharField(max_length=200, blank=True, verbose_name='URL de administración')
    estado = models.CharField(max_length=15, choices=ESTADOS, default='por_confirmar')
    fecha_ultimo_respaldo = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    # <--- hecho por claude code: Fase 4 — pruebas de conectividad
    CONECT = (('ok', 'En línea'), ('caido', 'Caído'), ('desconocido', 'Sin probar'))
    conectividad = models.CharField(max_length=12, choices=CONECT, default='desconocido', editable=False)
    latencia_ms = models.FloatField(null=True, blank=True, editable=False)
    probado_en = models.DateTimeField(null=True, blank=True, editable=False)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_switch'
        ordering = ['nombre']
        verbose_name = 'Switch'
        verbose_name_plural = 'Switches'

    def __str__(self):
        return self.nombre


class SwitchPort(AuditModel):
    TIPOS = (('rj45', 'RJ45'), ('sfp', 'SFP'), ('sfp_plus', 'SFP+'), ('consola', 'Consola'))
    ESTADO_FISICO = (('up', 'Up'), ('down', 'Down'), ('bloqueado', 'Bloqueado'), ('desconocido', 'Desconocido'))
    MODO_VLAN = (('access', 'Access'), ('trunk', 'Trunk'), ('general', 'General'),
                 ('customer', 'Customer'), ('sin_config', 'Sin configurar'))
    switch = models.ForeignKey(Switch, on_delete=models.CASCADE, related_name='puertos')
    numero = models.PositiveIntegerField()
    nombre = models.CharField(max_length=20, blank=True, verbose_name='Nombre (GE1, GE2…)')
    tipo = models.CharField(max_length=10, choices=TIPOS, default='rj45')
    velocidad = models.CharField(max_length=30, blank=True)
    poe_disponible = models.BooleanField(default=False)
    poe_habilitado = models.BooleanField(default=False)
    estado_fisico = models.CharField(max_length=12, choices=ESTADO_FISICO, default='desconocido')
    modo_vlan = models.CharField(max_length=12, choices=MODO_VLAN, default='sin_config')
    vlan_access = models.ForeignKey(VLAN, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    verbose_name='VLAN access / PVID')
    vlan_nativa = models.ForeignKey(VLAN, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    vlans_tagged = models.CharField(max_length=120, blank=True, verbose_name='VLAN tagged (ej. 30,45)')
    dispositivo_conectado = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL,
                                              related_name='puertos_conectados')
    puerto_remoto = models.CharField(max_length=40, blank=True)
    descripcion = models.CharField(max_length=200, blank=True)
    ubicacion_destino = models.CharField(max_length=120, blank=True)
    cable_identificado = models.BooleanField(default=False)
    etiqueta_fisica = models.CharField(max_length=60, blank=True)
    fecha_ultima_validacion = models.DateField(null=True, blank=True)
    validado_por = models.CharField(max_length=120, blank=True)
    observaciones = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_switch_port'
        ordering = ['switch', 'numero']
        unique_together = ('switch', 'numero')
        verbose_name = 'Puerto de switch'
        verbose_name_plural = 'Puertos de switch'

    def __str__(self):
        return f'{self.switch.nombre} · {self.nombre or self.numero}'

    @property
    def tagged_list(self):
        return [x.strip() for x in (self.vlans_tagged or '').split(',') if x.strip()]


class NetworkLink(AuditModel):
    TIPOS = (('rj45', 'RJ45'), ('fibra', 'Fibra'), ('radio', 'Radio'), ('virtual', 'Virtual'))
    MODOS = (('access', 'Access'), ('trunk', 'Trunk'), ('simple', 'Enlace simple'))
    ESTADOS = (('activo', 'Activo'), ('inactivo', 'Inactivo'), ('prueba', 'En prueba'), ('por_confirmar', 'Por confirmar'))
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=10, choices=TIPOS, default='rj45')
    dispositivo_origen = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='enlaces_origen')
    puerto_origen = models.ForeignKey(SwitchPort, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    dispositivo_destino = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='enlaces_destino')
    puerto_destino = models.ForeignKey(SwitchPort, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    modo = models.CharField(max_length=10, choices=MODOS, default='simple')
    vlan_nativa = models.ForeignKey(VLAN, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    vlans_permitidas = models.CharField(max_length=120, blank=True)
    velocidad = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='por_confirmar')
    es_respaldo = models.BooleanField(default=False, verbose_name='Es enlace de respaldo')
    longitud_m = models.FloatField(null=True, blank=True, verbose_name='Longitud aprox. (m)')
    etiqueta_cable = models.CharField(max_length=60, blank=True)
    fecha_validacion = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'red_enlace'
        ordering = ['nombre']
        verbose_name = 'Enlace de red'
        verbose_name_plural = 'Enlaces de red'

    def __str__(self):
        return self.nombre


# ═══════════════════════ FASE 3 · Mapa de campus (planos + marcadores) ═══════════════════════
class Plano(AuditModel):
    """Plano/imagen de un edificio o del campus. Puede haber varios."""
    nombre = models.CharField(max_length=120)
    edificio = models.ForeignKey(Edificio, null=True, blank=True, on_delete=models.SET_NULL, related_name='planos')
    imagen = models.ImageField(upload_to='red/planos/')
    descripcion = models.CharField(max_length=200, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'red_plano'
        ordering = ['orden', 'nombre']
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'

    def __str__(self):
        return self.nombre


class Marcador(AuditModel):
    """Punto colocado sobre un plano (coordenadas relativas 0-100 %). Puede enlazar a un
    gabinete, dispositivo o switch para abrirlo al hacer clic."""
    TIPOS = (('edificio', 'Edificio'), ('gabinete', 'Gabinete'), ('dispositivo', 'Dispositivo'),
             ('switch', 'Switch'), ('nota', 'Nota'))
    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, related_name='marcadores')
    etiqueta = models.CharField(max_length=80)
    tipo = models.CharField(max_length=12, choices=TIPOS, default='nota')
    x = models.FloatField(default=50)   # % horizontal sobre la imagen
    y = models.FloatField(default=50)   # % vertical
    color = models.CharField(max_length=7, default='#206bc4')
    # <--- hecho por claude code: figuras de RED (no geométricas); el ícono lo pinta plano_map.js
    FORMAS = (('pin', 'Marcador'), ('router', 'Router'), ('switch', 'Switch'),
              ('servidor', 'Servidor'), ('ap', 'Access Point'), ('firewall', 'Firewall'),
              ('camara', 'Cámara'), ('pc', 'Computadora'), ('impresora', 'Impresora'),
              ('gabinete', 'Gabinete/Rack'), ('nube', 'Internet/Nube'), ('telefono', 'Teléfono IP'),
              ('reloj', 'Reloj marcador'), ('acceso', 'Reloj de acceso'))
    forma = models.CharField(max_length=12, choices=FORMAS, default='pin')
    # <--- hecho por claude code: tamaño del badge en px y rotación del ícono en grados
    tamano = models.PositiveSmallIntegerField(default=30)
    rotacion = models.PositiveSmallIntegerField(default=0)
    gabinete = models.ForeignKey(Gabinete, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    dispositivo = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    switch = models.ForeignKey(Switch, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    observaciones = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'red_marcador'
        ordering = ['plano', 'id']
        verbose_name = 'Marcador de plano'
        verbose_name_plural = 'Marcadores de plano'

    def __str__(self):
        return f'{self.etiqueta} @ {self.plano}'


class LineaPlano(AuditModel):
    """<--- hecho por claude code: línea/cable dibujado sobre un plano que une dos
    marcadores. Se mueve con ellos y también alimenta la vista de topología."""
    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, related_name='lineas')
    origen = models.ForeignKey(Marcador, on_delete=models.CASCADE, related_name='lineas_origen')
    destino = models.ForeignKey(Marcador, on_delete=models.CASCADE, related_name='lineas_destino')
    etiqueta = models.CharField(max_length=80, blank=True)
    color = models.CharField(max_length=7, default='#495057')
    # <--- hecho por claude code: trazado — recta o quebrada en ángulos rectos (ortogonal),
    # con un punto de referencia (codo) mx/my en % del plano
    ESTILOS = (('recta', 'Recta'), ('orto', 'Ortogonal'))
    estilo = models.CharField(max_length=6, choices=ESTILOS, default='recta')
    mx = models.FloatField(null=True, blank=True)
    my = models.FloatField(null=True, blank=True)
    # <--- hecho por claude code: Parte 2 — la línea puede apuntar a un equipo concreto del rack
    equipo_origen = models.ForeignKey('RackItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    equipo_destino = models.ForeignKey('RackItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'red_linea_plano'
        ordering = ['plano', 'id']
        verbose_name = 'Línea de plano'
        verbose_name_plural = 'Líneas de plano'

    def __str__(self):
        return f'{self.origen_id}→{self.destino_id} @ {self.plano_id}'


class RackItem(AuditModel):
    """<--- hecho por claude code: equipo montado en un gabinete/rack (elevación tipo draw.io).
    Cada ítem ocupa un rango de unidades (U) y puede enlazar a un Device o Switch del inventario."""
    TIPOS = (('switch', 'Switch'), ('patch', 'Patch panel'), ('servidor', 'Servidor'),
             ('firewall', 'Firewall'), ('router', 'Router'), ('nvr', 'NVR (grabador)'),
             ('mediaconv', 'Media converter'), ('bandeja', 'Bandeja'), ('pdu', 'PDU / Regleta'),
             ('organizador', 'Organizador'), ('kvm', 'KVM / Consola'), ('ups', 'UPS'),
             ('blank', 'Espacio libre'), ('otro', 'Otro'))
    # <--- hecho por claude code: cara del gabinete (frente/atrás); numeración U estándar (1=abajo)
    CARAS = (('frente', 'Frente'), ('atras', 'Atrás'))
    gabinete = models.ForeignKey(Gabinete, on_delete=models.CASCADE, related_name='rack_items')
    nombre = models.CharField(max_length=80)
    tipo = models.CharField(max_length=12, choices=TIPOS, default='switch')
    cara = models.CharField(max_length=6, choices=CARAS, default='frente')
    u_pos = models.PositiveSmallIntegerField(default=1)    # U inferior del equipo (1 = abajo)
    u_alto = models.PositiveSmallIntegerField(default=1)   # altura en unidades
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    switch = models.ForeignKey(Switch, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    color = models.CharField(max_length=7, default='#495057')
    observaciones = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'red_rack_item'
        ordering = ['gabinete', 'u_pos']
        verbose_name = 'Ítem de rack'
        verbose_name_plural = 'Ítems de rack'

    def __str__(self):
        return f'{self.nombre} (U{self.u_pos}) @ {self.gabinete_id}'
