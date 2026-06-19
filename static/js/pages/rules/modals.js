// ========== МОДАЛЬНЫЕ ОКНА ДЛЯ ПРАВИЛ ==========

// Открыть модальное окно
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

// Закрыть модальное окно
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Закрыть все модальные окна
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(function(modal) {
        modal.style.display = 'none';
    });
    document.body.style.overflow = '';
}

// Закрытие модалки при клике вне контента
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        document.body.style.overflow = '';
    }
});

// Закрытие модалок по Escape
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        document.querySelectorAll('.modal').forEach(function(modal) {
            modal.style.display = 'none';
        });
        document.body.style.overflow = '';
    }
});

// ========== ФУНКЦИИ ДЛЯ РАЗДЕЛОВ (КАТЕГОРИЙ) ==========

function openAddCategoryModal() {
    // Получаем следующий номер для раздела
    const versionId = document.querySelector('input[name="version_id"]')?.value;
    if (versionId) {
        fetch('/rules/api/next-category-number/?version_id=' + versionId)
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.next_number) {
                    document.getElementById('category_number').value = data.next_number;
                    document.getElementById('category_number_hint').textContent = 
                        'Будет создан раздел №' + data.next_number;
                }
            })
            .catch(function() {
                // Если не получилось, оставляем заглушку
            });
    }
    openModal('addCategoryModal');
}

function openEditCategoryModal(categoryId) {
    fetch('/rules/api/category/' + categoryId + '/')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            document.getElementById('edit_category_number').value = data.number;
            document.getElementById('edit_category_title').value = data.title;
            document.getElementById('edit_category_description').value = data.description || '';
            document.getElementById('edit_category_order').value = data.order || 0;
            document.getElementById('editCategoryForm').action = '/rules/edit-category/' + categoryId + '/';
            openModal('editCategoryModal');
        })
        .catch(function() {
            alert('Ошибка загрузки данных раздела');
        });
}

function deleteCategory(categoryId) {
    if (!confirm('Удалить этот раздел?')) return;
    
    fetch('/rules/delete-category/' + categoryId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
        },
    })
    .then(function() { location.reload(); })
    .catch(function() { alert('Ошибка при удалении'); });
}

// ========== ФУНКЦИИ ДЛЯ ПОДРАЗДЕЛОВ ==========

function openAddSectionModal(categoryId) {
    document.getElementById('section_category_id').value = categoryId;
    
    // Получаем следующий номер для подраздела
    fetch('/rules/api/next-section-number/?category_id=' + categoryId)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.next_number) {
                document.getElementById('section_number').value = data.next_number;
                document.getElementById('section_number_hint').textContent = 
                    'Будет создан подраздел №' + data.next_number;
            }
        })
        .catch(function() {
            // Если не получилось, оставляем заглушку
        });
    
    openModal('addSectionModal');
}

function openEditSectionModal(sectionId) {
    fetch('/rules/api/section/' + sectionId + '/')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            document.getElementById('edit_section_number').value = data.number;
            document.getElementById('edit_section_title').value = data.title;
            document.getElementById('edit_section_description').value = data.description || '';
            document.getElementById('edit_section_order').value = data.order || 0;
            document.getElementById('editSectionForm').action = '/rules/edit-section/' + sectionId + '/';
            openModal('editSectionModal');
        })
        .catch(function() {
            alert('Ошибка загрузки данных подраздела');
        });
}

function deleteSection(sectionId) {
    if (!confirm('Удалить этот подраздел?')) return;
    
    fetch('/rules/delete-section/' + sectionId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
        },
    })
    .then(function() { location.reload(); })
    .catch(function() { alert('Ошибка при удалении'); });
}

// ========== ФУНКЦИИ ДЛЯ ПУНКТОВ ==========

