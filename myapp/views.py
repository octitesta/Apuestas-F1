from django.contrib.auth import login
from django.contrib.auth.models import User
import json
from .models import Piloto, Apuesta, Carrera, ResultadoQualy, ResultadoCarrera, Room
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ApuestaForm
from django.db.models import Sum, Value, Q, FloatField
from django.db.models.functions import Coalesce
from django.contrib.auth.forms import UserCreationForm
import uuid
@login_required
def crear_apuesta(request):

    carrera_activa = Carrera.objects.filter(
        estado="qualy_cargada"
    ).first()

    # Obtener el código de sala del parámetro GET
    room_code = request.GET.get('room')

    apuesta_existente = None
    form = None

    if carrera_activa:
        apuesta_existente = Apuesta.objects.filter(
            usuario=request.user,
            carrera=carrera_activa
        ).first()

        if request.method == "POST":

            form = ApuestaForm(
                request.POST,
                instance=apuesta_existente
            )

            if form.is_valid():
                apuesta = form.save(commit=False)
                apuesta.usuario = request.user
                apuesta.carrera = carrera_activa
                apuesta.save()

                # Redirigir a la sala si se proporcionó el parámetro
                if room_code:
                    return redirect("home_sala", code=room_code)
                else:
                    # Si no hay sala, obtener la primera sala del usuario
                    salas = request.user.rooms.all() | request.user.created_rooms.all()
                    if salas.exists():
                        return redirect("home_sala", code=salas.first().code)
                    return redirect("home")

        else:
            form = ApuestaForm(instance=apuesta_existente)

    return render(request, "crear_apuesta.html", {
        "form": form,
        "carrera": carrera_activa,
        "apuesta_existente": apuesta_existente,
        "room_code": room_code
    })


@login_required
def home(request):
    """Dashboard principal - Muestra todas las salas del usuario"""
    salas_creadas = request.user.created_rooms.all()
    salas_miembro = request.user.rooms.all()
    todas_las_salas = (salas_creadas | salas_miembro).distinct()
    
    # Si el usuario solo tiene una sala, redirigir directamente a ella
    if todas_las_salas.count() == 1:
        return redirect('home_sala', code=todas_las_salas.first().code)
    
    context = {
        'salas_creadas': salas_creadas,
        'salas_miembro': salas_miembro,
        'todas_las_salas': todas_las_salas
    }
    return render(request, 'dashboard_salas.html', context)


@login_required
def ver_salas(request):
    """Vista para ver todas las salas (sin redirecciones)"""
    salas_creadas = request.user.created_rooms.all()
    salas_miembro = request.user.rooms.all()
    todas_las_salas = (salas_creadas | salas_miembro).distinct()
    
    context = {
        'salas_creadas': salas_creadas,
        'salas_miembro': salas_miembro,
        'todas_las_salas': todas_las_salas
    }
    return render(request, 'dashboard_salas.html', context)


@login_required
def home_sala(request, code):
    """Home dentro de una sala específica"""
    room = get_object_or_404(Room, code=code)
    
    # Verificar que el usuario sea miembro de la sala
    if request.user not in room.members.all() and request.user != room.created_by:
        messages.error(request, 'No tienes acceso a esta sala')
        return redirect('home')
    
    carrera_activa = Carrera.objects.filter(estado="qualy_cargada").first()

    carrera_en_curso = Carrera.objects.filter(estado="en_curso").first()

    proxima = Carrera.objects.filter(estado="pendiente").order_by("date").first()

    apuesta_usuario = None
    apuestas = []  # Inicializar como lista vacía en lugar de None
    resultados_qualy = []

    if request.user.is_authenticated and carrera_activa:
        apuesta_usuario = Apuesta.objects.filter(
            usuario=request.user,
            carrera=carrera_activa
        ).first()

    # Obtener apuestas para mostrar quién apostó (SOLO DE LA SALA)
    # En carrera activa: solo mostrar usuarios (sin piloto)
    # En carrera en curso: mostrar usuarios con piloto
    if carrera_en_curso:
        apuestas = list(Apuesta.objects.filter(
            carrera=carrera_en_curso,
            usuario__in=room.members.all()
        ).select_related("usuario", "piloto"))
    elif carrera_activa:
        apuestas = list(Apuesta.objects.filter(
            carrera=carrera_activa,
            usuario__in=room.members.all()
        ).select_related("usuario"))

    carrera_para_qualy = carrera_activa or carrera_en_curso
    if carrera_para_qualy:
        resultados_qualy = ResultadoQualy.objects.filter(carrera=carrera_para_qualy).order_by("posicion")

    # Countdown: mostrar la carrera activa (qualy_cargada) o la próxima pendiente
    # No mostrar countdown cuando hay carrera en curso
    if carrera_en_curso:
        carrera_countdown = None
    elif carrera_activa:
        carrera_countdown = carrera_activa
    else:
        carrera_countdown = proxima

    return render(request, "home2.html", {
        "room": room,
        "carrera_activa": carrera_activa,
        "carrera_en_curso": carrera_en_curso,
        "resultados_qualy": resultados_qualy,
        "proxima": proxima,
        "carrera_countdown": carrera_countdown,
        "apuesta_usuario": apuesta_usuario,
        "apuestas": apuestas
    })  


