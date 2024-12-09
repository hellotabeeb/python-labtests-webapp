document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('validationForm');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        let isValid = true;
        
        // Email validation
        const email = document.getElementById('email');
        const emailError = document.getElementById('emailError');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!emailRegex.test(email.value)) {
            emailError.textContent = 'Please enter a valid email address';
            isValid = false;
        } else {
            emailError.textContent = '';
        }
        
        // Password validation
        const password = document.getElementById('password');
        const passwordError = document.getElementById('passwordError');
        
        if (password.value.length < 8) {
            passwordError.textContent = 'Password must be at least 8 characters long';
            isValid = false;
        } else {
            passwordError.textContent = '';
        }
        
        if (isValid) {
            console.log('Form is valid, submitting...');
            // Add your form submission logic here
        }
    });
});