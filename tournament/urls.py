from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),  # добавили эту строку
    path('profile/', views.profile, name='profile'),
    path('apply-host/', views.apply_host, name='apply_host'),
    path('tournament/create/', views.create_tournament, name='create_tournament'),
    path('tournament/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('my-tournaments/', views.my_tournaments, name='my_tournaments'),
    path('tournament/<int:tournament_id>/players/', views.get_players_for_tournament, name='tournament_players_api'),
    path('tournament/<int:tournament_id>/add/<int:player_id>/', views.add_player_to_tournament, name='add_player_to_tournament'),
    path('tournament/<int:tournament_id>/remove/<int:player_id>/', views.remove_player_from_tournament, name='remove_player_from_tournament'),
]