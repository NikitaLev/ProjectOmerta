from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу"""
    if dictionary is None:
        return None
    return dictionary.get(key, {}) if dictionary else {}

@register.filter
def get_role_icon(role):
    """Возвращает иконку для роли"""
    icons = {
        'don': '<span class="role-icon role-icon-don role-icon-md"></span>',
        'mafia': '<span class="role-icon role-icon-mafia role-icon-md"></span>',
        'sheriff': '<span class="role-icon role-icon-sheriff role-icon-md"></span>',
        'civil': '<span class="role-icon role-icon-civil role-icon-md"></span>'
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