from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.db import models
from django.db.models import Sum, Max

from ..models import User, Tournament, TournamentPlayer, PlayerGameStats
from ..forms import ProfileEditForm, ProfilePasswordForm

@login_required
def profile(request):
    user = request.user
    
    # Турниры где участвует игроком
    player_tournaments = Tournament.objects.filter(
        players__user=user
    ).distinct().order_by('-created_at')
    
    player_stats = {
        'total': player_tournaments.count(),
        'active': player_tournaments.filter(status='active').count(),
        'completed': player_tournaments.filter(status='completed').count(),
    }
    
    # Статистика по каждому турниру для игрока
    tournament_stats = {}
    for tournament in player_tournaments:
        try:
            tp = TournamentPlayer.objects.get(tournament=tournament, user=user)
            total_score = PlayerGameStats.objects.filter(tournament_player=tp).aggregate(total=models.Sum('total_score'))['total'] or 0
            tournament_stats[tournament.id] = {
                'total_score': round(total_score, 2),
                'games_played': PlayerGameStats.objects.filter(tournament_player=tp).count(),
            }
        except TournamentPlayer.DoesNotExist:
            tournament_stats[tournament.id] = {'total_score': 0, 'games_played': 0}
    
    # Сериализация турниров где игрок участвует
    player_tournaments_list = []
    for tournament in player_tournaments[:5]:
            # Получаем место игрока в этом турнире
        final_place = None
        try:
            tp = TournamentPlayer.objects.get(tournament=tournament, user=user)
            final_place = tp.final_place
        except TournamentPlayer.DoesNotExist:
            pass
        player_tournaments_list.append({
            'id': tournament.id,
            'name': tournament.name,
            'status': tournament.status,
            'status_display': tournament.get_status_display(),
            'start_date': tournament.start_date.strftime('%d.%m.%Y') if tournament.start_date else None,
            'host_username': tournament.host.username,
            'final_place': final_place,
        })
    
    # Проведённые турниры (для ведущего)
    hosted_tournaments_data = []
    hosted_tournaments_list = []
    hosted_stats = None
    
    if user.role == 'host' and user.is_approved_host:
        hosted_tournaments = Tournament.objects.filter(host=user).order_by('-created_at')
        hosted_stats = {
            'total': hosted_tournaments.count(),
            'active': hosted_tournaments.filter(status='active').count(),
            'completed': hosted_tournaments.filter(status='completed').count(),
            'draft': hosted_tournaments.filter(status='draft').count(),
        }
        
        for tournament in hosted_tournaments[:5]:
            completed_games = tournament.games.exclude(winning_team__isnull=True).count()
            hosted_tournaments_data.append({
                'id': tournament.id,
                'name': tournament.name,
                'status': tournament.status,
                'status_display': tournament.get_status_display(),
                'start_date': tournament.start_date,
                'host_username': tournament.host.username,
                'players_count': tournament.players.count(),
                'max_players': tournament.max_players,
                'total_games': tournament.games.count(),
                'completed_games': completed_games,
            })
            
            hosted_tournaments_list.append({
                'id': tournament.id,
                'name': tournament.name,
                'status': tournament.status,
                'status_display': tournament.get_status_display(),
                'start_date': tournament.start_date.strftime('%d.%m.%Y') if tournament.start_date else None,
                'total_games': tournament.games.count(),
                'completed_games': completed_games,
                'players_count': tournament.players.count(),
                'max_players': tournament.max_players,
            })
    
    # Созданные игроки (для ведущего)
    created_players_data = []
    created_players_stats = {'active': 0, 'pending': 0, 'total': 0}
    
    if user.role == 'host' and user.is_approved_host:
        created_players = user.created_players.all().order_by('is_active', '-invitation_created')
        created_players_stats['total'] = created_players.count()
        created_players_stats['active'] = created_players.filter(is_active=True).count()
        created_players_stats['pending'] = created_players.filter(is_active=False).count()
        
        for player in created_players:
            created_players_data.append({
                'id': player.id,
                'nickname': player.player_nickname,
                'is_active': player.is_active,
                'created_at': player.invitation_created.strftime('%d.%m.%Y') if player.invitation_created else None,
                'invitation_token': player.invitation_token if not player.is_active else None,
            })
    context = {
        'user': user,
        'role_display': dict(user.ROLE_CHOICES).get(user.role, 'Игрок'),
        'is_host': user.role == 'host' and user.is_approved_host,
        'player_tournaments': player_tournaments[:5],
        'player_tournaments_json': player_tournaments_list,
        'tournament_stats': tournament_stats,
        'hosted_tournaments': hosted_tournaments_data,
        'hosted_tournaments_json': hosted_tournaments_list,
        'hosted_stats': hosted_stats,
        'created_players_data': created_players_data,
        'created_players_stats': created_players_stats,
    }
    return render(request, 'tournament/profile.html', context)


