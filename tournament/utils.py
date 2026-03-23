import secrets
from django.utils import timezone
from django.db import models
from django.db.models import Sum, Count, Q, F
from .models import PlayerGameStats, TournamentPlayer, Game
import random
from collections import defaultdict
import math
import json

def generate_invitation_token():
    """Генерирует уникальный токен для приглашения"""
    return secrets.token_urlsafe(32)

def generate_seating(players, total_games):
    """
    Генерирует рассадку для турнира.
    
    Args:
        players: список объектов User (игроки)
        total_games: количество игр в турнире
    
    Returns:
        list: список рассадок для каждой игры, где каждая рассадка - список ID игроков в порядке мест (0..N-1)
    """
    player_ids = [p.id for p in players]
    num_players = len(player_ids)
    
    # Если игроков столько же, сколько игр - генерируем сбалансированную рассадку
    if num_players == total_games:
        return generate_balanced_seating(player_ids)
    else:
        # Иначе - просто случайные перестановки
        return generate_random_seating(player_ids, total_games)

def generate_balanced_seating(player_ids):
    """
    Генерирует сбалансированную рассадку, где каждый игрок сидит на каждом месте ровно один раз.
    Используется латинский квадрат с последующим перемешиванием строк и столбцов.
    """
    n = len(player_ids)
    
    # Строим базовый латинский квадрат (циклический сдвиг)
    base_square = []
    for i in range(n):
        row = []
        for j in range(n):
            # Индекс игрока: (j + i) % n
            row.append(player_ids[(j + i) % n])
        base_square.append(row)
    
    # Перемешиваем строки (игры)
    random.shuffle(base_square)
    
    # Перемешиваем столбцы (места) одинаково для всех игр, чтобы сохранить свойство "каждый игрок на каждом месте"
    # Для этого генерируем случайную перестановку столбцов и применяем ко всем строкам
    col_perm = list(range(n))
    random.shuffle(col_perm)
    
    seating_plan = []
    for row in base_square:
        new_row = [row[col_perm[j]] for j in range(n)]
        seating_plan.append(new_row)
    
    # Проверка (опционально) - можно оставить для отладки
    if n <= 10:  # не выводить для больших n, чтобы не засорять консоль
        verify_seating(seating_plan, player_ids, n)
    
    return seating_plan

def generate_random_seating(player_ids, total_games):
    """Простая случайная рассадка для случая, когда игроков больше или меньше, чем игр."""
    seating_plan = []
    for _ in range(total_games):
        shuffled = player_ids.copy()
        random.shuffle(shuffled)
        seating_plan.append(shuffled)
    return seating_plan

def verify_seating(seating_plan, player_ids, num_players):
    """
    Проверяет, что каждый игрок был на каждом месте ровно один раз.
    Выводит предупреждение, если это не так.
    """
    position_matrix = defaultdict(set)
    for game_idx, positions in enumerate(seating_plan):
        for seat_idx, player_id in enumerate(positions):
            position_matrix[player_id].add(seat_idx)
    
    all_seats_covered = all(len(positions) == num_players for positions in position_matrix.values())
    if not all_seats_covered:
        print("⚠️ Предупреждение: не все позиции покрыты уникально")
        for player_id in player_ids:
            missing = set(range(num_players)) - position_matrix[player_id]
            if missing:
                # Найдём имя игрока (можно передавать словарь имён, но для простоты оставим ID)
                print(f"Игрок {player_id} не был на местах: {missing}")
    else:
        print("✅ Уникальность позиций подтверждена")
    return all_seats_covered

