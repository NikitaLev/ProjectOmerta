from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_role_icon(role):
    """Возвращает иконку для роли"""
    icons = {
        'don': '<i class="ph-fill ph-crown-simple" style="color: #d4af37;"></i>',
        'sheriff': '<i class="mdi mdi-police-badge" style="color: #fbbf24;"></i>',
        'mafia': '<i class="bi bi-hand-thumbs-down-fill" style="color: #6b21a5;"></i>',
        'civil': '<i class="bi bi-hand-thumbs-up-fill" style="color: #ef4444;"></i>',
    }
    return icons.get(role, '')

@register.filter
def get_role_name(role):
    """Возвращает название роли на русском"""
    names = {
        'don': 'Дон',
        'sheriff': 'Шериф',
        'mafia': 'Мафия',
        'civil': 'Мирный',
    }
    return names.get(role, role)