from django.urls import path   
from . import views 
from .admin_panel import admin_panel, admin_cargar_qualy, admin_marcar_en_curso, admin_finalizar_carrera, admin_editar_qualy, admin_editar_carrera
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name="home"),
    path("salas/", views.ver_salas, name="ver_salas"),
    path("apostar/", views.crear_apuesta, name="apostar"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("register/", views.register, name="register"),
    path('sala/crear/', views.crear_sala, name='crear_sala'),
    path('sala/unirse/', views.unirse_sala, name='unirse_sala'),
    path('mis-salas/', views.mis_salas, name='mis_salas'),
    path('sala/<str:code>/detalle/', views.sala_detalle, name='sala_detalle'),
    path('sala/<str:code>/clasificacion/', views.clasificacion_sala, name='clasificacion_sala'),
    path('sala/<str:code>/dejar/', views.dejar_sala, name='dejar_sala'),
    path('simulador/', views.simulador, name='simulador'),
    path('sala/<str:code>/', views.home_sala, name='home_sala'),
    # Admin Panel
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('admin-panel/carrera/<int:carrera_id>/cargar-qualy/', admin_cargar_qualy, name='admin_cargar_qualy'),
    path('admin-panel/carrera/<int:carrera_id>/editar-qualy/', admin_editar_qualy, name='admin_editar_qualy'),
    path('admin-panel/carrera/<int:carrera_id>/en-curso/', admin_marcar_en_curso, name='admin_marcar_en_curso'),
    path('admin-panel/carrera/<int:carrera_id>/finalizar/', admin_finalizar_carrera, name='admin_finalizar_carrera'),
    path('admin-panel/carrera/<int:carrera_id>/editar-carrera/', admin_editar_carrera, name='admin_editar_carrera'),
]
