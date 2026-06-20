from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
import json

from ..models import (
    RuleVersion, RuleCategory, RuleSection, RuleItem, 
    RuleVariable, RuleHint, RuleTag, User
)

def is_admin(user):
    """Проверка, является ли пользователь администратором"""
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def rules_admin(request):
    """Главная страница управления правилами"""
    from ..models import RuleTag
    
    versions = RuleVersion.objects.all().order_by('-published_date')
    active_version = RuleVersion.objects.filter(is_active=True).first()
    
    categories = []
    if active_version:
        categories = RuleCategory.objects.filter(
            version=active_version
        ).prefetch_related(
            'sections__items', 
            'direct_items',
            'direct_items__tags',
            'tags'
        ).order_by('order')
    
    variables = []
    if active_version:
        variables = RuleVariable.objects.filter(version=active_version).order_by('key')
    
    all_tags = RuleTag.objects.all().order_by('name')
    
    context = {
        'versions': versions,
        'active_version': active_version,
        'categories': categories,
        'variables': variables,
        'all_tags': all_tags,
    }
    return render(request, 'tournament/rules/admin.html', context)


@login_required
@user_passes_test(is_admin)
def rules_create_version(request):
    """Создание новой версии правил"""
    if request.method == 'POST':
        version = request.POST.get('version')
        published_date = request.POST.get('published_date')
        changelog = request.POST.get('changelog', '')
        copy_from = request.POST.get('copy_from')
        
        if not version or not published_date:
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('rules_admin')
        
        # Проверяем, что такой версии нет
        if RuleVersion.objects.filter(version=version).exists():
            messages.error(request, f'Версия {version} уже существует')
            return redirect('rules_admin')
        
        from datetime import datetime
        published_date = datetime.strptime(published_date, '%Y-%m-%d')
        
        new_version = RuleVersion.objects.create(
            version=version,
            published_date=published_date,
            is_active=False,
            created_by=request.user,
            changelog=changelog
        )
        
        # Если нужно скопировать из другой версии
        if copy_from:
            source_version = get_object_or_404(RuleVersion, id=copy_from)
            
            # Копируем категории
            for source_category in source_version.categories.all():
                new_category = RuleCategory.objects.create(
                    version=new_version,
                    number=source_category.number,
                    title=source_category.title,
                    description=source_category.description,
                    order=source_category.order,
                    is_new=False,  # <-- НЕ НОВОЕ (скопировано)
                    is_changed=False,  # <-- НЕ ИЗМЕНЕНО
                    changed_in_version=None  # <-- НЕ ПРИВЯЗАНО К ВЕРСИИ
                )
                
                # Копируем теги категории
                if source_category.tags.exists():
                    new_category.tags.set(source_category.tags.all())
                
                # Копируем ПРЯМЫЕ ПУНКТЫ (без подраздела)
                for source_item in source_category.direct_items.all():
                    new_item = RuleItem.objects.create(
                        category=new_category,
                        number=source_item.number,
                        content=source_item.content,
                        order=source_item.order
                    )
                    # Копируем теги пункта
                    if source_item.tags.exists():
                        new_item.tags.set(source_item.tags.all())
                    
                    # Копируем подсказки пункта
                    for source_hint in source_item.hints.all():
                        RuleHint.objects.create(
                            rule_item=new_item,
                            text=source_hint.text,
                            priority=source_hint.priority
                        )
                
                # Копируем подразделы
                for source_section in source_category.sections.all():
                    new_section = RuleSection.objects.create(
                        category=new_category,
                        number=source_section.number,
                        title=source_section.title,
                        description=source_section.description,
                        order=source_section.order
                    )
                    
                    # Копируем теги подраздела
                    if source_section.tags.exists():
                        new_section.tags.set(source_section.tags.all())
                    
                    # Копируем пункты подраздела
                    for source_item in source_section.items.all():
                        new_item = RuleItem.objects.create(
                            section=new_section,
                            number=source_item.number,
                            content=source_item.content,
                            order=source_item.order
                        )
                        # Копируем теги пункта
                        if source_item.tags.exists():
                            new_item.tags.set(source_item.tags.all())
                        
                        # Копируем подсказки пункта
                        for source_hint in source_item.hints.all():
                            RuleHint.objects.create(
                                rule_item=new_item,
                                text=source_hint.text,
                                priority=source_hint.priority
                            )
            
            # Копируем переменные
            for source_var in source_version.variables.all():
                RuleVariable.objects.create(
                    version=new_version,
                    key=source_var.key,
                    name=source_var.name,
                    description=source_var.description,
                    value=source_var.value,
                    var_type=source_var.var_type,
                    is_editable=source_var.is_editable,
                    rule_reference=source_var.rule_reference
                )
            
            # Копируем систему оценки (если есть)
            if hasattr(source_version, 'scoring'):
                scoring = source_version.scoring
                from ..models import RuleScoring
                RuleScoring.objects.create(
                    version=new_version,
                    win_points=scoring.win_points,
                    loss_points=scoring.loss_points,
                    lh_bonus_3=scoring.lh_bonus_3,
                    lh_bonus_2=scoring.lh_bonus_2,
                    yellow_base_penalty=scoring.yellow_base_penalty,
                    yellow_progression=scoring.yellow_progression,
                    red_card_penalty=scoring.red_card_penalty,
                    ppk_penalty=scoring.ppk_penalty,
                    disqualification_penalty=scoring.disqualification_penalty,
                    ci_percent=scoring.ci_percent,
                    ci_min_games=scoring.ci_min_games,
                    ci_coef_win_with_black=scoring.ci_coef_win_with_black,
                    ci_coef_lose_with_black=scoring.ci_coef_lose_with_black,
                    ci_coef_win_no_black=scoring.ci_coef_win_no_black,
                    ci_coef_lose_no_black=scoring.ci_coef_lose_no_black,
                    extra_min=scoring.extra_min,
                    extra_max=scoring.extra_max,
                    extra_step=scoring.extra_step
                )
        
        messages.success(request, f'Версия {version} успешно создана!')
        return redirect('rules_admin')
    
    # GET запрос - показываем форму
    versions = RuleVersion.objects.all().order_by('-published_date')
    context = {
        'versions': versions,
    }
    return render(request, 'tournament/rules/create_version.html', context)