@login_required
def clasificacion_sala(request, code):
    """Clasificación dentro de una sala específica"""
    room = get_object_or_404(Room, code=code)
    
    # Verificar que el usuario sea miembro de la sala
    if request.user not in room.members.all() and request.user != room.created_by:
        messages.error(request, 'No tienes acceso a esta sala')
        return redirect('home')
    
    # Obtener solo usuarios de la sala
    usuarios = room.members.all().annotate(
        total_puntos=Coalesce(
            Sum(
                "apuesta__puntos",
                filter=Q(apuesta__carrera__estado="finalizada")
            ),
            Value(0, output_field=FloatField())
        )
    ).order_by("-total_puntos")

    # Contar carreras finalizadas
    carreras_finalizadas = Carrera.objects.filter(estado="finalizada").count()

    # Obtener todas las carreras ordenadas por fecha
    carreras = Carrera.objects.all().order_by("date")

    # Tabla de multiplicadores
    MULTIPLICADORES = {
        1: 1.0, 2: 1.10, 3: 1.28, 4: 1.44, 5: 1.63,
        6: 1.84, 7: 2.08, 8: 2.35, 9: 2.66, 10: 3.0,
        11: 5.20, 12: 7.40, 13: 9.60, 14: 11.80, 15: 14.0,
        16: 16.20, 17: 18.40, 18: 20.60, 19: 22.80, 20: 25.0,
        21: 26.0, 22: 27.0,
    }
    
    datos_por_carrera = []
    for carrera in carreras:
        puntos_carrera = {}
        # Solo obtener apuestas de usuarios de la sala
        apuestas = Apuesta.objects.filter(
            carrera=carrera,
            usuario__in=room.members.all()
        ).select_related('usuario', 'piloto')
        
        for apuesta in apuestas:
            try:
                qualy = ResultadoQualy.objects.get(carrera=carrera, piloto=apuesta.piloto)
                pos_qualy = qualy.posicion
            except ResultadoQualy.DoesNotExist:
                pos_qualy = None
            
            try:
                resultado = ResultadoCarrera.objects.get(carrera=carrera, piloto=apuesta.piloto)
                pos_carrera = resultado.posicion
            except ResultadoCarrera.DoesNotExist:
                pos_carrera = None
            
            multiplicador = MULTIPLICADORES.get(pos_qualy, 1.0) if pos_qualy else None
            
            puntos_carrera[apuesta.usuario.id] = {
                'puntos': apuesta.puntos if apuesta.puntos is not None else 0,
                'piloto': apuesta.piloto.name,
                'pos_qualy': pos_qualy,
                'pos_carrera': pos_carrera,
                'multiplicador': multiplicador
            }
        
        datos_por_carrera.append({
            'carrera': carrera,
            'puntos': puntos_carrera,
            'usuarios_ordenados': sorted(
                usuarios,
                key=lambda u: puntos_carrera.get(u.id, {}).get('puntos', -1),
                reverse=True
            )
        })

    # Preparar datos para el gráfico de progresión
    carreras_finalizadas_list = [d['carrera'] for d in datos_por_carrera if d['carrera'].estado in ["finalizada", "en_curso"]]
    
    progresion_grafico = []
    for usuario in usuarios:
        puntos_acumulados = []
        total = 0
        for dato in datos_por_carrera:
            if dato['carrera'].estado in ["finalizada", "en_curso"]:
                if usuario.id in dato['puntos']:
                    total += dato['puntos'][usuario.id]['puntos']
                puntos_acumulados.append(total)
        
        if puntos_acumulados:
            progresion_grafico.append({
                'usuario': usuario.username,
                'puntos': puntos_acumulados,
                'color': '#' + format(hash(usuario.username) & 0xFFFFFF, '06x')
            })

    etiquetas_grafico = [c.name[:15] for c in carreras_finalizadas_list]
    datos_json = json.dumps({
        'etiquetas': etiquetas_grafico,
        'series': progresion_grafico
    })

    return render(request, "clasificacion.html", {
        "usuarios": usuarios,
        "carreras_finalizadas": carreras_finalizadas,
        "carreras": carreras,
        "datos_por_carrera": datos_por_carrera,
        "datos_json": datos_json,
        "room": room
    })


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Loguea automÃ¡ticamente
            return redirect("home")
    else:
        form = UserCreationForm()

    # Agregar clases Bootstrap dinÃ¡micamente
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control"
        field.help_text = None

    return render(request, "registration/register.html", {
        "form": form
    })

