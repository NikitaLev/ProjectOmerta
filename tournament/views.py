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
from .utils import generate_invitation_token, generate_seating, calculate_final_places, calculate_tournament_statistics
from django.db.models import Count, Sum, Max
from .forms import ProfileEditForm, ProfilePasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

import logging
logger = logging.getLogger('tournament')


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

# tournament/views.py

# tournament/views.py

from django.views.decorators.csrf import csrf_exempt
import json
