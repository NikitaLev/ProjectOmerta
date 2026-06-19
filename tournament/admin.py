from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, HostApplication, Tournament, TournamentPlayer, Game, PlayerGameStats
from django.utils.timezone import now

from django.contrib import admin
from .models import (
    RuleVersion, RuleCategory, RuleSection, RuleItem, 
    RuleVariable, RuleHint
)


# Расширенный админ для пользователей
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_approved_host', 'player_nickname', 'games_played', 'tournaments_hosted')
    list_filter = ('role', 'is_approved_host', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Роли и статусы', {
            'fields': ('role', 'is_approved_host', 'player_nickname', 'player_rating', 'games_played',
                      'host_rating', 'tournaments_hosted', 'approved_by', 'approved_at')
        }),
    )

# Админ для заявок
@admin.register(HostApplication)
class HostApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'full_name', 'email')
    readonly_fields = ('created_at',)
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        for application in queryset:
            application.status = 'approved'
            application.reviewed_at = now()
            application.reviewed_by = request.user
            application.save()
            
            # Одобряем пользователя как ведущего
            user = application.user
            user.is_approved_host = True
            user.role = 'host'
            user.approved_by = request.user
            user.approved_at = now()
            user.save()
        self.message_user(request, f"{queryset.count()} заявок одобрено")
    approve_applications.short_description = "Одобрить выбранные заявки"
    
    def reject_applications(self, request, queryset):
        queryset.update(status='rejected', reviewed_at=now(), reviewed_by=request.user)
        self.message_user(request, f"{queryset.count()} заявок отклонено")
    reject_applications.short_description = "Отклонить выбранные заявки"

# Админ для турниров
@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'status', 'start_date', 'current_round', 'max_players')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'host__username')
    readonly_fields = ('created_at',)

# Админ для игроков в турнире
@admin.register(TournamentPlayer)
class TournamentPlayerAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'user', 'total_main_score', 'total_bonus_score', 'final_place')
    list_filter = ('tournament__status',)

# Админ для игр
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'round_number', 'winning_team', 'played_at')
    list_filter = ('winning_team', 'tournament__status')

# Админ для статистики
@admin.register(PlayerGameStats)
class PlayerGameStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'role', 'place', 'total_score', 'ci')
    list_filter = ('role', 'game__tournament')
    search_fields = ('user__username',)

# ========== АДМИНКА ДЛЯ ПРАВИЛ ==========

@admin.register(RuleVersion)
class RuleVersionAdmin(admin.ModelAdmin):
    list_display = ['version', 'published_date', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'published_date']
    search_fields = ['version', 'changelog']
    readonly_fields = ['created_at']
    fields = ['version', 'published_date', 'is_active', 'created_by', 'changelog', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RuleCategory)
class RuleCategoryAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'version', 'order']
    list_filter = ['version']
    search_fields = ['number', 'title']
    ordering = ['version', 'order']


@admin.register(RuleSection)
class RuleSectionAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'category', 'order']
    list_filter = ['category__version', 'category']
    search_fields = ['number', 'title']
    ordering = ['category', 'order']


@admin.register(RuleItem)
class RuleItemAdmin(admin.ModelAdmin):
    list_display = ['number', 'section', 'content_preview', 'order']
    list_filter = ['section__category__version', 'section__category', 'section']
    search_fields = ['number', 'content']
    ordering = ['section', 'order']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Содержание (предпросмотр)'


@admin.register(RuleVariable)
class RuleVariableAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'value', 'var_type', 'version', 'rule_reference']
    list_filter = ['var_type', 'version']
    search_fields = ['key', 'name', 'description']
    ordering = ['version', 'key']


@admin.register(RuleHint)
class RuleHintAdmin(admin.ModelAdmin):
    list_display = ['rule_item', 'text_preview', 'priority', 'created_at']
    list_filter = ['priority', 'rule_item__section__category__version']
    search_fields = ['text']
    ordering = ['-priority', 'rule_item']
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Текст (предпросмотр)'