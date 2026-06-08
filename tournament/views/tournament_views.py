from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.utils import timezone

from ..models import Tournament, TournamentPlayer, Game, PlayerGameStats
from ..forms import TournamentCreateForm
from ..utils import generate_seating, calculate_final_places, calculate_tournament_statistics


def home(request):
    """Главная страница"""
    # Получаем все турниры, кроме черновиков, сортируем по дате
    tournaments = Tournament.objects.exclude(status='draft').order_by('-start_date')[:9]
    
    # Для каждого турнира добавляем дополнительную информацию
    for tournament in tournaments:
        if tournament.status == 'active':
            total_games = tournament.games.count()
            completed_games = tournament.games.exclude(winning_team__isnull=True).count()
            tournament.completed_games = completed_games
            tournament.completed_percent = int(completed_games / total_games * 100) if total_games > 0 else 0
    
    context = {
        'tournaments': tournaments,
    }
    return render(request, 'tournament/home.html', context)



@login_required
def create_tournament(request):
    # Проверяем, что пользователь - одобренный ведущий
    if request.user.role != 'host' or not request.user.is_approved_host:
        messages.error(request, 'У вас нет прав для создания турниров')
        return redirect('profile')
    
    if request.method == 'POST':
        form = TournamentCreateForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.host = request.user
            tournament.status = 'draft'  # Начинаем как черновик
            tournament.save()
            messages.success(request, f'Турнир "{tournament.name}" успешно создан!')
            return redirect('tournament_detail', tournament_id=tournament.id)
    else:
        form = TournamentCreateForm()
    
    return render(request, 'tournament/create_tournament.html', {'form': form})

@login_required
def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    can_edit = (request.user == tournament.host)
    
    # Статистика игр
    games = tournament.games.all()
    completed_games = games.exclude(winning_team__isnull=True).count()
    pending_games = games.filter(winning_team__isnull=True).count()

    player_totals = {}
    for tp in tournament.players.all():
        total_score = PlayerGameStats.objects.filter(
            tournament_player=tp
        ).aggregate(total=models.Sum('total_score'))['total'] or 0
        player_totals[tp.user.id] = round(total_score, 2)

    game_stats = {}
    for game in games:
        stats_for_game = {}
        player_stats = PlayerGameStats.objects.filter(game=game).select_related('user')
        for stat in player_stats:
            stats_for_game[stat.user_id] = {
                'total_score': stat.total_score,
                'role': stat.role,
                'main_score': stat.main_score,
                'bonus_score': stat.bonus_score,
                'penalty_score': stat.penalty_score,
                'ci': stat.ci,
            }
        game_stats[game.id] = stats_for_game
    
    context = {
        'tournament': tournament,
        'can_edit': can_edit,
        'completed_games': completed_games,
        'pending_games': pending_games,
        'player_totals': player_totals,  # Добавляем суммы баллов
        'game_stats': game_stats,  # Добавляем статистику по играм
    }
    return render(request, 'tournament/tournament_detail.html', context)

@login_required
def my_tournaments(request):
    if request.user.role == 'host' and request.user.is_approved_host:
        # Ведущий видит свои турниры
        tournaments = Tournament.objects.filter(host=request.user).order_by('-created_at')
    else:
        # Игрок видит турниры, в которых участвует
        tournaments = Tournament.objects.filter(
            players__user=request.user
        ).order_by('-created_at')
    
    context = {
        'tournaments': tournaments,
        'is_host': request.user.role == 'host' and request.user.is_approved_host,
    }
    return render(request, 'tournament/my_tournaments.html', context)

