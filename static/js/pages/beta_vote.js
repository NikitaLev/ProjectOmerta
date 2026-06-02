let players = [];
let nominated = [];
let votes = {};
let alivePlayers = [];
let totalVoters = 0;
let roundNumber = 1;

document.addEventListener('DOMContentLoaded', function() {
    loadVotingData();
    setupKeyboard();
});

function setupKeyboard() {
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'z') {
            e.preventDefault();
            undo();
        }
    });
}

function loadVotingData() {
    const savedData = sessionStorage.getItem('voting_data');
    
    if (!savedData) {
        showEmptyState();
        return;
    }
    
    const data = JSON.parse(savedData);
    players = data.players || [];
    nominated = data.nominated || [];
    alivePlayers = data.alivePlayers || Array.from({length: players.length}, (_, i) => i + 1);
    votes = data.votes || {};
    roundNumber = data.roundNumber || 1;
    
    // Получаем актуальные фолы и выбывших
    const fouls = JSON.parse(sessionStorage.getItem('beta_fouls') || '{}');
    const eliminated = JSON.parse(sessionStorage.getItem('beta_eliminated') || '[]');
    
    // Обновляем alivePlayers: живые = не в eliminated И фолов < 4
    const updatedAlivePlayers = [];
    for (let i = 1; i <= 10; i++) {
        const foulCount = fouls[i] || 0;
        if (!eliminated.includes(i) && foulCount < 4) {
            updatedAlivePlayers.push(i);
        }
    }
    alivePlayers = updatedAlivePlayers;
    totalVoters = alivePlayers.length;
    
    // Фильтруем nominated: только живые кандидаты
    nominated = nominated.filter(p => alivePlayers.includes(p.num));
    
    if (nominated.length === 0) {
        showEmptyState();
        return;
    }
    
    renderNominatedList();
    updateTotalInfo();
    addLog(`📋 Раунд ${roundNumber}. Выставлены кандидаты в порядке очереди`);
}

function showEmptyState() {
    const container = document.getElementById('nominatedList');
    if (container) {
        container.innerHTML = '<div class="empty-state">📭 Нет выставленных игроков</div>';
    }
}

function getMaxVotesForPlayer(currentIndex) {
    let previousTotal = 0;
    for (let i = 0; i < currentIndex; i++) {
        const prevPlayer = nominated[i];
        previousTotal += votes[prevPlayer.num] || 0;
    }
    return totalVoters - previousTotal;
}

function renderNominatedList() {
    const container = document.getElementById('nominatedList');
    if (!container) return;
    container.innerHTML = '';
    
    nominated.forEach((player, idx) => {
        const currentVotes = votes[player.num] || 0;
        const maxVotes = getMaxVotesForPlayer(idx);
        
        let voteButtons = '';
        for (let i = 0; i <= maxVotes; i++) {
            const isSelected = (currentVotes === i);
            voteButtons += `
                <button class="vote-option ${isSelected ? 'selected' : ''}" 
                        onclick="setVotes(${player.num}, ${i}, ${idx})">
                    ${i}
                </button>
            `;
        }
        
        container.innerHTML += `
            <div class="nominated-item" id="nominee${player.num}" data-index="${idx}">
                <div class="nominated-info">
                    <div class="nominated-number">${player.num}</div>
                    <div class="nominated-name">${player.name}</div>
                    <div class="nominated-by">выставил №${player.nominatedBy}</div>
                </div>
                <div class="vote-controls">
                    <div class="vote-buttons" id="voteButtons${player.num}">
                        ${voteButtons}
                    </div>
                    <div class="current-votes">текущий: ${currentVotes}</div>
                </div>
            </div>
        `;
    });
}

