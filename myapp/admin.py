from django.contrib import admin
from .models import Piloto, Apuesta, Carrera, ResultadoQualy, Room, ResultadoCarrera

# Register your models here.
admin.site.register(Piloto)
admin.site.register(Apuesta)
admin.site.register(ResultadoQualy)
admin.site.register(ResultadoCarrera)

# 1️⃣ Creamos la acción
@admin.action(description="Finalizar carrera y calcular puntos")
def finalizar_carrera(modeladmin, request, queryset):
    for carrera in queryset:
        carrera.finalizar()  # Llama al método que definimos antes

# 2️⃣ Registramos el admin con la acción
@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "estado")
    actions = [finalizar_carrera]  # Aquí aparece el botón

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_by', 'get_members_count', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('code', 'created_at')
    filter_horizontal = ('members',)
    
    def get_members_count(self, obj):
        return obj.members.count()
    get_members_count.short_description = 'Miembros'