@login_required
def profile_edit(request):
    """Редактирование профиля (email, никнейм, пароль) - AJAX поддержка"""
    
    if request.method == 'POST':
        # AJAX запрос
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            
            # Смена пароля
            if 'change_password' in request.POST:
                old_password = request.POST.get('old_password', '')
                new_password1 = request.POST.get('new_password1', '')
                new_password2 = request.POST.get('new_password2', '')
                
                errors = []
                
                # Проверка текущего пароля
                if not request.user.check_password(old_password):
                    errors.append('❌ Неверный текущий пароль')
                
                # Проверка нового пароля
                if not new_password1:
                    errors.append('❌ Новый пароль не может быть пустым')
                elif len(new_password1) < 8:
                    errors.append('❌ Пароль должен содержать минимум 8 символов')
                elif new_password1 in ['12345678', 'qwerty123', 'password123']:
                    errors.append('⚠️ Слишком простой пароль')
                elif new_password1 != new_password2:
                    errors.append('❌ Пароли не совпадают')
                
                if errors:
                    return JsonResponse({'success': False, 'errors': errors})
                
                # Смена пароля
                request.user.set_password(new_password1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                
                return JsonResponse({
                    'success': True, 
                    'message': '✅ Пароль успешно изменён!'
                })
            
            # Редактирование профиля
            else:
                email = request.POST.get('email', '').strip()
                player_nickname = request.POST.get('player_nickname', '').strip()
                
                errors = []
                
                # Валидация email
                if not email:
                    errors.append('❌ Email не может быть пустым')
                elif '@' not in email or '.' not in email.split('@')[-1]:
                    errors.append('❌ Введите корректный email адрес')
                elif User.objects.exclude(id=request.user.id).filter(email=email).exists():
                    errors.append(f'❌ Пользователь с email "{email}" уже существует')
                
                if errors:
                    return JsonResponse({'success': False, 'errors': errors})
                
                # Обновление
                request.user.email = email
                request.user.player_nickname = player_nickname if player_nickname else ''
                request.user.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '✅ Профиль успешно обновлён!'
                })
        
        # Обычный POST (без AJAX) — для обратной совместимости
        if 'change_password' in request.POST:
            password_form = ProfilePasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, '✅ Пароль успешно изменён!')
                return redirect('profile_edit')
            else:
                for error in password_form.errors.values():
                    messages.error(request, error)
                return redirect('profile_edit')
        else:
            profile_form = ProfileEditForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, '✅ Профиль успешно обновлён!')
                return redirect('profile_edit')
            else:
                for error in profile_form.errors.values():
                    messages.error(request, error)
                return redirect('profile_edit')
    
    # GET запрос
    return render(request, 'tournament/profile_edit.html', {
        'user': request.user,
    })