function openAddItemModal(sectionId) {
    document.getElementById('item_section_id').value = sectionId;
    
    // Получаем следующий номер для пункта
    fetch('/rules/api/next-item-number/?section_id=' + sectionId)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.next_number) {
                document.getElementById('item_number').value = data.next_number;
                document.getElementById('item_number_hint').textContent = 
                    'Будет создан пункт №' + data.next_number;
            }
        })
        .catch(function() {
            // Если не получилось, оставляем заглушку
        });
    
    openModal('addItemModal');
}

function openEditItemModal(itemId) {
    fetch('/rules/api/item/' + itemId + '/')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            document.getElementById('edit_item_number').value = data.number;
            document.getElementById('edit_item_content').value = data.content;
            document.getElementById('edit_item_order').value = data.order || 0;
            document.getElementById('editItemForm').action = '/rules/edit-item/' + itemId + '/';
            openModal('editItemModal');
        })
        .catch(function() {
            alert('Ошибка загрузки данных пункта');
        });
}

function deleteItem(itemId) {
    if (!confirm('Удалить этот пункт?')) return;
    
    fetch('/rules/delete-item/' + itemId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
        },
    })
    .then(function() { location.reload(); })
    .catch(function() { alert('Ошибка при удалении'); });
}

// ========== ФУНКЦИИ ДЛЯ ПЕРЕМЕННЫХ ==========

function openAddVariableModal() {
    openModal('addVariableModal');
}

function openEditVariableModal(variableId) {
    fetch('/rules/api/variable/' + variableId + '/')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            document.getElementById('edit_variable_key').value = data.key;
            document.getElementById('edit_variable_name').value = data.name;
            document.getElementById('edit_variable_value').value = data.value;
            document.getElementById('edit_variable_type').value = data.var_type;
            document.getElementById('edit_variable_reference').value = data.rule_reference || '';
            document.getElementById('edit_variable_description').value = data.description || '';
            document.getElementById('editVariableForm').action = '/rules/edit-variable/' + variableId + '/';
            openModal('editVariableModal');
        })
        .catch(function() {
            alert('Ошибка загрузки данных переменной');
        });
}

function deleteVariable(variableId) {
    if (!confirm('Удалить эту переменную?')) return;
    
    fetch('/rules/delete-variable/' + variableId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
        },
    })
    .then(function() { location.reload(); })
    .catch(function() { alert('Ошибка при удалении'); });
}

// ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
}

// ========== ФУНКЦИИ ДЛЯ ПРЯМЫХ ПУНКТОВ ==========

function openAddDirectItemModal(categoryId) {
    document.getElementById('direct_item_category_id').value = categoryId;
    
    // Получаем следующий номер для прямого пункта
    fetch('/rules/api/next-direct-item-number/?category_id=' + categoryId)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.next_number) {
                document.getElementById('direct_item_number').value = data.next_number;
                document.getElementById('direct_item_number_hint').textContent = 
                    'Будет создан пункт №' + data.next_number;
            }
        })
        .catch(function() {
            // Если не получилось, оставляем заглушку
        });
    
    openModal('addDirectItemModal');
}

function openEditDirectItemModal(itemId) {
    fetch('/rules/api/direct-item/' + itemId + '/')
        .then(function(response) { 
            if (!response.ok) {
                throw new Error('Ошибка загрузки: ' + response.status);
            }
            return response.json(); 
        })
        .then(function(data) {
            document.getElementById('edit_direct_item_id').value = data.id;
            document.getElementById('edit_direct_item_number').value = data.number;
            document.getElementById('edit_direct_item_content').value = data.content;
            document.getElementById('edit_direct_item_order').value = data.order || 0;
            
            // Выбираем теги
            const select = document.getElementById('edit_direct_item_tags');
            if (select) {
                for (let option of select.options) {
                    option.selected = data.tags.includes(parseInt(option.value));
                }
            }
            
            document.getElementById('editDirectItemForm').action = '/rules/edit-direct-item/' + itemId + '/';
            openModal('editDirectItemModal');
        })
        .catch(function(error) {
            console.error('Ошибка:', error);
            alert('Ошибка загрузки данных пункта: ' + error.message);
        });
}