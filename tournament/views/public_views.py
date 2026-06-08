from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from ..models import Game, Tournament, TournamentPlayer, PlayerGameStats


def tournament_public(request, tournament_id):
    """Публичная страница турнира с вкладками"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    
    # Если данные скрыты и пользователь не ведущий - показываем заглушку
    if not tournament.data_visible:
        return render(request, 'tournament/tournament_hidden.html', {'tournament': tournament})
    
    
    context = {
        'tournament': tournament,
    }
    return render(request, 'tournament/tournament_public.html', context)

def tournament_public_stats(request, tournament_id):
    """API для получения статистики игроков турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if not tournament.data_visible:
        return JsonResponse({
            'hidden': True,
            'message': 'Данные турнира скрыты ведущим'
        }, status=403)
    
    # Собираем статистику по каждому игроку
    players_data = []
    
    for tp in tournament.players.all().select_related('user'):
        # Все статистики игрока в этом турнире
        all_stats = PlayerGameStats.objects.filter(
            tournament_player=tp,
            game__winning_team__isnull=False  # только сыгранные игры
        ).select_related('game')
        
        # Базовая статистика
        total_score = sum(stat.total_score for stat in all_stats)
        total_main = sum(stat.main_score for stat in all_stats)
        total_bonus = sum(stat.bonus_score for stat in all_stats)
        total_penalty = sum(stat.penalty_score for stat in all_stats)
        total_ci = sum(stat.ci for stat in all_stats)
        
        # Количество побед (игрок победил, если его команда выиграла)
        wins = 0
        for stat in all_stats:
            if (stat.game.winning_team == 'mafia' and stat.role in ['mafia', 'don']) or \
               (stat.game.winning_team == 'peace' and stat.role in ['civil', 'sheriff']):
                wins += 1
        
        # Первые отстрелы
        first_kills = all_stats.filter(first_shot__isnull=False).exclude(first_shot='').count()
        
        # Баллы за лучший ход
        lh_bonus = sum(stat.lh_bonus for stat in all_stats)
        
        # Жёлтые и красные карточки
        yellow_cards = sum(1 for stat in all_stats if stat.yellow_cards == 1)
        red_cards = sum(1 for stat in all_stats if stat.yellow_cards >= 2)
        
        # Статистика по ролям
        don_games = all_stats.filter(role='don').count()
        mafia_games = all_stats.filter(role='mafia').count()
        sheriff_games = all_stats.filter(role='sheriff').count()
        civil_games = all_stats.filter(role='civil').count()
        
        players_data.append({
            'id': tp.user.id,
            'nickname': tp.user.player_nickname or tp.user.username,
            'username': tp.user.username,
            'total_score': round(total_score, 2),
            'main_score': round(total_main, 2),
            'bonus_score': round(total_bonus, 2),
            'penalty_score': round(total_penalty, 2),
            'ci': round(total_ci, 2),
            'wins': wins,
            'first_kills': first_kills,
            'lh_bonus': round(lh_bonus, 2),
            'yellow_cards': yellow_cards,
            'red_cards': red_cards,
            'games_played': all_stats.count(),
            'roles': {
                'don': don_games,
                'mafia': mafia_games,
                'sheriff': sheriff_games,
                'civil': civil_games,
            }
        })
    
    # Общая статистика турнира
    total_games = tournament.games.count()
    completed_games = tournament.games.exclude(winning_team__isnull=True).count()
    
    data = {
        'tournament': {
            'id': tournament.id,
            'name': tournament.name,
            'status': tournament.status,
            'status_display': tournament.get_status_display(),
            'rules': tournament.get_rules_display(),
            'total_games': total_games,
            'completed_games': completed_games,
            'players_count': tournament.players.count(),
        },
        'players': players_data,
    }
    
    # Если турнир завершён, добавляем статистику из completed_stats
    if tournament.status == 'completed' and tournament.completed_stats:
        data['completed_stats'] = tournament.completed_stats
    
    return JsonResponse(data)

