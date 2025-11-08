
from django.contrib import admin
from django.urls import path
from dispositivos.views import inicio,device,iniciarSesion,recoverPassword,devices_list,alerts_list,measurements_list,register

urlpatterns = [
    path('admin/', admin.site.urls),
    path("",inicio,name="panel"),
    path("device/<int:device_id>/",device,name="device"),
    path("login/",iniciarSesion,name="iniciarSesion"),
    path("password-reset/",recoverPassword,name="recoverpassword"),
    path("devices/",devices_list,name="devices_list"),
    path("alerts/",alerts_list,name="alerts_list"),
    path("measurements/",measurements_list,name="measurements_list"),
    path("register/",register,name="register"),
]
