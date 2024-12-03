// static/js/doctor_registration.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('doctor-registration-form');

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(form);

        fetch('/register-doctor', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Doctor registered successfully.');
                form.reset();
            } else {
                alert('Failed to register doctor.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });
    });
});