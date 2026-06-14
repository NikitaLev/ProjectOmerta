document.addEventListener('DOMContentLoaded', function() {
    const tournamentId = JSON.parse(document.getElementById('tournamentId').textContent);
    const originalOrders = {};
    let selectedButton = null;

    // Сохраняем исходный порядок игроков для каждой игры
    document.querySelectorAll('.game-card').forEach(card => {
        const gameId = card.querySelector('.save-game-btn')?.dataset.gameId;
        if (gameId) {
            const rows = card.querySelectorAll('.seating-row');
            const originalOrder = [];
            rows.forEach(row => {
                const btn = row.querySelector('.player-button');
                if (btn) originalOrder.push(parseInt(btn.dataset.playerId));
            });
            originalOrders[gameId] = [...originalOrder];
        }
    });

    // Обновление текста «было на месте»
    function updatePreviousSeats(gameCard, originalOrder) {
        const rows = gameCard.querySelectorAll('.seating-row');
        rows.forEach((row, index) => {
            const btn = row.querySelector('.player-button');
            const prevSpan = row.querySelector('.prev-seat-badge');
            if (!btn || !prevSpan) return;

            const currentPlayerId = parseInt(btn.dataset.playerId);
            const originalPosition = originalOrder.indexOf(currentPlayerId);

            if (originalPosition !== -1 && originalPosition !== index) {
                prevSpan.innerHTML = `← с места ${originalPosition + 1}`;
                prevSpan.className = 'prev-seat-badge prev-seat-moved';
            } else if (originalPosition !== -1 && originalPosition === index) {
                prevSpan.innerHTML = `● на месте`;
                prevSpan.className = 'prev-seat-badge prev-seat-same';
            } else {
                prevSpan.innerHTML = `✦ новый`;
                prevSpan.className = 'prev-seat-badge prev-seat-new';
            }
        });
    }

    // Обмен игроками (меняем data-player-id и текст)
    function swapPlayers(btnA, btnB) {
        const rowA = btnA.closest('.seating-row');
        const rowB = btnB.closest('.seating-row');
        const gameCard = rowA.closest('.game-card');
        const gameId = gameCard.querySelector('.save-game-btn')?.dataset.gameId;

        const playerIdA = btnA.dataset.playerId;
        const playerIdB = btnB.dataset.playerId;
        const nameA = btnA.textContent;
        const nameB = btnB.textContent;

        btnA.dataset.playerId = playerIdB;
        btnA.textContent = nameB;
        btnB.dataset.playerId = playerIdA;
        btnB.textContent = nameA;

        if (gameId && originalOrders[gameId]) {
            updatePreviousSeats(gameCard, originalOrders[gameId]);
        }
        checkDuplicates(gameCard);
    }

    // Проверка дубликатов
    function checkDuplicates(gameCard) {
        const btns = gameCard.querySelectorAll('.player-button');
        const values = [];
        let hasDuplicate = false;
        let duplicateValue = null;

        btns.forEach(btn => {
            const val = btn.dataset.playerId;
            if (values.includes(val)) {
                hasDuplicate = true;
                duplicateValue = val;
            }
            values.push(val);
        });

        const warningDiv = gameCard.querySelector('.duplicate-warning');
        if (hasDuplicate) {
            const duplicateBtn = gameCard.querySelector(`.player-button[data-player-id="${duplicateValue}"]`);
            const duplicateName = duplicateBtn?.textContent || 'Игрок';
            warningDiv.style.display = 'flex';
            warningDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Ошибка: "${duplicateName}" не может быть на двух местах одновременно!`;
        } else {
            warningDiv.style.display = 'none';
            warningDiv.innerHTML = '';
        }
    }

    // Обработчик клика по кнопке игрока
    function onPlayerClick(event) {
        const btn = event.currentTarget;
        const gameCard = btn.closest('.game-card');
        if (gameCard.classList.contains('game-completed')) return;

        if (selectedButton === null) {
            selectedButton = btn;
            selectedButton.classList.add('selected');
        } else {
            if (selectedButton === btn) {
                selectedButton.classList.remove('selected');
                selectedButton = null;
                return;
            }
            swapPlayers(selectedButton, btn);
            selectedButton.classList.remove('selected');
            selectedButton = null;
        }
    }

    // Навешиваем обработчики
    document.querySelectorAll('.player-button').forEach(btn => {
        btn.addEventListener('click', onPlayerClick);
    });

    // Сохранение рассадки
    document.querySelectorAll('.save-game-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const gameId = this.dataset.gameId;
            const gameCard = this.closest('.game-card');
            const rows = gameCard.querySelectorAll('.seating-row');
            const btns = gameCard.querySelectorAll('.player-button');

            // Финальная проверка дубликатов
            let hasDuplicate = false;
            const values = [];
            btns.forEach(btn => {
                if (values.includes(btn.dataset.playerId)) hasDuplicate = true;
                values.push(btn.dataset.playerId);
            });

            if (hasDuplicate) {
                alert('❌ Ошибка: один игрок не может быть на двух местах!');
                return;
            }

            const newOrder = [];
            rows.forEach(row => {
                const button = row.querySelector('.player-button');
                newOrder.push(parseInt(button.dataset.playerId));
            });

            const saveBtn = this;
            const originalHtml = saveBtn.innerHTML;
            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
            saveBtn.disabled = true;

            fetch(`/tournament/${tournamentId}/seating/save/${gameId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ order: newOrder })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ ' + data.message);
                    // Обновляем оригинальный порядок после успешного сохранения
                    originalOrders[gameId] = [...newOrder];
                    updatePreviousSeats(gameCard, originalOrders[gameId]);
                } else {
                    alert('❌ ' + (data.error || 'Ошибка сохранения'));
                }
            })
            .catch(() => alert('❌ Ошибка сети'))
            .finally(() => {
                saveBtn.innerHTML = originalHtml;
                saveBtn.disabled = false;
            });
        });
    });

    function getCsrfToken() {
        // Ищем скрытое поле формы
        let csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrf) return csrf.value;
        
        // Ищем в мета-теге (часто используется в современных проектах)
        csrf = document.querySelector('meta[name="csrf-token"]');
        if (csrf) return csrf.getAttribute('content');
        
        // Если не нашли — выводим ошибку
        console.error('CSRF token not found');
        return '';
    }

    // Инициализация отображения «было»
    document.querySelectorAll('.game-card').forEach(card => {
        const gameId = card.querySelector('.save-game-btn')?.dataset.gameId;
        if (gameId && originalOrders[gameId]) {
            updatePreviousSeats(card, originalOrders[gameId]);
        }
    });
});