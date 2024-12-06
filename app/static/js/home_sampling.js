// static/js/home_sampling.js - Add file size check
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('home-sampling-form');
    const prescriptionInput = document.getElementById('prescription');
    
    // Add file size validation
    prescriptionInput.addEventListener('change', function() {
        const fileSize = this.files[0].size;
        const maxSize = 10 * 1024 * 1024; // 10MB in bytes
        
        if (fileSize > maxSize) {
            alert('File size exceeds 10MB limit. Please choose a smaller file.');
            this.value = ''; // Clear the file input
        }
    });
    
    // Rest of your existing code...
});

// static/js/doctor_registration.js - Add file size validation for doctor uploads
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('doctor-registration-form');
    const imageInput = document.getElementById('doctor-image');
    const resumeInput = document.getElementById('doctor-resume');
    
    // Add file size validation for both files
    [imageInput, resumeInput].forEach(input => {
        input.addEventListener('change', function() {
            const fileSize = this.files[0].size;
            const maxSize = 10 * 1024 * 1024; // 10MB in bytes
            
            if (fileSize > maxSize) {
                alert('File size exceeds 10MB limit. Please choose a smaller file.');
                this.value = ''; // Clear the file input
            }
        });
    });
    
    // Rest of your existing code...
});