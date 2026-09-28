// static/js/script.js
// Navigation toggle
const hamburger = document.querySelector(".hamburger");
const navMenu = document.querySelector(".nav-menu");

hamburger.addEventListener("click", () => {
    hamburger.classList.toggle("active");
    navMenu.classList.toggle("active");
});

document.querySelectorAll(".nav-link").forEach(n => n.addEventListener("click", () => {
    hamburger.classList.remove("active");
    navMenu.classList.remove("active");
}));

// Form validation
function validateForm(form) {
    let valid = true;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            valid = false;
            input.style.borderColor = '#e74c3c';
        } else {
            input.style.borderColor = '#ddd';
        }
    });
    
    // Validate Name (only characters and spaces)
    const nameInput = form.querySelector('#name');
    const nameError = form.querySelector('#name-error');
    if (nameInput && nameInput.value.trim()) {
        const charPattern = /^[A-Za-z\s]+$/;
        if (!charPattern.test(nameInput.value.trim())) {
            valid = false;
            nameInput.style.borderColor = '#e74c3c';
            if (nameError) nameError.style.display = 'block';
        } else {
            if (nameError) nameError.style.display = 'none';
        }
    }
    
    // Validate Phone (exactly 10 digits)
    const phoneInput = form.querySelector('#phone');
    const phoneError = form.querySelector('#phone-error');
    if (phoneInput && phoneInput.value.trim()) {
        const phonePattern = /^\d{10}$/;
        if (!phonePattern.test(phoneInput.value.trim())) {
            valid = false;
            phoneInput.style.borderColor = '#e74c3c';
            if (phoneError) phoneError.style.display = 'block';
        } else {
            if (phoneError) phoneError.style.display = 'none';
        }
    }
    
    // Validate Location/City (only characters, spaces, and commas)
    const locInput = form.querySelector('#location');
    const locError = form.querySelector('#location-error');
    if (locInput && locInput.value.trim()) {
        const locPattern = /^[A-Za-z\s,]+$/;
        if (!locPattern.test(locInput.value.trim())) {
            valid = false;
            locInput.style.borderColor = '#e74c3c';
            if (locError) locError.style.display = 'block';
        } else {
            if (locError) locError.style.display = 'none';
        }
    }
    
    return valid;
}

// Feature card navigation & Input Restrictions
document.addEventListener('DOMContentLoaded', function() {
    // Phone input restriction: numeric digits only, max 10 digits
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);
            const phoneError = document.getElementById('phone-error');
            if (this.value.length === 10) {
                this.style.borderColor = '#2ecc71';
                if (phoneError) phoneError.style.display = 'none';
            } else if (this.value.length > 0) {
                this.style.borderColor = '#e74c3c';
                if (phoneError) {
                    phoneError.textContent = `Phone number must be exactly 10 digits (${this.value.length}/10 digits entered).`;
                    phoneError.style.display = 'block';
                }
            } else {
                this.style.borderColor = '#ddd';
                if (phoneError) phoneError.style.display = 'none';
            }
        });
    }

    // Name input restriction: characters and spaces only
    const nameInput = document.getElementById('name');
    if (nameInput) {
        nameInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^A-Za-z\s]/g, '');
            const nameError = document.getElementById('name-error');
            if (nameInput.value.trim().length > 0) {
                this.style.borderColor = '#2ecc71';
                if (nameError) nameError.style.display = 'none';
            }
        });
    }

    // Location input restriction: characters, spaces, and commas only
    const locInput = document.getElementById('location');
    if (locInput) {
        locInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^A-Za-z\s,]/g, '');
            const locError = document.getElementById('location-error');
            if (locInput.value.trim().length > 0) {
                this.style.borderColor = '#2ecc71';
                if (locError) locError.style.display = 'none';
            }
        });
    }

    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.style.cursor = 'pointer';
        card.addEventListener('click', function() {
            // Get the target page from data attribute or content
            let targetPage = this.getAttribute('data-href');
            if (!targetPage) {
                const heading = this.querySelector('h3').textContent.toLowerCase();
                if (heading.includes('map')) targetPage = '/map';
                else if (heading.includes('alert') || heading.includes('warning')) targetPage = '/alerts';
                else if (heading.includes('volunteer')) targetPage = '/volunteer';
                else if (heading.includes('assistant') || heading.includes('ai')) targetPage = '/chatbot';
            }
            
            if (targetPage) {
                window.location.href = targetPage;
            }
        });
    });
});