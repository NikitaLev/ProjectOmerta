from django.urls import path
from . import views

from .views import rules_views

urlpatterns = [
    # Главная
    path('', views.home, name='home'),
    # Аутентификация
    path('register/', views.register, name='register'), 
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # Активация аккаунта
    path('activate/<str:token>/', views.activate_account, name='activate_account'),

    # Профиль
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/stats/', views.player_stats_api, name='player_stats_api'),

    # Заявка на ведущего
    path('apply-host/', views.apply_host, name='apply_host'),
    
    # Турниры
    path('tournament/create/', views.create_tournament, name='create_tournament'),
    path('tournament/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('my-tournaments/', views.my_tournaments, name='my_tournaments'),
    path('tournament/<int:tournament_id>/players/', views.get_players_for_tournament, name='tournament_players_api'),
    path('tournament/<int:tournament_id>/add/<int:player_id>/', views.add_player_to_tournament, name='add_player_to_tournament'),
    path('tournament/<int:tournament_id>/remove/<int:player_id>/', views.remove_player_from_tournament, name='remove_player_from_tournament'),
    path('tournament/<int:tournament_id>/create-player/', views.create_player_for_tournament, name='create_player_for_tournament'),
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
    path('tournament/<int:tournament_id>/complete/', views.complete_tournament, name='complete_tournament'),
    path('tournament/<int:tournament_id>/recalculate-stats/', views.recalculate_tournament_stats, name='recalculate_tournament_stats'),
    path('tournament/<int:tournament_id>/add-multiple/', views.add_multiple_players, name='add_multiple_players'),

    #ручная рассадка
    path('tournament/<int:tournament_id>/seating/', views.edit_seating, name='edit_seating'),
    path('tournament/<int:tournament_id>/seating/save/<int:game_id>/', views.save_seating, name='save_seating'),
    # Удаление турнира
    path('tournament/<int:tournament_id>/delete/', views.delete_tournament, name='delete_tournament'),

    # BETA модуль# BETA модуль
    path('beta/game/', views.beta_game, name='beta_game'),
    path('beta/day/<int:round_num>/', views.beta_day, name='beta_day'),
    path('beta/night/<int:round_num>/', views.beta_night, name='beta_night'),
    path('beta/vote/', views.beta_vote, name='beta_vote'),
    
    # Восстановление пароля (свои вьюшки, уникальные пути)
    path('recover-password/', views.custom_password_reset, name='password_reset'),
    path('recover-password/sent/', views.custom_password_reset_done, name='password_reset_done'),
    path('recover-password/confirm/<uidb64>/<token>/', views.custom_password_reset_confirm, name='password_reset_confirm'),
    path('recover-password/complete/', views.custom_password_reset_complete, name='password_reset_complete'),


      # ========== УПРАВЛЕНИЕ ПРАВИЛАМИ (ВСЕ МАРШРУТЫ ВМЕСТЕ) ==========
    # Главная страница управления правилами
    path('rules/view/<int:version_id>/', rules_views.rules_admin, name='rules_view_version'),
    path('rules/admin/', rules_views.rules_admin, name='rules_admin'),
    
    # Теги
    path('rules/tags/', rules_views.rules_tags, name='rules_tags'),
    path('rules/add-tag/', rules_views.rules_add_tag, name='rules_add_tag'),
    path('rules/delete-tag/<int:tag_id>/', rules_views.rules_delete_tag, name='rules_delete_tag'),
    
    # Версии
    path('rules/create-version/', rules_views.rules_create_version, name='rules_create_version'),
    path('rules/activate-version/<int:version_id>/', rules_views.rules_activate_version, name='rules_activate_version'),
    path('rules/delete-version/<int:version_id>/', rules_views.rules_delete_version, name='rules_delete_version'),
    
    # Категории (разделы)
    path('rules/add-category/', rules_views.rules_add_category, name='rules_add_category'),
    path('rules/edit-category/<int:category_id>/', rules_views.rules_edit_category, name='rules_edit_category'),
    path('rules/delete-category/<int:category_id>/', rules_views.rules_delete_category, name='rules_delete_category'),
    
    # Подразделы
    path('rules/add-section/', rules_views.rules_add_section, name='rules_add_section'),
    path('rules/edit-section/<int:section_id>/', rules_views.rules_edit_section, name='rules_edit_section'),
    path('rules/delete-section/<int:section_id>/', rules_views.rules_delete_section, name='rules_delete_section'),
    
    # Пункты (с подразделом)
    path('rules/add-item/', rules_views.rules_add_item, name='rules_add_item'),
    path('rules/edit-item/<int:item_id>/', rules_views.rules_edit_item, name='rules_edit_item'),
    path('rules/delete-item/<int:item_id>/', rules_views.rules_delete_item, name='rules_delete_item'),
    
    # Прямые пункты (без подраздела)
    path('rules/add-direct-item/', rules_views.rules_add_direct_item, name='rules_add_direct_item'),
    path('rules/edit-direct-item/<int:item_id>/', rules_views.rules_edit_direct_item, name='rules_edit_direct_item'),
    path('rules/delete-direct-item/<int:item_id>/', rules_views.rules_delete_direct_item, name='rules_delete_direct_item'),
    
    # Переменные
    path('rules/add-variable/', rules_views.rules_add_variable, name='rules_add_variable'),
    path('rules/edit-variable/<int:variable_id>/', rules_views.rules_edit_variable, name='rules_edit_variable'),
    path('rules/delete-variable/<int:variable_id>/', rules_views.rules_delete_variable, name='rules_delete_variable'),
    
    # API (должны быть в конце, чтобы не перекрывать другие маршруты)
    path('rules/api/category/<int:category_id>/', rules_views.rules_api_category, name='rules_api_category'),
    path('rules/api/section/<int:section_id>/', rules_views.rules_api_section, name='rules_api_section'),
    path('rules/api/item/<int:item_id>/', rules_views.rules_api_item, name='rules_api_item'),
    path('rules/api/variable/<int:variable_id>/', rules_views.rules_api_variable, name='rules_api_variable'),
    path('rules/api/direct-item/<int:item_id>/', rules_views.rules_api_direct_item, name='rules_api_direct_item'),
    path('rules/api/version/<int:version_id>/', rules_views.rules_get_version_data, name='rules_get_version_data'),
    
]