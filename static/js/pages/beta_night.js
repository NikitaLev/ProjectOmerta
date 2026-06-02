let players = [];
let roles = [];
let fouls = {};
let eliminated = [];
let mafiaKill = null;
let donCheck = null;
let sheriffCheck = null;
let round = 1;

document.addEventListener('DOMContentLoaded', function() {
    loadData();
    renderEliminatedInfo();
    renderButtons();
    addLog(`🌙 НОЧНАЯ ФАЗА — РАУНД ${round}`);
});

function loadData() {
    players = JSON.parse(sessionStorage.getItem('beta_players') || '[]');
    roles = JSON.parse(sessionStorage.getItem('beta_roles') || '{}');
    fouls = JSON.parse(sessionStorage.getItem('beta_fouls') || '{}');
    eliminated = JSON.parse(sessionStorage.getItem('beta_eliminated') || '[]');
    
    const path = window.location.pathname;
    const match = path.match(/\/beta\/night\/(\d+)\//);
    if (match) {
        round = parseInt(match[1]);
    }
    
    if (players.length === 0) {
        window.location.href = '/beta/game/';
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

function getMafiaTargets() {
    const alive = getAlivePlayers();
    return alive.filter(n => roles[n] !== 'mafia' && roles[n] !== 'don');
}

function renderEliminatedInfo() {
    const container = document.getElementById('eliminatedInfo');
    if (!container) return;
    
    if (eliminated.length > 0) {
        const eliminatedNames = eliminated.map(num => `${num}. ${players[num-1]}`).join(', ');
        container.innerHTML = `<i class="fas fa-skull"></i> Выбывшие: ${eliminatedNames}`;
    } else {
        container.innerHTML = '<i class="fas fa-info-circle"></i> Никто не выбыл';
    }
}

function renderButtons() {
    const alive = getAlivePlayers();
    const mafiaTargets = getMafiaTargets();
    
    // Мафия — кнопки игроков + кнопка ПРОМАХ
    const mafiaContainer = document.getElementById('mafiaButtons');
    if (mafiaContainer) {
        mafiaContainer.innerHTML = '';
        
        // Кнопка промаха
        const missClass = mafiaKill === 'miss' ? 'selected' : '';
        mafiaContainer.innerHTML += `<button class="player-btn ${missClass}" onclick="selectMafiaMiss()">❌ ПРОМАХ (никто не умирает)</button>`;
        
        if (mafiaTargets.length > 0) {
            mafiaTargets.forEach(n => {
                const selectedClass = (mafiaKill === n) ? 'selected' : '';
                mafiaContainer.innerHTML += `<button class="player-btn ${selectedClass}" onclick="selectMafiaKill(${n})">${n}. ${players[n-1]}</button>`;
            });
        } else {
            mafiaContainer.innerHTML += '<div class="empty-state">Нет целей для убийства</div>';
        }
    }
    
    // Дон
    const donContainer = document.getElementById('donButtons');
    if (donContainer) {
        donContainer.innerHTML = '';
        alive.forEach(n => {
            const selectedClass = (donCheck === n) ? 'selected' : '';
            donContainer.innerHTML += `<button class="player-btn ${selectedClass}" onclick="selectDonCheck(${n})">${n}. ${players[n-1]}</button>`;
        });
    }
    
    // Шериф
    const sheriffContainer = document.getElementById('sheriffButtons');
    if (sheriffContainer) {
        sheriffContainer.innerHTML = '';
        alive.forEach(n => {
            const selectedClass = (sheriffCheck === n) ? 'selected' : '';
            sheriffContainer.innerHTML += `<button class="player-btn ${selectedClass}" onclick="selectSheriffCheck(${n})">${n}. ${players[n-1]}</button>`;
        });
    }
}

function selectMafiaMiss() {
    mafiaKill = 'miss';
    addLog(`💀 Мафия выбрала ПРОМАХ — никто не умрёт`);
    renderButtons();
}

function selectMafiaKill(n) {
    mafiaKill = n;
    addLog(`💀 Мафия выбрала убийство: №${n} ${players[n-1]}`);
    renderButtons();
}

function selectDonCheck(n) {
    donCheck = n;
    const isSheriff = roles[n] === 'sheriff';
    addLog(`👑 Дон проверил №${n} ${players[n-1]} — ${isSheriff ? 'ЭТО ШЕРИФ!' : 'не шериф'}`);
    renderButtons();
}

function selectSheriffCheck(n) {
    sheriffCheck = n;
    const isMafia = roles[n] === 'mafia' || roles[n] === 'don';
    addLog(`⭐ Шериф проверил №${n} ${players[n-1]} — ${isMafia ? 'ЧЁРНЫЙ!' : 'КРАСНЫЙ'}`);
    renderButtons();
}

function nextPhase() {
    // Проверяем, есть ли игроки с 4 фолами, которые ещё не в eliminated
    for (let i = 1; i <= 10; i++) {
        const foulCount = fouls[i] || 0;
        if (foulCount >= 4 && !eliminated.includes(i)) {
            eliminated.push(i);
            addLog(`💀 Игрок №${i} ${players[i-1]} ДИСКВАЛИФИЦИРОВАН (4 фола)`);
        }
    }
    
    // Применяем убийство мафии (только если цель жива и не дисквалифицирована)
    if (mafiaKill && mafiaKill !== 'miss' && !eliminated.includes(mafiaKill)) {
        eliminated.push(mafiaKill);
        addLog(`💀 ИТОГ: Игрок №${mafiaKill} ${players[mafiaKill-1]} УБИТ НОЧЬЮ`);
    } else if (mafiaKill === 'miss') {
        addLog(`❌ ИТОГ: ПРОМАХ — никто не убит`);
    } else if (mafiaKill && eliminated.includes(mafiaKill)) {
        addLog(`⚠️ ИТОГ: Цель уже выбыла — промах`);
    } else {
        addLog(`⚠️ ИТОГ: Мафия не выбрала цель — промах`);
    }
    
    // Сохраняем обновлённые данные
    sessionStorage.setItem('beta_eliminated', JSON.stringify(eliminated));
    sessionStorage.setItem('beta_fouls', JSON.stringify(fouls));
    sessionStorage.setItem('beta_nominationOrder', JSON.stringify([]));
    sessionStorage.removeItem('voting_data');
    
    addLog(`☀️ ПЕРЕХОД В ДЕНЬ — РАУНД ${round + 1}`);
    window.location.href = `/beta/day/${round + 1}/`;
}

function addLog(message) {
    const logsList = document.getElementById('logsList');
    if (!logsList) return;
    const time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    logsList.innerHTML += `<div class="log-line"><span class="log-time">[${time}]</span> ${message}</div>`;
    logsList.scrollTop = logsList.scrollHeight;
}

function resetToSetup() {
    if (confirm('Начать новую игру?')) {
        sessionStorage.clear();
        window.location.href = '/beta/game/';
    }
}