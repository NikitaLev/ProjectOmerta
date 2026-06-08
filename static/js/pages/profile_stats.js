// Глобальные переменные для графиков
let rolesChart = null;
let performanceChart = null;

async function loadPlayerStats() {
    try {
        const response = await fetch('/profile/stats/');
        if (!response.ok) throw new Error('Статистика не найдена');
        
        const profileData = await response.json();
        
        // Обновляем мини-статистику в левой колонке
        document.getElementById('miniTotalGames').textContent = profileData.total_games || 0;
        document.getElementById('miniTotalScore').textContent = (profileData.total_score || 0).toFixed(2);
        document.getElementById('miniWinrate').textContent = `${profileData.winrate || 0}%`;
        document.getElementById('miniBestPlace').textContent = profileData.best_place ? `${profileData.best_place}-е` : '—';
        
        if (!profileData.has_stats) {
            showEmptyState();
            return;
        }
        
        // Рендерим все блоки
        renderOverallStats(profileData);
        renderAvgStats(profileData);
        renderDetailsStats(profileData);
        renderRolesStats(profileData);
        renderRecordsStats(profileData);
        renderCharts(profileData);
        
        hideLoaders();
        
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        showErrorState();
    }
}

function renderOverallStats(data) {
    const html = `
        <div class="stat-card">
            <div class="stat-value">${data.total_games || 0}</div>
            <div class="stat-label">Всего игр</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${(data.total_score || 0).toFixed(2)}</div>
            <div class="stat-label">Всего очков</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.wins || 0}</div>
            <div class="stat-label">Побед</div>
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
    `;
    document.getElementById('overallStatsGrid').innerHTML = html;
}

function renderAvgStats(data) {
    const html = `
        <div class="stat-card">
            <div class="stat-value">${data.avg_score || 0}</div>
            <div class="stat-label">Средний балл</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.winrate || 0}%</div>
            <div class="stat-label">Винрейт</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.avg_bonus || 0}</div>
            <div class="stat-label">Средний бонус</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.avg_ci || 0}</div>
            <div class="stat-label">Средний Ci</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.avg_penalty || 0}</div>
            <div class="stat-label">Средний штраф</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.first_kill_rate || 0}%</div>
            <div class="stat-label">1-й убит %</div>
        </div>
    `;
    document.getElementById('avgStatsGrid').innerHTML = html;
}

function renderDetailsStats(data) {
    const html = `
        <div class="stat-card">
            <div class="stat-value">${(data.total_main || 0).toFixed(2)}</div>
            <div class="stat-label">Основные баллы</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${(data.total_bonus || 0).toFixed(2)}</div>
            <div class="stat-label">Бонусные баллы</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${(data.total_penalty || 0).toFixed(2)}</div>
            <div class="stat-label">Штрафные баллы</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${(data.total_ci || 0).toFixed(2)}</div>
            <div class="stat-label">Компенсационные (Ci)</div>
        </div>
    `;
    document.getElementById('detailsStatsGrid').innerHTML = html;
}

function getRoleIconHtml(roleKey) {
    const icons = {
        'don': '<span class="role-icon role-icon-don role-icon-md"></span>',
        'mafia': '<span class="role-icon role-icon-mafia role-icon-md"></span>',
        'sheriff': '<span class="role-icon role-icon-sheriff role-icon-md"></span>',
        'civil': '<span class="role-icon role-icon-civil role-icon-md"></span>'
    };
    return icons[roleKey] || icons['civil'];
}

function renderRolesStats(data) {
    const roles = data.roles || {};
    const roleList = ['don', 'mafia', 'sheriff', 'civil'];
    const roleNames = {
        'don': 'Дон', 'mafia': 'Мафия', 'sheriff': 'Шериф', 'civil': 'Мирный'
    };
    
    let html = '';
    for (const roleKey of roleList) {
        const role = roles[roleKey];
        if (role) {
            html += `
                <div class="role-card">
                    <div class="role-stat-icon">${getRoleIconHtml(roleKey)}</div>
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
                    <div class="role-stat-icon">${getRoleIconHtml(roleKey)}</div>
                    <div class="role-name">${roleNames[roleKey]}</div>
                    <div class="role-stats">Нет игр</div>
                </div>
            `;
        }
    }
    document.getElementById('rolesStatsGrid').innerHTML = html;
}

function renderRecordsStats(data) {
    let html = '';
    
    if (data.best_tournament) {
        html += `
            <div class="record-card">
                <div class="record-label">🏆 Лучший турнир</div>
                <div class="record-value">${data.best_tournament.score} очков</div>
                <div class="record-label" style="margin-top: 4px; font-size: 0.6rem;">${data.best_tournament.tournament_name}</div>
            </div>
        `;
    }
    
    html += `
        <div class="record-card">
            <div class="record-label">⭐ Лучший бонус за ЛХ</div>
            <div class="record-value">${data.best_lh_bonus || 0}</div>
        </div>
        <div class="record-card">
            <div class="record-label">🔥 Лучшая серия побед</div>
            <div class="record-value">${data.best_streak || 0}</div>
        </div>
    `;
    
    if (data.best_role) {
        html += `
            <div class="record-card">
                <div class="record-label">🎭 Лучшая роль</div>
                <div class="record-value">${data.best_role}</div>
            </div>
        `;
    }
    
    html += `
        <div class="record-card">
            <div class="record-label">🏅 Лучшее место</div>
            <div class="record-value">${data.best_place ? data.best_place + '-е' : '—'}</div>
        </div>
        <div class="record-card">
            <div class="record-label">📊 Всего турниров</div>
            <div class="record-value">${data.tournaments_count || 0}</div>
        </div>
    `;
    
    document.getElementById('recordsStatsGrid').innerHTML = html;
}

