from django import template
from tournament.models import RuleVariable
import re

from django.template.defaultfilters import stringfilter
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

@register.filter
@stringfilter
def render_variables(content, version):
    """
    Заменяет {{ ключ }} на значения переменных из базы данных.
    Поддерживает любое количество переменных в тексте.
    """
    if not content or not version:
        return content
    
    # Ищем все {{ ключ }} в тексте
    pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
    matches = re.findall(pattern, content)
    
    if not matches:
        return content
    
    result = content
    
    # Получаем все переменные для этой версии один раз (оптимизация)
    variables_dict = {var.key: var.value for var in RuleVariable.objects.filter(version=version)}
    
    for key in set(matches):  # set чтобы не обрабатывать повторно
        if key in variables_dict:
            # Заменяем все варианты написания
            result = result.replace(f'{{{{ {key} }}}}', str(variables_dict[key]))
            result = result.replace(f'{{{{{key}}}}}', str(variables_dict[key]))
        else:
            # Если переменная не найдена, можно подсветить её для отладки
            # Оставляем как есть или добавляем маркер
            pass
    
    return result


@register.filter
def get_variables_list(content, version):
    """
    Возвращает список ключей переменных, использованных в тексте.
    Проверяет, существуют ли переменные в данной версии.
    """
    if not content:
        return []
    
    pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
    matches = re.findall(pattern, content)
    
    if not matches:
        return []
    
    # Получаем существующие ключи переменных в этой версии
    existing_keys = set(RuleVariable.objects.filter(version=version).values_list('key', flat=True))
    
    # Возвращаем только те, которые существуют
    result = []
    for key in set(matches):
        if key in existing_keys:
            result.append(key)
    
    return result