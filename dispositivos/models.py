from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

# ----------------------------
# Modelo Base con atributos comunes
# ----------------------------
class BaseModel(models.Model):
    STATES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    ]

    state = models.CharField(
        max_length=10, 
        choices=STATES, 
        default="ACTIVE",
        db_index=True,
        help_text="Estado del registro"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha de última actualización"
    )
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Fecha de borrado lógico"
    )

    class Meta:
        abstract = True  # no crea tabla, solo se hereda


# ----------------------------
#Usar modelo antiguo y cambiar nombres a ingles y agregar atributos nuevos como la organizacion 
# verbose name para debugear campos al ver la vista del admin en django 
# ----------------------------
class Category(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Nombre de la categoría"
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name
    
class Organization(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Nombre de la organización"
    )
    email = models.EmailField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Email de contacto de la organización"
    )

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.email})"


class Zone(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Nombre de la zona"
    )

    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"
        ordering = ['name']

    def __str__(self):
        return self.name


class Device(BaseModel):
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Nombre del dispositivo"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='devices',
        help_text="Categoría del dispositivo"
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.CASCADE,
        related_name='devices',
        help_text="Zona donde está ubicado el dispositivo"
    )
    max_usage = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        help_text="Consumo máximo en watts"
    )
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE,
        related_name='devices',
        help_text="Organización propietaria del dispositivo"
    )

    class Meta:
        verbose_name = "Device"
        verbose_name_plural = "Devices"
        ordering = ['name']
        unique_together = ['name', 'organization']

    def __str__(self):
        return f"{self.name} ({self.organization.name})"
    
class Measurement(BaseModel):
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE,
        related_name='measurements',
        help_text="Dispositivo que generó la medición"
    )
    date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Fecha y hora de la medición"
    )
    usage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10000.0)],
        help_text="Consumo en KWh"
    )

    class Meta:
        verbose_name = "Measurement"
        verbose_name_plural = "Measurements"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['device', '-date']),
            models.Index(fields=['-date']),
        ]

    def __str__(self):
        return f"{self.device.name} - {self.usage} KWh ({self.date.strftime('%Y-%m-%d %H:%M')})"
    
class Alert(BaseModel):
    LEVELS = [
        ("CRITICAL", "Critical"),
        ("HIGH", "High"),
        ("MEDIUM", "Medium"),
        ("LOW", "Low"),
    ]
    
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE,
        related_name='alerts',
        help_text="Dispositivo que generó la alerta"
    )
    message = models.CharField(
        max_length=200,
        help_text="Mensaje descriptivo de la alerta"
    )
    date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Fecha y hora de la alerta"
    )
    level = models.CharField(
        max_length=10, 
        choices=LEVELS, 
        default="MEDIUM",
        db_index=True,
        help_text="Nivel de criticidad de la alerta"
    )
    is_resolved = models.BooleanField(
        default=False,
        help_text="Indica si la alerta ha sido resuelta"
    )

    class Meta:
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['device', '-date']),
            models.Index(fields=['level', '-date']),
            models.Index(fields=['is_resolved', '-date']),
        ]

    def __str__(self):
        return f"{self.get_level_display()} - {self.device.name}: {self.message[:50]}..."


#para perfiles de usuario (operaodres y lectores)

class UserProfile(BaseModel):
    """Perfil de usuario para control de acceso por organización"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Usuario asociado al perfil"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Organización a la que pertenece el usuario"
    )
    role = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Administrador'),
            ('OPERATOR', 'Operador'),
            ('VIEWER', 'Solo Lectura'),
            ('MANAGER', 'Gerente'),
        ],
        default='VIEWER',
        help_text="Rol del usuario en el sistema"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Teléfono de contacto"
    )

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
        ordering = ['user__username']

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def has_organization_access(self, organization):
        """Verificar si el usuario tiene acceso a una organización específica"""
        if self.user.is_superuser:
            return True
        return self.organization == organization

    def can_edit_devices(self):
        """Verificar si el usuario puede editar dispositivos"""
        return self.role in ['ADMIN', 'OPERATOR', 'MANAGER']

    def can_view_all_organizations(self):
        """Verificar si el usuario puede ver todas las organizaciones"""
        return self.user.is_superuser or self.role == 'ADMIN'


