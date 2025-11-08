from django.shortcuts import render, redirect
from django.db.models import Count
from .models import Device,Zone,Category,Measurement,Alert,Organization

def inicio(request):
    empresa = request.session.get("empresa")
    if not empresa:
        return redirect("iniciarSesion")
    devices = Device.objects.filter(organization__name=empresa)
    categoria_id = request.GET.get("categoria")
    if categoria_id:
        devices = devices.filter(category_id=categoria_id)
    zones = Zone.objects.filter(device__in=devices).annotate(num_devices=Count("device", distinct=True))
    categories = Category.objects.filter(device__in=devices).distinct().annotate(num_devices=Count("device", distinct=True))
    measurements = Measurement.objects.filter(device__in=devices)[:10]
    alerts = Alert.objects.filter(device__in=devices)
    alerts_mid = alerts.filter(level='MID').count()
    alerts_high = alerts.filter(level='HIGH').count()
    alerts_critical = alerts.filter(level='CRITICAL').count()
    

    return render(request, 'dispositivos/panel.html',{'devices':devices,'zones':zones,'categories':categories,'measurements':measurements,'alerts':alerts,'empresa':empresa,'alerts_mid':alerts_mid,'alerts_high':alerts_high,'alerts_critical':alerts_critical})

def devices_list(request):
    empresa = request.session.get("empresa")
    devices = Device.objects.filter(organization__name=empresa)
    categoria_id = request.GET.get("categoria")
    if categoria_id:
        devices = devices.filter(category_id=categoria_id)
    categories = Category.objects.filter(device__in=devices).distinct()
    return render(request, 'dispositivos/devices_list.html', {'devices': devices, 'empresa': empresa, 'categories': categories})

def alerts_list(request):
    empresa = request.session.get("empresa")
    devices = Device.objects.filter(organization__name=empresa)
    alerts = Alert.objects.filter(device__in=devices)
    return render(request, 'dispositivos/alerts_list.html', {'alerts': alerts, 'empresa': empresa})

def measurements_list(request):
    empresa = request.session.get("empresa")
    devices = Device.objects.filter(organization__name=empresa)
    measurements = Measurement.objects.filter(device__in=devices).order_by('-date')
    return render(request, 'dispositivos/measurements_list.html', {'measurements': measurements, 'empresa': empresa})
def device(request,device_id):
    empresa = request.session.get("empresa")
    device = Device.objects.get(id=device_id)
    measurements = Measurement.objects.filter(device=device).order_by('-date')
    alerts = Alert.objects.filter(device=device)
    zone = Zone.objects.get(id=device.zone.id)
    return render(request,"dispositivos/device.html",{"device":device,'empresa':empresa,"measurements":measurements,"alerts":alerts,"zone":zone.name})


def iniciarSesion(request): 
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            return render(request, "dispositivos/login.html", {"error": "Por favor ingrese el email de la empresa."})
        empresa = Organization.objects.filter(email=email).first()
        if not empresa:
            return render(request, "dispositivos/login.html", {"error": "Empresa no encontrada."})
        
        request.session['empresa'] = empresa.name
        return redirect("panel")
    
    return render(request, "dispositivos/login.html")

def register(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        empresa = request.POST.get("empresa")
        password = request.POST.get("password")
        mensaje = f"La empresa '{empresa}' se registro con el siguente correo {correo}."
        return render(request, "dispositivos/register_done.html", {"mensaje": mensaje})
    return render(request, "dispositivos/register.html")

def recoverPassword(request):
    if request.method == "POST":
        empresa = request.POST.get("empresa")
        mensaje = f"Si la empresa '{empresa}' Registro casi completado, revise su correo."
        return render(request, "dispositivos/recoverpassword_done.html", {"mensaje": mensaje})
    return render(request, "dispositivos/recoverpassword.html")
