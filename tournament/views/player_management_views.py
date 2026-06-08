from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
import secrets

from ..models import User, Tournament, TournamentPlayer
from ..utils import generate_invitation_token


@login_required
def get_players_for_tournament(request, tournament_id):
    """API для получения списка игроков для выпадающего списка"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем, что пользователь - ведущий этого турнира
    if request.user != tournament.host:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    # Получаем всех игроков (кроме ведущего и уже добавленных)
    existing_player_ids = tournament.players.values_list('user_id', flat=True)
    
    # Поиск по запросу (по никнейму или username)
    search = request.GET.get('q', '').strip()
    
    players = User.objects.filter(
        ~Q(id__in=existing_player_ids)  # исключаем уже добавленных
    ).exclude(
        id=tournament.host.id  # исключаем ведущего
    )
    
    # Применяем поиск, если есть запрос
    if search:
        players = players.filter(
            Q(player_nickname__icontains=search) |
            Q(username__icontains=search)
        )
    
    # Сортируем по никнейму (в алфавитном порядке)
    players = players.order_by('player_nickname', 'username')
    
    data = [{
        'id': player.id,
        'nickname': player.player_nickname or '—',
        'username': player.username,
        'display': f"{player.player_nickname or '—'} (@{player.username})"  # Для отображения
    } for player in players]
    
    return JsonResponse({'players': data})

@login_required
def add_player_to_tournament(request, tournament_id, player_id):
    """Добавить игрока в турнир"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    player = get_object_or_404(User, id=player_id)
    
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Проверяем, не добавлен ли уже
    if tournament.players.filter(user=player).exists():
        messages.warning(request, f'Игрок {player.username} уже в турнире')
    else:
        TournamentPlayer.objects.create(
            tournament=tournament,
            user=player,
            is_active=True
        )
        messages.success(request, f'Игрок {player.username} добавлен в турнир')
    
    return redirect('tournament_detail', tournament_id=tournament.id)

@login_required
def remove_player_from_tournament(request, tournament_id, player_id):
    """Удалить игрока из турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    player = get_object_or_404(User, id=player_id)
    
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    tournament_player = tournament.players.filter(user=player).first()
    if tournament_player:
        tournament_player.delete()
        messages.success(request, f'Игрок {player.username} удален из турнира')
    
    return redirect('tournament_detail', tournament_id=tournament.id)

@login_required
def create_player_for_tournament(request, tournament_id):
    """Создание нового игрока и добавление в турнир"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if request.method == 'POST':
        nickname = request.POST.get('nickname', '').strip()
        
        if not nickname:
            messages.error(request, 'Введите никнейм')
            return redirect('tournament_detail', tournament_id=tournament.id)
        
        # Проверяем, нет ли уже такого никнейма
        if User.objects.filter(player_nickname=nickname).exists():
            messages.error(request, f'Игрок с никнеймом "{nickname}" уже существует')
            return redirect('tournament_detail', tournament_id=tournament.id)
        
        # Создаем временного пользователя
        token = generate_invitation_token()
        username = f"player_{secrets.token_hex(4)}"  # Временный username
        
        new_player = User.objects.create(
            username=username,
            player_nickname=nickname,
            created_by=request.user,
            invitation_token=token,
            invitation_created=timezone.now(),
            is_active=False,  # Неактивен до подтверждения
            role='player'
        )
        
        # Добавляем в турнир
        TournamentPlayer.objects.create(
            tournament=tournament,
            user=new_player,
            is_active=True
        )
        
        messages.success(request, f'Игрок {nickname} создан и добавлен в турнир')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    return redirect('tournament_detail', tournament_id=tournament.id)


@login_required
def delete_player(request, player_id):
    """Удаление созданного игрока"""
    player = get_object_or_404(User, id=player_id, created_by=request.user, is_active=False)
    
    if request.method == 'POST':
        player.delete()
        messages.success(request, f'Игрок {player.player_nickname} удален')
    
    return redirect('profile')


@login_required
def toggle_data_visibility(request, tournament_id):
    """Переключение видимости данных турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем, что пользователь - ведущий этого турнира
    if request.user != tournament.host:
        messages.error(request, 'У вас нет прав для изменения этого турнира')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Переключаем видимость
    tournament.data_visible = not tournament.data_visible
    tournament.save()
    
    status = "видны всем" if tournament.data_visible else "скрыты от игроков"
    messages.success(request, f'Данные турнира теперь {status}')
    
    return redirect('tournament_detail', tournament_id=tournament.id)
