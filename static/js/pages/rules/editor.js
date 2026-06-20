// ========== РЕДАКТОР ДЛЯ ПУНКТОВ ПРАВИЛ С АВТОДОПОЛНЕНИЕМ ==========

let quillEditors = {};
let availableVariables = [];

// Получаем переменные из скрытого поля
function loadVariables() {
    const varData = document.getElementById('variablesData');
    if (varData) {
        try {
            availableVariables = JSON.parse(varData.textContent);
        } catch(e) {
            console.error('Ошибка загрузки переменных:', e);
        }
    }
}

// Функция для показа подсказок
function showVariableSuggestions(editor, index, char) {
    const range = editor.getSelection();
    if (!range) return;

    const text = editor.getText(0, range.index);
    const beforeCursor = text.substring(0, range.index);
    
    // Ищем последние открытые скобки
    const lastOpen = beforeCursor.lastIndexOf('{{');
    const lastClose = beforeCursor.lastIndexOf('}}');
    
    // Если нет открытых скобок или есть закрытые после открытых
    if (lastOpen === -1 || (lastClose > lastOpen)) return;
    
    // Получаем введённый текст между {{ и курсором
    const partial = beforeCursor.substring(lastOpen + 2);
    
    // Ищем переменные, начинающиеся с введённого текста
    const suggestions = availableVariables.filter(v => 
        v.key.toLowerCase().startsWith(partial.toLowerCase())
    );
    
    if (suggestions.length === 0) {
        hideSuggestions();
        return;
    }
    
    // Создаём или обновляем подсказки
    let container = document.getElementById('variableSuggestions');
    if (!container) {
        container = document.createElement('div');
        container.id = 'variableSuggestions';
        container.className = 'variable-suggestions';
        document.body.appendChild(container);
    }
    
    // Позиционируем подсказки
    const rect = editor.container.getBoundingClientRect();
    const cursorPos = editor.getBounds(range.index);
    container.style.left = (rect.left + cursorPos.left) + 'px';
    container.style.top = (rect.top + cursorPos.top + cursorPos.height + 10) + 'px';
    container.style.display = 'block';
    
    // Заполняем подсказки
    container.innerHTML = '';
    suggestions.slice(0, 10).forEach(function(v) {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerHTML = `
            <span class="suggestion-key">${v.key}</span>
            <span class="suggestion-value">= ${v.value}</span>
        `;
        item.addEventListener('mousedown', function(e) {
            e.preventDefault();  // Предотвращаем потерю фокуса
            insertVariable(editor, v.key, partial, lastOpen);
            hideSuggestions();
        });
        container.appendChild(item);
    });
}

function insertVariable(editor, key, partial, openPos) {
    const range = editor.getSelection();
    if (!range) return;
    
    // Получаем текущий текст
    const fullText = editor.getText(0, range.index);
    
    // Находим позицию открывающих скобок
    const startIndex = fullText.lastIndexOf('{{', range.index);
    if (startIndex === -1) return;
    
    // Удаляем всё от {{ до текущей позиции (включая частичный ввод)
    const endIndex = range.index;
    editor.deleteText(startIndex, endIndex - startIndex);
    
    // Вставляем переменную с пробелами
    const variableText = `{{ ${key} }}`;
    editor.insertText(startIndex, variableText);
    
    // Устанавливаем курсор после вставленной переменной
    editor.setSelection(startIndex + variableText.length, 0);
    
    // Обновляем скрытое поле
    const hiddenInput = document.getElementById(editor.container.id.replace('_editor', 'Content'));
    if (hiddenInput) {
        hiddenInput.value = editor.root.innerHTML;
    }
}

// Показывает все переменные при вводе {{
function showAllVariables(editor, range) {
    if (availableVariables.length === 0) {
        hideSuggestions();
        return;
    }
    
    const container = getSuggestionsContainer();
    const rect = editor.container.getBoundingClientRect();
    const cursorPos = editor.getBounds(range.index);
    
    container.style.left = (rect.left + cursorPos.left) + 'px';
    container.style.top = (rect.top + cursorPos.top + cursorPos.height + 10) + 'px';
    container.style.display = 'block';
    container.innerHTML = '';
    
    availableVariables.slice(0, 15).forEach(function(v) {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerHTML = `
            <span class="suggestion-key">${v.key}</span>
            <span class="suggestion-value">= ${v.value}</span>
            <span class="insert-hint">↵ вставить</span>
        `;
        item.addEventListener('mousedown', function(e) {
            e.preventDefault();
            const range2 = editor.getSelection();
            if (range2) {
                // Удаляем {{ 
                const pos = range2.index - 2;
                editor.deleteText(pos, 2);
                // Вставляем переменную с пробелами
                const fullText = `{{ ${v.key} }}`;
                editor.insertText(pos, fullText);
                editor.setSelection(pos + fullText.length, 0);
                // Обновляем скрытое поле
                const hiddenInput = document.getElementById(editor.container.id.replace('_editor', 'Content'));
                if (hiddenInput) {
                    hiddenInput.value = editor.root.innerHTML;
                }
            }
            hideSuggestions();
        });
        container.appendChild(item);
    });
}