@login_required
@user_passes_test(is_admin)
def rules_activate_version(request, version_id):
    """Активировать версию правил"""
    version = get_object_or_404(RuleVersion, id=version_id)
    
    if request.method == 'POST':
        # Находим предыдущую активную версию
        old_active = RuleVersion.objects.filter(is_active=True).first()
        
        # Деактивируем все версии
        RuleVersion.objects.all().update(is_active=False)
        
        # Активируем выбранную
        version.is_active = True
        version.save()
        
        # Отмечаем изменения
        mark_changes_in_version(version, old_active)
        
        messages.success(request, f'Версия {version.version} активирована!')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin)
def rules_delete_version(request, version_id):
    """Удалить версию правил"""
    version = get_object_or_404(RuleVersion, id=version_id)
    
    if version.is_active:
        messages.error(request, 'Нельзя удалить активную версию правил')
        return redirect('rules_admin')
    
    if request.method == 'POST':
        version_name = version.version
        version.delete()
        messages.success(request, f'Версия {version_name} удалена')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ========== УПРАВЛЕНИЕ КАТЕГОРИЯМИ ==========

@login_required
@user_passes_test(is_admin)
def rules_add_category(request):
    """Добавить категорию (раздел)"""
    if request.method == 'POST':
        version_id = request.POST.get('version_id')
        number = request.POST.get('number')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        
        version = get_object_or_404(RuleVersion, id=version_id)
        
        # Если номер не указан или пустой - генерируем автоматически
        if not number:
            number = RuleCategory.get_next_number(version)
        
        if RuleCategory.objects.filter(version=version, number=number).exists():
            messages.error(request, f'Раздел с номером {number} уже существует')
            return redirect('rules_admin')
        
        # order = числовое значение номера
        order = int(number) if number.isdigit() else 0
        
        RuleCategory.objects.create(
            version=version,
            number=number,
            title=title,
            description=description,
            order=order,
            is_new=True,
            changed_in_version=version
        )
        
        messages.success(request, f'Раздел "{title}" добавлен')
        return redirect('rules_admin')
    
    # GET запрос — возвращаем следующий номер для предзаполнения
    version_id = request.GET.get('version_id')
    if version_id:
        version = get_object_or_404(RuleVersion, id=version_id)
        next_number = RuleCategory.get_next_number(version)
        return JsonResponse({'next_number': next_number})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin)
