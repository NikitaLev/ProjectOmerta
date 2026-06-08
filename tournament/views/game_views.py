from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from ..models import Tournament, Game, TournamentPlayer, PlayerGameStats

# Импорт вспомогательных функций из utils (их нужно перенести туда)
from ..utils import calculate_final_places, calculate_tournament_statistics, calculate_yellow_card_penalty, recalculate_yellow_card_penalties, recalculate_ci


def update_player_tournament_stats(tournament_player):
    """Обновляет общую статистику игрока в турнире"""
    all_stats = PlayerGameStats.objects.filter(tournament_player=tournament_player)
    
    total_main = sum(stat.main_score for stat in all_stats)
    total_bonus = sum(stat.bonus_score for stat in all_stats)
    total_ci = sum(stat.ci for stat in all_stats)
    
    tournament_player.total_main_score = total_main
    tournament_player.total_bonus_score = total_bonus
    tournament_player.total_ci = total_ci
    tournament_player.save()
    
    # Вызываем метод модели для обновления денормализованных полей (если нужно)
    tournament_player.update_denormalized_fields()
    
    return tournament_player


def check_tournament_completion(tournament):
    """Проверяет, все ли игры турнира завершены, и если да - завершает турнир"""
    total_games = tournament.games.count()
    completed_games = tournament.games.exclude(winning_team__isnull=True).count()
    
    if total_games == completed_games and total_games > 0:
        # Если турнир ещё не завершён
        if tournament.status != 'completed':
            tournament.status = 'completed'
            tournament.end_date = timezone.now()
            tournament.save()
            
            # Рассчитываем финальные места
            calculate_final_places(tournament)
            
            # Рассчитываем дополнительную статистику
            tournament_stats = calculate_tournament_statistics(tournament)
            
            # Сохраняем статистику в поле JSON
            tournament.completed_stats = tournament_stats
            tournament.save()
        
        return True
    return False

