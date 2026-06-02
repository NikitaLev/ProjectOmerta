let players = [];
let roles = {};
let currentDealStep = 'sheriff';

function renderSetupPlayers() {
    const container = document.getElementById('playersList');
    if (!container) return;
    container.innerHTML = '';
    
    for (let i = 1; i <= 10; i++) {
        container.innerHTML += `
            <div class="table-row">
                <div class="table-cell">${i}</div>
                <div class="table-cell">
                    <input type="text" class="player-input" id="player${i}" placeholder="Игрок ${i}" maxlength="25">
                </div>
            </div>
        `;
    }
}

function startGame() {
    players = [];
    for (let i = 1; i <= 10; i++) {
        const input = document.getElementById(`player${i}`);
        const value = input.value.trim();
        players.push(value || `Игрок ${i}`);
    }
    
    roles = {};
    currentDealStep = 'sheriff';
    
    document.getElementById('setupScreen').style.display = 'none';
    document.getElementById('roleDealScreen').style.display = 'block';
    
    renderRoleDeal();
    updateDealStatus();
}

function renderRoleDeal() {
    const container = document.getElementById('roleDealList');
    if (!container) return;
    container.innerHTML = '';
    
    players.forEach((player, i) => {
        const num = i + 1;
        const role = roles[num];
        let roleClass = '';
        let roleText = '';
        
        if (role === 'don') { roleClass = 'selected-don'; roleText = '<span class="role-badge don">👑 Дон</span>'; }
        else if (role === 'sheriff') { roleClass = 'selected-sheriff'; roleText = '<span class="role-badge sheriff">⭐ Шериф</span>'; }
        else if (role === 'mafia') { roleClass = 'selected-mafia'; roleText = '<span class="role-badge mafia">💀 Мафия</span>'; }
        else if (role === 'civil') { roleClass = 'selected-civil'; roleText = '<span class="role-badge civil">👥 Мирный</span>'; }
        
        container.innerHTML += `
            <div class="role-card ${roleClass}" onclick="assignRole(${num})">
                <div class="role-number">${num}</div>
                <div class="role-name">${player}</div>
                <div class="role-badge-place">${roleText || ''}</div>
            </div>
        `;
    });
}

function assignRole(playerNum) {
    if (currentDealStep === 'sheriff') {
        if (roles[playerNum]) { alert('У этого игрока уже есть роль'); return; }
        roles[playerNum] = 'sheriff';
        currentDealStep = 'don';
        addLogToDeal(`⭐ Шериф — №${playerNum} ${players[playerNum-1]}`);
    }
    else if (currentDealStep === 'don') {
        if (roles[playerNum]) { alert('У этого игрока уже есть роль'); return; }
        roles[playerNum] = 'don';
        currentDealStep = 'mafia';
        addLogToDeal(`👑 Дон — №${playerNum} ${players[playerNum-1]}`);
    }
    else if (currentDealStep === 'mafia') {
        if (roles[playerNum]) { alert('У этого игрока уже есть роль'); return; }
        const mafiaCount = Object.values(roles).filter(r => r === 'mafia').length;
        if (mafiaCount >= 2) { alert('Уже выбраны 2 мафии'); return; }
        roles[playerNum] = 'mafia';
        addLogToDeal(`💀 Мафия — №${playerNum} ${players[playerNum-1]}`);
        
        if (mafiaCount + 1 === 2) {
            currentDealStep = 'done';
            completeRoleDeal();
        }
    }
    
    renderRoleDeal();
    updateDealStatus();
}

function completeRoleDeal() {
    for (let i = 1; i <= 10; i++) {
        if (!roles[i]) {
            roles[i] = 'civil';
            addLogToDeal(`👥 Мирный — №${i} ${players[i-1]}`);
        }
    }
    renderRoleDeal();
    updateDealStatus();
    document.getElementById('confirmDealBtn').style.display = 'block';
}

function updateDealStatus() {
    const sheriffCount = Object.values(roles).filter(r => r === 'sheriff').length;
    const donCount = Object.values(roles).filter(r => r === 'don').length;
    const mafiaCount = Object.values(roles).filter(r => r === 'mafia').length;
    
    let message = '';
    if (currentDealStep === 'sheriff') message = '👆 Укажите ШЕРИФА';
    else if (currentDealStep === 'don') message = '👆 Укажите ДОНА';
    else if (currentDealStep === 'mafia') message = `👆 Укажите МАФИЮ (${mafiaCount}/2)`;
    else message = '✅ Все роли назначены!';
    
    document.getElementById('dealMessage').innerHTML = `<i class="fas fa-hand-point-up"></i> ${message}`;
    document.getElementById('sheriffCount').innerHTML = sheriffCount;
    document.getElementById('donCount').innerHTML = donCount;
    document.getElementById('mafiaCount').innerHTML = mafiaCount;
}

function addLogToDeal(message) {
    const logsDiv = document.getElementById('dealLogs');
    if (!logsDiv) return;
    const time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    logsDiv.innerHTML += `<div class="log-line"><span class="log-time">[${time}]</span> ${message}</div>`;
    logsDiv.scrollTop = logsDiv.scrollHeight;
}

function confirmStart() {
    const sheriffCount = Object.values(roles).filter(r => r === 'sheriff').length;
    const donCount = Object.values(roles).filter(r => r === 'don').length;
    const mafiaCount = Object.values(roles).filter(r => r === 'mafia').length;
    const civilCount = Object.values(roles).filter(r => r === 'civil').length;
    
    if (sheriffCount !== 1 || donCount !== 1 || mafiaCount !== 2 || civilCount !== 6) {
        alert('Ошибка: 1 Шериф, 1 Дон, 2 Мафии, 6 Мирных');
        return;
    }
    
    // Сохраняем в sessionStorage
    sessionStorage.setItem('beta_players', JSON.stringify(players));
    sessionStorage.setItem('beta_roles', JSON.stringify(roles));
    sessionStorage.setItem('beta_fouls', JSON.stringify({}));
    sessionStorage.setItem('beta_eliminated', JSON.stringify([]));
    sessionStorage.setItem('beta_nominationOrder', JSON.stringify([]));
    
    // Переходим на дневную фазу РАУНДА 1
    window.location.href = '/beta/day/1/';
}

function resetGame() {
    if (confirm('Сбросить всё?')) {
        players = [];
        roles = {};
        currentDealStep = 'sheriff';
        document.getElementById('setupScreen').style.display = 'block';
        document.getElementById('roleDealScreen').style.display = 'none';
        document.getElementById('dealLogs').innerHTML = '';
        renderSetupPlayers();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    renderSetupPlayers();
});