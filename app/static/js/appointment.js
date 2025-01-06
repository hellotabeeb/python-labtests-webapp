// Get DOM elements
const modal = document.getElementById('doctorModal');
const searchInput = document.querySelector('.search-bar input');
const categoryItems = document.querySelectorAll('.category-item');

// Open modal function
function openModal() {
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    searchInput.focus(); // Focus on search input when modal opens
}

// Close modal function
function closeModal() {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
    searchInput.value = ''; // Clear search input when modal closes
    filterCategories(''); // Reset category filtering
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == modal) {
        closeModal();
    }
}

// Handle escape key press to close modal
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && modal.style.display === 'block') {
        closeModal();
    }
});

// Filter categories based on search input
function filterCategories(searchTerm) {
    const normalizedSearchTerm = searchTerm.toLowerCase();
    
    categoryItems.forEach(item => {
        const categoryName = item.querySelector('.category-name').textContent.toLowerCase();
        if (categoryName.includes(normalizedSearchTerm)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

// Add search functionality
searchInput.addEventListener('input', (e) => {
    filterCategories(e.target.value);
});

// Add click event listeners to category items
categoryItems.forEach(item => {
    item.addEventListener('click', () => {
        const categoryName = item.querySelector('.category-name').textContent;
        console.log(`Selected category: ${categoryName}`);
        // Here you can add your logic for what happens when a category is selected
        // For example, redirect to a booking page or open another modal
    });
});



// Function to redirect to doctor listing page with selected category
function redirectToDoctorListing(category) {
    const formattedCategory = category.toLowerCase().replace(/\s+/g, '-');
    window.location.href = `/appointment/doctor-listing/${formattedCategory}`;
}

// Add click event listeners to category items
categoryItems.forEach(item => {
    item.addEventListener('click', () => {
        const categoryName = item.querySelector('.category-name').textContent;
        redirectToDoctorListing(categoryName);
    });
});