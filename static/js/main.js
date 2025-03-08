document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const translateBtn = document.getElementById('translate-btn');
    const queryInput = document.getElementById('query-input');
    const systemPrompt = document.getElementById('system-prompt');
    const resultsSection = document.getElementById('results-section');
    const translationsContainer = document.querySelector('.translations-container');
    const totalCostElement = document.getElementById('total-cost');
    const predefinedQueryButtons = document.querySelectorAll('.predefined-query');
    const usernameSelect = document.getElementById('username-select');
    const userPassword = document.getElementById('user-password');
    const loginBtn = document.getElementById('login-btn');
    const clearCacheBtn = document.getElementById('clear-cache-btn');
    const currentUsernameElement = document.getElementById('current-username');
    
    // Event Listeners
    translateBtn.addEventListener('click', handleTranslate);
    
    predefinedQueryButtons.forEach(button => {
        button.addEventListener('click', function() {
            queryInput.value = this.textContent.trim();
            handleTranslate();
        });
    });
    
    // Load users on page load
    loadUsers();
    
    // Login button event listener
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }
    
    // Clear cache button event listener
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', handleClearCache);
    }
    
    // Function to load users from the server
    function loadUsers() {
        fetch('/get_users')
            .then(response => response.json())
            .then(data => {
                if (data.users && usernameSelect) {
                    // Clear existing options except the first one
                    while (usernameSelect.options.length > 1) {
                        usernameSelect.remove(1);
                    }
                    
                    // Add user options
                    data.users.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.username;
                        option.textContent = user.username;
                        usernameSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading users:', error);
            });
    }
    
    // Function to handle login
    function handleLogin() {
        const username = usernameSelect.value;
        const password = userPassword.value;
        
        if (!username) {
            alert('Please select a user');
            return;
        }
        
        if (!password) {
            alert('Please enter your PIN/password');
            return;
        }
        
        fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            if (data.success) {
                // Update UI
                currentUsernameElement.textContent = username;
                userPassword.value = ''; // Clear password field
                
                // Reload the page to update all UI elements
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error logging in:', error);
            alert('Error logging in. Please try again.');
        });
    }
    
    // Handle translation request
    function handleTranslate() {
        console.log("Translate button clicked!"); // Debugging line
        const query = queryInput.value.trim();

        if (!query) {
            alert('Please enter text to translate');
            return;
        }

        // Show loading state
        resultsSection.classList.remove('hidden');
        translationsContainer.innerHTML = '<div class="loader">Loading translations...</div>';

        // Make API request
        fetch('/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                // system_prompt is now handled on the server-side
            })
        })
        .then(response => response.json())
        .then(data => {
            displayTranslations(data);
        })
        .catch(error => {
            console.error('Error fetching translations:', error);
            translationsContainer.innerHTML = '<div class="error">Error fetching translations. Please try again.</div>';
        });
    }

     // Display translations in the UI
    function displayTranslations(data) {
        translationsContainer.innerHTML = '';

        // Calculate total cost
        let totalCost = 0;

        // Create and append translation cards
        data.translations.forEach(translation => {
            const card = createTranslationCard(translation, data.voted_translation);
            translationsContainer.appendChild(card);

            totalCost += translation.cost;
        });

        // Update total cost display
        totalCostElement.textContent = '$' + totalCost.toFixed(6);
    }

   // Create a translation card from template
    function createTranslationCard(translation, votedTranslationId) {
        const template = document.getElementById('translation-template');
        const card = document.importNode(template.content, true).querySelector('.translation-card');

        // Set card data
        card.dataset.id = translation.id;
        card.dataset.model = translation.model || "Unknown"; // Store model name in data attribute
        card.querySelector('.position').textContent = translation.position;
        card.querySelector('.translation-text').textContent = translation.translation;
        
        // Set model name if available
        const modelElement = card.querySelector('.model');
        if (translation.model) {
            modelElement.textContent = translation.model;
        } else {
            modelElement.textContent = "Unknown";
        }

        // Hide model name until after voting
        card.querySelector('.model-name').classList.add('hidden');

        const voteBtn = card.querySelector('.vote-btn');
        const votedBadge = card.querySelector('.voted-badge');
        const modelName = card.querySelector('.model-name');

        // Check if this is the voted translation
        if (votedTranslationId && translation.id === votedTranslationId) {
            voteBtn.classList.add('hidden');
            votedBadge.classList.remove('hidden');
            //Always show model name
            modelName.classList.remove('hidden');
        }


        // Add vote event listener
        voteBtn.addEventListener('click', function() {
            vote(translation.id);
        });

        return card;
    }

    // Handle voting
    // Function to handle clearing the cache
    function handleClearCache() {
        if (!confirm('Are you sure you want to clear the translation cache?')) {
            return;
        }
        
        fetch('/clear_cache', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
            } else if (data.error) {
                alert(data.error);
            }
        })
        .catch(error => {
            console.error('Error clearing cache:', error);
            alert('Error clearing cache. Please try again.');
        });
    }

    function vote(translationId) {
         fetch('/vote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    translation_id: translationId
                })
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    // Update UI to show vote and model
                    document.querySelectorAll('.translation-card').forEach( card => {
                        const cardId = parseInt(card.dataset.id);
                        const voteBtn = card.querySelector('.vote-btn');
                        const votedBadge = card.querySelector('.voted-badge');
                        const modelName = card.querySelector('.model-name');

                        if (cardId === translationId) {
                            // This is the voted card
                            voteBtn.classList.add('hidden');
                            votedBadge.classList.remove('hidden');
                        } else {
                            // Reset other cards
                            voteBtn.classList.remove('hidden');
                            votedBadge.classList.add('hidden');
                        }
                        // Reveal model name
                        modelName.classList.remove('hidden');

                        // Update model name if it was returned from the server
                        if (data.model && cardId === translationId) {
                            card.dataset.model = data.model;
                        }
                        // Set the model text from the dataset
                        card.querySelector('.model').textContent = card.dataset.model;
                    });
                }
            })
            .catch(error => {
                console.error('Error submitting vote:', error);
                alert('Error submitting vote. Please try again.');
            });
    }
});
