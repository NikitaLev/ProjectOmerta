from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

@login_required
def beta_game(request):
    """BETA страница для ведения игры"""
    # Проверяем права (только ведущие и админы)
    if request.user.role != 'host' or not request.user.is_approved_host:
        if request.user.role != 'admin':
            messages.error(request, 'Доступ только для ведущих')
            return redirect('home')
    
    return render(request, 'tournament/beta_game.html')

@csrf_exempt
@login_required
def beta_start_game(request):
    """API для старта игры (сохраняет сессию)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        players = data.get('players', [])
        
        # Сохраняем в сессию
        request.session['beta_game'] = {
            'players': players,
            'started_at': timezone.now().isoformat(),
            'logs': [],  # Сюда будем записывать все действия
            'current_phase': 'day',  # day/night
            'round': 1,
        }
        
        return JsonResponse({'success': True, 'players': players})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
def beta_vote(request):
    """Страница голосования"""
    return render(request, 'tournament/beta_vote.html')

@login_required
def beta_game(request):
    if request.user.role != 'host' or not request.user.is_approved_host:
        if request.user.role != 'admin':
            messages.error(request, 'Доступ только для ведущих')
            return redirect('home')
    return render(request, 'tournament/beta_game.html')

def beta_day(request, round_num):
    return render(request, 'tournament/beta_day.html', {'round_num': round_num})

def beta_night(request, round_num):
    """Ночная фаза"""
    return render(request, 'tournament/beta_night.html', {'round_num': round_num})