function showFilteredSuggestions(editor, suggestions, range, openPos, partial) {
    const container = getSuggestionsContainer();
    const rect = editor.container.getBoundingClientRect();
    const cursorPos = editor.getBounds(range.index);
    
    container.style.left = (rect.left + cursorPos.left) + 'px';
    container.style.top = (rect.top + cursorPos.top + cursorPos.height + 10) + 'px';
    container.style.display = 'block';
    container.innerHTML = '';
    
    suggestions.slice(0, 10).forEach(function(v) {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        // Подсвечиваем совпадение
        let displayKey = v.key;
        if (partial.length > 0) {
            const matchIndex = v.key.toLowerCase().indexOf(partial.toLowerCase());
            if (matchIndex !== -1) {
                displayKey = v.key.substring(0, matchIndex) + 
                    '<strong style="color: var(--gold);">' + 
                    v.key.substring(matchIndex, matchIndex + partial.length) + 
                    '</strong>' + 
                    v.key.substring(matchIndex + partial.length);
            }
        }
        item.innerHTML = `
            <span class="suggestion-key">${displayKey}</span>
            <span class="suggestion-value">= ${v.value}</span>
        `;
        item.addEventListener('mousedown', function(e) {
            e.preventDefault();
            insertVariable(editor, v.key, partial, openPos);
            hideSuggestions();
        });
        container.appendChild(item);
    });
}

function getSuggestionsContainer() {
    let container = document.getElementById('variableSuggestions');
    if (!container) {
        container = document.createElement('div');
        container.id = 'variableSuggestions';
        container.className = 'variable-suggestions';
        document.body.appendChild(container);
    }
    return container;
}

function hideSuggestions() {
    const container = document.getElementById('variableSuggestions');
    if (container) {
        container.style.display = 'none';
    }
}

function getQuillContent(editorId) {
    const quill = quillEditors[editorId];
    if (quill) {
        return quill.root.innerHTML;
    }
    return '';
}

function destroyQuillEditor(editorId) {
    if (quillEditors[editorId]) {
        quillEditors[editorId].destroy();
        delete quillEditors[editorId];
    }
}

