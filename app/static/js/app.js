document.addEventListener('DOMContentLoaded', function() {
    const customSelect = document.querySelector('.custom-select');
    const customSelectTrigger = document.querySelector('.custom-select-trigger');
    const customOptions = document.querySelectorAll('.custom-option');
    const hiddenInput = document.getElementById('lab-select');
    const testSelectionContainer = document.getElementById('test-selection-container');
    const comingSoonMessage = document.getElementById('coming-soon-message');
    const testSearch = document.getElementById('test-search');
    const testList = document.getElementById('test-list');
    const selectedTestsList = document.getElementById('selected-tests-list');
    const totalFeeElement = document.getElementById('total-fee');
    const form = document.getElementById('lab-test-form');
    const loadingSpinner = document.getElementById('loading-spinner');
    const filterButtons = document.querySelectorAll('.filter-button');
    
    let tests = [];  // Store all tests from Firebase
    let selectedTests = new Set();  // Store selected test IDs
    let totalAmount = 0;
    let selectedDiscounts = new Set(); // To store selected discount filters
    
    // Lab-specific discount configurations
    const labDiscountConfigs = {
        'chughtai-lab': {
            defaultDiscount: 20,
            highDiscountTests: [
                "Lipid Profile",
                "Serum 25-OH Vitamin D",
                "Glycosylated Hemoglobin (HbA1c)"
            ],
            highDiscountPercentage: 30,
            testsToPlaceLast: [
                "CT Scanogram CompCt brain +orbit without contrast"
            ]
        },
        'idc-islamabad': {
            defaultDiscount: 10,
            highDiscountTests: [],
            highDiscountPercentage: 10,
            testsToPlaceLast: []
        },
        'dr-essa-lab': {
            defaultDiscount: 20,
            highDiscountTests: [],
            highDiscountPercentage: 20,
            testsToPlaceLast: []
        },
        'another-lab': {
            defaultDiscount: 15,
            highDiscountTests: [],
            highDiscountPercentage: 15,
            testsToPlaceLast: []
        }
    };

    // Function to show the loading spinner
    function showLoading() {
        loadingSpinner.classList.add('visible');
    }
    
    // Function to hide the loading spinner
    function hideLoading() {
        loadingSpinner.classList.remove('visible');
    }
    
    // Function to fetch tests from the server
    function fetchTests(labId) {
        showLoading(); // Show loading spinner
        fetch(`/tests?lab=${labId}`)
        .then(response => response.json())
        .then(data => {
            const labConfig = labDiscountConfigs[labId];
            
            // Assign discount based on lab configuration
            tests = data.map(test => ({
                ...test,
                discount: labConfig.highDiscountTests.includes(test.Name) 
                    ? labConfig.highDiscountPercentage 
                    : labConfig.defaultDiscount
            }));
    
            // Custom sorting function
            tests.sort((a, b) => {
                const nameA = a.Name.trim();
                const nameB = b.Name.trim();
    
                // Check if either test is in testsToPlaceLast
                const isAInLast = labConfig.testsToPlaceLast.includes(nameA);
                const isBInLast = labConfig.testsToPlaceLast.includes(nameB);
    
                // Check if tests start with numbers
                const aStartsWithNumber = /^\d/.test(nameA);
                const bStartsWithNumber = /^\d/.test(nameB);
    
                // If one test is in testsToPlaceLast and the other isn't
                if (isAInLast && !isBInLast) return 1;
                if (!isAInLast && isBInLast) return -1;
    
                // If one test starts with a number and the other doesn't
                if (aStartsWithNumber && !bStartsWithNumber) return 1;
                if (!aStartsWithNumber && bStartsWithNumber) return -1;
    
                // If both tests are in testsToPlaceLast or both start with numbers,
                // maintain their relative order
                if ((isAInLast && isBInLast) || (aStartsWithNumber && bStartsWithNumber)) {
                    return nameA.toLowerCase().localeCompare(nameB.toLowerCase());
                }
    
                // For all other cases, sort alphabetically
                return nameA.toLowerCase().localeCompare(nameB.toLowerCase());
            });
    
            hideLoading(); // Hide spinner after loading
            displayTests(tests); // Display tests after fetching
            
            // Update filter buttons based on lab configuration
            updateFilterButtons(labId);
        })
        .catch(error => {
            console.error('Error fetching tests:', error);
            hideLoading(); // Hide spinner even if there's an error
        });
    }
    
    // Function to update filter buttons based on lab configuration
    function updateFilterButtons(labId) {
        const labConfig = labDiscountConfigs[labId];
        
        // Hide filter buttons for labs with single discount
        if (labConfig.defaultDiscount === labConfig.highDiscountPercentage) {
            document.querySelector('.discount-filters').style.display = 'none';
        } else {
            document.querySelector('.discount-filters').style.display = 'block';
            
            // Reset previous filter state
            filterButtons.forEach(button => {
                button.classList.remove('active');
                const discount = parseInt(button.getAttribute('data-discount'));
                selectedDiscounts.delete(discount);
            });
        }
    }
    
    // Function to display tests as cards
    function displayTests(testsToShow) {
        testList.innerHTML = ''; // Clear existing tests
    
        if (testsToShow.length === 0) {
            testList.innerHTML = '<p>No tests found.</p>';
            return;
        }
    
        testsToShow.forEach(test => {
            const card = document.createElement('div');
            card.className = 'test-card';
            card.innerHTML = `
                <span class="tick-icon">&#10004;</span>
                <h3 class="test-name">${test.Name}</h3>
                <div class="price-container">
                    <p class="original-price">Rs.${test.Fees}</p>
                    <p class="discounted-price">Rs.${applyDiscount(test.Fees, test.discount)}</p>
                </div>
                <span class="discount-tag">${test.discount}% Off</span>
            `;
            testList.appendChild(card);
    
            // Update card selection state
            if (selectedTests.has(test.id)) {
                card.classList.add('selected');
            }
    
            // Add click event for the card
            card.addEventListener('click', () => toggleTest(test, card));
        });
    }
    
    // Function to apply discount based on percentage
    function applyDiscount(price, discount) {
        const discounted = parseFloat(price) - (parseFloat(price) * (discount / 100));
        return discounted.toFixed(2);
    }
    
    // Function to toggle test selection
    function toggleTest(test, card) {
        if (selectedTests.has(test.id)) {
            selectedTests.delete(test.id);
            card.classList.remove('selected');
            removeFromSelectedList(test);
            totalAmount -= parseFloat(applyDiscount(test.Fees, test.discount));
        } else {
            selectedTests.add(test.id);
            card.classList.add('selected');
            addToSelectedList(test);
            totalAmount += parseFloat(applyDiscount(test.Fees, test.discount));
        }
        updateTotalFee();
    }
    
    // Function to add test to selected list
    function addToSelectedList(test) {
        const li = document.createElement('li');
        li.setAttribute('data-test-id', test.id);
        li.innerHTML = `
            ${test.Name} - Rs.${applyDiscount(test.Fees, test.discount)}
            <button type="button" class="remove-test">&times;</button>
        `;
        selectedTestsList.appendChild(li);
    
        // Add event listener for remove button
        li.querySelector('.remove-test').addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent event bubbling
            selectedTests.delete(test.id);
            totalAmount -= parseFloat(applyDiscount(test.Fees, test.discount));
            updateTotalFee();
            li.remove();
            // Remove 'selected' class from the corresponding card
            const card = [...testList.children].find(c => 
                c.querySelector('.test-name').textContent === test.Name
            );
            if (card) {
                card.classList.remove('selected');
            }
        });
    }
    
    // Function to remove test from selected list
    function removeFromSelectedList(test) {
        const li = selectedTestsList.querySelector(`li[data-test-id="${test.id}"]`);
        if (li) {
            li.remove();
        }
    }
    
    // Function to update total fee
    function updateTotalFee() {
        totalFeeElement.textContent = `Rs.${totalAmount.toFixed(2)}`;
    }
    
    // Search functionality
    testSearch.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        let filteredTests = tests;
    
        // Apply search filter
        if (searchTerm) {
            filteredTests = tests.filter(test => 
                test.Name.toLowerCase().includes(searchTerm)
            );
        }
    
        // Apply discount filters if any are selected
        if (selectedDiscounts.size > 0) {
            filteredTests = filteredTests.filter(test => 
                selectedDiscounts.has(test.discount)
            );
        }
    
        displayTests(filteredTests);
    });
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Prevent default form submission
    
        if (selectedTests.size === 0) {
            alert('Please select at least one test before submitting.');
            return;
        }
    
        // Clear any existing hidden inputs
        const existingInputs = form.querySelectorAll('input[name="selected-tests"]');
        existingInputs.forEach(input => input.remove());
    
        // Add current selected tests to the form
        selectedTests.forEach(testId => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'selected-tests';
            input.value = testId;
            form.appendChild(input);
        });
    
        // Now you can submit the form
        form.submit();
    });
    
    // Handle Filter Button Clicks
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            const discount = parseInt(button.getAttribute('data-discount'));
            if (selectedDiscounts.has(discount)) {
                selectedDiscounts.delete(discount);
                button.classList.remove('active');
            } else {
                selectedDiscounts.add(discount);
                button.classList.add('active');
            }
            applyFilters();
        });
    });
    
    // Function to apply discount filters
    function applyFilters() {
        let filteredTests = tests;
        
        // Apply search filter if there's a search term
        const searchTerm = testSearch.value.toLowerCase().trim();
        if (searchTerm) {
            filteredTests = filteredTests.filter(test => 
                test.Name.toLowerCase().includes(searchTerm)
            );
        }
    
        // Apply discount filters if any are selected
        if (selectedDiscounts.size > 0) {
            filteredTests = filteredTests.filter(test => 
                selectedDiscounts.has(test.discount)
            );
        }
    
        displayTests(filteredTests);
    }
    
    // Event listener for custom select
    customSelectTrigger.addEventListener('click', function() {
        customSelect.classList.toggle('open');
    });

    customOptions.forEach(option => {
        option.addEventListener('click', function() {
            const value = option.getAttribute('data-value');
            const text = option.innerHTML;
            hiddenInput.value = value;
            customSelectTrigger.querySelector('span').innerHTML = text;
            customSelect.classList.remove('open');
            
            // Trigger change event for lab selection
            handleLabSelection(value);
        });
    });

    document.addEventListener('click', function(e) {
        if (!customSelect.contains(e.target)) {
            customSelect.classList.remove('open');
        }
    });

    function handleLabSelection(selectedLab) {
        // Reset selected tests and total amount
        selectedTests.clear();
        totalAmount = 0;
        selectedTestsList.innerHTML = '';
        updateTotalFee();
        
        if (selectedLab === 'chughtai-lab' || selectedLab === 'idc-islamabad' || selectedLab === 'dr-essa-lab' || selectedLab === 'another-lab') {
            testSelectionContainer.style.display = 'block';
            comingSoonMessage.style.display = 'none';
            
            // Fetch tests for the selected lab
            fetchTests(selectedLab);
        } else {
            testSelectionContainer.style.display = 'none';
            comingSoonMessage.style.display = 'block';
        }
    }
});