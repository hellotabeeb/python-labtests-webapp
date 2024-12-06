// static/js/doctor_registration.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('doctor-registration-form');
    const specialtySelect = document.getElementById('specialty');
    const fcpsSubSpecialty = document.getElementById('fcps-sub-specialty');
    const alliedHealthSubSpecialty = document.getElementById('allied-health-sub-specialty');
    const pmdcNumberField = document.getElementById('pmdc-number').parentElement; // Get the parent div.input-group
    const loadingSpinner = document.createElement('div');
    loadingSpinner.className = 'loading-spinner';
    loadingSpinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingSpinner);

    specialtySelect.addEventListener('change', function() {
        const selectedSpecialty = specialtySelect.value;
        
        // Handle sub-specialty sections
        fcpsSubSpecialty.style.display = selectedSpecialty === 'FCPS Consultant' ? 'block' : 'none';
        alliedHealthSubSpecialty.style.display = selectedSpecialty === 'Allied Health Services Professional' ? 'block' : 'none';
        
        // Handle PMDC number field visibility
        if (selectedSpecialty === 'Allied Health Services Professional') {
            pmdcNumberField.style.display = 'none';
            document.getElementById('pmdc-number').removeAttribute('required');
        } else {
            pmdcNumberField.style.display = 'block';
            document.getElementById('pmdc-number').setAttribute('required', '');
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Show the loading spinner
        loadingSpinner.style.display = 'flex';

        const formData = new FormData(form);

        // If Allied Health is selected, remove PMDC number from formData
        if (specialtySelect.value === 'Allied Health Services Professional') {
            formData.delete('pmdc-number');
        }

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