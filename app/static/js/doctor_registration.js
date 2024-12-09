// static/js/doctor_registration.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('doctor-registration-form');
    const specialtySelect = document.getElementById('specialty');
    const fcpsSubSpecialty = document.getElementById('fcps-sub-specialty');
    const alliedHealthSubSpecialty = document.getElementById('allied-health-sub-specialty');
    const pmdcNumberField = document.getElementById('pmdc-number').parentElement;
    const loadingSpinner = document.createElement('div');
    const imageInput = document.getElementById('doctor-image');
    const resumeInput = document.getElementById('doctor-resume');
    
    // Initialize loading spinner
    loadingSpinner.className = 'loading-spinner';
    loadingSpinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingSpinner);

    // File size validation
    [imageInput, resumeInput].forEach(input => {
        input.addEventListener('change', function() {
            const fileSize = this.files[0].size;
            const maxSize = 10 * 1024 * 1024; // 10MB
            
            if (fileSize > maxSize) {
                alert('File size exceeds 10MB limit. Please choose a smaller file.');
                this.value = '';
            }
        });
    });

    // Specialty change handler
    specialtySelect.addEventListener('change', function() {
        const selectedSpecialty = specialtySelect.value;
        
        // Handle sub-specialty sections
        fcpsSubSpecialty.style.display = selectedSpecialty === 'FCPS Consultant' ? 'block' : 'none';
        alliedHealthSubSpecialty.style.display = selectedSpecialty === 'Allied Health Services Professional' ? 'block' : 'none';
        
        // Handle PMDC number field visibility and requirements
        if (selectedSpecialty === 'Allied Health Services Professional') {
            pmdcNumberField.style.display = 'none';
            document.getElementById('pmdc-number').removeAttribute('required');
        } else {
            pmdcNumberField.style.display = 'block';
            document.getElementById('pmdc-number').setAttribute('required', '');
            
            // Update placeholder based on specialty
            const pmdcInput = document.getElementById('pmdc-number');
            if (selectedSpecialty === 'BDS') {
                pmdcInput.placeholder = 'Enter PMDC number (Dental Council)';
            } else {
                pmdcInput.placeholder = 'Enter PMDC number';
            }
        }
    });

    // Form submission handler
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Validate required fields
        const requiredFields = form.querySelectorAll('[required]');
        for (let field of requiredFields) {
            if (!field.value) {
                alert('Please fill in all required fields.');
                field.focus();
                return;
            }
        }

        // Show loading spinner
        loadingSpinner.style.display = 'flex';

        const formData = new FormData(form);

        // Remove PMDC number for Allied Health
        if (specialtySelect.value === 'Allied Health Services Professional') {
            formData.delete('pmdc-number');
        }

        // Add timestamp
        formData.append('timestamp', new Date().toISOString());

        fetch('/register-doctor', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            loadingSpinner.style.display = 'none';
            if (data.success) {
                alert('Doctor registered successfully.');
                form.reset();
                // Reset specialty sections
                fcpsSubSpecialty.style.display = 'none';
                alliedHealthSubSpecialty.style.display = 'none';
            } else {
                alert(data.message || 'Failed to register doctor.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
            loadingSpinner.style.display = 'none';
        });
    });
});