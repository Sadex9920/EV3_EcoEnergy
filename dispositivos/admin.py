from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

from .models import Category, Zone, Device, Organization, Measurement, Alert, UserProfile


class BaseModelAdmin(admin.ModelAdmin):
    """Clase base para todos los modelos con configuraciones comunes"""
    exclude = ("deleted_at",)
    readonly_fields = ("created_at", "updated_at")


class OrganizationFilteredAdmin(BaseModelAdmin):
    
    
    def get_queryset(self, request):
        """Filtrar por organización si el usuario no es superusuario"""
        qs = super().get_queryset(request)
        
        #aplicamos un if para los operadores o lectores ya que si es superusario puede ver todo 
        if not request.user.is_superuser:
            #verificar que el usuario exista en alguna organizacion
            if hasattr(request.user, 'profile') and request.user.profile.organization:
                user_org = request.user.profile.organization
                
                #si tenemos el campo organizacion, filtramos de una 
                if hasattr(self.model, 'organization'):
                    return qs.filter(organization=user_org)
                
                # si el atributo es deviceen el modelo fultramos por organizacion
                elif hasattr(self.model, 'device'):
                    return qs.filter(device__organization=user_org)
                
                # si el user no tiene oranizacion o esta mal logeado no mostrar nada 
                else:
                    return qs.none()
            else:
                # Si no tiene perfil o organización, no mostrar nada
                return qs.none()
        
        return qs


class MasterDataAdmin(BaseModelAdmin):
    """Clase base para tablas maestras (sin filtrado por organización)"""
    pass


# tablas maestras   

