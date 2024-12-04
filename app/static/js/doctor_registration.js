document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('doctor-registration-form');
    const specialtySelect = document.getElementById('specialty');
    const fcpsSubSpecialty = document.getElementById('fcps-sub-specialty');
    const alliedHealthSubSpecialty = document.getElementById('allied-health-sub-specialty');
    const loadingSpinner = document.createElement('div');
    loadingSpinner.className = 'loading-spinner';
    loadingSpinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingSpinner);

    specialtySelect.addEventListener('change', function() {
        const selectedSpecialty = specialtySelect.value;
        fcpsSubSpecialty.style.display = selectedSpecialty === 'FCPS Consultant' ? 'block' : 'none';
        alliedHealthSubSpecialty.style.display = selectedSpecialty === 'Allied Health Services Professional' ? 'block' : 'none';
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Show the loading spinner
        loadingSpinner.style.display = 'flex';

        const formData = new FormData(form);

        fetch('/register-doctor', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Hide the loading spinner
            loadingSpinner.style.display = 'none';

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
            // Hide the loading spinner
            loadingSpinner.style.display = 'none';
        });
    });
});