@login_required
def start_tournament(request, tournament_id):
    """Начать турнир - сгенерировать игры"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем права
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Проверяем, что турнир в статусе draft или pending
    if tournament.status not in ['draft', 'pending']:
        messages.error(request, 'Турнир уже начат или завершен')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Проверяем, что все места заполнены
    current_players = tournament.players.count()
    if current_players < tournament.max_players:
        messages.error(request, f'Не хватает игроков. Текущее количество: {current_players}, нужно: {tournament.max_players}')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Получаем список игроков
    players = [tp.user for tp in tournament.players.all()]
    
    # Генерируем рассадку
    seating_plan = generate_seating(players, tournament.total_games)
    
    # Создаем игры
    for round_num, game_seating in enumerate(seating_plan, 1):
        Game.objects.create(
            tournament=tournament,
            round_number=round_num,
            seating={
                'order': game_seating,
                'algorithm': 'smart_balanced'
            }
        )
    
    # Обновляем статус турнира
    tournament.status = 'active'
    tournament.save()
    
    messages.success(request, f'Турнир начат! Создано {tournament.total_games} игр.')
    return redirect('tournament_detail', tournament_id=tournament.id)

@login_required
def cancel_tournament_start(request, tournament_id):
    """Отменить старт турнира - удалить все игры"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем права
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Проверяем, что турнир активен
    if tournament.status != 'active':
        messages.error(request, 'Турнир не в активном состоянии')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Удаляем все игры турнира
    games_count = tournament.games.count()
    tournament.games.all().delete()
    
    # Возвращаем статус в черновик
    tournament.status = 'draft'
    tournament.save()
    
    messages.success(request, f'Старт турнира отменён. Удалено {games_count} игр.')
    return redirect('tournament_detail', tournament_id=tournament.id)

@login_required
def tournament_games(request, tournament_id):
    """Страница со всеми играми турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем доступ (ведущий или участник)
    is_participant = tournament.players.filter(user=request.user).exists()
    if request.user != tournament.host and not is_participant:
        messages.error(request, 'Нет доступа к этому турниру')
        return redirect('home')
    
    games = tournament.games.all().order_by('round_number')
    
    # Собираем статистику по играм
    completed_games = games.exclude(winning_team__isnull=True).count()
    pending_games = games.filter(winning_team__isnull=True).count()
    
    # Загружаем статистику для всех игр одним запросом
    game_stats = {}
    if games:
        all_stats = PlayerGameStats.objects.filter(
            game__in=games
        ).select_related('user', 'tournament_player')
        
        # Группируем статистику по играм
        for stat in all_stats:
            if stat.game_id not in game_stats:
                game_stats[stat.game_id] = {}
            game_stats[stat.game_id][stat.user_id] = stat
    max_totals = {}
    for game in games:
        if game.id in game_stats:
            totals = [stat.total_score for stat in game_stats[game.id].values()]
            if totals:
                max_totals[game.id] = max(totals)
    context = {
        'tournament': tournament,
        'games': games,
        'completed_games': completed_games,
        'pending_games': pending_games,
        'game_stats': game_stats,  # Добавляем статистику
        'is_host': request.user == tournament.host,
        'max_totals': max_totals,
    }
    
    return render(request, 'tournament/tournament_games.html', context)

@login_required
def complete_tournament(request, tournament_id):
    """Завершить турнир и рассчитать статистику"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем права
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Проверяем, что все игры завершены
    pending_games = tournament.games.filter(winning_team__isnull=True).count()
    if pending_games > 0:
        messages.error(request, f'Нельзя завершить турнир: осталось {pending_games} незавершённых игр')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Завершаем турнир
    stats = tournament.complete()
    
    messages.success(request, f'Турнир "{tournament.name}" завершён! Статистика рассчитана.')
    return redirect('tournament_detail', tournament_id=tournament.id)

@login_required
def recalculate_tournament_stats(request, tournament_id):
    """Пересчитать статистику завершённого турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем права
    if request.user != tournament.host and not request.user.is_superuser:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Проверяем, что турнир завершён
    if tournament.status != 'completed':
        messages.error(request, 'Статистика доступна только для завершённых турниров')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    # Пересчитываем
    calculate_final_places(tournament)
    stats = calculate_tournament_statistics(tournament)
    tournament.completed_stats = stats
    tournament.save()
    
    messages.success(request, 'Статистика турнира успешно пересчитана!')
    return redirect('tournament_detail', tournament_id=tournament.id)
