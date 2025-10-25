function validateForm() {
    const email = document.getElementById('email');
    const firstName = document.getElementById('first_name');
    const lastName = document.getElementById('last_name');
    const password = document.getElementById('password');
    const passwordConfirm = document.getElementById('password_confirm');
    const position = document.getElementById('position');
    const errorDiv = document.getElementById('errorMessage');

    errorDiv.style.display = 'none';
    errorDiv.textContent = '';

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.value)) {
        showError('Пожалуйста, введите корректный email адрес');
        email.focus();
        return false;
    }

    if (firstName.value.trim().length < 2) {
        showError('Имя должно содержать минимум 2 символа');
        firstName.focus();
        return false;
    }

    if (lastName.value.trim().length < 2) {
        showError('Фамилия должна содержать минимум 2 символа');
        lastName.focus();
        return false;
    }

    if (position.value.trim().length < 2) {
        showError('Должность должна содержать минимум 2 символа');
        position.focus();
        return false;
    }

    if (password.value.length < 6) {
        showError('Пароль должен содержать минимум 6 символов');
        password.focus();
        return false;
    }

    if (password.value !== passwordConfirm.value) {
        showError('Пароли не совпадают');
        passwordConfirm.focus();
        return false;
    }

    return true;
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}