@admin.register(Category)
class CategoryAdmin(MasterDataAdmin):
    """Administración de Categorías - Tabla Maestra"""
    list_display = ('name', 'state', 'created_at', 'device_count')
    list_filter = ('state', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
    list_select_related = ()
    
    def device_count(self, obj):
        """Mostrar cantidad de dispositivos en esta categoría"""
        count = obj.devices.count()
        if count > 0:
            url = reverse('admin:dispositivos_device_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} dispositivos</a>', url, count)
        return '0 dispositivos'
    device_count.short_description = 'Dispositivos'


@admin.register(Zone)
class ZoneAdmin(MasterDataAdmin):
    """Administración de Zonas - Tabla Maestra"""
    list_display = ('name', 'state', 'created_at', 'device_count')
    list_filter = ('state', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
    list_select_related = ()
    
    def device_count(self, obj):
        """Mostrar cantidad de dispositivos en esta zona"""
        count = obj.devices.count()
        if count > 0:
            url = reverse('admin:dispositivos_device_changelist') + f'?zone__id__exact={obj.id}'
            return format_html('<a href="{}">{} dispositivos</a>', url, count)
        return '0 dispositivos'
    device_count.short_description = 'Dispositivos'


@admin.register(Organization)
class OrganizationAdmin(MasterDataAdmin):
    """Administración de Organizaciones - Tabla Maestra"""
    list_display = ('name', 'email', 'state', 'created_at', 'device_count')
    list_filter = ('state', 'created_at')
    search_fields = ('name', 'email')
    ordering = ('name',)
    list_select_related = ()
    
    def device_count(self, obj):
        """Mostrar cantidad de dispositivos de esta organización"""
        count = obj.devices.count()
        if count > 0:
            url = reverse('admin:dispositivos_device_changelist') + f'?organization__id__exact={obj.id}'
            return format_html('<a href="{}">{} dispositivos</a>', url, count)
        return '0 dispositivos'
    device_count.short_description = 'Dispositivos'


#tablas operativas 

class MeasurementInline(admin.TabularInline):
    """Inline para mostrar mediciones en el dispositivo"""
    model = Measurement
    extra = 0
    readonly_fields = ('date',)
    fields = ('date', 'usage', 'state')
    ordering = ('-date',)
    
    def get_queryset(self, request):
        """Limitar a las últimas 5 mediciones"""
        qs = super().get_queryset(request)
        return qs[:5]


class AlertInline(admin.TabularInline):
    """Inline para mostrar alertas en el dispositivo"""
    model = Alert
    extra = 0
    readonly_fields = ('date',)
    fields = ('date', 'level', 'message', 'is_resolved', 'state')
    ordering = ('-date',)
    
    def get_queryset(self, request):
        """Limitar a las últimas 3 alertas"""
        qs = super().get_queryset(request)
        return qs[:3]


class MeasurementFormSet(BaseInlineFormSet):
    """FormSet personalizado para validaciones de mediciones"""
    
    def clean(self):
        """Validar que las mediciones sean consistentes"""
        if any(self.errors):
            return
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                usage = form.cleaned_data.get('usage', 0)
                if usage < 0:
                    raise ValidationError('El consumo no puede ser negativo')
                if usage > 10000:
                    raise ValidationError('El consumo no puede exceder 10,000 KWh')


@admin.register(Device)
class DeviceAdmin(OrganizationFilteredAdmin):
    """Administración de Dispositivos - Tabla Operativa"""
    list_display = ('name', 'organization', 'category', 'zone', 'max_usage', 'state', 'created_at')
    list_filter = ('state', 'category', 'zone', 'organization', 'created_at')
    search_fields = ('name', 'organization__name', 'category__name', 'zone__name')
    ordering = ('name',)
    list_select_related = ('organization', 'category', 'zone')
    
    #inlines
    inlines = [MeasurementInline, AlertInline]
    
    # Campos para el formulario
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'organization', 'category', 'zone')
        }),
        ('Configuración', {
            'fields': ('max_usage', 'state')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Acción personalizada
    actions = ['mark_as_active', 'mark_as_inactive', 'generate_usage_report']
    
    def mark_as_active(self, request, queryset):
        """Marcar dispositivos como activos"""
        updated = queryset.update(state='ACTIVE')
        self.message_user(request, f'{updated} dispositivos marcados como activos.')
    mark_as_active.short_description = "Marcar como activos"
    
    def mark_as_inactive(self, request, queryset):
        """Marcar dispositivos como inactivos"""
        updated = queryset.update(state='INACTIVE')
        self.message_user(request, f'{updated} dispositivos marcados como inactivos.')
    mark_as_inactive.short_description = "Marcar como inactivos"
    
    def generate_usage_report(self, request, queryset):
        """Generar reporte de uso para dispositivos seleccionados"""
        if queryset.count() > 10:
            self.message_user(request, 'Solo se pueden generar reportes para máximo 10 dispositivos.', level=messages.WARNING)
            return
        
        # Aquí se implementaría la lógica del reporte
        self.message_user(request, f'Reporte generado para {queryset.count()} dispositivos.')
    generate_usage_report.short_description = "Generar reporte de uso"
    
@admin.register(Measurement)
class MeasurementAdmin(OrganizationFilteredAdmin):
    """Administración de Mediciones - Tabla Operativa"""
    list_display = ('device', 'usage', 'date', 'state', 'created_at')
    list_filter = ('state', 'date', 'device__organization', 'device__category', 'created_at')
    search_fields = ('device__name', 'device__organization__name')
    ordering = ('-date',)
    list_select_related = ('device', 'device__organization', 'device__category')
    
    # Campos para el formulario
    fieldsets = (
        ('Medición', {
            'fields': ('device', 'usage', 'date')
        }),
        ('Estado', {
            'fields': ('state',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Acción personalizada
    actions = ['export_measurements']
    
    def export_measurements(self, request, queryset):
        """Exportar mediciones seleccionadas"""
        count = queryset.count()
        self.message_user(request, f'Exportando {count} mediciones...')
        # Aquí se implementaría la lógica de exportación
    export_measurements.short_description = "Exportar mediciones"
    
@admin.register(Alert)
class AlertAdmin(OrganizationFilteredAdmin):
    """Administración de Alertas - Tabla Operativa"""
    list_display = ('device', 'level', 'message_short', 'is_resolved', 'date', 'state')
    list_filter = ('level', 'is_resolved', 'state', 'date', 'device__organization', 'created_at')
    search_fields = ('message', 'device__name', 'device__organization__name')
    ordering = ('-date',)
    list_select_related = ('device', 'device__organization')
    
    #campos para el formulario nuevo 
    fieldsets = (
        ('Alerta', {
            'fields': ('device', 'level', 'message', 'is_resolved')
        }),
        ('Estado', {
            'fields': ('state',)
        }),
        ('Metadatos', {
            'fields': ('date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    #Acciones custom
    actions = ['mark_as_resolved', 'mark_as_unresolved']
    
    def message_short(self, obj):
        """Mostrar mensaje truncado"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_short.short_description = 'Mensaje'
    
    def mark_as_resolved(self, request, queryset):
        """Marcar alertas como resueltas"""
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f'{updated} alertas marcadas como resueltas.')
    mark_as_resolved.short_description = "Marcar como resueltas"
    
    def mark_as_unresolved(self, request, queryset):
        """Marcar alertas como no resueltas"""
        updated = queryset.update(is_resolved=False)
        self.message_user(request, f'{updated} alertas marcadas como no resueltas.')
    mark_as_unresolved.short_description = "Marcar como no resueltas"
    
#config de admin
@admin.register(UserProfile)
class UserProfileAdmin(BaseModelAdmin):
    """Administración de Perfiles de Usuario"""
    list_display = ('user', 'organization', 'role', 'phone', 'state', 'created_at')
    list_filter = ('role', 'organization', 'state', 'created_at')
    search_fields = ('user__username', 'user__email', 'organization__name', 'phone')
    ordering = ('user__username',)
    list_select_related = ('user', 'organization')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'organization', 'role')
        }),
        ('Contacto', {
            'fields': ('phone',)
        }),
        ('Estado', {
            'fields': ('state',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# Personalizar el título del admin
admin.site.site_header = "EcoEnergy Evaluacion 2"
admin.site.site_title = "Monitoreo Admin"
admin.site.index_title = "Panel de Administración"

