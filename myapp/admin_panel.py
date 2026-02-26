from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Carrera, Piloto, ResultadoQualy, ResultadoCarrera


def staff_required(view_func):
    """Decorator que verifica que el usuario sea staff"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@login_required
@staff_required
def admin_panel(request):
    """Panel principal: lista de carreras ordenadas por fecha"""
    carreras = Carrera.objects.all().order_by('date')
    pilotos = Piloto.objects.all().order_by('name')

    # Para cada carrera, cargar las posiciones existentes de qualy y carrera
    carreras_data = []
    for carrera in carreras:
        qualy_results = {}
        carrera_results = {}

        for rq in ResultadoQualy.objects.filter(carrera=carrera):
            qualy_results[rq.piloto_id] = rq.posicion

        for rc in ResultadoCarrera.objects.filter(carrera=carrera):
            carrera_results[rc.piloto_id] = rc.posicion

        carreras_data.append({
            'carrera': carrera,
            'qualy_results': qualy_results,
            'carrera_results': carrera_results,
        })

    return render(request, 'admin_panel.html', {
        'carreras_data': carreras_data,
        'pilotos': pilotos,
        'positions': range(1, 23),
    })


@login_required
@staff_required
def admin_cargar_qualy(request, carrera_id):
    """Cargar resultados de clasificación y pasar a estado qualy_cargada"""
    carrera = get_object_or_404(Carrera, id=carrera_id)

    if carrera.estado != 'pendiente':
        messages.error(request, 'Esta carrera no está en estado pendiente.')
        return redirect('admin_panel')

    if request.method == 'POST':
        pilotos = Piloto.objects.all()
        posiciones_usadas = []
        resultados = []

        for piloto in pilotos:
            pos = request.POST.get(f'posicion_{piloto.id}')
            if not pos:
                messages.error(request, f'Falta la posición para {piloto.name}.')
                return redirect('admin_panel')

            pos = int(pos)
            if pos in posiciones_usadas:
                messages.error(request, f'La posición {pos} está duplicada.')
                return redirect('admin_panel')

            posiciones_usadas.append(pos)
            resultados.append(ResultadoQualy(
                carrera=carrera,
                piloto=piloto,
                posicion=pos
            ))

        # Eliminar resultados anteriores si existían
        ResultadoQualy.objects.filter(carrera=carrera).delete()

        # Crear los nuevos resultados
        ResultadoQualy.objects.bulk_create(resultados)

        # Cambiar estado
        carrera.estado = 'qualy_cargada'
        carrera.save()

        messages.success(request, f'Clasificación cargada para {carrera.name}. Estado: Qualy Cargada.')

    return redirect('admin_panel')


@login_required
@staff_required
def admin_editar_qualy(request, carrera_id):
    """Editar resultados de clasificación sin cambiar el estado"""
    carrera = get_object_or_404(Carrera, id=carrera_id)

    if carrera.estado == 'pendiente':
        messages.error(request, 'Esta carrera aún no tiene qualy cargada.')
        return redirect('admin_panel')

    if request.method == 'POST':
        pilotos = Piloto.objects.all()
        posiciones_usadas = []
        resultados = []

        for piloto in pilotos:
            pos = request.POST.get(f'posicion_{piloto.id}')
            if not pos:
                messages.error(request, f'Falta la posición para {piloto.name}.')
                return redirect('admin_panel')

            pos = int(pos)
            if pos in posiciones_usadas:
                messages.error(request, f'La posición {pos} está duplicada.')
                return redirect('admin_panel')

            posiciones_usadas.append(pos)
            resultados.append(ResultadoQualy(
                carrera=carrera,
                piloto=piloto,
                posicion=pos
            ))

        ResultadoQualy.objects.filter(carrera=carrera).delete()
        ResultadoQualy.objects.bulk_create(resultados)

        # Si la carrera ya fue finalizada, recalcular puntos
        if carrera.estado == 'finalizada':
            for apuesta in carrera.apuesta_set.all():
                apuesta.calcular_puntos()
            messages.success(request, f'Qualy actualizada para {carrera.name}. Puntos recalculados.')
        else:
            messages.success(request, f'Qualy actualizada para {carrera.name}.')

    return redirect('admin_panel')


@login_required
@staff_required
def admin_marcar_en_curso(request, carrera_id):
    """Marcar carrera como en curso"""
    carrera = get_object_or_404(Carrera, id=carrera_id)

    if carrera.estado != 'qualy_cargada':
        messages.error(request, 'Esta carrera no está en estado Qualy Cargada.')
        return redirect('admin_panel')

    if request.method == 'POST':
        carrera.estado = 'en_curso'
        carrera.save()
        messages.success(request, f'{carrera.name} marcada como En Curso.')

    return redirect('admin_panel')


@login_required
@staff_required
def admin_finalizar_carrera(request, carrera_id):
    """Cargar resultados de carrera y finalizar"""
    carrera = get_object_or_404(Carrera, id=carrera_id)

    if carrera.estado != 'en_curso':
        messages.error(request, 'Esta carrera no está en curso.')
        return redirect('admin_panel')

    if request.method == 'POST':
        pilotos = Piloto.objects.all()
        posiciones_usadas = []
        resultados = []

        for piloto in pilotos:
            pos = request.POST.get(f'posicion_{piloto.id}')
            if not pos:
                messages.error(request, f'Falta la posición para {piloto.name}.')
                return redirect('admin_panel')

            pos = int(pos)
            if pos in posiciones_usadas:
                messages.error(request, f'La posición {pos} está duplicada.')
                return redirect('admin_panel')

            posiciones_usadas.append(pos)
            resultados.append(ResultadoCarrera(
                carrera=carrera,
                piloto=piloto,
                posicion=pos
            ))

        # Eliminar resultados anteriores si existían
        ResultadoCarrera.objects.filter(carrera=carrera).delete()

        # Crear los nuevos resultados
        ResultadoCarrera.objects.bulk_create(resultados)

        # Finalizar carrera (cambia estado y calcula puntos)
        carrera.finalizar()

        messages.success(request, f'{carrera.name} finalizada. Puntos calculados.')

    return redirect('admin_panel')


@login_required
@staff_required
def admin_editar_carrera(request, carrera_id):
    """Editar resultados finales de la carrera y recalcular puntos"""
    carrera = get_object_or_404(Carrera, id=carrera_id)

    if carrera.estado != 'finalizada':
        messages.error(request, 'Solo se pueden editar resultados de carreras finalizadas.')
        return redirect('admin_panel')

    if request.method == 'POST':
        pilotos = Piloto.objects.all()
        posiciones_usadas = []
        resultados = []

        for piloto in pilotos:
            pos = request.POST.get(f'posicion_{piloto.id}')
            if not pos:
                messages.error(request, f'Falta la posición para {piloto.name}.')
                return redirect('admin_panel')

            pos = int(pos)
            if pos in posiciones_usadas:
                messages.error(request, f'La posición {pos} está duplicada.')
                return redirect('admin_panel')

            posiciones_usadas.append(pos)
            resultados.append(ResultadoCarrera(
                carrera=carrera,
                piloto=piloto,
                posicion=pos
            ))

        ResultadoCarrera.objects.filter(carrera=carrera).delete()
        ResultadoCarrera.objects.bulk_create(resultados)

        # Recalcular todos los puntos
        for apuesta in carrera.apuesta_set.all():
            apuesta.calcular_puntos()

        messages.success(request, f'Resultados actualizados para {carrera.name}. Puntos recalculados.')

    return redirect('admin_panel')
