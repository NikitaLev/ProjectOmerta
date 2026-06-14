from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.contrib.auth import login as auth_login, logout as auth_logout

from ..models import User, TournamentPlayer, PlayerGameStats
from ..forms import UserRegistrationForm
import logging

logger = logging.getLogger('tournament')

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

def activate_account(request, token):
    """Активация аккаунта по приглашению"""
    user = get_object_or_404(User, invitation_token=token, is_active=False)
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        errors = []
        
        # Валидация username
        if not username:
            errors.append('❌ Имя пользователя обязательно для заполнения')
        elif len(username) < 3:
            errors.append(f'❌ Имя пользователя должно содержать минимум 3 символа. Сейчас: {len(username)}')
        elif len(username) > 30:
            errors.append(f'❌ Имя пользователя не может превышать 30 символов. Сейчас: {len(username)}')
        elif not username.replace('_', '').isalnum():
            errors.append('❌ Имя пользователя может содержать только латинские буквы, цифры и знак подчеркивания (_)')
        elif User.objects.filter(username=username).exists():
            errors.append(f'❌ Имя пользователя "{username}" уже занято. Придумайте другое')
        
        # Валидация email
        if not email:
            errors.append('❌ Email обязателен для заполнения')
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors.append('❌ Введите корректный email адрес. Пример: username@domain.ru')
        elif User.objects.filter(email=email).exists():
            errors.append(f'❌ Пользователь с email "{email}" уже существует')
        
        # Валидация пароля
        if not password1:
            errors.append('❌ Пароль обязателен для заполнения')
        elif len(password1) < 8:
            errors.append(f'❌ Пароль должен содержать минимум 8 символов. Сейчас: {len(password1)}')
        elif password1 in ['12345678', 'qwerty123', 'password123', '11111111']:
            errors.append('⚠️ Слишком простой пароль. Используйте комбинацию букв и цифр')
        elif password1 != password2:
            errors.append('❌ Пароли не совпадают')
        
        if errors:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            
            for error in errors:
                messages.error(request, error, extra_tags='activation')
            return redirect('activate_account', token=token)
        
        # Всё ок — активируем
        user.username = username
        user.email = email
        user.set_password(password1)
        user.is_active = True
        user.invitation_token = None
        user.invitation_created = None
        user.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': '/login/'})
        
        messages.success(request, f'✅ Аккаунт "{username}" успешно активирован!', extra_tags='activation')
        return redirect('login')
    
    return render(request, 'registration/activate.html', {'user': user})


def log_tournament_details(tournament, user):
    """Подробное логирование статистики турнира для игрока"""
    logger.info(f"=== ПОДРОБНАЯ СТАТИСТИКА ТУРНИРА: {tournament.name} (ID: {tournament.id}) ===")
    logger.info(f"Статус турнира: {tournament.status}")
    logger.info(f"Всего игр в турнире: {tournament.games.count()}")
    logger.info(f"Завершённых игр: {tournament.games.exclude(winning_team__isnull=True).count()}")
    
    # Все игроки турнира с их очками
    logger.info("--- ВСЕ ИГРОКИ ТУРНИРА ---")
    all_players = TournamentPlayer.objects.filter(tournament=tournament).select_related('user')
    for tp in all_players:
        total = tp.get_total_score() 
        logger.info(f"  {tp.user.username} | main: {tp.get_total_main_score()} | bonus: {tp.total_bonus_score} | ci: {tp.total_ci} | ИТОГО: {total} | место: {tp.final_place}")
    
    # Конкретный игрок
    try:
        tp_user = TournamentPlayer.objects.get(tournament=tournament, user=user)
        logger.info(f"--- ДАННЫЕ ИГРОКА {user.username} ---")
        logger.info(f"  total_main_score: {tp_user.total_main_score}")
        logger.info(f"  total_bonus_score: {tp_user.total_bonus_score}")
        logger.info(f"  total_ci: {tp_user.total_ci}")
        logger.info(f"  ИТОГО: {tp_user.total_main_score + tp_user.total_bonus_score + tp_user.total_ci}")
        logger.info(f"  final_place: {tp_user.final_place}")
        
        # Детали по играм
        logger.info("--- ИГРЫ ИГРОКА ---")
        all_stats = PlayerGameStats.objects.filter(
            tournament_player=tp_user,
            game__winning_team__isnull=False
        ).order_by('game__round_number').select_related('game')
        
        for stat in all_stats:
            logger.info(f"  Игра {stat.game.round_number} | роль: {stat.role} | main: {stat.main_score} | bonus: {stat.bonus_score} | ci: {stat.ci} | penalty: {stat.penalty_score} | total: {stat.total_score}")
        
        # Первые убийства
        first_kills = all_stats.filter(first_shot__isnull=False).exclude(first_shot='')
        logger.info(f"--- ПЕРВЫЕ УБИЙСТВА ({first_kills.count()}) ---")
        for stat in first_kills:
            logger.info(f"  Игра {stat.game.round_number}: {stat.first_shot} | бонус за ЛХ: {stat.lh_bonus}")
        
    except TournamentPlayer.DoesNotExist:
        logger.info(f"Игрок {user.username} не найден в турнире")
    
    logger.info("=== КОНЕЦ ПОДРОБНОЙ СТАТИСТИКИ ===")


def custom_login(request):
    """Своя страница входа"""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def custom_logout(request):
    """Свой выход"""
    auth_logout(request)
    return redirect('home')


def custom_password_reset(request):
    """Своя страница запроса сброса пароля"""
    
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            reset_url = f'/recover-password/confirm/{uid}/{token}/'
            full_url = request.build_absolute_uri(reset_url)
            
            subject = 'Восстановление пароля на Project Omerta'
            message = f'''Здравствуйте!

Вы получили это письмо, потому что запросили восстановление пароля.

Перейдите по ссылке, чтобы установить новый пароль:
{full_url}

Если вы не запрашивали восстановление, просто проигнорируйте это письмо.

---
С уважением, команда Project Omerta'''
            
            send_mail(subject, message, 'noreply@omerta.com', [email])
            
        except User.DoesNotExist:
            pass
        
        return redirect('password_reset_done')
    
    return render(request, 'registration/password_reset.html')

def custom_password_reset_done(request):
    """Страница после отправки письма"""
    
    response = render(request, 'registration/password_reset_done.html')
    return response

def custom_password_reset_confirm(request, uidb64, token):
    """Страница установки нового пароля"""
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception as e:
        logger.error(f"Ошибка декодирования/поиска пользователя: {e}")
        user = None
    
    if user and default_token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            password1 = request.POST.get('new_password1')
            password2 = request.POST.get('new_password2')
            
            if password1 and password1 == password2 and len(password1) >= 8:
                user.set_password(password1)
                user.save()
                return redirect('password_reset_complete')
            else:
                error = 'Пароли не совпадают или слишком короткий (минимум 8 символов)'
                logger.warning(f"Ошибка валидации пароля: {error}")
                return render(request, 'registration/password_reset_confirm.html', {
                    'validlink': True,
                    'error': error,
                })
        else:
            return render(request, 'registration/password_reset_confirm.html', {'validlink': True})
    else:
        logger.warning("Токен НЕ валиден или пользователь не найден")
        return render(request, 'registration/password_reset_confirm.html', {'validlink': False})


def custom_password_reset_complete(request):
    """Страница успешной смены пароля"""
    
    return render(request, 'registration/password_reset_complete.html')