function setVotes(playerNum, value, currentIndex) {
    let previousTotal = 0;
    for (let i = 0; i < currentIndex; i++) {
        const prevPlayer = nominated[i];
        previousTotal += votes[prevPlayer.num] || 0;
    }
    
    let nextTotal = 0;
    for (let i = currentIndex + 1; i < nominated.length; i++) {
        const nextPlayer = nominated[i];
        nextTotal += votes[nextPlayer.num] || 0;
    }
    
    const maxForThis = totalVoters - previousTotal;
    const newTotal = previousTotal + value + nextTotal;
    
    if (value > maxForThis) {
        addLog(`❌ Нельзя: максимум ${maxForThis} голосов для этого кандидата`);
        return;
    }
    
    if (newTotal > totalVoters) {
        addLog(`❌ Нельзя: превышение общего числа голосов`);
        return;
    }
    
    const oldValue = votes[playerNum] || 0;
    votes[playerNum] = value;
    
    addLog(`🗳️ Игрок №${playerNum} ${players[playerNum-1]} - ${value} голосов (было ${oldValue})`);
    
    updatePlayerVoteButtons(playerNum, currentIndex);
    
    for (let i = currentIndex + 1; i < nominated.length; i++) {
        const nextPlayer = nominated[i];
        updatePlayerVoteButtons(nextPlayer.num, i);
    }
    
    updateTotalInfo();
    saveToSession();
}

function updatePlayerVoteButtons(playerNum, playerIndex) {
    const currentVotes = votes[playerNum] || 0;
    const maxVotes = getMaxVotesForPlayer(playerIndex);
    
    const buttonsContainer = document.getElementById(`voteButtons${playerNum}`);
    if (!buttonsContainer) return;
    
    let newButtons = '';
    for (let i = 0; i <= maxVotes; i++) {
        const isSelected = (currentVotes === i);
        newButtons += `
            <button class="vote-option ${isSelected ? 'selected' : ''}" 
                    onclick="setVotes(${playerNum}, ${i}, ${playerIndex})">
                ${i}
            </button>
        `;
    }
    buttonsContainer.innerHTML = newButtons;
    
    const nomineeDiv = document.getElementById(`nominee${playerNum}`);
    if (nomineeDiv) {
        const currentSpan = nomineeDiv.querySelector('.current-votes');
        if (currentSpan) currentSpan.innerHTML = `текущий: ${currentVotes}`;
    }
}

function updateTotalInfo() {
    const totalGiven = Object.values(votes).reduce((sum, val) => sum + val, 0);
    const remaining = totalVoters - totalGiven;
    
    const totalGivenSpan = document.getElementById('totalGiven');
    const remainSpan = document.getElementById('remainVotes');
    const totalVotersSpan = document.getElementById('totalVoters');
    
    if (totalVotersSpan) totalVotersSpan.innerHTML = totalVoters;
    if (totalGivenSpan) totalGivenSpan.innerHTML = totalGiven;
    if (remainSpan) remainSpan.innerHTML = remaining;
}

function finishVoting() {
    const totalGiven = Object.values(votes).reduce((sum, val) => sum + val, 0);
    
    if (totalGiven < totalVoters) {
        addLog(`⚠️ Осталось ${totalVoters - totalGiven} непроголосовавших игроков`);
        if (!confirm('Не все игроки проголосовали. Завершить голосование?')) {
            return;
        }
    }
    
    // Находим максимальное количество голосов
    let maxVotes = -1;
    for (const player of nominated) {
        const currentVotes = votes[player.num] || 0;
        if (currentVotes > maxVotes) {
            maxVotes = currentVotes;
        }
    }
    
    // Собираем ВСЕХ, кто набрал максимальное количество голосов
    const eliminatedPlayers = [];
    for (const player of nominated) {
        const currentVotes = votes[player.num] || 0;
        if (currentVotes === maxVotes && maxVotes > 0) {
            eliminatedPlayers.push(player);
        }
    }
    
    if (eliminatedPlayers.length === 0) {
        addLog(`⚠️ Никто не набрал голосов. Переход в ночь без изменений.`);
        goToNight([]);
        return;
    }
    
    // Показываем информацию о выбывших
    showEliminated(eliminatedPlayers, maxVotes);
}

