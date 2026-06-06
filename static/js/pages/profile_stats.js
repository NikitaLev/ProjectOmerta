async function loadPlayerStats() {
    try {
        const response = await fetch('/profile/stats/');
        if (!response.ok) {
            throw new Error('Статистика не найдена');
        }
        const data = await response.json();
        
        // Обновляем бейдж с общим количеством игр
        document.getElementById('totalGamesBadge').textContent = data.total_games || 0;

        if (!data.has_stats) {
            showEmptyState(data.message || 'Нет данных для отображения');
            return;
        }
        
        // Рендерим все вкладки
        renderOverallStats(data);
        renderRolesStats(data);
        renderPlacesStats(data);
        renderRecordsStats(data);
        hideLoaders();
        
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        const errorHtml = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Статистика временно недоступна</p></div>';
        document.getElementById('overallContent').innerHTML = errorHtml;
        document.getElementById('rolesContent').innerHTML = errorHtml;
        document.getElementById('placesContent').innerHTML = errorHtml;
        document.getElementById('recordsContent').innerHTML = errorHtml;
    }
}

function renderOverallStats(data) {
    const html = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${data.total_games || 0}</div>
                <div class="stat-label">Всего игр</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total_score || 0}</div>
                <div class="stat-label">Всего очков</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.avg_score || 0}</div>
                <div class="stat-label">Средний балл</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.wins || 0}</div>
                <div class="stat-label">Побед</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.winrate || 0}%</div>
                <div class="stat-label">Винрейт</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.first_kills || 0}</div>
                <div class="stat-label">Первых убийств</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.yellow_cards || 0}</div>
                <div class="stat-label">Жёлтые карточки</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.red_cards || 0}</div>
                <div class="stat-label">Красные карточки</div>
            </div>
        </div>
        <div class="stats-grid" style="margin-top: 15px;">
            <div class="stat-card">
                <div class="stat-value">${data.total_main || 0}</div>
                <div class="stat-label">Основные баллы</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total_bonus || 0}</div>
                <div class="stat-label">Бонусные баллы</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total_penalty || 0}</div>
                <div class="stat-label">Штрафные баллы</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total_ci || 0}</div>
                <div class="stat-label">Компенсационные (Ci)</div>
            </div>
        </div>
    `;
    
    document.getElementById('overallContent').innerHTML = html;
    document.getElementById('loadingOverall').style.display = 'none';
    document.getElementById('overallContent').style.display = 'block';
}

function getRoleIconHtml(roleKey) {
    const icons = {
        'don': '<span class="role-icon role-icon-don role-icon-lg"></span>',
        'mafia': '<span class="role-icon role-icon-mafia role-icon-lg"></span>',
        'sheriff': '<span class="role-icon role-icon-sheriff role-icon-lg"></span>',
        'civil': '<span class="role-icon role-icon-civil role-icon-lg"></span>'
    };
    return icons[roleKey] || icons['civil'];
}

function renderRolesStats(data) {
    const roles = data.roles || {};
    const roleList = ['don', 'mafia', 'sheriff', 'civil'];
    const roleNames = {
        'don': 'Дон',
        'mafia': 'Мафия',
        'sheriff': 'Шериф',
        'civil': 'Мирный'
    };
    
    let html = '<div class="role-stats-grid">';
    for (const roleKey of roleList) {
        const role = roles[roleKey];
        if (role) {
            html += `
                <div class="role-card">
                    <div class="role-stat-icon">
                        ${getRoleIconHtml(roleKey)}
                    </div>
                    <div class="role-name">${role.name}</div>
                    <div class="role-stats">
                        Игр: <span>${role.count}</span><br>
                        Очков: <span>${role.total_score}</span><br>
                        Средний: <span>${role.avg_score}</span><br>
                        Побед: <span>${role.wins}</span> (${role.winrate}%)
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="role-card">
                    <div class="role-stat-icon">
                        ${getRoleIconHtml(roleKey)}
                    </div>
                    <div class="role-name">${roleNames[roleKey]}</div>
                    <div class="role-stats">Нет игр</div>
                </div>
            `;
        }
    }
    html += '</div>';
    
    document.getElementById('rolesContent').innerHTML = html;
    document.getElementById('loadingRoles').style.display = 'none';
    document.getElementById('rolesContent').style.display = 'block';
}

function renderPlacesStats(data) {
    const distribution = data.place_distribution || {};
    const places = Object.keys(distribution).sort((a, b) => parseInt(a) - parseInt(b));
    const totalPlaces = Object.values(distribution).reduce((a, b) => a + b, 0);
    
    if (places.length === 0) {
         document.getElementById('placesContent').innerHTML = `
            <div class="empty-state">
                <i class="fas fa-chart-simple"></i>
                <p>Нет данных о местах в турнирах</p>
                <small>Завершённые турниры появятся здесь</small>
            </div>
        `;
        document.getElementById('loadingPlaces').style.display = 'none';
        document.getElementById('placesContent').style.display = 'block';
        return;
    }
    
    let html = `<div class="place-bars">`;
    for (const place of places) {
        const count = distribution[place];
        const percent = (count / totalPlaces * 100).toFixed(1);
        html += `
            <div class="place-bar-item">
                <div class="place-label">${place}-е место</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${percent}%">${count}</div>
                </div>
            </div>
        `;
    }
    html += `</div>`;
    
    if (data.best_place) {
        html += `<div class="record-card" style="margin-top: 20px;">
                    <div class="record-label">Лучшее место в турнире</div>
                    <div class="record-value">${data.best_place}-е место</div>
                </div>`;
    }
    
    document.getElementById('placesContent').innerHTML = html;
    document.getElementById('loadingPlaces').style.display = 'none';
    document.getElementById('placesContent').style.display = 'block';
}

function renderRecordsStats(data) {
    let html = `<div class="stats-grid">`;
    
    if (!data.best_tournament && data.tournaments_count === 0) {
        document.getElementById('recordsContent').innerHTML = `
            <div class="empty-state">
                <i class="fas fa-trophy"></i>
                <p>Рекорды появятся после участия в турнирах</p>
            </div>
        `;
        return;
    }
    
    if (data.best_tournament) {
        html += `
            <div class="record-card">
                <div class="record-label">Лучший турнир</div>
                <div class="record-value">${data.best_tournament.score} очков</div>
                <div class="record-label" style="margin-top: 8px;">${data.best_tournament.tournament_name}</div>
                ${data.best_tournament.place ? `<div class="record-label">${data.best_tournament.place}-е место</div>` : ''}
            </div>
        `;
    }
    
    html += `
        <div class="record-card">
            <div class="record-label">Лучший бонус за ЛХ</div>
            <div class="record-value">${data.best_lh_bonus || 0}</div>
        </div>
        <div class="record-card">
            <div class="record-label">Всего турниров</div>
            <div class="record-value">${data.tournaments_count || 0}</div>
        </div>
    `;
    
    html += `</div>`;
    
    document.getElementById('recordsContent').innerHTML = html;
    document.getElementById('loadingRecords').style.display = 'none';
    document.getElementById('recordsContent').style.display = 'block';
}

// Табы
document.addEventListener('DOMContentLoaded', function() {
    loadPlayerStats();
    
    const tabs = document.querySelectorAll('.stats-tab');
    const contents = {
        overall: document.getElementById('overallStats'),
        roles: document.getElementById('rolesStats'),
        places: document.getElementById('placesStats'),
        records: document.getElementById('recordsStats')
    };
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const target = this.getAttribute('data-tab');
            
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            Object.values(contents).forEach(content => content.classList.remove('active'));
            if (contents[target]) contents[target].classList.add('active');
        });
    });
    
    // Модальное окно для игроков (оставляем как было)
    const modal = document.getElementById('createdPlayersModal');
    const showBtn = document.getElementById('showCreatedPlayersBtn');
    
    if (modal && showBtn) {
        modal.style.display = 'none';
        
        showBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        });
        
        window.closePlayersModal = function() {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        };
        
        const closeBtn = modal.querySelector('.close-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', closePlayersModal);
        }
        
        window.addEventListener('click', function(event) {
            if (event.target === modal) closePlayersModal();
        });
    }
});

// Функция копирования ссылки
window.copyInviteLink = function(elementId) {
    const input = document.getElementById(elementId);
    if (!input) return;
    
    input.select();
    input.setSelectionRange(0, 99999);
    
    try {
        document.execCommand('copy');
        const btn = event.target.closest('.copy-btn');
        if (btn) {
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i>';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.classList.remove('copied');
            }, 2000);
        }
    } catch (err) {
        console.error('Ошибка копирования:', err);
    }
}

function showEmptyState(message) {
    const emptyHtml = `
        <div class="empty-state">
            <i class="fas fa-chart-simple"></i>
            <h3>Статистика отсутствует</h3>
            <p>${message}</p>
            <a href="/" class="btn btn-outline btn-sm" style="margin-top: 15px;">
                <i class="fas fa-trophy"></i> Найти турнир
            </a>
        </div>
    `;
    
    // Показываем заглушку во всех вкладках
    const contents = ['overallContent', 'rolesContent', 'placesContent', 'recordsContent'];
    contents.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = emptyHtml;
            el.style.display = 'block';
        }
    });
    
    // Обновляем бейдж
    const badge = document.getElementById('totalGamesBadge');
    if (badge) badge.textContent = '0';
    
    // Скрываем лоадеры
    hideLoaders();
}

function hideLoaders() {
    const loaders = ['loadingOverall', 'loadingRoles', 'loadingPlaces', 'loadingRecords'];
    loaders.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    
    const contents = ['overallContent', 'rolesContent', 'placesContent', 'recordsContent'];
    contents.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'block';
    });
}