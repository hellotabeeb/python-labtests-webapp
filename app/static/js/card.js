document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const loadingSpinner = document.querySelector('.loading-spinner');
    const paymentProofInput = document.querySelector('#payment-proof');

    // File size validation
    paymentProofInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const fileSize = file.size;
            const maxSize = 10 * 1024 * 1024; // 10MB
            
            if (fileSize > maxSize) {
                alert('File size exceeds 10MB limit. Please choose a smaller file.');
                this.value = '';
                return;
            }

            // Validate file type
            const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
            if (!allowedTypes.includes(file.type)) {
                alert('Please upload an image file (JPEG, PNG) or PDF');
                this.value = '';
                return;
            }
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Basic form validation
        const requiredFields = form.querySelectorAll('[required]');
        for (let field of requiredFields) {
            if (!field.value) {
                alert('Please fill in all required fields');
                field.focus();
                return;
            }
        }

        // Show loading spinner
        loadingSpinner.style.display = 'flex';

        const formData = new FormData(form);

        fetch('/submit-card-purchase', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingSpinner.style.display = 'none';
            
            if (data.success) {
                alert(data.message);
                form.reset();
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                throw new Error(data.message || 'Failed to submit card purchase');
            }
        })
        .catch(error => {
            loadingSpinner.style.display = 'none';
            alert('An error occurred while submitting your purchase. Please try again or contact support if the problem persists.');
            console.error('Error:', error);
        });
    });
});