def rules_edit_category(request, category_id):
    """Редактировать категорию"""
    category = get_object_or_404(RuleCategory, id=category_id)
    
    if request.method == 'POST':
        category.number = request.POST.get('number', category.number)
        category.title = request.POST.get('title', category.title)
        category.description = request.POST.get('description', category.description)
        category.order = request.POST.get('order', category.order)
        category.is_changed = True  # <-- ДОБАВИТЬ
        category.is_new = False  # <-- если было новым, теперь не новое
        category.changed_in_version = category.version  # <-- ДОБАВИТЬ
        category.save()
        
        messages.success(request, f'Раздел {category.number} обновлен')
        return redirect('rules_admin')
    
    context = {'category': category}
    return render(request, 'tournament/rules/admin.html', context)


@login_required
@user_passes_test(is_admin)
def rules_delete_category(request, category_id):
    """Удалить категорию"""
    category = get_object_or_404(RuleCategory, id=category_id)
    
    if request.method == 'POST':
        category_number = category.number
        category.delete()
        messages.success(request, f'Раздел {category_number} удален')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ========== УПРАВЛЕНИЕ ПОДРАЗДЕЛАМИ ==========

@login_required
@user_passes_test(is_admin)
def rules_add_section(request):
    """Добавить подраздел"""
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        number = request.POST.get('number')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        
        category = get_object_or_404(RuleCategory, id=category_id)
        
        # Если номер не указан - генерируем автоматически
        if not number:
            number = RuleSection.get_next_number(category)
        
        if RuleSection.objects.filter(category=category, number=number).exists():
            messages.error(request, f'Подраздел с номером {number} уже существует')
            return redirect('rules_admin')
        
        # order = числовое значение после точки (4.1 -> 1)
        try:
            order = int(number.split('.')[1]) if '.' in number else 0
        except (ValueError, IndexError):
            order = 0
        
        RuleSection.objects.create(
            category=category,
            number=number,
            title=title,
            description=description,
            order=order,
            is_new=True,
            changed_in_version=category.version 
        )
        
        messages.success(request, f'Подраздел "{title}" добавлен')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin)
def rules_edit_section(request, section_id):
    """Редактировать подраздел"""
    section = get_object_or_404(RuleSection, id=section_id)
    
    if request.method == 'POST':
        section.number = request.POST.get('number', section.number)
        section.title = request.POST.get('title', section.title)
        section.description = request.POST.get('description', section.description)
        section.order = request.POST.get('order', section.order)
        section.is_changed = True  # <-- ДОБАВИТЬ
        section.is_new = False  # <-- если было новым, теперь не новое
        section.changed_in_version = section.category.version  # <-- ДОБАВИТЬ
        section.save()
        
        messages.success(request, f'Подраздел {section.number} обновлен')
        return redirect('rules_admin')
    
    context = {'section': section}
    return render(request, 'tournament/rules/admin.html', context)


@login_required
@user_passes_test(is_admin)
def rules_delete_section(request, section_id):
    """Удалить подраздел"""
    section = get_object_or_404(RuleSection, id=section_id)
    
    if request.method == 'POST':
        section_number = section.number
        section.delete()
        messages.success(request, f'Подраздел {section_number} удален')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ========== УПРАВЛЕНИЕ ПУНКТАМИ ==========

