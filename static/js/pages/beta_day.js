let players = [];
let roles = [];
let fouls = {};
let eliminated = [];
let nominationOrder = [];
let currentMode = 'none';
let currentSpeaker = null;
let waitingForNomination = false;
let actionHistory = [];
let historyIndex = -1;
let roundNumber = window.roundNumber || 1;
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    renderPlayers();
    addLog('☀️ НАЧАЛО ДНЯ');
    
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'z') {
            e.preventDefault();
            undo();
        }
    });
});

function loadData() {
    // Получаем номер раунда из URL
    const path = window.location.pathname;
    const match = path.match(/\/beta\/day\/(\d+)\//);
    if (match) {
        roundNumber = parseInt(match[1]);
    }
    
    players = JSON.parse(sessionStorage.getItem('beta_players') || '[]');
    roles = JSON.parse(sessionStorage.getItem('beta_roles') || '{}');
    fouls = JSON.parse(sessionStorage.getItem('beta_fouls') || '{}');
    eliminated = JSON.parse(sessionStorage.getItem('beta_eliminated') || '[]');
    nominationOrder = JSON.parse(sessionStorage.getItem('beta_nominationOrder') || '[]');
    
    if (players.length === 0) {
        window.location.href = '/beta/game/';
    }
}

function saveData() {
    sessionStorage.setItem('beta_fouls', JSON.stringify(fouls));
    sessionStorage.setItem('beta_nominationOrder', JSON.stringify(nominationOrder));
}
function renderEliminatedInfo() {
    const container = document.getElementById('eliminatedInfo');
    if (!container) return;
    
    if (eliminated.length > 0) {
        const eliminatedNames = eliminated.map(num => `${num}. ${players[num-1]}`).join(', ');
        container.innerHTML = `
            <i class="fas fa-skull"></i> 
            Выбывшие: ${eliminatedNames}
        `;
    } else {
        container.innerHTML = '<i class="fas fa-info-circle"></i> Никто не выбыл';
    }
}

function getAlivePlayers() {
    const alive = [];
    for (let i = 1; i <= 10; i++) {
        if (!eliminated.includes(i)) {
            alive.push(i);
        }
    }
    return alive;
}
function renderPlayers() {
    const container = document.getElementById('playersContainer');
    if (!container) return;
    container.innerHTML = '';
    
    const roleNames = { don: 'Дон', mafia: 'Мафия', sheriff: 'Шериф', civil: 'Мирный' };
    const roleClass = { don: 'role-don', mafia: 'role-mafia', sheriff: 'role-sheriff', civil: 'role-civil' };
    const alivePlayers = getAlivePlayers();
    
    for (const num of alivePlayers) {
        const player = players[num - 1];
        const role = roles[num];
        const foulCount = fouls[num] || 0;
        
        let foulDots = '';
        for (let f = 1; f <= 4; f++) {
            foulDots += `<div class="foul-dot ${f <= foulCount ? 'active' : ''}"></div>`;
        }
        
        const nomination = nominationOrder.find(n => n.num === num);
        const nominationHtml = nomination ? `<span class="nomination-badge">🎙️${nomination.nominatedBy}</span>` : '';
        
        container.innerHTML += `
            <div class="player-item" onclick="handlePlayerClick(${num})">
                <div class="player-number">${num}</div>
                <div class="player-name">${player}</div>
                <div class="player-role ${roleClass[role]}">${roleNames[role]}</div>
                <div class="foul-indicators">${foulDots}</div>
                ${nominationHtml}
            </div>
        `;
    }
}

function handlePlayerClick(playerNum) {
    if (currentMode === 'foul') {
        addFoul(playerNum);
    }
    else if (currentMode === 'nominate') {
        handleNomination(playerNum);
    }
}

function addFoul(playerNum) {
    const current = fouls[playerNum] || 0;
    if (current >= 4) {
        addLog(`⚠️ Игрок №${playerNum} ${players[playerNum-1]} уже дисквалифицирован`);
        return;
    }
    
    const newFoulCount = current + 1;
    fouls[playerNum] = newFoulCount;
    addLog(`⚠️ ФОЛ | №${playerNum} ${players[playerNum-1]} (${newFoulCount}/4)`);
    
    // Проверяем, достиг ли игрок 4 фолов
    if (newFoulCount >= 4) {
        // Добавляем игрока в список выбывших, если его там ещё нет
        if (!eliminated.includes(playerNum)) {
            eliminated.push(playerNum);
            addLog(`💀 ИГРОК №${playerNum} ${players[playerNum-1]} ДИСКВАЛИФИЦИРОВАН (4 фола)`);
        }
        
        // Очищаем выставления этого игрока, если он был выставлен
        nominationOrder = nominationOrder.filter(item => item.num !== playerNum);
        
        // Сохраняем обновлённые данные
        sessionStorage.setItem('beta_eliminated', JSON.stringify(eliminated));
        sessionStorage.setItem('beta_nominationOrder', JSON.stringify(nominationOrder));
    }
    
    saveData();
    renderPlayers();
    saveState();
}

function handleNomination(playerNum) {
    if (currentSpeaker === null) {
        currentSpeaker = playerNum;
        waitingForNomination = true;
        addLog(`🎙️ ГОВОРИТ №${playerNum} ${players[playerNum-1]}`);
        document.getElementById('modeInfo').innerHTML = '<i class="fas fa-microphone"></i> 🎙️ Теперь выберите КАНДИДАТА';
        highlightSpeaker(playerNum);
        saveState();
        return;
    }
    
    if (waitingForNomination) {
        if (currentSpeaker === playerNum) {
            addLog(`❌ Нельзя выставить самого себя`);
            return;
        }
        
        // Проверяем, не выставлен ли уже этот игрок
        if (nominationOrder.some(n => n.num === playerNum)) {
            addLog(`❌ Игрок №${playerNum} уже выставлен`);
            return;
        }
        
        // Добавляем в конец списка (сохраняем порядок)
        nominationOrder.push({
            num: playerNum,
            nominatedBy: currentSpeaker
        });
        
        addLog(`📌 №${currentSpeaker} выставил №${playerNum} ${players[playerNum-1]}`);
        
        waitingForNomination = false;
        currentSpeaker = null;
        currentMode = 'none';
        
        document.getElementById('foulModeBtn').classList.remove('active');
        document.getElementById('nominateModeBtn').classList.remove('active');
        document.getElementById('modeInfo').innerHTML = '<i class="fas fa-check-circle"></i> ✅ Кандидат выставлен';
        
        clearHighlight();
        saveData();
        renderPlayers();
        saveState();
        
        setTimeout(() => {
            if (currentMode === 'none') {
                document.getElementById('modeInfo').innerHTML = '<i class="fas fa-info-circle"></i> Выберите режим';
            }
        }, 2000);
    }
}

function highlightSpeaker(playerNum) {
    clearHighlight();
    const items = document.querySelectorAll('.player-item');
    if (items[playerNum - 1]) {
        items[playerNum - 1].classList.add('selected');
    }
}

function clearHighlight() {
    document.querySelectorAll('.player-item').forEach(el => el.classList.remove('selected'));
}

function setMode(mode) {
    currentMode = mode;
    
    document.getElementById('foulModeBtn').classList.remove('active');
    document.getElementById('nominateModeBtn').classList.remove('active');
    
    if (mode === 'foul') {
        document.getElementById('foulModeBtn').classList.add('active');
        document.getElementById('modeInfo').innerHTML = '<i class="fas fa-exclamation-triangle"></i> ⚠️ Режим: ВЫДАЧА ФОЛОВ (клик по игроку)';
    } 
    else if (mode === 'nominate') {
        document.getElementById('nominateModeBtn').classList.add('active');
        document.getElementById('modeInfo').innerHTML = '<i class="fas fa-microphone"></i> 🎙️ Выберите ГОВОРЯЩЕГО игрока';
        waitingForNomination = false;
        currentSpeaker = null;
        clearHighlight();
    }
    
    saveState();
}

function goToVoting() {
    const alivePlayers = getAlivePlayers();
    
    // Собираем выставленных игроков
    const nominatedList = nominationOrder
        .filter(item => alivePlayers.includes(item.num)) // только живые
        .map(item => ({
            num: item.num,
            name: players[item.num - 1],
            nominatedBy: item.nominatedBy
        }));
    
    if (nominatedList.length === 0) {
        addLog('❌ Нет выставленных игроков. Сначала выставьте кандидатов в режиме "Выставление"');
        alert('Нет выставленных игроков. Сначала выставьте кандидатов.');
        return;
    }
    
    sessionStorage.setItem('voting_data', JSON.stringify({
        nominated: nominatedList,
        players: players,
        roles: roles,
        alivePlayers: alivePlayers,
        votes: {},
        roundNumber: roundNumber
    }));
    
    addLog(`🗳️ ПЕРЕХОД К ГОЛОСОВАНИЮ (${nominatedList.length} кандидатов)`);
    window.location.href = '/beta/vote/';
}

function nextPhase() {
    addLog('🌙 ПЕРЕХОД В НОЧЬ (пока заглушка)');
}

function addLog(message) {
    const logsList = document.getElementById('logsList');
    if (!logsList) return;
    const time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    logsList.innerHTML += `<div class="log-line"><span class="log-time">[${time}]</span> ${message}</div>`;
    logsList.scrollTop = logsList.scrollHeight;
    saveState();
}

function saveState() {
    const state = {
        fouls: JSON.parse(JSON.stringify(fouls)),
        nominationOrder: JSON.parse(JSON.stringify(nominationOrder)),
        currentMode: currentMode,
        currentSpeaker: currentSpeaker,
        waitingForNomination: waitingForNomination,
        logs: document.getElementById('logsList').innerHTML
    };
    
    if (historyIndex < actionHistory.length - 1) {
        actionHistory = actionHistory.slice(0, historyIndex + 1);
    }
    
    actionHistory.push(state);
    historyIndex++;
    
    if (actionHistory.length > 50) actionHistory.shift();
}

function undo() {
    if (historyIndex <= 0) {
        addLog('↩️ Нет действий для отмены');
        return;
    }
    
    historyIndex--;
    const state = actionHistory[historyIndex];
    
    fouls = JSON.parse(JSON.stringify(state.fouls));
    nominationOrder = JSON.parse(JSON.stringify(state.nominationOrder));
    currentMode = state.currentMode;
    currentSpeaker = state.currentSpeaker;
    waitingForNomination = state.waitingForNomination;
    
    document.getElementById('logsList').innerHTML = state.logs;
    
    renderPlayers();
    
    document.getElementById('foulModeBtn').classList.remove('active');
    document.getElementById('nominateModeBtn').classList.remove('active');
    
    if (currentMode === 'foul') {
        document.getElementById('foulModeBtn').classList.add('active');
        document.getElementById('modeInfo').innerHTML = '<i class="fas fa-exclamation-triangle"></i> ⚠️ Режим: ВЫДАЧА ФОЛОВ';
    } else if (currentMode === 'nominate') {
        document.getElementById('nominateModeBtn').classList.add('active');
        if (currentSpeaker === null) {
            document.getElementById('modeInfo').innerHTML = '<i class="fas fa-microphone"></i> 🎙️ Выберите ГОВОРЯЩЕГО игрока';
        } else {
            document.getElementById('modeInfo').innerHTML = '<i class="fas fa-microphone"></i> 🎙️ Выберите КАНДИДАТА';
        }
    } else {
        document.getElementById('modeInfo').innerHTML = '<i class="fas fa-info-circle"></i> Выберите режим';
    }
    
    clearHighlight();
    if (currentSpeaker) highlightSpeaker(currentSpeaker);
    
    addLog('↩️ Отмена действия');
    saveData();
}

function resetToSetup() {
    if (confirm('Начать новую игру?')) {
        sessionStorage.clear();
        window.location.href = '/beta/game/';
    }
}

function endGame() {
    addLog('🏁 ИГРА ЗАВЕРШЕНА');
    alert('Игра завершена! Протокол можно скопировать.');
}

function goToNightNoElimination() {
    // Очищаем выставления
    sessionStorage.setItem('beta_nominationOrder', JSON.stringify([]));
    sessionStorage.removeItem('voting_data');
    
    addLog(`🌙 ПЕРЕХОД В НОЧЬ (без выбывания). РАУНД ${roundNumber + 1}`);
    
    // Переходим на страницу ночной фазы со следующим раундом
    window.location.href = `/beta/night/${roundNumber + 1}/`;
}