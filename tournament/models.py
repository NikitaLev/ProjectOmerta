from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('player', 'Игрок'),
        ('host', 'Ведущий'),
        ('admin', 'Администратор'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    is_approved_host = models.BooleanField(default=False)
    player_nickname = models.CharField(max_length=100, blank=True)
    player_rating = models.FloatField(default=0.0)
    games_played = models.IntegerField(default=0)
    host_rating = models.FloatField(default=0.0)
    tournaments_hosted = models.IntegerField(default=0)
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_hosts')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='created_players'
    )
    invitation_token = models.CharField(max_length=100, blank=True, null=True)
    invitation_created = models.DateTimeField(null=True, blank=True)

    @property
    def created_players(self):
        return User.objects.filter(created_by=self)
    
    @property
    def active(self):
        return self.filter(is_active=True)
    
    @property
    def pending(self):
        return self.filter(is_active=False)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
class HostApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='host_applications')
    full_name = models.CharField(max_length=200, verbose_name="Полное имя")
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    experience = models.TextField(verbose_name="Опыт ведения турниров")
    reason = models.TextField(verbose_name="Почему хотите стать ведущим?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_applications')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заявка от {self.user.username} - {self.get_status_display()}"
    
class Tournament(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending', 'Ожидает начала'),
        ('active', 'Активен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    # Добавляем выбор правил
    RULES_CHOICES = [
        ('BMF', 'БМФ'),
        ('KSL', 'КСЛ'),
    ]

    name = models.CharField(max_length=200, verbose_name="Название турнира")
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournaments')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    max_players = models.IntegerField(default=10)
    current_round = models.IntegerField(default=1)
    total_games = models.IntegerField(
        default=10, 
        verbose_name="Количество игр",
        help_text="Сколько игр будет сыграно в турнире"
    )
    rules = models.CharField(
        max_length=3,
        choices=RULES_CHOICES,
        default='BMF',
        verbose_name='Правила турнира'
    )
    
    # Статистика ведущего по этому турниру
    host_rating_delta = models.FloatField(default=0.0)  # Изменение рейтинга ведущего
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.host.username})"

class TournamentPlayer(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='players')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_participations')
    registered_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Итоговая статистика по турниру
    total_main_score = models.FloatField(default=0.0)
    total_bonus_score = models.FloatField(default=0.0)
    total_ci = models.FloatField(default=0.0)
    final_place = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['tournament', 'user']
    
    def __str__(self):
        return f"{self.user.username} в {self.tournament.name}"

class Game(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='games')
    round_number = models.IntegerField(verbose_name="Номер игры")
    winning_team = models.CharField(max_length=20, choices=[('mafia', 'Мафия'), ('peace', 'Мирные')], blank=True, null=True)
    played_at = models.DateTimeField(auto_now_add=True)
    
    # Новое поле для хранения рассадки
    seating = models.JSONField(default=dict, blank=True, verbose_name="Рассадка")
    
    class Meta:
        ordering = ['round_number']
        unique_together = ['tournament', 'round_number']
    
    def __str__(self):
        return f"{self.tournament.name} - Игра {self.round_number}"
    
class PlayerGameStats(models.Model):
    ROLE_CHOICES = [
        ('don', 'Дон'),
        ('sheriff', 'Шериф'),
        ('mafia', 'Мафия'),
        ('civil', 'Мирный'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='player_stats')
    tournament_player = models.ForeignKey(TournamentPlayer, on_delete=models.CASCADE, related_name='game_stats')
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Для быстрого доступа
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    place = models.IntegerField(verbose_name="Место в игре")
    main_score = models.FloatField(default=0.0, verbose_name="Основные баллы")
    bonus_score = models.FloatField(default=0.0, verbose_name="Бонусные баллы")
    penalty_score = models.FloatField(default=0.0, verbose_name="Штрафные баллы")
    first_shot = models.CharField(max_length=50, blank=True, verbose_name="Первый отстрел")
    
    # Вычисляемые поля
    total_score = models.FloatField(default=0.0)  # main + bonus - penalty
    ci = models.FloatField(default=0.0, verbose_name="Ci коэффициент")
    
    class Meta:
        unique_together = ['game', 'tournament_player']
    
    def save(self, *args, **kwargs):
        self.total_score = self.main_score + self.bonus_score - self.penalty_score
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} - Игра {self.game.round_number} - {self.get_role_display()}"