@login_required
@user_passes_test(is_admin)
def rules_add_item(request):
    """Добавить пункт правил в подраздел"""
    if request.method == 'POST':
        section_id = request.POST.get('section_id')
        number = request.POST.get('number')
        content = request.POST.get('content')
        tags = request.POST.getlist('tags')
        
        section = get_object_or_404(RuleSection, id=section_id)
        
        # Если номер не указан - генерируем автоматически
        if not number:
            number = RuleItem.get_next_number_for_section(section)
        
        if RuleItem.objects.filter(section=section, number=number).exists():
            messages.error(request, f'Пункт с номером {number} уже существует')
            return redirect('rules_admin')
        
        # order = числовое значение после второй точки (4.1.1 -> 1)
        try:
            parts = number.split('.')
            order = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 0
        except (ValueError, IndexError):
            order = 0
        
        item = RuleItem.objects.create(
            section=section,
            number=number,
            content=content,
            order=order,
            is_new=True,
            changed_in_version=section.category.version
        )
        
        if tags:
            item.tags.set(tags)
        
        messages.success(request, f'Пункт {number} добавлен')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin)
def rules_edit_item(request, item_id):
    """Редактировать пункт правил"""
    item = get_object_or_404(RuleItem, id=item_id)
    
    if request.method == 'POST':
        item.number = request.POST.get('number', item.number)
        item.content = request.POST.get('content', item.content)
        item.order = request.POST.get('order', item.order)
        item.is_changed = True  # <-- ДОБАВИТЬ
        item.is_new = False  # <-- если было новым, теперь не новое
        # Определяем версию
        if item.section:
            item.changed_in_version = item.section.category.version
        elif item.category:
            item.changed_in_version = item.category.version
        item.save()
        
        messages.success(request, f'Пункт {item.number} обновлен')
        return redirect('rules_admin')
    
    context = {'item': item}
    return render(request, 'tournament/rules/admin.html', context)


@login_required
@user_passes_test(is_admin)
def rules_delete_item(request, item_id):
    """Удалить пункт правил"""
    item = get_object_or_404(RuleItem, id=item_id)
    
    if request.method == 'POST':
        item_number = item.number
        item.delete()
        messages.success(request, f'Пункт {item_number} удален')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ========== УПРАВЛЕНИЕ ПЕРЕМЕННЫМИ ==========

@login_required
@user_passes_test(is_admin)
def rules_add_variable(request):
    """Добавить переменную правил"""
    if request.method == 'POST':
        version_id = request.POST.get('version_id')
        key = request.POST.get('key')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        value = request.POST.get('value')
        var_type = request.POST.get('var_type')
        rule_reference = request.POST.get('rule_reference', '')
        
        version = get_object_or_404(RuleVersion, id=version_id)
        
        if RuleVariable.objects.filter(version=version, key=key).exists():
            messages.error(request, f'Переменная с ключом {key} уже существует')
            return redirect('rules_admin')
        
        RuleVariable.objects.create(
            version=version,
            key=key,
            name=name,
            description=description,
            value=value,
            var_type=var_type,
            rule_reference=rule_reference
        )
        
        messages.success(request, f'Переменная {key} добавлена')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin)
def rules_edit_variable(request, variable_id):
    """Редактировать переменную"""
    variable = get_object_or_404(RuleVariable, id=variable_id)
    
    if request.method == 'POST':
        variable.key = request.POST.get('key', variable.key)
        variable.name = request.POST.get('name', variable.name)
        variable.description = request.POST.get('description', variable.description)
        variable.value = request.POST.get('value', variable.value)
        variable.var_type = request.POST.get('var_type', variable.var_type)
        variable.rule_reference = request.POST.get('rule_reference', variable.rule_reference)
        variable.save()
        
        messages.success(request, f'Переменная {variable.key} обновлена')
        return redirect('rules_admin')
    
    context = {'variable': variable}
    return render(request, 'tournament/rules/admin.html', context)


