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
    """Рассчитывает итоговые места игроков в турнире"""
    players = list(TournamentPlayer.objects.filter(tournament=tournament))
    
    # Получаем актуальные очки напрямую через агрегацию
    player_scores = []
    for player in players:
        total = player.get_total_score()
        player_scores.append((player, total))
    
    # Сортируем по очкам (по убыванию)
    player_scores.sort(key=lambda x: x[1], reverse=True)
    
    for i, (player, total) in enumerate(player_scores):
        if i > 0 and total == player_scores[i-1][1]:
            player.final_place = player_scores[i-1][0].final_place
        else:
            player.final_place = i + 1
        player.save()
    
    return True


def recalculate_yellow_card_penalties(tournament):
    """
    Пересчитывает штрафы за ЖК для ВСЕХ игр турнира
    Вызывать после любого изменения ЖК в любой игре
    """
    # Получаем все завершённые игры по порядку
    games = tournament.games.filter(winning_team__isnull=False).order_by('round_number')
    
    if not games:
        return
    
    # Для каждого игрока в турнире
    for tp in tournament.players.all():
        cumulative_yellow = 0  # Счётчик ЖК на текущий момент
        
        # Проходим по всем играм по порядку
        for game in games:
            try:
                stats = PlayerGameStats.objects.get(
                    game=game,
                    tournament_player=tp
                )
                
                # Получаем ручной штраф из отдельного поля
                manual_penalty = stats.manual_penalty
                
                # Сколько ЖК в этой игре
                game_yellow = stats.yellow_cards
                
                # Рассчитываем штраф за ЖК для ЭТОЙ игры
                if game_yellow >= 2:
                    # Красная карточка - фиксированный штраф
                    yellow_penalty = 0.5
                    cumulative_yellow += game_yellow
                elif game_yellow == 1:
                    # Обычная ЖК - штраф зависит от номера
                    cumulative_yellow += 1
                    yellow_penalty = 0.15 * cumulative_yellow
                else:
                    yellow_penalty = 0
                
                # Сохраняем отдельно штраф за ЖК
                stats.yellow_penalty = yellow_penalty
                
                # Общий штраф = ручной штраф + штраф за ЖК
                stats.penalty_score = manual_penalty + yellow_penalty
                
                # Сохраняем (total_score пересчитается автоматически)
                stats.save()
                
            except PlayerGameStats.DoesNotExist:
                # Если статистики нет, значит игра не введена - пропускаем
                pass
    
    return True

def recalculate_ci(tournament):
    """
    Пересчитывает компенсационные баллы Ci для всех игроков турнира.
    Вызывать после каждого изменения результатов игр.
    """
    # Получаем всех игроков турнира
    tournament_players = TournamentPlayer.objects.filter(tournament=tournament)
    
    for tp in tournament_players:
        # Все завершённые игры игрока в этом турнире
        all_stats = PlayerGameStats.objects.filter(
            tournament_player=tp,
            game__winning_team__isnull=False
        ).order_by('game__round_number')
        
        N = all_stats.count()
        if N == 0:
            continue
        
        # Подсчёт i: количество первых убийств в роли мирного или шерифа
        first_kill_stats = all_stats.filter(
            role__in=['civil', 'sheriff'],
            first_shot__isnull=False
        ).exclude(first_shot='')
        i = first_kill_stats.count()
        
        # Вычисление B (40% от N, округлённое до целого, но не менее 4)
        B = round(0.4 * N)
        if B < 4:
            B = 4
        
        # Вычисление глобального Ci
        if i <= B and B > 0:
            Ci_global = (i / B) * 0.4
        else:
            Ci_global = 0.4
        
        # Для каждой игры, где игрок был первым убитым, вычисляем индивидуальный ci
        for stat in first_kill_stats:
            # Проверяем наличие чёрных (мафия/дон) в лучшем ходе
            best_shot = stat.first_shot
            has_black = False
            if best_shot:
                try:
                    numbers = [int(x) for x in best_shot.split() if x.strip()]
                    seating_order = stat.game.seating.get('order', [])
                    for num in numbers:
                        if 1 <= num <= len(seating_order):
                            target_player_id = seating_order[num - 1]
                            # Ищем статистику цели в этой игре
                            target_stat = PlayerGameStats.objects.filter(
                                game=stat.game,
                                user_id=target_player_id
                            ).first()
                            if target_stat and target_stat.role in ['mafia', 'don']:
                                has_black = True
                                break
                except (ValueError, TypeError, IndexError):
                    pass
            
            # Определяем коэффициент по правилам 8.2
            winning_team = stat.game.winning_team
            if winning_team == 'mafia':  # красная команда проиграла
                coef = 1.0 if has_black else 0.5
            else:  # красная команда выиграла
                coef = 0.5 if has_black else 0.25
            
            # Вычисляем ci для этой игры
            ci_value = round(Ci_global * coef, 2)
            
            # Обновляем поле ci
            stat.ci = ci_value
            stat.save()  # save автоматически пересчитает total_score


def calculate_yellow_card_penalty(tournament_player, current_game_yellow_cards):
    """
    Рассчитывает штраф за жёлтые карточки с учётом всех игр турнира
    
    Args:
        tournament_player: объект TournamentPlayer
        current_game_yellow_cards: количество ЖК в текущей игре (0, 1, или 2)
    
    Returns:
        float: сумма штрафа за ЖК для этой игры
    """
    # Получаем все предыдущие игры игрока в этом турнире
    previous_stats = PlayerGameStats.objects.filter(
        tournament_player=tournament_player
    ).exclude(game__winning_team__isnull=True)  # только сыгранные игры
    
    # Считаем общее количество ЖК до этой игры
    total_previous_yellow = sum(stat.yellow_cards for stat in previous_stats)
    
    # Если в текущей игре 2 ЖК - это красная карточка, фиксированный штраф 0.5
    if current_game_yellow_cards >= 2:
        return 0.5
    
    # Если 0 или 1 ЖК - считаем по прогрессии
    if current_game_yellow_cards == 0:
        return 0.0
    else:  # 1 ЖК
        # Номер этой ЖК в общем зачёте
        card_number = total_previous_yellow + 1
        # Штраф = 0.15 * номер карточки
        return 0.15 * card_number
    