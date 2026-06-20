// ========== ДОПОЛНИТЕЛЬНАЯ ЛОГИКА ДЛЯ СТРАНИЦЫ ПРАВИЛ ==========

// Пока все функции вынесены в modals.js

// Пример: авто-скрытие сообщений
document.addEventListener('DOMContentLoaded', function() {
    // Если есть сообщения, скрываем их через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 300);
        }, 5000);
    });
});

// ========== СВОРАЧИВАНИЕ РАЗДЕЛОВ ==========

document.addEventListener('DOMContentLoaded', function() {
    // Находим все карточки категорий (разделов)
    const categoryCards = document.querySelectorAll('.category-card');
    
    categoryCards.forEach(function(card) {
        // Добавляем кнопку сворачивания в заголовок
        const header = card.querySelector('.category-header');
        if (header) {
            // Проверяем, есть ли уже кнопка
            if (!header.querySelector('.collapse-toggle')) {
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'collapse-toggle btn btn-sm btn-outline';
                toggleBtn.setAttribute('type', 'button');
                toggleBtn.setAttribute('title', 'Свернуть/развернуть раздел');
                toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
                
                // Вставляем кнопку в конец заголовка
                const actions = header.querySelector('.category-actions');
                if (actions) {
                    actions.prepend(toggleBtn);
                } else {
                    header.appendChild(toggleBtn);
                }
                
                // Обработчик клика
                toggleBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    toggleCategory(card);
                });
            }
        }
        
        // По умолчанию все разделы развёрнуты
        card.classList.add('expanded');
    });
    
    // Восстанавливаем состояние из localStorage
    restoreCollapseState();
});

function toggleCategory(card) {
    const isExpanded = card.classList.contains('expanded');
    
    if (isExpanded) {
        card.classList.remove('expanded');
        card.classList.add('collapsed');
        // Меняем иконку
        const toggle = card.querySelector('.collapse-toggle i');
        if (toggle) {
            toggle.className = 'fas fa-chevron-down';
        }
        // Сохраняем состояние
        saveCollapseState(card.dataset.categoryId, 'collapsed');
    } else {
        card.classList.remove('collapsed');
        card.classList.add('expanded');
        // Меняем иконку
        const toggle = card.querySelector('.collapse-toggle i');
        if (toggle) {
            toggle.className = 'fas fa-chevron-up';
        }
        // Сохраняем состояние
        saveCollapseState(card.dataset.categoryId, 'expanded');
    }
}

function saveCollapseState(categoryId, state) {
    try {
        const states = JSON.parse(localStorage.getItem('rules_collapse_states') || '{}');
        states[categoryId] = state;
        localStorage.setItem('rules_collapse_states', JSON.stringify(states));
    } catch (e) {
        // Игнорируем ошибки localStorage
    }
}

function restoreCollapseState() {
    try {
        const states = JSON.parse(localStorage.getItem('rules_collapse_states') || '{}');
        const cards = document.querySelectorAll('.category-card');
        
        cards.forEach(function(card) {
            const categoryId = card.dataset.categoryId;
            if (categoryId && states[categoryId]) {
                if (states[categoryId] === 'collapsed') {
                    card.classList.remove('expanded');
                    card.classList.add('collapsed');
                    const toggle = card.querySelector('.collapse-toggle i');
                    if (toggle) {
                        toggle.className = 'fas fa-chevron-down';
                    }
                } else {
                    card.classList.add('expanded');
                    card.classList.remove('collapsed');
                }
            }
        });
    } catch (e) {
        // Игнорируем ошибки
    }
}

// Добавляем кнопку "Свернуть все" / "Развернуть все"
document.addEventListener('DOMContentLoaded', function() {
    const sectionHeader = document.querySelector('.categories-section .section-header');
    if (sectionHeader) {
        const actionsDiv = sectionHeader.querySelector('.section-actions');
        if (actionsDiv) {
            const collapseAllBtn = document.createElement('button');
            collapseAllBtn.className = 'btn btn-sm btn-outline';
            collapseAllBtn.setAttribute('type', 'button');
            collapseAllBtn.setAttribute('title', 'Свернуть все разделы');
            collapseAllBtn.innerHTML = '<i class="fas fa-compress-alt"></i>';
            collapseAllBtn.addEventListener('click', function() {
                toggleAllCategories(false);
            });
            actionsDiv.appendChild(collapseAllBtn);
            
            const expandAllBtn = document.createElement('button');
            expandAllBtn.className = 'btn btn-sm btn-outline';
            expandAllBtn.setAttribute('type', 'button');
            expandAllBtn.setAttribute('title', 'Развернуть все разделы');
            expandAllBtn.innerHTML = '<i class="fas fa-expand-alt"></i>';
            expandAllBtn.addEventListener('click', function() {
                toggleAllCategories(true);
            });
            actionsDiv.appendChild(expandAllBtn);
        }
    }
});

function toggleAllCategories(expand) {
    const cards = document.querySelectorAll('.category-card');
    cards.forEach(function(card) {
        if (expand) {
            card.classList.remove('collapsed');
            card.classList.add('expanded');
            const toggle = card.querySelector('.collapse-toggle i');
            if (toggle) {
                toggle.className = 'fas fa-chevron-up';
            }
            saveCollapseState(card.dataset.categoryId, 'expanded');
        } else {
            card.classList.remove('expanded');
            card.classList.add('collapsed');
            const toggle = card.querySelector('.collapse-toggle i');
            if (toggle) {
                toggle.className = 'fas fa-chevron-down';
            }
            saveCollapseState(card.dataset.categoryId, 'collapsed');
        }
    });
}