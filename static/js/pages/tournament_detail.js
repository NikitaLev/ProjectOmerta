// tournament_detail.js - скрипты для страницы управления турниром

document.addEventListener('DOMContentLoaded', function() {
    // ========== ПОЛУЧАЕМ ДАННЫЕ ИЗ HTML ==========
    const modal = document.getElementById('addPlayersModal');
    const deleteModal = document.getElementById('deleteTournamentModal');
    const deleteForm = document.getElementById('deleteTournamentForm');
    const showDeleteBtn = document.getElementById('showDeleteModal');
    
    // Данные из data-атрибутов
    const tournamentId = modal ? modal.dataset.tournamentId : null;
    const tournamentName = modal ? modal.dataset.tournamentName : '';
    let currentPlayersCount = modal ? parseInt(modal.dataset.currentCount) : 0;
    let maxPlayers = modal ? parseInt(modal.dataset.maxPlayers) : 0;
    
    // ========== МОДАЛЬНОЕ ОКНО ДОБАВЛЕНИЯ ИГРОКОВ ==========
    if (modal) {
        const showBtn = document.getElementById('showAddPlayers');
        const closeBtn = modal.querySelector('.close-modal');
        const closeFooterBtn = modal.querySelector('.close-modal-btn');
        const searchInput = document.getElementById('playerSearchInputMulti');
        const addBtn = document.getElementById('addSelectedPlayersBtn');
        const selectAllBtn = document.getElementById('selectAllBtn');
        const selectNoneBtn = document.getElementById('selectNoneBtn');
        const selectedCountSpan = document.getElementById('selectedCount');
        const selectedCountFooter = document.getElementById('selectedCountFooter');
        const playersListDiv = document.getElementById('playersCheckboxList');
        const selectedPlayersPanel = document.getElementById('selectedPlayersPanel');
        const selectedPlayersListDiv = document.getElementById('selectedPlayersList');
        const selectedPlayersCountBadge = document.getElementById('selectedPlayersCountBadge');
        const selectedPlayersWarning = document.getElementById('selectedPlayersWarning');
        const availableSlotsSpan = document.getElementById('availableSlots');
        
        let allPlayers = [];
        let filteredPlayers = [];
        let selectedPlayers = new Map(); // id -> {nickname, username}
        
        // Функция обновления интерфейса
        function updateUI() {
            const totalSelected = selectedPlayers.size;
            const availableSlots = maxPlayers - currentPlayersCount;
            const canAdd = totalSelected <= availableSlots && totalSelected > 0;
            
            selectedCountSpan.textContent = totalSelected;
            if (selectedPlayersCountBadge) selectedPlayersCountBadge.textContent = totalSelected;
            
            if (totalSelected > 0) {
                if (selectedCountFooter) selectedCountFooter.style.display = 'flex';
                if (selectedPlayersPanel) selectedPlayersPanel.style.display = 'block';
                if (addBtn) addBtn.disabled = !canAdd;
            } else {
                if (selectedCountFooter) selectedCountFooter.style.display = 'none';
                if (selectedPlayersPanel) selectedPlayersPanel.style.display = 'none';
                if (addBtn) addBtn.disabled = true;
            }
            
            if (totalSelected > availableSlots && availableSlotsSpan) {
                availableSlotsSpan.textContent = availableSlots;
                if (selectedPlayersWarning) selectedPlayersWarning.style.display = 'flex';
            } else {
                if (selectedPlayersWarning) selectedPlayersWarning.style.display = 'none';
            }
            
            // Обновляем галочки
            document.querySelectorAll('.player-checkbox').forEach(cb => {
                cb.checked = selectedPlayers.has(parseInt(cb.value));
            });
            
            renderSelectedPlayersList();
        }
        
        // Отображение выбранных игроков
        function renderSelectedPlayersList() {
            if (!selectedPlayersListDiv) return;
            
            if (selectedPlayers.size === 0) {
                selectedPlayersListDiv.innerHTML = '<div style="padding: 15px; text-align: center; color: var(--text-secondary);">Никого не выбрано</div>';
                return;
            }
            
            let html = '';
            for (const [id, player] of selectedPlayers) {
                html += `
                    <div class="selected-player-tag" data-id="${id}">
                        <span>${escapeHtml(player.nickname)}</span>
                        <span class="remove-player" data-id="${id}">
                            <i class="fas fa-times-circle"></i>
                        </span>
                    </div>
                `;
            }
            selectedPlayersListDiv.innerHTML = html;
            
            document.querySelectorAll('.remove-player').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const id = parseInt(this.dataset.id);
                    selectedPlayers.delete(id);
                    updateUI();
                });
            });
        }
        
        // Загрузка списка игроков
        function loadPlayersList() {
            if (!playersListDiv) return;
            playersListDiv.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner"></i> Загрузка...</div>';
            
            fetch(`/tournament/${tournamentId}/players/`)
                .then(response => response.json())
                .then(data => {
                    allPlayers = data.players || [];
                    filteredPlayers = [...allPlayers];
                    renderPlayersList(filteredPlayers);
                })
                .catch(error => {
                    playersListDiv.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Ошибка загрузки</p></div>';
                });
        }
        
        // Отображение списка игроков с чекбоксами
        function renderPlayersList(players) {
            if (!playersListDiv) return;
            
            if (players.length === 0) {
                playersListDiv.innerHTML = '<div class="empty-state"><i class="fas fa-user-slash"></i><p>Нет доступных игроков</p></div>';
                return;
            }
            
            let html = '';
            players.forEach(player => {
                const isChecked = selectedPlayers.has(player.id) ? 'checked' : '';
                html += `
                    <label class="player-checkbox-item">
                        <input type="checkbox" class="player-checkbox" value="${player.id}" data-nickname="${escapeHtml(player.nickname)}" data-username="${escapeHtml(player.username)}" ${isChecked}>
                        <div class="player-checkbox-info">
                            <span class="player-checkbox-nickname">${escapeHtml(player.nickname)}</span>
                            <span class="player-checkbox-username">@${escapeHtml(player.username)}</span>
                        </div>
                    </label>
                `;
            });
            playersListDiv.innerHTML = html;
            
            document.querySelectorAll('.player-checkbox').forEach(cb => {
                cb.addEventListener('change', function() {
                    const id = parseInt(this.value);
                    const nickname = this.dataset.nickname;
                    const username = this.dataset.username;
                    
                    if (this.checked) {
                        selectedPlayers.set(id, { nickname, username });
                    } else {
                        selectedPlayers.delete(id);
                    }
                    updateUI();
                });
            });
            
            updateUI();
        }
        
        // Открыть модальное окно
        if (showBtn) {
            showBtn.addEventListener('click', function(e) {
                e.preventDefault();
                modal.style.display = 'block';
                loadPlayersList();
            });
        }
        
        // Закрытие модального окна
        function closeModal() {
            modal.style.display = 'none';
            if (searchInput) searchInput.value = '';
            selectedPlayers.clear();
            updateUI();
        }
        
        if (closeBtn) closeBtn.addEventListener('click', closeModal);
        if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeModal);
        
        window.addEventListener('click', function(e) {
            if (e.target === modal) closeModal();
        });
        
        // Поиск
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                const query = this.value.toLowerCase().trim();
                if (query === '') {
                    filteredPlayers = [...allPlayers];
                } else {
                    filteredPlayers = allPlayers.filter(player => 
                        player.nickname.toLowerCase().includes(query)
                    );
                }
                renderPlayersList(filteredPlayers);
            });
        }
        
        // Выбрать всех
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', function() {
                const availableSlots = maxPlayers - currentPlayersCount;
                const currentSelected = selectedPlayers.size;
                const canSelectMore = availableSlots - currentSelected;
                
                let added = 0;
                for (const player of filteredPlayers) {
                    if (!selectedPlayers.has(player.id)) {
                        if (added >= canSelectMore) break;
                        selectedPlayers.set(player.id, { 
                            nickname: player.nickname, 
                            username: player.username 
                        });
                        added++;
                    }
                }
                renderPlayersList(filteredPlayers);
                updateUI();
            });
        }
        
        // Снять всех
        if (selectNoneBtn) {
            selectNoneBtn.addEventListener('click', function() {
                selectedPlayers.clear();
                renderPlayersList(filteredPlayers);
                updateUI();
            });
        }
        
        // Массовое добавление
        if (addBtn) {
            addBtn.addEventListener('click', function() {
                const selectedIds = Array.from(selectedPlayers.keys());
                if (selectedIds.length === 0) return;
                
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/tournament/${tournamentId}/add-multiple/`;
                
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
                if (csrfToken) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'csrfmiddlewaretoken';
                    input.value = csrfToken.value;
                    form.appendChild(input);
                }
                
                selectedIds.forEach(id => {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'player_ids';
                    input.value = id;
                    form.appendChild(input);
                });
                
                document.body.appendChild(form);
                form.submit();
            });
        }
        
        // Переключение вкладок
        const tabExisting = document.getElementById('tabExisting');
        const tabNew = document.getElementById('tabNew');
        const existingTab = document.getElementById('existingPlayersTab');
        const newTab = document.getElementById('newPlayerTab');
        const addExistingBtn = document.getElementById('addSelectedPlayersBtn');
        const addNewBtn = document.getElementById('createNewPlayerBtn');
        
        if (tabExisting) {
            tabExisting.addEventListener('click', function() {
                tabExisting.classList.add('active');
                tabNew.classList.remove('active');
                existingTab.classList.add('active');
                newTab.classList.remove('active');
                if (addExistingBtn) addExistingBtn.style.display = 'block';
                if (addNewBtn) addNewBtn.style.display = 'none';
                loadPlayersList();
            });
        }
        
        if (tabNew) {
            tabNew.addEventListener('click', function() {
                tabNew.classList.add('active');
                tabExisting.classList.remove('active');
                newTab.classList.add('active');
                existingTab.classList.remove('active');
                if (addExistingBtn) addExistingBtn.style.display = 'none';
                if (addNewBtn) addNewBtn.style.display = 'block';
            });
        }
        
        // Создание нового игрока
        const createNewBtn = document.getElementById('createNewPlayerBtn');
        if (createNewBtn) {
            createNewBtn.addEventListener('click', function() {
                document.getElementById('newPlayerForm').submit();
            });
        }
    }
    
    // ========== МОДАЛЬНОЕ ОКНО УДАЛЕНИЯ ТУРНИРА ==========
    if (deleteModal && showDeleteBtn && deleteForm) {
        showDeleteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const nameSpan = document.getElementById('deleteTournamentName');
            if (nameSpan) nameSpan.textContent = tournamentName;
            deleteForm.action = `/tournament/${tournamentId}/delete/`;
            deleteModal.style.display = 'block';
        });
        
        function closeDeleteModal() {
            deleteModal.style.display = 'none';
        }
        
        document.querySelectorAll('.close-delete-modal, .close-delete-modal-btn').forEach(btn => {
            btn.addEventListener('click', closeDeleteModal);
        });
        
        window.addEventListener('click', function(e) {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }
    
    // ========== СОРТИРОВКА ТАБЛИЦЫ ==========
    const sortHeader = document.querySelector('.player-cell.sortable');
    if (sortHeader) {
        let currentSort = { column: 'score', order: 'desc' };
        
        function updateSortIcon(order) {
            const icon = sortHeader.querySelector('i.fa-sort, i.fa-sort-up, i.fa-sort-down');
            if (!icon) return;
            icon.classList.remove('fa-sort', 'fa-sort-up', 'fa-sort-down');
            if (order === 'desc') {
                icon.classList.add('fa-sort-down');
            } else {
                icon.classList.add('fa-sort-up');
            }
        }
        
        function sortTable(order) {
            const table = document.querySelector('.players-table');
            const rows = Array.from(document.querySelectorAll('.players-table-row'));
            rows.sort((a, b) => {
                const scoreA = parseFloat(a.querySelector('.player-total-score')?.textContent) || 0;
                const scoreB = parseFloat(b.querySelector('.player-total-score')?.textContent) || 0;
                return order === 'desc' ? scoreB - scoreA : scoreA - scoreB;
            });
            rows.forEach(row => table.appendChild(row));
            currentSort.order = order;
            updateSortIcon(order);
        }
        
        sortTable('desc');
        sortHeader.addEventListener('click', function() {
            const newOrder = currentSort.order === 'desc' ? 'asc' : 'desc';
            sortTable(newOrder);
        });
    }
    
    // ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});