// profile_edit.js - логика редактирования профиля

// DOM элементы
const profileForm = document.getElementById('profileForm');
const passwordForm = document.getElementById('passwordForm');
const notificationContainer = document.getElementById('notificationContainer');

// Функция показа уведомления
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = 'notification';
    
    let icon = '';
    if (type === 'success') {
        icon = '<i class="fas fa-check-circle"></i>';
    } else if (type === 'error') {
        icon = '<i class="fas fa-exclamation-circle"></i>';
    } else {
        icon = '<i class="fas fa-info-circle"></i>';
    }
    
    notification.innerHTML = `
        <div class="notification-content notification-${type}">
            <div class="notification-icon">${icon}</div>
            <div class="notification-message">${message}</div>
            <div class="notification-close">
                <i class="fas fa-times"></i>
            </div>
        </div>
    `;
    
    notificationContainer.appendChild(notification);
    
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    });
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Очистка ошибок в полях
function clearFieldErrors() {
    document.querySelectorAll('.form-control.error').forEach(el => {
        el.classList.remove('error');
    });
    document.querySelectorAll('.error-text').forEach(el => {
        el.textContent = '';
    });
}

// Подсветка поля с ошибкой
function highlightField(fieldId, errorMessage) {
    const field = document.getElementById(fieldId);
    const errorDiv = document.getElementById(`${fieldId}Error`);
    if (field) {
        field.classList.add('error');
        setTimeout(() => {
            field.classList.remove('error');
        }, 3000);
    }
    if (errorDiv) {
        errorDiv.textContent = errorMessage;
    }
    showNotification(errorMessage, 'error');
}

// Валидация email
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@([^\s@.,]+\.)+[^\s@.,]{2,}$/;
    if (!email) return 'Email не может быть пустым';
    if (!emailRegex.test(email)) return 'Введите корректный email адрес (например, name@domain.ru)';
    return null;
}

// Валидация пароля (для смены)
function validatePassword(password, confirmPassword) {
    if (!password) return 'Пароль не может быть пустым';
    if (password.length < 8) return 'Пароль должен содержать минимум 8 символов';
    if (password === '12345678' || password === 'qwerty123' || password === 'password123') {
        return 'Слишком простой пароль. Используйте комбинацию букв и цифр';
    }
    if (password !== confirmPassword) return 'Пароли не совпадают';
    return null;
}

// Обновление профиля (AJAX)
async function updateProfile(email, playerNickname) {
    const response = await fetch('/profile/edit/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: new URLSearchParams({
            csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value,
            email: email,
            player_nickname: playerNickname,
            edit_profile: 'true'
        })
    });
    
    const data = await response.json();
    return data;
}

// Смена пароля (AJAX)
async function changePassword(oldPassword, newPassword1, newPassword2) {
    const response = await fetch('/profile/edit/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: new URLSearchParams({
            csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value,
            old_password: oldPassword,
            new_password1: newPassword1,
            new_password2: newPassword2,
            change_password: 'true'
        })
    });
    
    const data = await response.json();
    return data;
}

// Обработчик формы профиля
profileForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors();
    
    const email = document.getElementById('email').value.trim();
    const playerNickname = document.getElementById('player_nickname').value.trim();
    const submitBtn = document.getElementById('saveProfileBtn');
    
    // Валидация email
    const emailError = validateEmail(email);
    if (emailError) {
        highlightField('email', emailError);
        return;
    }
    
    // Блокируем кнопку
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading-spinner-small"></span> Сохранение...';
    
    try {
        const result = await updateProfile(email, playerNickname);
        
        if (result.success) {
            showNotification(result.message || '✅ Профиль успешно обновлён!', 'success');
            // Обновляем отображаемые данные
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            if (result.errors && result.errors.length > 0) {
                result.errors.forEach(error => {
                    if (error.includes('email') || error.includes('Email')) {
                        highlightField('email', error);
                    } else {
                        showNotification(error, 'error');
                    }
                });
            } else {
                showNotification('❌ Не удалось обновить профиль', 'error');
            }
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('❌ Произошла ошибка на сервере', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
});

// Обработчик формы смены пароля
passwordForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors();
    
    const oldPassword = document.getElementById('old_password').value;
    const newPassword1 = document.getElementById('new_password1').value;
    const newPassword2 = document.getElementById('new_password2').value;
    const submitBtn = document.getElementById('changePasswordBtn');
    
    // Валидация
    if (!oldPassword) {
        highlightField('old_password', 'Введите текущий пароль');
        return;
    }
    
    const passwordError = validatePassword(newPassword1, newPassword2);
    if (passwordError) {
        if (passwordError.includes('минимум')) {
            highlightField('new_password1', passwordError);
        } else if (passwordError.includes('не совпадают')) {
            highlightField('new_password2', passwordError);
        } else {
            highlightField('new_password1', passwordError);
        }
        return;
    }
    
    // Блокируем кнопку
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading-spinner-small"></span> Смена пароля...';
    
    try {
        const result = await changePassword(oldPassword, newPassword1, newPassword2);
        
        if (result.success) {
            showNotification(result.message || '✅ Пароль успешно изменён!', 'success');
            // Очищаем поля
            document.getElementById('old_password').value = '';
            document.getElementById('new_password1').value = '';
            document.getElementById('new_password2').value = '';
        } else {
            if (result.errors && result.errors.length > 0) {
                result.errors.forEach(error => {
                    if (error.includes('текущий') || error.includes('старый') || error.includes('old')) {
                        highlightField('old_password', error);
                    } else if (error.includes('совпадают')) {
                        highlightField('new_password2', error);
                    } else {
                        highlightField('new_password1', error);
                    }
                });
            } else {
                showNotification('❌ Не удалось сменить пароль', 'error');
            }
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('❌ Произошла ошибка на сервере', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
});

// Валидация в реальном времени
const emailField = document.getElementById('email');
emailField?.addEventListener('blur', () => {
    const error = validateEmail(emailField.value.trim());
    if (error) {
        highlightField('email', error);
    } else {
        document.getElementById('emailError').textContent = '';
        emailField.classList.remove('error');
    }
});

const newPassword1Field = document.getElementById('new_password1');
newPassword1Field?.addEventListener('blur', () => {
    const value = newPassword1Field.value;
    if (value && value.length < 8) {
        highlightField('new_password1', 'Пароль должен быть минимум 8 символов');
    }
});

const newPassword2Field = document.getElementById('new_password2');
newPassword2Field?.addEventListener('blur', () => {
    const pwd1 = document.getElementById('new_password1').value;
    const pwd2 = newPassword2Field.value;
    if (pwd2 && pwd1 !== pwd2) {
        highlightField('new_password2', 'Пароли не совпадают');
    }
});