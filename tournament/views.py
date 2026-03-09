from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import HostApplication
from .models import Tournament, TournamentPlayer, User, Game
from .forms import HostApplicationForm
from .forms import TournamentCreateForm
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .utils import generate_invitation_token
from django.contrib.auth.hashers import make_password
import secrets
from .utils import generate_seating

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
    
    context = {
        'tournament': tournament,
        'can_edit': can_edit,
        'completed_games': completed_games,
        'pending_games': pending_games,
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
    
    context = {
        'tournament': tournament,
        'games': games,
        'completed_games': completed_games,
        'pending_games': pending_games,
        'is_host': request.user == tournament.host,
    }
    
    return render(request, 'tournament/tournament_games.html', context)