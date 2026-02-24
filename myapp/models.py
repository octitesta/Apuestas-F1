from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group

# Create your models here.
class Piloto(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Carrera(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateTimeField()
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("qualy_cargada", "Qualy cargada"),
        ("en_curso", "En curso"),
        ("finalizada", "Finalizada"),
    ]

    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    def finalizar(self):
        self.estado = "finalizada"
        self.save()

        # Calcular puntos de todas las apuestas de esta carrera
        for apuesta in self.apuesta_set.all():
            apuesta.calcular_puntos()

    def __str__(self):
        return self.name + " - " + self.date.strftime("%d/%m/%Y %H:%M")

class ResultadoQualy(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    piloto = models.ForeignKey(Piloto, on_delete=models.CASCADE)
    posicion = models.IntegerField()

    def __str__(self):
        return self.piloto.name + " - " + self.carrera.name + " - " + str(self.posicion)

class ResultadoCarrera(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    piloto = models.ForeignKey(Piloto, on_delete=models.CASCADE)
    posicion = models.IntegerField()

  

    def __str__(self):
        return self.piloto.name + " - " + self.carrera.name + " - " + str(self.posicion)

class Apuesta(models.Model):
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    piloto = models.ForeignKey(Piloto, on_delete=models.CASCADE)
    puntos = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("usuario", "carrera")

    def clean(self):
        if not self.carrera_id:
            return  # todavía no fue asignada
    
    def calcular_puntos(self):
        """
        Sistema de puntos con multiplicadores:
        - Multiplicador según posición de salida (qualy)
        - Puntos según posición de llegada (carrera)
        - Puntos finales = puntos_por_posicion * multiplicador
        """
        
        # Tabla de multiplicadores según posición de salida
        MULTIPLICADORES = {
            1: 1.0,
            2: 1.10,
            3: 1.28,
            4: 1.44,
            5: 1.63,
            6: 1.84,
            7: 2.08,
            8: 2.35,
            9: 2.66,
            10: 3.0,
            11: 5.20,
            12: 7.40,
            13: 9.60,
            14: 11.80,
            15: 14.0,
            16: 16.20,
            17: 18.40,
            18: 20.60,
            19: 22.80,
            20: 25.0,
            21: 26.0,
            22: 27.0,
        }
        
        # Tabla de puntos según posición de llegada
        PUNTOS_POR_POSICION = {
            1: 25,
            2: 18,
            3: 15,
            4: 12,
            5: 10,
            6: 8,
            7: 6,
            8: 4,
            9: 2,
            10: 1,
        }
        
        try:
            # Obtener posición de salida (qualifying)
            qualy = ResultadoQualy.objects.get(carrera=self.carrera, piloto=self.piloto)
            pos_salida = qualy.posicion
            
            # Obtener posición de llegada (carrera)
            resultado = ResultadoCarrera.objects.get(carrera=self.carrera, piloto=self.piloto)
            pos_llegada = resultado.posicion
            
            # Obtener multiplicador (si la posición no está en la tabla, multiplicador = 1)
            multiplicador = MULTIPLICADORES.get(pos_salida, 1.0)
            
            # Obtener puntos base (si termina fuera del top 10, puntos = 0)
            puntos_base = PUNTOS_POR_POSICION.get(pos_llegada, 0)
            
            # Calcular puntos finales
            self.puntos = puntos_base * multiplicador
            
        except (ResultadoQualy.DoesNotExist, ResultadoCarrera.DoesNotExist):
            self.puntos = 0
            
        self.save()

    def __str__(self):
            return f"{self.usuario}"

class Room(models.Model):
    """Modelo para las salas de competencia"""
    name = models.CharField(max_length=100,  verbose_name="Nombre de la sala")
    code = models.CharField(max_length=8, unique=True, verbose_name="Código de acceso")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    members = models.ManyToManyField(User, related_name='rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def save(self, *args, **kwargs):
        # Primera vez que se crea la sala
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            # Crear grupo automáticamente
            group, _ = Group.objects.get_or_create(name=f'room_{self.code}')
    
    def add_member(self, user):
        """Agregar usuario a la sala y al grupo"""
        self.members.add(user)
        group = Group.objects.get(name=f'room_{self.code}')
        user.groups.add(group)
    
    def remove_member(self, user):
        """Remover usuario de la sala y del grupo"""
        self.members.remove(user)
        group = Group.objects.get(name=f'room_{self.code}')
        user.groups.remove(group)