@login_required
def crear_sala(request):
    """Vista para crear una nueva sala"""
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if not name:
            messages.error(request, 'El nombre de la sala es obligatorio')
            return redirect('crear_sala')
        
        # Generar código único
        code = str(uuid.uuid4())[:8].upper()
        
        # Crear la sala
        room = Room.objects.create(
            name=name,
            code=code,
            created_by=request.user
        )
        
        # Agregar al creador como miembro
        room.add_member(request.user)
        
        messages.success(request, f'Sala "{name}" creada con código: {code}')
        return redirect('home_sala', code=room.code)
    
    return render(request, 'crear_sala.html')


@login_required
def unirse_sala(request):
    """Vista para unirse a una sala existente"""
    if request.method == 'POST':
        code = request.POST.get('code').upper().strip()
        
        try:
            room = Room.objects.get(code=code, is_active=True)
            
            # Verificar si ya es miembro
            if request.user in room.members.all():
                messages.warning(request, 'Ya eres miembro de esta sala')
                return redirect('home_sala', code=room.code)
            
            # Agregar a la sala
            room.add_member(request.user)
            messages.success(request, f'Te has unido a "{room.name}"')
            return redirect('home_sala', code=room.code)
        
        except Room.DoesNotExist:
            messages.error(request, 'Código de sala no válido o sala inactiva')
            return redirect('unirse_sala')
    
    # Si el usuario ya está en salas, mostrarlas
    mis_salas = request.user.rooms.all()
    context = {'mis_salas': mis_salas}
    return render(request, 'unirse_sala.html', context)


@login_required
def sala_detalle(request, code):
    """Vista detallada de una sala con clasificación"""
    room = get_object_or_404(Room, code=code)
    
    # Verificar que el usuario sea miembro
    if request.user not in room.members.all() and request.user != room.created_by:
        messages.error(request, 'No tienes acceso a esta sala')
        return redirect('home')
    
    usuarios = room.members.all().annotate(
        total_puntos=Coalesce(
            Sum(
                "apuesta__puntos",
                filter=Q(apuesta__carrera__estado="finalizada")
            ),
            Value(0, output_field=FloatField())
        )
    ).order_by('-total_puntos')
    
    context = {
        'room': room,
        'usuarios': usuarios,
        'es_creador': room.created_by == request.user,
        'titulo_pagina': f'Clasificación - {room.name}'
    }
    return render(request, 'sala_detalle.html', context)


@login_required
def dejar_sala(request, code):
    """Vista para dejar una sala"""
    room = get_object_or_404(Room, code=code)
    
    if request.user == room.created_by:
        # Si eres el creador, eliminar la sala
        room_name = room.name
        room.delete()
        messages.success(request, f'La sala "{room_name}" ha sido eliminada')
    elif request.user in room.members.all():
        # Si eres miembro, solo salir de la sala
        room.remove_member(request.user)
        messages.success(request, f'Has dejado la sala "{room.name}"')
    
    return redirect('home')


@login_required
def mis_salas(request):
    """Vista para listar las salas del usuario"""
    salas_creadas = request.user.created_rooms.all()
    salas_miembro = request.user.rooms.all()
    
    context = {
        'salas_creadas': salas_creadas,
        'salas_miembro': salas_miembro
    }
    return render(request, 'mis_salas.html', context)


@login_required
def simulador(request):
    """Simulador de puntos"""
    return render(request, 'simulador.html')