// ОСНОВНАЯ ФУНКЦИЯ ИНИЦИАЛИЗАЦИИ QUILL
function initQuillEditor(editorId, hiddenInputId) {
    if (quillEditors[editorId]) {
        quillEditors[editorId].destroy();
        delete quillEditors[editorId];
    }
    
    const container = document.getElementById(editorId);
    if (!container) return null;
    
    // Загружаем переменные
    loadVariables();
    
    const quill = new Quill('#' + editorId, {
        theme: 'snow',
        modules: {
            toolbar: [
                [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
                ['bold', 'italic', 'underline', 'strike'],
                ['blockquote', 'code-block'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                [{ 'indent': '-1'}, { 'indent': '+1' }],
                [{ 'align': [] }],
                ['link'],
                ['clean']
            ],
            clipboard: {
                matchVisual: false,
            }
        },
        placeholder: 'Введите текст пункта правил... Для вставки переменной введите {{...',
        formats: [
            'header',
            'bold', 'italic', 'underline', 'strike',
            'blockquote', 'code-block',
            'list', 'bullet',
            'indent',
            'align',
            'link'
        ]
    });
    
    // Кастомная тема для Quill (темная)
    const style = document.createElement('style');
    style.textContent = `
        .ql-container.ql-snow {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0 0 10px 10px;
            min-height: 200px;
            font-family: var(--font-primary), sans-serif;
            font-size: 14px;
        }
        .ql-toolbar.ql-snow {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px 10px 0 0;
            padding: 8px;
        }
        .ql-toolbar.ql-snow .ql-stroke {
            stroke: var(--text-secondary);
        }
        .ql-toolbar.ql-snow .ql-fill {
            fill: var(--text-secondary);
        }
        .ql-toolbar.ql-snow .ql-picker {
            color: var(--text-secondary);
        }
        .ql-toolbar.ql-snow .ql-picker-options {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
        }
        .ql-toolbar.ql-snow .ql-picker-item:hover {
            color: var(--gold);
            background: rgba(212, 175, 55, 0.05);
        }
        .ql-editor {
            color: var(--text-primary);
            min-height: 200px;
            font-size: 14px;
            line-height: 1.6;
        }
        .ql-editor p {
            margin-bottom: 8px;
        }
        .ql-editor h1, .ql-editor h2, .ql-editor h3 {
            color: var(--gold);
        }
        .ql-editor blockquote {
            border-left: 3px solid var(--gold);
            padding-left: 15px;
            margin: 10px 0;
            color: var(--text-secondary);
        }
        .ql-editor ul, .ql-editor ol {
            padding-left: 20px;
        }
        .ql-editor li {
            margin-bottom: 4px;
        }
        .ql-editor code {
            background: var(--bg-secondary);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            color: var(--gold);
        }
        .ql-editor a {
            color: var(--gold);
            text-decoration: underline;
        }
        .ql-editor.ql-blank::before {
            color: var(--text-muted);
            font-style: italic;
        }
        
        /* Стили для подсказок переменных */
        .variable-suggestions {
            position: fixed;
            background: var(--bg-card);
            border: 1px solid var(--gold);
            border-radius: 10px;
            min-width: 250px;
            max-width: 400px;
            max-height: 250px;
            overflow-y: auto;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: none;
        }
        .variable-suggestions .suggestion-item {
            padding: 8px 14px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            transition: all 0.2s;
        }
        .variable-suggestions .suggestion-item:hover {
            background: rgba(212, 175, 55, 0.1);
        }
        .variable-suggestions .suggestion-item:last-child {
            border-bottom: none;
        }
        .variable-suggestions .suggestion-key {
            color: var(--gold);
            font-weight: 600;
            font-family: monospace;
        }
        .variable-suggestions .suggestion-value {
            color: var(--text-secondary);
            font-size: 0.85rem;
        }
        .variable-suggestions .suggestion-item .insert-hint {
            color: var(--text-muted);
            font-size: 0.7rem;
            margin-left: 10px;
        }
    `;
    document.head.appendChild(style);
    
    // Получаем скрытое поле для сохранения HTML
    const hiddenInput = document.getElementById(hiddenInputId);
    if (hiddenInput) {
        quill.on('text-change', function() {
            const html = quill.root.innerHTML;
            hiddenInput.value = html;
        });
    }
    
    // ===== АВТОДОПОЛНЕНИЕ ПРИ ВВОДЕ =====
    quill.on('text-change', function(delta, oldDelta, source) {
        if (source === 'user') {
            const range = quill.getSelection();
            if (range) {
                const text = quill.getText(0, range.index);
                const beforeCursor = text.substring(0, range.index);
                const lastTwoChars = beforeCursor.slice(-2);
                
                if (lastTwoChars === '{{') {
                    // Показываем все переменные
                    showAllVariables(quill, range);
                } else {
                    // Проверяем, находимся ли внутри {{ ... }}
                    const lastOpen = beforeCursor.lastIndexOf('{{');
                    const lastClose = beforeCursor.lastIndexOf('}}');
                    if (lastOpen > lastClose) {
                        // Мы внутри скобок
                        const partial = beforeCursor.substring(lastOpen + 2);
                        const suggestions = availableVariables.filter(v => 
                            v.key.toLowerCase().startsWith(partial.toLowerCase())
                        );
                        if (suggestions.length > 0) {
                            showFilteredSuggestions(quill, suggestions, range, lastOpen, partial);
                        } else {
                            hideSuggestions();
                        }
                    } else {
                        hideSuggestions();
                    }
                }
            }
        }
    });
    
    // Скрываем подсказки при потере фокуса
    quill.on('selection-change', function(range) {
        if (!range) {
            setTimeout(hideSuggestions, 300);
        }
    });
    
    // Скрываем подсказки при клике вне редактора
    document.addEventListener('click', function(e) {
        if (!container.contains(e.target) && !document.getElementById('variableSuggestions')?.contains(e.target)) {
            hideSuggestions();
        }
    });
    
    // Сохраняем редактор
    quillEditors[editorId] = quill;
    
    return quill;
}