def calculate_tournament_statistics(tournament):
    """
    Рассчитывает дополнительную статистику для завершённого турнира
    """
    # Импортируем модели внутри функции
    from .models import PlayerGameStats, TournamentPlayer, Game
    
    stats = {}
    
    # Получаем всех игроков турнира
    players = tournament.players.all()
    
    # 1. Кого чаще всего стреляли (первый убитый)
    first_kill_stats = defaultdict(int)
    for game in tournament.games.filter(winning_team__isnull=False):
        for stat in game.player_stats.filter(first_shot__isnull=False).exclude(first_shot=''):
            first_kill_stats[stat.user_id] += 1
    
    if first_kill_stats:
        most_killed_user_id = max(first_kill_stats, key=first_kill_stats.get)
        try:
            player = players.get(user_id=most_killed_user_id).user
            stats['most_killed'] = {
                'player_id': player.id,
                'player_name': player.player_nickname or player.username,
                'count': first_kill_stats[most_killed_user_id]
            }
        except TournamentPlayer.DoesNotExist:
            pass
    
    # 3. Лучший на каждой роли (по сумме дополнительных баллов)
    roles = ['don', 'mafia', 'sheriff', 'civil']
    role_stats = {}
    
    for role in roles:
        role_players = []
        for player in players:
            role_data = PlayerGameStats.objects.filter(
                tournament_player=player,
                role=role
            ).aggregate(
                total_bonus=Sum('bonus_score'),
                total_main=Sum('main_score'),
                games_played=Count('id')
            )
            
            if role_data['games_played'] > 0:
                role_players.append({
                    'player_id': player.user.id,
                    'player_name': player.user.player_nickname or player.user.username,
                    'total_bonus': float(role_data['total_bonus'] or 0),
                    'total_main': float(role_data['total_main'] or 0),
                    'games_played': role_data['games_played']
                })
        
        # Сортируем: сначала по сумме бонусов (убывание), потом по количеству игр (возрастание)
        if role_players:
            role_players.sort(key=lambda x: (-x['total_bonus'], x['games_played']))
            role_stats[role] = {
                'player_id': role_players[0]['player_id'],
                'player_name': role_players[0]['player_name'],
                'total_bonus': role_players[0]['total_bonus'],
                'games_played': role_players[0]['games_played']
            }
    
    stats['best_per_role'] = role_stats
    
    # 4. Самый стабильный игрок (наименьшее отклонение баллов)
    stability_stats = []
    for player in players:
        scores = PlayerGameStats.objects.filter(
            tournament_player=player
        ).values_list('total_score', flat=True)
        
        scores_list = [float(s) for s in scores]
        if len(scores_list) > 1:
            avg = sum(scores_list) / len(scores_list)
            variance = sum((s - avg) ** 2 for s in scores_list) / len(scores_list)
            stability_stats.append({
                'player_id': player.user.id,
                'player_name': player.user.player_nickname or player.user.username,
                'variance': variance,
                'avg_score': avg
            })
    
    if stability_stats:
        stability_stats.sort(key=lambda x: x['variance'])
        stats['most_stable'] = {
            'player_id': stability_stats[0]['player_id'],
            'player_name': stability_stats[0]['player_name'],
            'variance': round(stability_stats[0]['variance'], 2),
            'avg_score': round(stability_stats[0]['avg_score'], 2)
        }
    
    # 5. Самый результативный игрок (максимум основных баллов)
    top_main = players.annotate(
        total_main=Sum('game_stats__main_score')
    ).order_by('-total_main').first()
    
    if top_main and top_main.total_main and float(top_main.total_main) > 0:
        stats['top_main'] = {
            'player_id': top_main.user.id,
            'player_name': top_main.user.player_nickname or top_main.user.username,
            'total_main': round(float(top_main.total_main), 2)
        }
    
    # 6. Самый бонусный игрок (максимум бонусных баллов)
    top_bonus = players.annotate(
        total_bonus=Sum('game_stats__bonus_score')
    ).order_by('-total_bonus').first()
    
    if top_bonus and top_bonus.total_bonus and float(top_bonus.total_bonus) > 0:
        stats['top_bonus'] = {
            'player_id': top_bonus.user.id,
            'player_name': top_bonus.user.player_nickname or top_bonus.user.username,
            'total_bonus': round(float(top_bonus.total_bonus), 2)
        }
    
    # 7. Самый штрафной игрок (максимум штрафов)
    top_penalty = players.annotate(
        total_penalty=Sum('game_stats__penalty_score')
    ).order_by('-total_penalty').first()
    
    if top_penalty and top_penalty.total_penalty and float(top_penalty.total_penalty) > 0:
        stats['top_penalty'] = {
            'player_id': top_penalty.user.id,
            'player_name': top_penalty.user.player_nickname or top_penalty.user.username,
            'total_penalty': round(float(top_penalty.total_penalty), 2)
        }
    
    # 8. Рекордсмен по жёлтым карточкам
    top_yellow = players.annotate(
        total_yellow=Sum('game_stats__yellow_cards')
    ).order_by('-total_yellow').first()
    
    if top_yellow and top_yellow.total_yellow and top_yellow.total_yellow > 0:
        stats['top_yellow'] = {
            'player_id': top_yellow.user.id,
            'player_name': top_yellow.user.player_nickname or top_yellow.user.username,
            'total_yellow': top_yellow.total_yellow
        }
    
    # 9. Статистика по командам
    total_completed = tournament.games.filter(winning_team__isnull=False).count()
    mafia_wins = tournament.games.filter(winning_team='mafia').count()
    peace_wins = tournament.games.filter(winning_team='peace').count()
    
    if total_completed > 0:
        stats['team_stats'] = {
            'mafia_wins': mafia_wins,
            'peace_wins': peace_wins,
            'total_games': total_completed
        }
    
    # 10. ПОБЕДИТЕЛЬ ТУРНИРА (игрок с максимальным total_score)
    winner_data = players.annotate(
        total_score=Sum('game_stats__total_score')
    ).order_by('-total_score').first()
    
    if winner_data and winner_data.total_score:
        # Находим второе место для определения уникальности
        second_place = players.annotate(
            total_score=Sum('game_stats__total_score')
        ).exclude(id=winner_data.id).order_by('-total_score').first()
        
        is_unique = True
        if second_place and second_place.total_score == winner_data.total_score:
            is_unique = False
        
        stats['winner'] = {
            'player_id': winner_data.user.id,
            'player_name': winner_data.user.player_nickname or winner_data.user.username,
            'total_score': round(float(winner_data.total_score), 2),
            'is_unique': is_unique
        }
    
    return stats

def calculate_final_places(tournament):
    """
    Рассчитывает итоговые места игроков в турнире
    """
    players = TournamentPlayer.objects.filter(
        tournament=tournament
    ).annotate(
        total_main=Sum('game_stats__main_score'),
        total_bonus=Sum('game_stats__bonus_score')
    ).order_by('-total_main', '-total_bonus')
    
    current_place = 1
    for i, player in enumerate(players):
        if i > 0:
            prev_player = players[i-1]
            if (player.total_main == prev_player.total_main and 
                player.total_bonus == prev_player.total_bonus):
                player.final_place = prev_player.final_place
            else:
                player.final_place = i + 1
        else:
            player.final_place = 1
        
        player.save()
    
    return True