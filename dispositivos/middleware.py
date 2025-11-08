from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User

class OrganizationFilterMiddleware(MiddlewareMixin):
    """
    Middleware para asegurar que los usuarios solo vean datos de su organización
    """
    
    def process_request(self, request):
        """Procesar la request para agregar información de organización del usuario"""
        if request.user.is_authenticated and not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.organization:
                # Agregar la organización del usuario a la request para uso en templates
                request.user_organization = request.user.profile.organization
            else:
                request.user_organization = None
        else:
            request.user_organization = None