@login_required
@user_passes_test(is_admin)
def rules_delete_variable(request, variable_id):
    """Удалить переменную"""
    variable = get_object_or_404(RuleVariable, id=variable_id)
    
    if request.method == 'POST':
        variable_key = variable.key
        variable.delete()
        messages.success(request, f'Переменная {variable_key} удалена')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ========== API ДЛЯ AJAX ==========

@login_required
@user_passes_test(is_admin)
def rules_get_version_data(request, version_id):
    """Получить данные версии для отображения в дереве"""
    version = get_object_or_404(RuleVersion, id=version_id)
    
    categories = []
    for category in version.categories.all().order_by('order'):
        sections_data = []
        for section in category.sections.all().order_by('order'):
            items_data = []
            for item in section.items.all().order_by('order'):
                items_data.append({
                    'id': item.id,
                    'number': item.number,
                    'content': item.content[:200] + '...' if len(item.content) > 200 else item.content
                })
            sections_data.append({
                'id': section.id,
                'number': section.number,
                'title': section.title,
                'items': items_data
            })
        categories.append({
            'id': category.id,
            'number': category.number,
            'title': category.title,
            'sections': sections_data
        })
    
    variables = []
    for var in version.variables.all().order_by('key'):
        variables.append({
            'id': var.id,
            'key': var.key,
            'name': var.name,
            'value': var.value,
            'var_type': var.var_type,
            'rule_reference': var.rule_reference
        })
    
    return JsonResponse({
        'categories': categories,
        'variables': variables
    })


# ========== API ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ==========

@login_required
@user_passes_test(is_admin)
def rules_api_category(request, category_id):
    """Получить данные категории для редактирования"""
    category = get_object_or_404(RuleCategory, id=category_id)
    return JsonResponse({
        'id': category.id,
        'number': category.number,
        'title': category.title,
        'description': category.description,
        'order': category.order,
        'tags': list(category.tags.values_list('id', flat=True)) if category.tags.exists() else []
    })

@login_required
@user_passes_test(is_admin)
def rules_api_section(request, section_id):
    """Получить данные подраздела для редактирования"""
    section = get_object_or_404(RuleSection, id=section_id)
    return JsonResponse({
        'id': section.id,
        'number': section.number,
        'title': section.title,
        'description': section.description,
        'order': section.order,
        'tags': list(section.tags.values_list('id', flat=True)) if hasattr(section, 'tags') and section.tags.exists() else []
    })

@login_required
@user_passes_test(is_admin)
def rules_api_item(request, item_id):
    """Получить данные пункта для редактирования"""
    item = get_object_or_404(RuleItem, id=item_id)
    return JsonResponse({
        'id': item.id,
        'number': item.number,
        'content': item.content,
        'order': item.order,
        'tags': list(item.tags.values_list('id', flat=True)) if item.tags.exists() else []
    })

@login_required
@user_passes_test(is_admin)
def rules_api_variable(request, variable_id):
    """Получить данные переменной для редактирования"""
    variable = get_object_or_404(RuleVariable, id=variable_id)
    return JsonResponse({
        'id': variable.id,
        'key': variable.key,
        'name': variable.name,
        'value': variable.value,
        'var_type': variable.var_type,
        'rule_reference': variable.rule_reference,
        'description': variable.description
    })

@login_required
@user_passes_test(is_admin)
def rules_add_direct_item(request):
    """Добавить пункт прямо в раздел (без подраздела)"""
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        number = request.POST.get('number')
        content = request.POST.get('content')
        order = request.POST.get('order', 0)
        tags = request.POST.getlist('tags')
        
        category = get_object_or_404(RuleCategory, id=category_id)
        
        # Если номер не указан - генерируем автоматически
        if not number:
            number = RuleItem.get_next_number_for_category(category)
        
        if RuleItem.objects.filter(category=category, number=number).exists():
            messages.error(request, f'Пункт с номером {number} уже существует')
            return redirect('rules_admin')
        
        # order = числовое значение после точки (1.1 -> 1)
        try:
            parts = number.split('.')
            order = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
        except (ValueError, IndexError):
            order = 0
        
        item = RuleItem.objects.create(
            category=category,
            number=number,
            content=content,
            order=order,
            is_new=True,  
            changed_in_version=category.version  
        )
        
        if tags:
            item.tags.set(tags)
        
        messages.success(request, f'Пункт {number} добавлен в раздел "{category.title}"')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@user_passes_test(is_admin)