@login_required
def game_input(request, tournament_id, game_round):
    """Страница ввода результатов для новой игры"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    game = get_object_or_404(Game, tournament=tournament, round_number=game_round)
    
    # Проверяем, что игра ещё не завершена
    if game.winning_team:
        messages.warning(request, 'Эта игра уже завершена. Используйте страницу редактирования.')
        return redirect('game_edit', tournament_id=tournament.id, game_round=game_round)
    
    # Проверяем права (только ведущий)
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_games', tournament_id=tournament.id)
    
    if request.method == 'POST':
        try:
            # Получаем победителя
            winning_team = request.POST.get('winning_team')
            if not winning_team:
                messages.error(request, 'Необходимо выбрать победителя игры')
                return redirect('game_input', tournament_id=tournament.id, game_round=game_round)
            
            # Обновляем игру
            game.winning_team = winning_team
            game.save()
            
            # Получаем порядок рассадки
            seating_order = game.seating.get('order', [])
            
            # Находим первого убитого
            first_killed_id = None
            for player_id in seating_order:
                if request.POST.get(f'first_kill_{player_id}') == 'true':
                    first_killed_id = player_id
                    break
            
            # Словарь для хранения ролей
            roles_dict = {}
            for tp in tournament.players.all():
                player_id = tp.user.id
                role = request.POST.get(f'role_{player_id}')
                if role:
                    roles_dict[player_id] = role
            
            # Сохраняем статистику для каждого игрока
            for position, player_id in enumerate(seating_order, 1):
                tp = tournament.players.get(user_id=player_id)
                role = roles_dict.get(player_id)
                
                if not role:
                    messages.error(request, f'Не выбрана роль для игрока {tp.user.player_nickname or tp.user.username}')
                    return redirect('game_input', tournament_id=tournament.id, game_round=game_round)
                
                # Получаем данные из формы
                manual_bonus = float(request.POST.get(f'bonus_{player_id}', 0) or 0)

                manual_penalty = float(request.POST.get(f'penalty_{player_id}', 0) or 0)

                penalty = float(request.POST.get(f'penalty_{player_id}', 0) or 0)
                
                first_kill = (str(player_id) == str(first_killed_id))
                best_shot = request.POST.get(f'best_shot_{player_id}', '') if first_kill else ''

                yellow_cards = int(request.POST.get(f'yellow_cards_{player_id}', 0) or 0)

                yellow_penalty = calculate_yellow_card_penalty(tp, yellow_cards)
                total_penalty = penalty + yellow_penalty
                
                # Основные баллы
                main_score = 0
                if (winning_team == 'mafia' and role in ['mafia', 'don']) or \
                   (winning_team == 'peace' and role in ['civil', 'sheriff']):
                    main_score = 1
                
                # Расчёт бонуса за лучший ход
                lh_bonus = 0
                if first_kill and best_shot and role in ['civil', 'sheriff']:
                    try:
                        numbers = [int(x) for x in best_shot.split() if x.strip()]
                        if len(numbers) == 3 and all(1 <= n <= len(seating_order) for n in numbers):
                            mafia_count = 0
                            for seat_num in numbers:
                                target_player_id = seating_order[seat_num - 1]
                                target_role = roles_dict.get(target_player_id)
                                if target_role in ['mafia', 'don']:
                                    mafia_count += 1
                            
                            if mafia_count >= 3:
                                lh_bonus = 0.5
                            elif mafia_count >= 2:
                                lh_bonus = 0.3
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Создаём запись
                stats = PlayerGameStats(
                    game=game,
                    tournament_player=tp,
                    user=tp.user,
                    role=role,
                    place=position,
                    main_score=main_score,
                    bonus_score=manual_bonus + lh_bonus,
                    yellow_cards=yellow_cards,
                    manual_penalty=manual_penalty,
                    lh_bonus=lh_bonus,
                    first_shot=best_shot if first_kill else '',
                    ci=0.0,
                )
                # Не сохраняем penalty_score отдельно, он пересчитается при save() через calculate_penalty()
                stats.save()
            
            
            recalculate_yellow_card_penalties(tournament)
            recalculate_ci(tournament)
            # Обновляем статистику турнира
            for tp in tournament.players.all():
                update_player_tournament_stats(tp)
            
            check_tournament_completion(tournament)
            
            messages.success(request, f'Результаты игры {game.round_number} успешно сохранены!')
            return redirect('tournament_games', tournament_id=tournament.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при сохранении: {str(e)}')
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            return redirect('game_input', tournament_id=tournament.id, game_round=game_round)
    
    # GET запрос - показываем пустую форму
    context = {
        'tournament': tournament,
        'game': game,
        'is_edit': False,
    }
    return render(request, 'tournament/game_input.html', context)

@login_required
def game_edit(request, tournament_id, game_round):
    """Страница редактирования результатов завершённой игры"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    game = get_object_or_404(Game, tournament=tournament, round_number=game_round)
    
    # Проверяем, что игра завершена
    if not game.winning_team:
        messages.warning(request, 'Эта игра ещё не завершена. Используйте страницу ввода результатов.')
        return redirect('game_input', tournament_id=tournament.id, game_round=game_round)
    
    # Проверяем права (только ведущий)
    if request.user != tournament.host:
        messages.error(request, 'Нет доступа')
        return redirect('tournament_games', tournament_id=tournament.id)
    
    # Получаем существующую статистику
    existing_stats = {}
    player_stats = PlayerGameStats.objects.filter(game=game).select_related('user', 'tournament_player')
    for stat in player_stats:
        existing_stats[stat.user_id] = stat
    
    if request.method == 'POST':
        try:
            # Получаем нового победителя
            winning_team = request.POST.get('winning_team')
            if not winning_team:
                messages.error(request, 'Необходимо выбрать победителя игры')
                return redirect('game_edit', tournament_id=tournament.id, game_round=game_round)
            
            # Обновляем игру
            game.winning_team = winning_team
            game.save()
            
            # Получаем порядок рассадки
            seating_order = game.seating.get('order', [])
            
            # Находим первого убитого
            first_killed_id = None
            for player_id in seating_order:
                if request.POST.get(f'first_kill_{player_id}') == 'true':
                    first_killed_id = player_id
                    break
            
            # Словарь для хранения ролей
            roles_dict = {}
            for tp in tournament.players.all():
                player_id = tp.user.id
                role = request.POST.get(f'role_{player_id}')
                if role:
                    roles_dict[player_id] = role
            
            # Обрабатываем каждого игрока
            for position, player_id in enumerate(seating_order, 1):
                tp = tournament.players.get(user_id=player_id)
                role = roles_dict.get(player_id)
                
                if not role:
                    messages.error(request, f'Не выбрана роль для игрока {tp.user.player_nickname or tp.user.username}')
                    return redirect('game_edit', tournament_id=tournament.id, game_round=game_round)
                
                # Получаем данные из формы
                manual_bonus = float(request.POST.get(f'bonus_{player_id}', 0) or 0)  # Ручной бонус
                manual_penalty = float(request.POST.get(f'penalty_{player_id}', 0) or 0)  # Ручной штраф
                yellow_cards = int(request.POST.get(f'yellow_cards_{player_id}', 0) or 0)
                
                first_kill = (str(player_id) == str(first_killed_id))
                best_shot = request.POST.get(f'best_shot_{player_id}', '') if first_kill else ''
                
                # Основные баллы
                main_score = 0
                if (winning_team == 'mafia' and role in ['mafia', 'don']) or \
                   (winning_team == 'peace' and role in ['civil', 'sheriff']):
                    main_score = 1
                
                # Расчёт нового бонуса за лучший ход
                new_lh_bonus = 0
                if first_kill and best_shot and role in ['civil', 'sheriff']:
                    try:
                        numbers = [int(x) for x in best_shot.split() if x.strip()]
                        if len(numbers) == 3 and all(1 <= n <= len(seating_order) for n in numbers):
                            mafia_count = 0
                            for seat_num in numbers:
                                target_player_id = seating_order[seat_num - 1]
                                target_role = roles_dict.get(target_player_id)
                                if target_role in ['mafia', 'don']:
                                    mafia_count += 1
                            
                            if mafia_count >= 3:
                                new_lh_bonus = 0.5
                            elif mafia_count >= 2:
                                new_lh_bonus = 0.3
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Общий бонус = ручной бонус + новый бонус за ЛХ
                total_bonus = manual_bonus + new_lh_bonus
                
                # Обновляем или создаём запись
                try:
                    stats = PlayerGameStats.objects.get(
                        game=game,
                        tournament_player=tp
                    )
                    
                    # Обновляем поля
                    stats.role = role
                    stats.place = position
                    stats.main_score = main_score
                    stats.bonus_score = total_bonus
                    stats.manual_penalty = manual_penalty  # Сохраняем ручной штраф отдельно
                    stats.yellow_cards = yellow_cards
                    stats.lh_bonus = new_lh_bonus
                    stats.first_shot = best_shot if first_kill else ''
                    stats.ci = 0.0
                    stats.save()  # penalty_score и total_score пока не пересчитываем
                    
                except PlayerGameStats.DoesNotExist:
                    # Если записи нет, создаём новую
                    stats = PlayerGameStats.objects.create(
                        game=game,
                        tournament_player=tp,
                        user=tp.user,
                        role=role,
                        place=position,
                        main_score=main_score,
                        bonus_score=total_bonus,
                        manual_penalty=manual_penalty,
                        yellow_cards=yellow_cards,
                        lh_bonus=new_lh_bonus,
                        first_shot=best_shot if first_kill else '',
                        ci=0.0,
                        penalty_score=0,  # Временное значение
                    )
                    stats.save()
            
            # После обновления всех игроков, пересчитываем штрафы за ЖК для всех игр
            recalculate_yellow_card_penalties(tournament)
            recalculate_ci(tournament)
            # Обновляем общую статистику игроков в турнире
            for tp in tournament.players.all():
                update_player_tournament_stats(tp)
            
            check_tournament_completion(tournament)
            
            messages.success(request, f'Результаты игры {game.round_number} успешно обновлены!')
            return redirect('tournament_games', tournament_id=tournament.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            return redirect('game_edit', tournament_id=tournament.id, game_round=game_round)
    
    # GET запрос - передаём существующие данные в шаблон
    context = {
        'tournament': tournament,
        'game': game,
        'existing_stats': existing_stats,
    }
    return render(request, 'tournament/game_edit.html', context)

@login_required
def game_view(request, tournament_id, game_round):
    """Страница просмотра результатов игры"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    game = get_object_or_404(Game, tournament=tournament, round_number=game_round)
    
    # Получаем статистику
    existing_stats = {}
    player_stats = PlayerGameStats.objects.filter(game=game).select_related('user', 'tournament_player')
    
    max_total = 0
    total_yellow = 0
    total_red = 0
    first_killed_name = None
    total_score_sum = 0
    
    # Для подсчёта номера карточки в турнире
    for stat in player_stats:
        existing_stats[stat.user_id] = stat
        if stat.total_score > max_total:
            max_total = stat.total_score
        
        if stat.yellow_cards == 1:
            total_yellow += 1
        elif stat.yellow_cards >= 2:
            total_red += 1
        
        if stat.first_shot:
            first_killed_name = stat.user.player_nickname or stat.user.username
            
            # Подсчёт чёрных игроков в лучшем ходе
            if stat.first_shot and stat.role in ['civil', 'sheriff']:
                try:
                    numbers = [int(x) for x in stat.first_shot.split() if x.strip()]
                    seating_order = game.seating.get('order', [])
                    
                    black_count = 0
                    for seat_num in numbers:
                        if 1 <= seat_num <= len(seating_order):
                            target_player_id = seating_order[seat_num - 1]
                            target_stats = existing_stats.get(target_player_id)
                            if target_stats and target_stats.role in ['mafia', 'don']:
                                black_count += 1
                    
                    stat.lh_black_count = black_count
                except (ValueError, TypeError, IndexError):
                    stat.lh_black_count = 0
        
        total_score_sum += stat.total_score
    
    # Подсчёт номера карточки в турнире для каждого игрока
    for player_id, stat in existing_stats.items():
        if stat.yellow_cards > 0:
            # Получаем все игры турнира по порядку
            all_games = tournament.games.filter(
                winning_team__isnull=False,
                round_number__lte=game.round_number
            ).order_by('round_number')
            
            card_number = 0
            for g in all_games:
                try:
                    g_stats = PlayerGameStats.objects.get(
                        game=g,
                        tournament_player=stat.tournament_player
                    )
                    if g_stats.yellow_cards > 0:
                        card_number += g_stats.yellow_cards
                        if g.id == game.id:
                            break
                except PlayerGameStats.DoesNotExist:
                    pass
            
            stat.card_number_in_tournament = card_number
    
    avg_score = total_score_sum / len(player_stats) if player_stats else 0
    
    context = {
        'tournament': tournament,
        'game': game,
        'existing_stats': existing_stats,
        'max_total': max_total,
        'total_yellow': total_yellow,
        'total_red': total_red,
        'first_killed_name': first_killed_name,
        'avg_score': avg_score,
        'total_score_sum': total_score_sum,
    }
    return render(request, 'tournament/game_view.html', context)
