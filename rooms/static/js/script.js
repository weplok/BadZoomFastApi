
// Функции для валидации формы регистрации
function validateForm(formType) {
    if (formType === 'register') {
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
            showError('Пожалуйста, введите корректный email адрес', formType);
            email.focus();
            return false;
        }

        if (firstName.value.trim().length < 2) {
            showError('Имя должно содержать минимум 2 символа', formType);
            firstName.focus();
            return false;
        }

        if (lastName.value.trim().length < 2) {
            showError('Фамилия должна содержать минимум 2 символа', formType);
            lastName.focus();
            return false;
        }

        if (position.value.trim().length < 2) {
            showError('Должность должна содержать минимум 2 символа', formType);
            position.focus();
            return false;
        }

        if (password.value.length < 6) {
            showError('Пароль должен содержать минимум 6 символов', formType);
            password.focus();
            return false;
        }

        if (password.value !== passwordConfirm.value) {
            showError('Пароли не совпадают', formType);
            passwordConfirm.focus();
            return false;
        }
    } else if (formType == 'sign') {
        const email = document.getElementById('email');
        const password = document.getElementById('password');
        const errorDiv = document.getElementById('errorMessage');

        errorDiv.style.display = 'none';
        errorDiv.textContent = '';

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value)) {
            showError('Пожалуйста, введите корректный email адрес', formType);
            email.focus();
            return false;
        }

        if (password.value.length < 6) {
            showError('Пароль должен содержать минимум 6 символов', formType);
            password.focus();
            return false;
        }
    }

    return true;
}

// Обновленная функция showError
function showError(message, formType) {
    let errorDiv;

    if (formType == 'register') {
        errorDiv = document.getElementById('errorMessage');
    } else if (formType == 'sign') {
        errorDiv = document.getElementById('errorMessage');
    }

    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    // Прокручиваем к ошибке
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}


// Функции для главной страницы
document.addEventListener('DOMContentLoaded', function() {
    // Плавная прокрутка для навигационных ссылок
    const navLinks = document.querySelectorAll('a[href^="#"]');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                const headerHeight = document.querySelector('.header').offsetHeight;
                const targetPosition = targetElement.offsetTop - headerHeight - 20;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Анимация появления элементов при скролле
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Наблюдаем за виджетами
    const widgets = document.querySelectorAll('.widget');
    widgets.forEach(widget => {
        widget.style.opacity = '0';
        widget.style.transform = 'translateY(30px)';
        widget.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(widget);
    });

    // Изменение header при скролле
    const header = document.querySelector('.header');

    window.addEventListener('scroll', function() {
        if (window.scrollY > 100) {
            header.style.background = 'rgba(255, 255, 255, 0.98)';
            header.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        } else {
            header.style.background = 'rgba(255, 255, 255, 0.95)';
            header.style.boxShadow = 'none';
        }
    });

    // Real-time валидация паролей для формы регистрации
    const password = document.getElementById('password');
    const passwordConfirm = document.getElementById('password_confirm');

    if (password && passwordConfirm) {
        function validatePasswords() {
            if (password.value && passwordConfirm.value) {
                if (password.value !== passwordConfirm.value) {
                    passwordConfirm.style.borderColor = 'var(--error-color)';
                } else {
                    passwordConfirm.style.borderColor = 'var(--success-color)';
                }
            }
        }

        password.addEventListener('input', validatePasswords);
        passwordConfirm.addEventListener('input', validatePasswords);
    }

    // Анимация полей формы при фокусе
    const formInputs = document.querySelectorAll('.form-input');

    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'translateY(-2px)';
        });

        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'translateY(0)';
        });
    });
});