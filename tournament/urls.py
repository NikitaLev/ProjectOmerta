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
    path('tournament/<int:tournament_id>/create-player/', views.create_player_for_tournament, name='create_player_for_tournament'),
    path('activate/<str:token>/', views.activate_account, name='activate_account'),
    path('delete-player/<int:player_id>/', views.delete_player, name='delete_player'),
    path('tournament/<int:tournament_id>/start/', views.start_tournament, name='start_tournament'),
    path('tournament/<int:tournament_id>/cancel/', views.cancel_tournament_start, name='cancel_tournament_start'),
    path('tournament/<int:tournament_id>/games/', views.tournament_games, name='tournament_games'),
    path('tournament/<int:tournament_id>/game/<int:game_round>/input/', views.game_input, name='game_input'),
    path('tournament/<int:tournament_id>/game/<int:game_round>/edit/', views.game_edit, name='game_edit'),
    path('tournament/<int:tournament_id>/game/<int:game_round>/view/', views.game_view, name='game_view'),
    path('tournament/<int:tournament_id>/public/', views.tournament_public, name='tournament_public'),
    path('tournament/<int:tournament_id>/public/stats/', views.tournament_public_stats, name='tournament_public_stats'),
    path('tournament/<int:tournament_id>/public/games/', views.tournament_public_games, name='tournament_public_games'),
    path('tournament/<int:tournament_id>/game/<int:game_round>/public-view/', views.public_game_view, name='public_game_view'),
    path('tournament/<int:tournament_id>/toggle-visibility/', views.toggle_data_visibility, name='toggle_data_visibility'),
]