def rules_edit_direct_item(request, item_id):
    """Редактировать прямой пункт"""
    item = get_object_or_404(RuleItem, id=item_id)
    
    if request.method == 'POST':
        number = request.POST.get('number')
        content = request.POST.get('content')
        order = request.POST.get('order', 0)
        tags = request.POST.getlist('tags')
        
        if RuleItem.objects.filter(
            category=item.category, 
            number=number
        ).exclude(id=item.id).exists():
            messages.error(request, f'Пункт с номером {number} уже существует')
            return redirect('rules_admin')
        
        item.number = number
        item.content = content
        item.order = order
        if tags:
            item.tags.set(tags)
        else:
            item.tags.clear()
        item.is_changed = True  # <-- ДОБАВИТЬ
        item.is_new = False  # <-- если было новым, теперь не новое
        item.changed_in_version = item.category.version  # <-- ДОБАВИТЬ
        item.save()
        
        messages.success(request, f'Пункт {number} обновлен')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@user_passes_test(is_admin)
def rules_delete_direct_item(request, item_id):
    """Удалить прямой пункт"""
    item = get_object_or_404(RuleItem, id=item_id)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Пункт удален')
        return redirect('rules_admin')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin)
def rules_api_direct_item(request, item_id):
    """Получить данные прямого пункта для редактирования"""
    item = get_object_or_404(RuleItem, id=item_id)
    return JsonResponse({
        'id': item.id,
        'number': item.number,
        'content': item.content,
        'order': item.order,
        'tags': list(item.tags.values_list('id', flat=True))
    })


@login_required
@user_passes_test(is_admin)
def rules_tags(request):
    """Страница управления тегами"""
    tags = RuleTag.objects.all().order_by('name')
    return render(request, 'tournament/rules/tags.html', {'tags': tags})


@login_required
@user_passes_test(is_admin)
def rules_add_tag(request):
    """Добавить тег"""
    if request.method == 'POST':
        name = request.POST.get('name')
        color = request.POST.get('color', '#D4AF37')
        
        if RuleTag.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Тег "{name}" уже существует')
            return redirect('rules_tags')
        
        RuleTag.objects.create(name=name, color=color)
        messages.success(request, f'Тег "{name}" добавлен')
        return redirect('rules_tags')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@user_passes_test(is_admin)
def rules_delete_tag(request, tag_id):
    """Удалить тег"""
    tag = get_object_or_404(RuleTag, id=tag_id)
    
    if request.method == 'POST':
        tag.delete()
        messages.success(request, 'Тег удален')
        return redirect('rules_tags')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ========== API ДЛЯ ПОЛУЧЕНИЯ СЛЕДУЮЩИХ НОМЕРОВ ==========

@login_required
@user_passes_test(is_admin)
def rules_api_next_category_number(request):
    """Получить следующий номер для раздела"""
    version_id = request.GET.get('version_id')
    if version_id:
        version = get_object_or_404(RuleVersion, id=version_id)
        next_number = RuleCategory.get_next_number(version)
        return JsonResponse({'next_number': next_number})
    return JsonResponse({'error': 'version_id required'}, status=400)


@login_required
@user_passes_test(is_admin)
def rules_api_next_section_number(request):
    """Получить следующий номер для подраздела"""
    category_id = request.GET.get('category_id')
    if category_id:
        category = get_object_or_404(RuleCategory, id=category_id)
        next_number = RuleSection.get_next_number(category)
        return JsonResponse({'next_number': next_number})
    return JsonResponse({'error': 'category_id required'}, status=400)