function renderCharts(data) {
    const totalGames = data.total_games || 1;
    
    // 1. Круговая диаграмма — распределение по ролям (оставляем)
    const roles = data.roles || {};
    const roleLabels = ['Дон', 'Мафия', 'Шериф', 'Мирный'];
    const roleCounts = [
        roles.don?.count || 0,
        roles.mafia?.count || 0,
        roles.sheriff?.count || 0,
        roles.civil?.count || 0
    ];
    const roleColors = ['#8b5cf6', '#a855f7', '#fbbf24', '#ef4444'];
    
    const ctx1 = document.getElementById('rolesChart')?.getContext('2d');
    if (ctx1) {
        if (rolesChart) rolesChart.destroy();
        rolesChart = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: roleLabels,
                datasets: [{
                    data: roleCounts,
                    backgroundColor: roleColors,
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#ccc', font: { size: 10 } } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                const total = roleCounts.reduce((a, b) => a + b, 0);
                                const percent = total > 0 ? ((ctx.raw / total) * 100).toFixed(2) : 0;
                                return `${ctx.label}: ${ctx.raw} игр (${percent}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // 2. Горизонтальная столбчатая диаграмма — ключевые показатели (новая)
    const ctx2 = document.getElementById('performanceChart')?.getContext('2d');
    if (ctx2) {
        if (performanceChart) performanceChart.destroy();
        
        // Нормализованные показатели (0-100)
        const winPercent = (data.wins / totalGames * 100).toFixed(2);
        const firstKillPercent = (data.first_kills / totalGames * 100).toFixed(2);
        const avgBonusPerGame = (data.avg_bonus * 10).toFixed(2); // бонус до 10 = 100%
        const avgCiPerGame = (data.avg_ci * 50).toFixed(2); // Ci до 0.4 = 100%
        const cleanPercent = Math.max(0, 100 - (data.yellow_cards / totalGames * 25)).toFixed(2);
        
        const metrics = {
            'Победы': Math.min(100, winPercent),
            'Первые убийства': Math.min(100, firstKillPercent),
            'Средний бонус': Math.min(100, avgBonusPerGame),
            'Компенсация Ci': Math.min(100, avgCiPerGame),
            'Чистота игры': Math.min(100, cleanPercent)
        };
        
        performanceChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: Object.keys(metrics),
                datasets: [{
                    label: 'Показатель (нормализован, %)',
                    data: Object.values(metrics),
                    backgroundColor: 'rgba(212, 175, 55, 0.7)',
                    borderRadius: 8,
                    borderColor: '#d4af37',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y', // Горизонтальная ориентация
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                let originalValue = '';
                                if (context.label === 'Победы') originalValue = `${data.wins} / ${totalGames} (${value}%)`;
                                else if (context.label === 'Первые убийства') originalValue = `${data.first_kills} / ${totalGames} (${value}%)`;
                                else if (context.label === 'Средний бонус') originalValue = `${data.avg_bonus} / 10 (${value}%)`;
                                else if (context.label === 'Компенсация Ci') originalValue = `${data.avg_ci} / 0.4 (${value}%)`;
                                else if (context.label === 'Чистота игры') originalValue = `Без карточек в ${value}% игр`;
                                return `${context.dataset.label}: ${value}% — ${originalValue}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        max: 100,
                        title: { display: true, text: '% от максимума', color: '#ccc', font: { size: 10 } },
                        ticks: { color: '#ccc', stepSize: 20 },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    y: {
                        ticks: { color: '#ccc', font: { size: 11 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }
}

function showEmptyState() {
    const emptyHtml = `<div class="empty-state"><i class="fas fa-chart-simple"></i><p>Нет данных для отображения</p></div>`;
    const containers = ['overallStatsGrid', 'avgStatsGrid', 'detailsStatsGrid', 'rolesStatsGrid', 'recordsStatsGrid'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = emptyHtml;
    });
    hideLoaders();
}

function showErrorState() {
    const errorHtml = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Ошибка загрузки статистики</p></div>`;
    const containers = ['overallStatsGrid', 'avgStatsGrid', 'detailsStatsGrid', 'rolesStatsGrid', 'recordsStatsGrid'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = errorHtml;
    });
    hideLoaders();
}

function hideLoaders() {
    const loaders = document.querySelectorAll('.loading-spinner');
    loaders.forEach(loader => loader.style.display = 'none');
}

// Запуск при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadPlayerStats();
});