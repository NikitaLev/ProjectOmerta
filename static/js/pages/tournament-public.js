document.addEventListener('DOMContentLoaded', function() {
    console.log('=== tournament-public.js загружен ===');
    
    const tabs = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    // Переключение вкладок
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            tabPanes.forEach(pane => pane.classList.remove('active'));
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            loadTabData(tabId);
        });
    });
    
    // Загружаем данные для активной вкладки
    loadTabData('stats');
    
    function loadTabData(tabId) {
        if (tabId === 'stats') {
            loadStatsData();
        } else if (tabId === 'games') {
            loadGamesData();
        }
    }
    
    function loadStatsData() {
        const loadingEl = document.querySelector('#tab-stats .stats-loading');
        const contentEl = document.querySelector('#tab-stats .stats-content');
        
        if (contentEl.style.display !== 'none') return;
        
        const tournamentId = window.location.pathname.split('/')[2];
        
        fetch(`/tournament/${tournamentId}/public/stats/`)
            .then(response => response.json())
            .then(data => {
                renderStats(data);
                loadingEl.style.display = 'none';
                contentEl.style.display = 'block';
            })
            .catch(error => {
                console.error('Error loading stats:', error);
                loadingEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Ошибка загрузки статистики';
            });
    }
    
    function loadGamesData() {
        const loadingEl = document.querySelector('#tab-games .games-loading');
        const contentEl = document.querySelector('#tab-games .games-content');
        
        if (contentEl.style.display !== 'none') return;
        
        const tournamentId = window.location.pathname.split('/')[2];
        
        fetch(`/tournament/${tournamentId}/public/games/`)
            .then(response => response.json())
            .then(data => {
                renderGames(data);
                loadingEl.style.display = 'none';
                contentEl.style.display = 'block';
            })
            .catch(error => {
                console.error('Error loading games:', error);
                loadingEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Ошибка загрузки игр';
            });
    }
    
    function renderStats(data) {
        const template = document.getElementById('player-stats-template').content.cloneNode(true);
        const container = document.querySelector('#tab-stats .stats-content');
        container.innerHTML = '';
        
        template.querySelector('#total-games').textContent = data.tournament.total_games;
        template.querySelector('#completed-games').textContent = data.tournament.completed_games;
        
        const tbody = template.querySelector('#players-stats-body');
        
        data.players.sort((a, b) => b.total_score - a.total_score).forEach(player => {
            const row = document.createElement('tr');
            
            row.innerHTML = `
                <td class="player-name-cell">${player.nickname}</td>
                <td><strong>${player.total_score}</strong></td>
                <td>${player.wins}</td>
                <td>${player.first_kills}</td>
                <td>${player.lh_bonus}</td>
                <td>${player.bonus_score}</td>
                <td>${player.penalty_score}</td>
                <td>${player.ci}</td>
                <td>
                    ${player.yellow_cards > 0 ? `<span class="card-badge yellow" title="Жёлтые">Ж:${player.yellow_cards}</span>` : ''}
                    ${player.red_cards > 0 ? `<span class="card-badge red" title="Красные">К:${player.red_cards}</span>` : ''}
                </td>
                <td>${player.roles.don}</td>
                <td>${player.roles.mafia}</td>
                <td>${player.roles.sheriff}</td>
                <td>${player.roles.civil}</td>
            `;
            
            tbody.appendChild(row);
        });
        
        container.appendChild(template);
    }
    
    function renderGames(data) {
        const template = document.getElementById('games-list-template').content.cloneNode(true);
        const container = document.querySelector('#tab-games .games-content');
        container.innerHTML = '';
        
        template.querySelector('#games-total').textContent = data.total_games;
        template.querySelector('#games-completed').textContent = data.completed_games;
        
        const grid = template.querySelector('#public-games-grid');
        
        data.games.forEach(game => {
            const cardTemplate = document.getElementById('game-card-template').content.cloneNode(true);
            
            // Номер игры
            cardTemplate.querySelector('.round-number').textContent = game.round_number;
            
            // Статус
            const statusBadge = cardTemplate.querySelector('.game-status-badge');
            if (game.winning_team) {
                statusBadge.classList.add('completed');
                statusBadge.innerHTML = '<i class="fas fa-check-circle"></i> Завершена';
            } else {
                statusBadge.classList.add('pending');
                statusBadge.innerHTML = '<i class="fas fa-clock"></i> Ожидает';
            }
            
            // Находим максимальный total_score для этой игры (MVP)
            let maxTotal = 0;
            game.seating.forEach(seat => {
                if (seat.total_score > maxTotal) {
                    maxTotal = seat.total_score;
                }
            });
            
            // Рассадка
            const seatingList = cardTemplate.querySelector('#seating-list');
            seatingList.innerHTML = '';
            
            game.seating.forEach(seat => {
                const seatItem = document.createElement('div');
                
                // Формируем классы для seat-item
                let seatClasses = 'seat-item';
                
                // Жёлтые/красные карточки
                if (seat.yellow_cards === 1) {
                    seatClasses += ' has-yellow';
                } else if (seat.yellow_cards >= 2) {
                    seatClasses += ' has-red';
                }
                
                // MVP (если у игрока максимальный балл в игре и он > 0)
                if (seat.total_score === maxTotal && maxTotal > 0) {
                    seatClasses += ' mvp';
                }
                
                seatItem.className = seatClasses;
                
                // Строим HTML для баллов
                let statsHtml = '<div class="player-stats">';
                
                // Основные баллы (всегда показываем)
                statsHtml += `<span class="stat-badge main" title="Основные"><i class="fas fa-star"></i> ${seat.main_score.toFixed(2)}</span>`;
                
                // Бонус (если не 0)
                if (seat.bonus_score !== 0) {
                    statsHtml += `<span class="stat-badge bonus" title="Бонус"><i class="fas fa-plus-circle"></i> ${seat.bonus_score.toFixed(2)}</span>`;
                }
                
                // Штраф (если не 0)
                if (seat.penalty_score !== 0) {
                    statsHtml += `<span class="stat-badge penalty" title="Штраф"><i class="fas fa-minus-circle"></i> ${seat.penalty_score.toFixed(2)}</span>`;
                }
                
                // Ci (если не 0)
                if (seat.ci !== 0) {
                    statsHtml += `<span class="stat-badge ci" title="Ci"><i class="fas fa-shield-alt"></i> ${seat.ci.toFixed(2)}</span>`;
                }
                
                // Итого (всегда показываем)
                statsHtml += `<span class="stat-badge total" title="Итого"><i class="fas fa-calculator"></i> ${seat.total_score.toFixed(2)}</span>`;
                
                statsHtml += '</div>';
                
                // HTML с иконкой роли
                let roleIconHtml = '';
                if (seat.role) {
                    const roleMap = {
                        'don': '<i class="ph-fill ph-crown-simple" style="color: #d4af37;"></i>',
                        'mafia': '<i class="bi bi-hand-thumbs-down-fill" style="color: #6b21a5;"></i>',
                        'sheriff': '<i class="mdi mdi-police-badge" style="color: #fbbf24;"></i>',
                        'civil': '<i class="bi bi-hand-thumbs-up-fill" style="color: #ef4444;"></i>'
                    };
                    roleIconHtml = `<span class="player-role-badge" title="${getRoleName(seat.role)}">${roleMap[seat.role] || ''}</span>`;
                }
                
                seatItem.innerHTML = `
                    <span class="seat-number">${seat.position}</span>
                    <div class="player-info">
                        <span class="player-nickname">${escapeHtml(seat.nickname)}</span>
                        ${roleIconHtml}
                    </div>
                    ${statsHtml}
                `;
                
                seatingList.appendChild(seatItem);
            });
            
            // Победитель
            const winnerInfo = cardTemplate.querySelector('.game-winner-info');
            if (game.winning_team) {
                winnerInfo.style.display = 'flex';
                winnerInfo.innerHTML = `
                    <span class="winner-label">Победа:</span>
                    <span class="winner-team ${game.winning_team === 'mafia' ? 'mafia' : 'peace'}">
                        ${game.winning_team === 'mafia' ? '<i class="fas fa-skull"></i> Мафия' : '<i class="fas fa-users"></i> Мирные'}
                    </span>
                `;
            } else {
                winnerInfo.style.display = 'none';
            }
            
            // Кнопка просмотра
            const viewBtn = cardTemplate.querySelector('.view-game-btn');
            const tournamentId = window.location.pathname.split('/')[2];
            viewBtn.href = `/tournament/${tournamentId}/game/${game.round_number}/public-view/`;
            
            grid.appendChild(cardTemplate);
        });
        
        container.appendChild(template);
    }

    // Вспомогательная функция для получения имени роли
    function getRoleName(role) {
        const roleNames = {
            'don': 'Дон',
            'mafia': 'Мафия',
            'sheriff': 'Шериф',
            'civil': 'Мирный'
        };
        return roleNames[role] || role;
    }

    // Вспомогательная функция для экранирования HTML (безопасность)
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    function renderStats(data) {
        const template = document.getElementById('player-stats-template').content.cloneNode(true);
        const container = document.querySelector('#tab-stats .stats-content');
        const completedStatsContainer = document.querySelector('#tab-stats .completed-stats-container');
        
        container.innerHTML = '';
        
        template.querySelector('#total-games').textContent = data.tournament.total_games;
        template.querySelector('#completed-games').textContent = data.tournament.completed_games;

        const tbody = template.querySelector('#players-stats-body');
        
        // Сортируем игроков по сумме баллов (убывание)
        const sortedPlayers = [...data.players].sort((a, b) => b.total_score - a.total_score);
        
        // Рассчитываем места (с учётом равенства баллов)
        let currentPlace = 1;
        let previousScore = null;
        
        sortedPlayers.forEach((player, index) => {
            // Если баллы совпадают с предыдущим игроком, место то же
            if (index > 0 && player.total_score === previousScore) {
                // Место не меняем
            } else {
                currentPlace = index + 1;
            }
            
            // Определяем класс для значка места
            let placeClass = '';
            if (currentPlace === 1) {
                placeClass = 'first';
            } else if (currentPlace === 2) {
                placeClass = 'second';
            } else if (currentPlace === 3) {
                placeClass = 'third';
            }
            
            const row = document.createElement('tr');
            
            row.innerHTML = `
                <td class="player-name-cell">
                    <span class="place-badge ${placeClass}">${currentPlace}</span>
                    ${escapeHtml(player.nickname)}
                </td>
                <td><strong>${player.total_score}</strong></td>
                <td>${player.wins}</td>
                <td>${player.first_kills}</td>
                <td>${player.lh_bonus}</td>
                <td>${player.bonus_score}</td>
                <td>${player.penalty_score}</td>
                <td>${player.ci}</td>
                <td>
                    ${player.yellow_cards > 0 ? `<span class="card-badge yellow" title="Жёлтые">Ж:${player.yellow_cards}</span>` : ''}
                    ${player.red_cards > 0 ? `<span class="card-badge red" title="Красные">К:${player.red_cards}</span>` : ''}
                    ${player.yellow_cards === 0 && player.red_cards === 0 ? '—' : ''}
                </td>
                <td>${player.roles.don}</td>
                <td>${player.roles.mafia}</td>
                <td>${player.roles.sheriff}</td>
                <td>${player.roles.civil}</td>
            `;
            
            tbody.appendChild(row);
            previousScore = player.total_score;
        });
        
        container.appendChild(template);
        
        // Если турнир завершён, показываем дополнительную статистику
        if (data.tournament.status === 'completed' && data.completed_stats) {
            renderCompletedStats(data.completed_stats, completedStatsContainer);
            completedStatsContainer.style.display = 'block';
        } else {
            completedStatsContainer.style.display = 'none';
        }
    }

    // Вспомогательная функция для экранирования HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderCompletedStats(stats, container) {
        container.innerHTML = '';
        
        // Статистика команд
        if (stats.team_stats) {
            const teamStatsHtml = `
                <div class="stats-category">
                    <h3>Статистика команд</h3>
                    <div class="team-stats">
                        <div class="team-card mafia">
                            <i class="fas fa-skull"></i>
                            <div class="team-name">Мафия</div>
                            <div class="team-wins">${stats.team_stats.mafia_wins} побед</div>
                        </div>
                        <div class="team-card peace">
                            <i class="fas fa-users"></i>
                            <div class="team-name">Мирные</div>
                            <div class="team-wins">${stats.team_stats.peace_wins} побед</div>
                        </div>
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', teamStatsHtml);
        }
        
        // Лучшие по ролям
        if (stats.best_per_role) {
            let rolesHtml = `
                <div class="stats-category">
                    <h3>Лучшие по ролям</h3>
                    <div class="stats-grid">
            `;
            
            for (const [role, data] of Object.entries(stats.best_per_role)) {
                let roleIcon = '';
                let roleName = '';
                
                switch(role) {
                    case 'don':
                        roleIcon = '<i class="ph-fill ph-crown-simple"></i>';
                        roleName = 'Дон';
                        break;
                    case 'mafia':
                        roleIcon = '<i class="bi bi-hand-thumbs-down-fill"></i>';
                        roleName = 'Мафия';
                        break;
                    case 'sheriff':
                        roleIcon = '<i class="mdi mdi-police-badge"></i>';
                        roleName = 'Шериф';
                        break;
                    default:
                        roleIcon = '<i class="bi bi-hand-thumbs-up-fill"></i>';
                        roleName = 'Мирный';
                }
                
                rolesHtml += `
                    <div class="stat-card">
                        <div class="role-icon">${roleIcon}</div>
                        <div class="role-name">${roleName}</div>
                        <div class="player-name">${data.player_name}</div>
                        <div class="stats-detail">
                            <span>Бонус: ${data.total_bonus.toFixed(2)}</span>
                            <span>Игр: ${data.games_played}</span>
                        </div>
                    </div>
                `;
            }
            
            rolesHtml += `</div></div>`;
            container.insertAdjacentHTML('beforeend', rolesHtml);
        }
        
        // Рекорды
        let recordsHtml = `
            <div class="stats-category">
                <h3>Рекорды турнира</h3>
                <div class="records-grid">
        `;
        
        if (stats.most_killed) {
            recordsHtml += `
                <div class="record-card">
                    <i class="fas fa-skull"></i>
                    <div class="record-label">Чаще всех убивали</div>
                    <div class="record-value">${stats.most_killed.player_name}</div>
                    <div class="record-count">${stats.most_killed.count} раз</div>
                </div>
            `;
        }
        
        if (stats.most_stable) {
            recordsHtml += `
                <div class="record-card">
                    <i class="fas fa-chart-line"></i>
                    <div class="record-label">Самый стабильный</div>
                    <div class="record-value">${stats.most_stable.player_name}</div>
                    <div class="record-count">Отклонение: ${stats.most_stable.variance}</div>
                </div>
            `;
        }
        
        if (stats.top_main) {
            recordsHtml += `
                <div class="record-card">
                    <i class="fas fa-star"></i>
                    <div class="record-label">Самый результативный</div>
                    <div class="record-value">${stats.top_main.player_name}</div>
                    <div class="record-count">Основных баллов: ${stats.top_main.total_main}</div>
                </div>
            `;
        }
        
        if (stats.top_bonus) {
            recordsHtml += `
                <div class="record-card">
                    <i class="fas fa-plus-circle"></i>
                    <div class="record-label">Самый бонусный</div>
                    <div class="record-value">${stats.top_bonus.player_name}</div>
                    <div class="record-count">Бонусов: ${stats.top_bonus.total_bonus}</div>
                </div>
            `;
        }
        
        if (stats.top_yellow) {
            recordsHtml += `
                <div class="record-card">
                    <i class="fas fa-square"></i>
                    <div class="record-label">Больше всех карточек</div>
                    <div class="record-value">${stats.top_yellow.player_name}</div>
                    <div class="record-count">${stats.top_yellow.total_yellow} шт</div>
                </div>
            `;
        }
        
        recordsHtml += `</div></div>`;
        container.insertAdjacentHTML('beforeend', recordsHtml);
    }
});