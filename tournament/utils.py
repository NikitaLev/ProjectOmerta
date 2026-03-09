import secrets
from django.utils import timezone
import random
from collections import defaultdict
import math

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