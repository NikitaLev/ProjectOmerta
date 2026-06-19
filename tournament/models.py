from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

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
    data_visible = models.BooleanField(
        default=True,
        verbose_name="Данные турнира видны всем"
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    completed_stats = models.JSONField(default=dict, blank=True, verbose_name="Статистика завершённого турнира")
    
    host_rating_delta = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.host.username})"
    
    def complete(self):
        """Завершить турнир и рассчитать статистику"""
        if self.status != 'active':
            return False
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        from .utils import calculate_final_places, calculate_tournament_statistics
        
        calculate_final_places(self)
        tournament_stats = calculate_tournament_statistics(self)
        
        self.completed_stats = tournament_stats
        self.save()

        return tournament_stats

class TournamentPlayer(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='players')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_participations')
    registered_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # ВРЕМЕННО: оставляем поля для обратной совместимости, но помечаем как deprecated
    total_main_score = models.FloatField(default=0.0)  # DEPRECATED: использовать метод get_total_main_score()
    total_bonus_score = models.FloatField(default=0.0)  # DEPRECATED: использовать метод get_total_bonus_score()
    total_ci = models.FloatField(default=0.0)  # DEPRECATED: использовать метод get_total_ci()
    final_place = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['tournament', 'user']
    
    def __str__(self):
        return f"{self.user.username} в {self.tournament.name}"
    
    # ========== НОВЫЕ СВОЙСТВА (вместо полей) ==========
    
    @property
    def all_stats(self):
        """Все статистики игрока в этом турнире"""
        return PlayerGameStats.objects.filter(tournament_player=self)
    
    def get_total_main_score(self):
        """Сумма основных баллов за все игры"""
        return self.all_stats.aggregate(total=models.Sum('main_score'))['total'] or 0.0
    
    def get_total_bonus_score(self):
        """Сумма бонусных баллов за все игры"""
        return self.all_stats.aggregate(total=models.Sum('bonus_score'))['total'] or 0.0
    
    def get_total_ci(self):
        """Сумма Ci за все игры"""
        return self.all_stats.aggregate(total=models.Sum('ci'))['total'] or 0.0
    
    def get_total_penalty(self):
        """Сумма штрафов за все игры"""
        return self.all_stats.aggregate(total=models.Sum('penalty_score'))['total'] or 0.0
    
    def get_total_score(self):
        """Общая сумма очков за турнир"""
        return self.all_stats.aggregate(total=models.Sum('total_score'))['total'] or 0.0
    
    def update_denormalized_fields(self):
        """Обновляет денормализованные поля (для обратной совместимости)"""
        self.total_main_score = self.get_total_main_score()
        self.total_bonus_score = self.get_total_bonus_score()
        self.total_ci = self.get_total_ci()
        self.save()

class Game(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='games')
    round_number = models.IntegerField(verbose_name="Номер игры")
    winning_team = models.CharField(max_length=20, choices=[('mafia', 'Мафия'), ('peace', 'Мирные')], blank=True, null=True)
    played_at = models.DateTimeField(auto_now_add=True)
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    place = models.IntegerField(verbose_name="Место в игре")
    
    # БАЗОВЫЕ ПОЛЯ
    main_score = models.FloatField(default=0.0, verbose_name="Основные баллы")
    bonus_score = models.FloatField(default=0.0, verbose_name="Бонусные баллы")
    manual_penalty = models.FloatField(default=0.0, verbose_name="Ручной штраф")
    yellow_cards = models.IntegerField(default=0, verbose_name="Жёлтые карточки")
    first_shot = models.CharField(max_length=50, blank=True, verbose_name="Первый отстрел")
    lh_bonus = models.FloatField(default=0.0, verbose_name="Бонус за лучший ход")
    
    # ВЫЧИСЛЯЕМЫЕ ПОЛЯ (заполняются при пересчёте)
    ci = models.FloatField(default=0.0, verbose_name="Ci коэффициент")
    yellow_penalty = models.FloatField(default=0.0, verbose_name="Штраф за ЖК")
    penalty_score = models.FloatField(default=0.0, verbose_name="Штрафные баллы (ручной + ЖК)")
    total_score = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['game', 'tournament_player']
    
    def calculate_penalty(self):
        """Пересчитывает penalty_score = manual_penalty + yellow_penalty"""
        self.penalty_score = self.manual_penalty + self.yellow_penalty
        return self.penalty_score
    
    def calculate_total(self):
        """Пересчитывает total_score = main + bonus + ci - penalty"""
        self.total_score = round(self.main_score + self.bonus_score + self.ci - self.penalty_score, 2)
        return self.total_score
    
    def save(self, *args, **kwargs):
        # Автоматически пересчитываем при сохранении
        self.calculate_penalty()
        self.calculate_total()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} - Игра {self.game.round_number} - {self.get_role_display()}"
    

# ========== МОДУЛЬ ПРАВИЛ ==========