function showEliminated(eliminatedPlayers, votesCount) {
    const winnerDiv = document.getElementById('winnerAlert');
    if (winnerDiv) {
        let message = '';
        if (eliminatedPlayers.length === 1) {
            message = `
                <div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 15px; border-radius: 16px; text-align: center; margin-bottom: 20px;">
                    <i class="fas fa-skull"></i>
                    <strong>ВЫБЫВАЕТ!</strong><br>
                    Игрок №${eliminatedPlayers[0].num} ${eliminatedPlayers[0].name}<br>
                    набрал ${votesCount} из ${totalVoters} голосов
                </div>
            `;
        } else {
            const names = eliminatedPlayers.map(p => `№${p.num} ${p.name}`).join(', ');
            message = `
                <div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 15px; border-radius: 16px; text-align: center; margin-bottom: 20px;">
                    <i class="fas fa-skull"></i>
                    <strong>ВЫБЫВАЮТ!</strong><br>
                    ${names}<br>
                    каждый набрал ${votesCount} из ${totalVoters} голосов
                </div>
            `;
        }
        winnerDiv.innerHTML = message;
        
        document.querySelectorAll('.vote-option').forEach(btn => {
            btn.disabled = true;
        });
    }
    
    eliminatedPlayers.forEach(p => {
        addLog(`💀 ВЫБЫЛ: №${p.num} ${p.name} (${votesCount} голосов)`);
    });
    
    // Автоматически переходим в ночь через 2 секунды
    setTimeout(() => {
        goToNight(eliminatedPlayers);
    }, 2000);
}

function goToNight(eliminatedPlayers) {
    // Получаем текущие данные
    let eliminated = JSON.parse(sessionStorage.getItem('beta_eliminated') || '[]');
    const fouls = JSON.parse(sessionStorage.getItem('beta_fouls') || '{}');
    
    // Добавляем выбывших игроков
    for (const player of eliminatedPlayers) {
        if (!eliminated.includes(player.num)) {
            eliminated.push(player.num);
        }
    }
    
    // Обновляем данные
    sessionStorage.setItem('beta_eliminated', JSON.stringify(eliminated));
    sessionStorage.setItem('beta_fouls', JSON.stringify(fouls));
    sessionStorage.setItem('beta_nominationOrder', JSON.stringify([])); // Очищаем выставления
    
    // Сохраняем информацию о выбывших в этом раунде
    sessionStorage.setItem('beta_last_eliminated', JSON.stringify({
        players: eliminatedPlayers.map(p => ({ num: p.num, name: p.name })),
        round: roundNumber,
        votesCount: eliminatedPlayers.length > 0 ? Object.values(votes)[0] : 0
    }));
    
    addLog(`🌙 ПЕРЕХОД В НОЧНУЮ ФАЗУ. РАУНД ${roundNumber + 1}`);
    
    // Переходим на страницу ночной фазы
    window.location.href = `/beta/night/${roundNumber + 1}/`;
}

function addLog(message) {
    const logsList = document.getElementById('voteLog');
    if (!logsList) return;
    
    const time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    logsList.innerHTML += `<div class="log-line"><span class="log-time">[${time}]</span> ${message}</div>`;
    logsList.scrollTop = logsList.scrollHeight;
}

function saveToSession() {
    const savedData = sessionStorage.getItem('voting_data');
    if (savedData) {
        const data = JSON.parse(savedData);
        data.votes = votes;
        sessionStorage.setItem('voting_data', JSON.stringify(data));
    }
}

function resetVoting() {
    if (confirm('Сбросить все голоса?')) {
        votes = {};
        renderNominatedList();
        updateTotalInfo();
        addLog('🔄 Все голоса сброшены');
        
        const winnerDiv = document.getElementById('winnerAlert');
        if (winnerDiv) winnerDiv.innerHTML = '';
        
        saveToSession();
    }
}

function goBack() {
    saveToSession();
    window.location.href = `/beta/day/${roundNumber}/`;
}