@login_required
def player_stats_api(request):
    """API для получения расширенной статистики игрока"""
    user = request.user

    
    tournament_players = TournamentPlayer.objects.filter(user=user)
    all_stats = PlayerGameStats.objects.filter(user=user, game__winning_team__isnull=False)
    
    total_games = all_stats.count()
    if total_games == 0:
        return JsonResponse({'has_stats': False, 'message': 'У вас пока нет сыгранных игр'})
    
    tournament_players = TournamentPlayer.objects.filter(user=user)
    all_stats = PlayerGameStats.objects.filter(user=user, game__winning_team__isnull=False)
    
    total_games = all_stats.count()
    if total_games == 0:
        return JsonResponse({'has_stats': False, 'message': 'У вас пока нет сыгранных игр'})
    
    # --- ОБЩАЯ СТАТИСТИКА (сырые числа) ---
    total_score = all_stats.aggregate(total=Sum('total_score'))['total'] or 0
    total_main = all_stats.aggregate(total=Sum('main_score'))['total'] or 0
    total_bonus = all_stats.aggregate(total=Sum('bonus_score'))['total'] or 0
    total_penalty = all_stats.aggregate(total=Sum('penalty_score'))['total'] or 0
    total_ci = all_stats.aggregate(total=Sum('ci'))['total'] or 0
    
    # Победы
    wins = 0
    for stat in all_stats:
        if (stat.game.winning_team == 'mafia' and stat.role in ['mafia', 'don']) or \
           (stat.game.winning_team == 'peace' and stat.role in ['civil', 'sheriff']):
            wins += 1
    
    # Первые убийства
    first_kills = all_stats.filter(first_shot__isnull=False).exclude(first_shot='').count()
    
    # Карточки
    yellow_cards = all_stats.filter(yellow_cards=1).count()
    red_cards = all_stats.filter(yellow_cards__gte=2).count()
    
    # --- СРЕДНИЕ ПОКАЗАТЕЛИ (на игру) ---
    avg_score = total_score / total_games if total_games > 0 else 0
    winrate = (wins / total_games * 100) if total_games > 0 else 0
    avg_bonus = total_bonus / total_games if total_games > 0 else 0
    avg_ci = total_ci / total_games if total_games > 0 else 0
    avg_penalty = total_penalty / total_games if total_games > 0 else 0
    first_kill_rate = (first_kills / total_games * 100) if total_games > 0 else 0
    
    # --- ЛУЧШИЙ ТУРНИР ---
    tournament_scores = []
    for tp in tournament_players:
        total = tp.get_total_score() 
        tournament_scores.append({
            'tournament_id': tp.tournament.id,
            'tournament_name': tp.tournament.name,
            'score': round(total, 2),
            'place': tp.final_place
        })
    tournament_scores.sort(key=lambda x: x['score'], reverse=True)
    best_tournament = tournament_scores[0] if tournament_scores else None
    
    # --- СТАТИСТИКА ПО РОЛЯМ ---
    roles_stats = {}
    for role, role_name in [('don', 'Дон'), ('mafia', 'Мафия'), ('sheriff', 'Шериф'), ('civil', 'Мирный')]:
        role_stats = all_stats.filter(role=role)
        role_count = role_stats.count()
        if role_count > 0:
            role_total_score = role_stats.aggregate(total=Sum('total_score'))['total'] or 0
            role_wins = 0
            for stat in role_stats:
                if (stat.game.winning_team == 'mafia' and stat.role in ['mafia', 'don']) or \
                   (stat.game.winning_team == 'peace' and stat.role in ['civil', 'sheriff']):
                    role_wins += 1
            roles_stats[role] = {
                'name': role_name,
                'count': role_count,
                'total_score': round(role_total_score, 2),
                'avg_score': round(role_total_score / role_count, 2),
                'wins': role_wins,
                'winrate': round(role_wins / role_count * 100, 1),
                'icon': get_role_icon(role)
            }
    
    # --- РАСПРЕДЕЛЕНИЕ МЕСТ ---
    places = []
    for tp in tournament_players:
        if tp.final_place:
            places.append(tp.final_place)
    place_distribution = {}
    for place in places:
        place_distribution[place] = place_distribution.get(place, 0) + 1
    best_place = min(places) if places else None
    
    # --- РЕКОРДЫ ---
    best_lh_bonus = all_stats.aggregate(max=Max('lh_bonus'))['max'] or 0
    
    # Лучшая серия побед (подряд)
    best_streak = 0
    current_streak = 0
    # Сортируем игры по дате
    sorted_stats = all_stats.select_related('game').order_by('game__played_at')
    for stat in sorted_stats:
        is_win = (stat.game.winning_team == 'mafia' and stat.role in ['mafia', 'don']) or \
                 (stat.game.winning_team == 'peace' and stat.role in ['civil', 'sheriff'])
        if is_win:
            current_streak += 1
            best_streak = max(best_streak, current_streak)
        else:
            current_streak = 0
    
    # Самая результативная роль (по среднему баллу)
    best_role_avg = None
    best_role_name = None
    for role, data in roles_stats.items():
        if data['count'] >= 3:  # минимум 3 игры для статистики
            if best_role_avg is None or data['avg_score'] > best_role_avg:
                best_role_avg = data['avg_score']
                best_role_name = data['name']
    
    data = {
        'has_stats': True,
        # Общая статистика
        'total_games': total_games,
        'total_score': round(total_score, 2),
        'wins': wins,
        'first_kills': first_kills,
        'yellow_cards': yellow_cards,
        'red_cards': red_cards,
        'total_main': round(total_main, 2),
        'total_bonus': round(total_bonus, 2),
        'total_penalty': round(total_penalty, 2),
        'total_ci': round(total_ci, 2),
        # Средние показатели
        'avg_score': round(avg_score, 2),
        'winrate': round(winrate, 1),
        'avg_bonus': round(avg_bonus, 2),
        'avg_ci': round(avg_ci, 2),
        'avg_penalty': round(avg_penalty, 2),
        'first_kill_rate': round(first_kill_rate, 1),
        # Рекорды
        'best_lh_bonus': best_lh_bonus,
        'best_streak': best_streak,
        'best_role': best_role_name,
        'best_tournament': best_tournament,
        'best_place': best_place,
        # Остальное
        'tournaments_count': tournament_players.count(),
        'roles': roles_stats,
        'place_distribution': place_distribution,
    }
    
    return JsonResponse(data)


def get_role_icon(role):
    icons = {
        'don': 'fas fa-crown',
        'mafia': 'fas fa-skull',
        'sheriff': 'fas fa-star',
        'civil': 'fas fa-hand-peace'
    }
    return icons.get(role, 'fas fa-user')
