from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import HostApplication
from .models import Tournament, TournamentPlayer, User, Game, PlayerGameStats  
from .forms import HostApplicationForm
from .forms import TournamentCreateForm
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .utils import generate_invitation_token
from django.contrib.auth.hashers import make_password
import secrets
from .utils import generate_seating
from django.conf import settings
from django.db import models

@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
        'role_display': dict(user.ROLE_CHOICES).get(user.role, 'Игрок'),
        'is_host': user.role == 'host' and user.is_approved_host,
    }
    return render(request, 'tournament/profile.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт для {username} успешно создан! Теперь вы можете войти.')
            return redirect('login')  # Перенаправляем на страницу входа
    else:
        form = UserRegistrationForm()
    
    return render(request, 'tournament/register.html', {'form': form})

def home(request):
    return render(request, 'tournament/home.html')

@login_required
def apply_host(request):
    # Проверяем, не подавал ли уже заявку
    existing_application = HostApplication.objects.filter(user=request.user).first()
    
    if existing_application:
        if existing_application.status == 'pending':
            messages.info(request, 'Вы уже подали заявку. Ожидайте рассмотрения.')
        elif existing_application.status == 'approved':
            messages.success(request, 'Вы уже являетесь ведущим!')
        elif existing_application.status == 'rejected':
            messages.warning(request, 'Ваша заявка была отклонена. Вы можете подать новую.')
            existing_application.delete()
    
    if request.method == 'POST':
        form = HostApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            messages.success(request, 'Заявка успешно отправлена! Ожидайте рассмотрения.')
            return redirect('profile')
    else:
        form = HostApplicationForm()
    
    return render(request, 'tournament/apply_host.html', {'form': form})

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

def activate_account(request, token):
    """Активация аккаунта по приглашению"""
    user = get_object_or_404(User, invitation_token=token, is_active=False)
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        errors = []
        
        # Проверка username
        if not username:
            errors.append('Имя пользователя обязательно для заполнения')
        elif User.objects.filter(username=username).exists():
            errors.append('Пользователь с таким именем уже существует')
        
        # Проверка email
        if not email:
            errors.append('Email обязателен для заполнения')
        elif User.objects.filter(email=email).exists():
            errors.append('Пользователь с таким email уже существует')
        
        # Проверка паролей
        if not password1 or not password2:
            errors.append('Пароль обязателен для заполнения')
        elif password1 != password2:
            errors.append('Пароли не совпадают')
        elif len(password1) < 8:
            errors.append('Пароль должен быть не менее 8 символов')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('activate_account', token=token)
        
        # Обновляем пользователя
        user.username = username
        user.email = email
        user.set_password(password1)
        user.is_active = True
        user.invitation_token = None
        user.invitation_created = None
        user.save()
        
        messages.success(request, 'Аккаунт активирован! Теперь вы можете войти.', extra_tags='activation')
        return redirect('login')
    
    return render(request, 'registration/activate.html', {'user': user})

@login_required
def delete_player(request, player_id):
    """Удаление созданного игрока"""
    player = get_object_or_404(User, id=player_id, created_by=request.user, is_active=False)
    
    if request.method == 'POST':
        player.delete()
        messages.success(request, f'Игрок {player.player_nickname} удален')
    
    return redirect('profile')


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
                PlayerGameStats.objects.create(
                    game=game,
                    tournament_player=tp,
                    user=tp.user,
                    role=role,
                    place=position,
                    main_score=main_score,
                    bonus_score=manual_bonus + lh_bonus,
                    yellow_cards=yellow_cards,
                    manual_penalty=manual_penalty,  # Сохраняем ручной штраф отдельно
                    penalty_score=0,  # Временное значение
                    lh_bonus=lh_bonus,
                    first_shot=best_shot if first_kill else '',
                    ci=0.0,
                )

            
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

def update_player_tournament_stats(tournament_player):
    """Обновляет общую статистику игрока в турнире"""
    # Получаем все статистики игрока в этом турнире
    all_stats = PlayerGameStats.objects.filter(
        tournament_player=tournament_player
    )
    
    # Суммируем все баллы
    total_main = sum(stat.main_score for stat in all_stats)
    total_bonus = sum(stat.bonus_score for stat in all_stats)
    total_ci = sum(stat.ci for stat in all_stats)
    
    # Обновляем запись
    tournament_player.total_main_score = total_main
    tournament_player.total_bonus_score = total_bonus
    tournament_player.total_ci = total_ci
    tournament_player.save()
    
    return tournament_player


def check_tournament_completion(tournament):
    """Проверяет, все ли игры турнира завершены"""
    total_games = tournament.games.count()
    completed_games = tournament.games.exclude(winning_team__isnull=True).count()
    
    if total_games == completed_games and total_games > 0:
        tournament.status = 'completed'
        tournament.end_date = timezone.now()
        tournament.save()
        
        # Рассчитываем итоговые места
        calculate_final_places(tournament)
        
        return True
    return False


def calculate_final_places(tournament):
    """Рассчитывает итоговые места игроков в турнире"""
    players = TournamentPlayer.objects.filter(
        tournament=tournament
    ).order_by('-total_main_score', '-total_bonus_score')
    
    current_place = 1
    for i, player in enumerate(players):
        if i > 0:
            prev_player = players[i-1]
            if (player.total_main_score == prev_player.total_main_score and 
                player.total_bonus_score == prev_player.total_bonus_score):
                player.final_place = prev_player.final_place
            else:
                player.final_place = i + 1
        else:
            player.final_place = 1
        
        player.save()

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
    
def recalculate_all_penalties(tournament, game):
    """Пересчитывает штрафы за ЖК для всех игр турнира после редактирования"""
    
    # Получаем все игры турнира по порядку
    all_games = tournament.games.filter(winning_team__isnull=False).order_by('round_number')
    
    for player in tournament.players.all():
        # Сбрасываем счётчик ЖК
        total_yellow = 0
        
        # Проходим по всем играм по порядку
        for g in all_games:
            try:
                stats = PlayerGameStats.objects.get(
                    game=g,
                    tournament_player=player
                )
                
                # Получаем ЖК в этой игре
                game_yellow = stats.yellow_cards
                
                # Рассчитываем штраф для этой игры
                if game_yellow >= 2:
                    # Красная карточка
                    yellow_penalty = 0.5
                elif game_yellow == 1:
                    # Обычная ЖК
                    total_yellow += 1
                    yellow_penalty = 0.15 * total_yellow
                else:
                    yellow_penalty = 0
                
                # Обновляем штраф (оставляем ручной штраф из penalty_score без изменений)
                # В penalty_score хранится только ручной штраф, не включая ЖК
                stats.penalty_score = stats.penalty_score  # оставляем как есть
                stats.save()
                
            except PlayerGameStats.DoesNotExist:
                pass

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