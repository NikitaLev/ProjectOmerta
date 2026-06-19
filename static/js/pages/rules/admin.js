// ========== ДОПОЛНИТЕЛЬНАЯ ЛОГИКА ДЛЯ СТРАНИЦЫ ПРАВИЛ ==========

// Пока все функции вынесены в modals.js
// Этот файл можно использовать для дополнительной логики в будущем

console.log('Rules admin page loaded');

// Пример: авто-скрытие сообщений
document.addEventListener('DOMContentLoaded', function() {
    // Если есть сообщения, скрываем их через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 300);
        }, 5000);
    });
});