@login_required
@user_passes_test(is_admin)
def rules_api_next_item_number(request):
    """Получить следующий номер для пункта (в подразделе)"""
    section_id = request.GET.get('section_id')
    if section_id:
        section = get_object_or_404(RuleSection, id=section_id)
        next_number = RuleItem.get_next_number_for_section(section)
        return JsonResponse({'next_number': next_number})
    return JsonResponse({'error': 'section_id required'}, status=400)


@login_required
@user_passes_test(is_admin)
def rules_api_next_direct_item_number(request):
    """Получить следующий номер для прямого пункта (в разделе)"""
    category_id = request.GET.get('category_id')
    if category_id:
        category = get_object_or_404(RuleCategory, id=category_id)
        next_number = RuleItem.get_next_number_for_category(category)
        return JsonResponse({'next_number': next_number})
    return JsonResponse({'error': 'category_id required'}, status=400)

def mark_changes_in_version(version, old_version=None):
    """
    Отмечает новые и изменённые элементы в версии.
    Сравнивает с предыдущей активной версией.
    """
    from ..models import RuleCategory, RuleSection, RuleItem
    
    # Если нет старой версии, всё считается новым
    if not old_version:
        # Все категории, разделы и пункты в новой версии — новые
        for category in version.categories.all():
            category.is_new = True
            category.changed_in_version = version
            category.save()
            for section in category.sections.all():
                section.is_new = True
                section.changed_in_version = version
                section.save()
                for item in section.items.all():
                    item.is_new = True
                    item.changed_in_version = version
                    item.save()
            for item in category.direct_items.all():
                item.is_new = True
                item.changed_in_version = version
                item.save()
        return
    
    # Сравниваем со старой версией
    old_categories = {c.number: c for c in old_version.categories.all()}
    new_categories = {c.number: c for c in version.categories.all()}
    
    # Проверяем категории
    for num, new_cat in new_categories.items():
        if num in old_categories:
            old_cat = old_categories[num]
            # Проверяем изменения
            if (old_cat.title != new_cat.title or 
                old_cat.description != new_cat.description):
                new_cat.is_changed = True
                new_cat.changed_in_version = version
                new_cat.save()
        else:
            # Новая категория
            new_cat.is_new = True
            new_cat.changed_in_version = version
            new_cat.save()
        
        # Проверяем подразделы
        old_sections = {s.number: s for s in old_cat.sections.all()} if num in old_categories else {}
        new_sections = {s.number: s for s in new_cat.sections.all()}
        
        for sec_num, new_sec in new_sections.items():
            if sec_num in old_sections:
                old_sec = old_sections[sec_num]
                if (old_sec.title != new_sec.title or 
                    old_sec.description != new_sec.description):
                    new_sec.is_changed = True
                    new_sec.changed_in_version = version
                    new_sec.save()
            else:
                new_sec.is_new = True
                new_sec.changed_in_version = version
                new_sec.save()
            
            # Проверяем пункты в подразделах
            old_items = {i.number: i for i in old_sec.items.all()} if sec_num in old_sections else {}
            new_items = {i.number: i for i in new_sec.items.all()}
            
            for item_num, new_item in new_items.items():
                if item_num in old_items:
                    old_item = old_items[item_num]
                    if old_item.content != new_item.content:
                        new_item.is_changed = True
                        new_item.changed_in_version = version
                        new_item.save()
                else:
                    new_item.is_new = True
                    new_item.changed_in_version = version
                    new_item.save()
        
        # Проверяем прямые пункты (без подраздела)
        old_direct = {i.number: i for i in old_cat.direct_items.all()} if num in old_categories else {}
        new_direct = {i.number: i for i in new_cat.direct_items.all()}
        
        for item_num, new_item in new_direct.items():
            if item_num in old_direct:
                old_item = old_direct[item_num]
                if old_item.content != new_item.content:
                    new_item.is_changed = True
                    new_item.changed_in_version = version
                    new_item.save()
            else:
                new_item.is_new = True
                new_item.changed_in_version = version
                new_item.save()