def tournament_public_games(request, tournament_id):
    """API для получения списка игр турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    
    # Если данные скрыты и пользователь не ведущий - возвращаем пустые данные
    if not tournament.data_visible:
        return JsonResponse({
            'hidden': True,
            'message': 'Данные турнира скрыты ведущим'
        }, status=403)
    
    games_data = []
    games = tournament.games.all().order_by('round_number')
    
    # Загружаем статистику для всех игр
    game_stats = {}
    all_stats = PlayerGameStats.objects.filter(game__in=games).select_related('user')
    for stat in all_stats:
        if stat.game_id not in game_stats:
            game_stats[stat.game_id] = {}
        game_stats[stat.game_id][stat.user_id] = {
            'total_score': float(stat.total_score),
            'main_score': float(stat.main_score),
            'bonus_score': float(stat.bonus_score),
            'penalty_score': float(stat.penalty_score),
            'ci': float(stat.ci),
            'role': stat.role,
            'yellow_cards': stat.yellow_cards,
            'first_shot': stat.first_shot,
        }
    
    for game in games:
        # Получаем рассадку
        seating_order = game.seating.get('order', [])
        seating = []
        
        # Создаем словарь для быстрого доступа к игрокам
        players_dict = {tp.user.id: tp for tp in tournament.players.all()}
        
        for position, player_id in enumerate(seating_order, 1):
            tp = players_dict.get(player_id)
            if tp:
                stats = game_stats.get(game.id, {}).get(player_id, {})
                seating.append({
                    'position': position,
                    'player_id': player_id,
                    'nickname': tp.user.player_nickname or tp.user.username,
                    'username': tp.user.username,
                    'total_score': stats.get('total_score', 0),
                    'main_score': stats.get('main_score', 0),
                    'bonus_score': stats.get('bonus_score', 0),
                    'penalty_score': stats.get('penalty_score', 0),
                    'ci': stats.get('ci', 0),
                    'role': stats.get('role'),
                    'yellow_cards': stats.get('yellow_cards', 0),
                })
        
        games_data.append({
            'id': game.id,
            'round_number': game.round_number,
            'winning_team': game.winning_team,
            'played_at': game.played_at.strftime('%d.%m.%Y %H:%M') if game.played_at else None,
            'seating': seating,
        })
    
    data = {
        'games': games_data,
        'total_games': games.count(),
        'completed_games': games.exclude(winning_team__isnull=True).count(),
    }
    
    return JsonResponse(data)

def public_game_view(request, tournament_id, game_round):
    """Публичная страница просмотра результатов игры (без редактирования)"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    game = get_object_or_404(Game, tournament=tournament, round_number=game_round)
    
    # Проверяем доступ (участник турнира или ведущий)
    # Если данные скрыты и пользователь не ведущий - показываем заглушку
    if not tournament.data_visible:
        return render(request, 'tournament/game_hidden.html', {'tournament': tournament, 'game': game})
    
    
    game_stats = {}
    player_stats = PlayerGameStats.objects.filter(game=game).select_related('user', 'tournament_player')
    
    max_total = 0
    mvp_name = None
    total_yellow = 0
    total_red = 0
    first_killed_name = None
    first_killed_role = None
    total_score_sum = 0
    
    for stat in player_stats:
        game_stats[stat.user_id] = stat
        
        if stat.total_score > max_total:
            max_total = stat.total_score
            mvp_name = stat.user.player_nickname or stat.user.username
        
        if stat.yellow_cards == 1:
            total_yellow += 1
        elif stat.yellow_cards >= 2:
            total_red += 1
        
        if stat.first_shot:
            first_killed_name = stat.user.player_nickname or stat.user.username
            first_killed_role = stat.get_role_display()
        
        total_score_sum += stat.total_score
    
    context = {
        'tournament': tournament,
        'game': game,
        'game_stats': game_stats,
        'max_total': max_total,
        'mvp_name': mvp_name,
        'total_yellow': total_yellow,
        'total_red': total_red,
        'first_killed_name': first_killed_name,
        'first_killed_role': first_killed_role,
        'total_score_sum': total_score_sum,
    }
    return render(request, 'tournament/public_game_view.html', context)
