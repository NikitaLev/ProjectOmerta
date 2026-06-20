// ========== РЕДАКТОР ДЛЯ ПУНКТОВ ПРАВИЛ ==========

let quillEditors = {};

function initQuillEditor(editorId, hiddenInputId) {
    if (quillEditors[editorId]) {
        // Если редактор уже создан, удаляем его
        quillEditors[editorId].destroy();
        delete quillEditors[editorId];
    }
    
    const container = document.getElementById(editorId);
    if (!container) return null;
    
    // Создаем редактор Quill с темной темой
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
        placeholder: 'Введите текст пункта правил...',
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
    `;
    document.head.appendChild(style);
    
    // Получаем скрытое поле для сохранения HTML
    const hiddenInput = document.getElementById(hiddenInputId);
    if (hiddenInput) {
        // При изменении содержимого обновляем скрытое поле
        quill.on('text-change', function() {
            const html = quill.root.innerHTML;
            hiddenInput.value = html;
        });
    }
    
    // Сохраняем редактор
    quillEditors[editorId] = quill;
    
    return quill;
}

function setQuillContent(editorId, content) {
    const quill = quillEditors[editorId];
    if (quill && content) {
        quill.root.innerHTML = content;
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