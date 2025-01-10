// Import Firebase modules
import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js';
import { getFirestore, collection, getDocs } from 'https://www.gstatic.com/firebasejs/9.6.1/firebase-firestore.js';

// Initialize Firebase (get config from the server)
async function initializeFirebase() {
    try {
        const response = await fetch('/firebase-config');
        if (!response.ok) {
            throw new Error('Failed to fetch Firebase config');
        }
        const firebaseConfig = await response.json();
        if (!firebaseConfig.projectId) {
            throw new Error('Firebase config is missing projectId');
        }
        const app = initializeApp(firebaseConfig);
        return getFirestore(app);
    } catch (error) {
        console.error("Error initializing Firebase:", error);
        return null;
    }
}

// Format category name to match database structure
function formatCategoryName(category) {
    // Special case for dermatologist
    if (category === 'dermatologist') {
        return 'dermatologists';
    }
    
    // For other categories, use the original name with first letter capitalized
    return category.charAt(0).toUpperCase() + category.slice(1);
}

// Fetch doctors based on category
async function fetchDoctorsByCategory(db, category) {
    if (!db) return [];
    
    const formattedCategory = formatCategoryName(category);
    console.log("Fetching doctors for category:", formattedCategory);
    
    const doctors = [];
    try {
        const doctorsRef = collection(db, 'doctors', formattedCategory, 'all');
        const querySnapshot = await getDocs(doctorsRef);
        querySnapshot.forEach((doc) => {
            const data = doc.data();
            doctors.push({
                id: doc.id,
                name: data.doctorName || 'Name Not Available',
                specialty: data.specialty || formattedCategory,
                experience: data.experience || 'N/A',
                hospital: data.hospital || 'Hospital Not Available',
                availableTime: data.availableTime || 'Schedule Not Available',
                email: data.email || '',
                pictureLink: data.pictureLink || '/api/placeholder/150/150',
                isOnline: Math.random() < 0.5, // Temporarily randomized
            });
        });
        console.log("Fetched doctors:", doctors);
    } catch (error) {
        console.error("Error fetching doctors:", error);
    }
    return doctors;
}

// Render doctor cards
function renderDoctorCards(doctors) {
    const doctorsContainer = document.getElementById('doctorsContainer');
    const template = document.getElementById('doctorCardTemplate');

    doctorsContainer.innerHTML = ''; // Clear previous content
    
    if (doctors.length === 0) {
        doctorsContainer.innerHTML = '<p class="no-doctors">No doctors found in this category.</p>';
        return;
    }

    doctors.forEach(doctor => {
        const clone = document.importNode(template.content, true);
        
        // Update card content
        const doctorNameElement = clone.querySelector('.doctor-name');
        if (doctorNameElement) doctorNameElement.textContent = doctor.name;

        const doctorSpecialtyElement = clone.querySelector('.specialty-text');
        if (doctorSpecialtyElement) doctorSpecialtyElement.textContent = doctor.specialty;

        const experienceElement = clone.querySelector('.experience-text');
        if (experienceElement) experienceElement.textContent = `${doctor.experience} years of experience`;

        const hospitalElement = clone.querySelector('.hospital-text');
        if (hospitalElement) hospitalElement.textContent = doctor.hospital;

        const availableTimeElement = clone.querySelector('.next-available');
        if (availableTimeElement) availableTimeElement.textContent = `Available: ${doctor.availableTime}`;

        const doctorImageElement = clone.querySelector('.doctor-image img');
        if (doctorImageElement) doctorImageElement.src = doctor.pictureLink;

        const onlineStatusElement = clone.querySelector('.online-status');
        if (onlineStatusElement) onlineStatusElement.classList.add(doctor.isOnline ? 'online' : 'offline');
        
        // Add event listeners to buttons
        const bookButton = clone.querySelector('.book-button');
        if (bookButton) bookButton.addEventListener('click', () => openBookingDialog(doctor));

        doctorsContainer.appendChild(clone);
    });
}

// Open booking dialog
function openBookingDialog(doctor) {
    const dialog = document.getElementById('bookingDialog');
    dialog.style.display = 'block';

    const form = document.getElementById('bookingForm');
    form.onsubmit = (e) => handleBookingFormSubmit(e, doctor);
}

// Close booking dialog
function closeBookingDialog() {
    const dialog = document.getElementById('bookingDialog');
    dialog.style.display = 'none';
}

// Handle booking form submission
async function handleBookingFormSubmit(event, doctor) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    // Add doctor details to FormData
    formData.append('doctorName', doctor.name);
    formData.append('doctorSpecialty', doctor.specialty);
    formData.append('doctorEmail', doctor.email);
    
    // Convert form field names to match backend expectations
    formData.append('patientName', formData.get('patient-name'));
    formData.append('patientAge', formData.get('patient-age'));
    formData.append('patientPhone', formData.get('patient-phone'));
    formData.append('patientEmail', formData.get('patient-email'));
    formData.append('appointmentDay', formData.get('appointment-day'));
    formData.append('appointmentTime', formData.get('appointment-time'));
    formData.append('patientRemarks', formData.get('patient-remarks'));

    // Add attachment to FormData
    const attachment = formData.get('attachment');
    if (attachment && attachment.size > 10 * 1024 * 1024) {
        alert('Attachment size exceeds 10MB limit.');
        return;
    }
    if (attachment) {
        formData.append('attachment', attachment);
    }

    // Show progress indicator
    const progressIndicator = document.getElementById('progress-indicator');
    progressIndicator.style.display = 'flex';

    try {
        const response = await fetch('/book-appointment', {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();
        if (result.success) {
            alert('Booking confirmed! You will be contacted soon.');
            closeBookingDialog();
        } else {
            alert('Booking failed. Please try again.');
        }
    } catch (error) {
        console.error('Error booking appointment:', error);
        alert('Booking failed. Please try again.');
    } finally {
        // Hide progress indicator
        progressIndicator.style.display = 'none';
    }
}

// Initialize page
async function initializePage() {
    // Get category from URL
    const pathSegments = window.location.pathname.split('/');
    let category = pathSegments[pathSegments.length - 1];
    
    if (!category) {
        console.error("No category found in URL");
        return;
    }

    // Temporary hardcode for testing
    if (category === 'dermatologist') {
        category = 'dermatologists';
    }

    // Show progress indicator
    const progressIndicator = document.getElementById('progress-indicator');
    progressIndicator.style.display = 'flex';

    // Initialize Firebase and fetch doctors
    const db = await initializeFirebase();
    if (db) {
        console.log("Firebase initialized successfully");
        const doctors = await fetchDoctorsByCategory(db, category);
        renderDoctorCards(doctors);
        
        // Initialize search functionality
        const searchInput = document.getElementById('doctorSearch');
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const filteredDoctors = doctors.filter(doctor => 
                doctor.name.toLowerCase().includes(searchTerm)
            );
            renderDoctorCards(filteredDoctors);
        });
    }

    // Hide progress indicator
    progressIndicator.style.display = 'none';

    // Add event listener to close button
    const closeButton = document.querySelector('.close-button');
    closeButton.addEventListener('click', closeBookingDialog);
}

// Fetch and render doctors on page load
document.addEventListener('DOMContentLoaded', initializePage);