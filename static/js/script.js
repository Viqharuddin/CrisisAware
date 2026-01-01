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
    
    return valid;
}

// Feature card navigation
document.addEventListener('DOMContentLoaded', function() {
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