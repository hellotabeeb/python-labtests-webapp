// static/js/home_sampling.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('home-sampling-form');
    const loadingSpinner = document.createElement('div');
    loadingSpinner.className = 'loading-spinner';
    loadingSpinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingSpinner);

    const progressIndicator = document.getElementById('progress-indicator');

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Show the loading spinner
        progressIndicator.style.display = 'flex';

        const formData = new FormData(form);

        fetch('/home-sampling', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Hide the loading spinner
            progressIndicator.style.display = 'none';

            if (data.success) {
                alert('Your home sampling request has been successfully booked. You\'ll be contacted soon on your given number.');
                form.reset();
            } else {
                alert('Failed to submit home sampling request.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
            // Hide the loading spinner
            progressIndicator.style.display = 'none';
        });
    });
});