class RuleTag(models.Model):
    """Тег для правил (для поиска и фильтрации)"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Название тега")
    color = models.CharField(max_length=7, default='#D4AF37', verbose_name="Цвет тега")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Тег правил"
        verbose_name_plural = "Теги правил"
    
    def __str__(self):
        return self.name
class RuleVersion(models.Model):
    """Версия правил"""
    version = models.CharField(max_length=20, verbose_name="Версия")  # "1.0", "2.0"
    published_date = models.DateTimeField(verbose_name="Дата публикации")
    is_active = models.BooleanField(default=False, verbose_name="Активна")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='rule_versions',
        verbose_name="Создал"
    )
    changelog = models.TextField(blank=True, verbose_name="Что нового")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    
    class Meta:
        ordering = ['-published_date']
        verbose_name = "Версия правил"
        verbose_name_plural = "Версии правил"
    
    def __str__(self):
        return f"Правила v{self.version} ({self.published_date.strftime('%d.%m.%Y')})"
    
    def save(self, *args, **kwargs):
        # Если эта версия становится активной, деактивируем все остальные
        if self.is_active:
            RuleVersion.objects.exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)


class RuleCategory(models.Model):
    """Раздел правил (1, 2, 3...)"""
    version = models.ForeignKey(
        RuleVersion, 
        on_delete=models.CASCADE, 
        related_name='categories',
        verbose_name="Версия"
    )
    number = models.CharField(max_length=10, verbose_name="Номер")  # "1", "2", "3"
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    tags = models.ManyToManyField(RuleTag, blank=True, related_name='rule_categories', verbose_name="Теги")
    
    class Meta:
        ordering = ['order']
        unique_together = ['version', 'number']
        verbose_name = "Раздел правил"
        verbose_name_plural = "Разделы правил"
    
    def __str__(self):
        return f"{self.number}. {self.title}"


class RuleSection(models.Model):
    """Подраздел правил (4.1, 4.2, 5.6...)"""
    category = models.ForeignKey(
        RuleCategory, 
        on_delete=models.CASCADE, 
        related_name='sections',
        verbose_name="Раздел"
    )
    number = models.CharField(max_length=10, verbose_name="Номер")  # "4.1", "4.2"
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    tags = models.ManyToManyField(RuleTag, blank=True, related_name='rule_sections', verbose_name="Теги")
    
    class Meta:
        ordering = ['order']
        unique_together = ['category', 'number']
        verbose_name = "Подраздел правил"
        verbose_name_plural = "Подразделы правил"
    
    def __str__(self):
        return f"{self.number} {self.title}"


class RuleItem(models.Model):
    """Конкретный пункт правил (4.1.1, 4.1.2...)"""
    section = models.ForeignKey(
        RuleSection, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Подраздел",
        null=True,
        blank=True  # теперь может быть без подраздела
    )
    category = models.ForeignKey(
        RuleCategory,
        on_delete=models.CASCADE,
        related_name='direct_items',
        verbose_name="Раздел (прямые пункты)",
        null=True,
        blank=True
    )
    number = models.CharField(max_length=10, verbose_name="Номер")  # "1.1", "1.2"
    content = models.TextField(verbose_name="Содержание")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    tags = models.ManyToManyField(RuleTag, blank=True, related_name='rule_items', verbose_name="Теги")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Пункт правил"
        verbose_name_plural = "Пункты правил"
    
    def __str__(self):
        return f"{self.number}"


class RuleVariable(models.Model):
    """Переменные правила (штрафы, коэффициенты)"""
    VARIABLE_TYPES = [
        ('penalty', 'Штраф'),
        ('bonus', 'Бонус'),
        ('coefficient', 'Коэффициент'),
        ('time', 'Время'),
        ('count', 'Количество'),
    ]
    
    version = models.ForeignKey(
        RuleVersion, 
        on_delete=models.CASCADE, 
        related_name='variables',
        verbose_name="Версия"
    )
    key = models.CharField(max_length=50, verbose_name="Ключ")
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    value = models.FloatField(verbose_name="Значение")
    var_type = models.CharField(max_length=20, choices=VARIABLE_TYPES, default='penalty', verbose_name="Тип")
    is_editable = models.BooleanField(default=True, verbose_name="Редактируемо")
    rule_reference = models.CharField(max_length=20, blank=True, verbose_name="Ссылка на пункт правил")
    
    class Meta:
        ordering = ['key']
        unique_together = ['version', 'key']
        verbose_name = "Переменная правил"
        verbose_name_plural = "Переменные правил"
    
    def __str__(self):
        return f"{self.key} = {self.value}"


class RuleHint(models.Model):
    """Подсказка для ведущего на основе правил"""
    rule_item = models.ForeignKey(
        RuleItem, 
        on_delete=models.CASCADE, 
        related_name='hints',
        verbose_name="Пункт правил"
    )
    text = models.TextField(verbose_name="Текст подсказки")
    priority = models.IntegerField(
        default=0, 
        choices=[(0, 'Низкий'), (1, 'Средний'), (2, 'Высокий')],
        verbose_name="Приоритет"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    
    class Meta:
        ordering = ['-priority']
        verbose_name = "Подсказка"
        verbose_name_plural = "Подсказки"
    
    def __str__(self):
        return f"Подсказка к {self.rule_item.number}"
    