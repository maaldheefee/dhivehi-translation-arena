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
    const submitVotesBtn = document.getElementById('submit-votes-btn');
    const queryIdField = document.getElementById('query-id');
    const voteStatusDiv = document.getElementById('vote-status');
    
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
    
    // Submit votes button event listener
    if (submitVotesBtn) {
        submitVotesBtn.addEventListener('click', handleSubmitVotes);
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

        // Store query_id for voting
        if (queryIdField && data.query_id) {
            queryIdField.value = data.query_id;
        }

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
        
        // Show submit button if not previously voted
        if (!data.voted_translation) {
             if (submitVotesBtn) {
                submitVotesBtn.style.display = 'inline-block';
            }
        } else {
            // Hide submit button if already voted
            if (submitVotesBtn) {
                submitVotesBtn.style.display = 'none';
            }
        }
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

        const modelName = card.querySelector('.model-name');

        // Set unique name for rating input
        const ratingInput = card.querySelector('.rating-value');
        ratingInput.name = `rating-${translation.id}`;

        // Check if this is the voted translation
        if (votedTranslationId && translation.id === votedTranslationId) {
            //Always show model name
            modelName.classList.remove('hidden');
        }

        // Add star rating event listeners
        setupStarRatingListeners(card);

        return card;
    }

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

    // Setup star rating event listeners for a card
    function setupStarRatingListeners(card) {
        const stars = card.querySelectorAll('.star');
        const rejectBtn = card.querySelector('.reject-btn-new');
        const ratingInput = card.querySelector('.rating-value');

        stars.forEach(star => {
            star.addEventListener('click', function() {
                const value = this.dataset.value;
                ratingInput.value = value;

                // Update star visual state
                stars.forEach(s => {
                    s.classList.toggle('selected', s.dataset.value <= value);
                });

                // Clear reject state
                rejectBtn.classList.remove('selected');
            });

            star.addEventListener('mouseover', function() {
                const value = this.dataset.value;
                stars.forEach(s => {
                    s.classList.toggle('hovered', s.dataset.value <= value);
                });
            });

            star.addEventListener('mouseout', function() {
                stars.forEach(s => {
                    s.classList.remove('hovered');
                });
            });
        });

        rejectBtn.addEventListener('click', function() {
            const wasSelected = this.classList.contains('selected');
            
            if (wasSelected) {
                this.classList.remove('selected');
                ratingInput.value = 0;
            } else {
                this.classList.add('selected');
                ratingInput.value = -1;

                // Clear star rating
                stars.forEach(s => {
                    s.classList.remove('selected');
                });
            }
        });
    }

    // Handle submit votes
    function handleSubmitVotes() {
        const queryId = queryIdField ? queryIdField.value : null;
        
        if (!queryId) {
            showVoteStatus('No query ID found', 'error');
            return;
        }

        const votes = [];
        const cards = document.querySelectorAll('.translation-card');

        cards.forEach(card => {
            const translationId = parseInt(card.dataset.id);
            const ratingInput = card.querySelector('.rating-value');
            const rating = parseInt(ratingInput.value);

            // Only include votes that have a non-zero rating
            if (rating !== 0) {
                votes.push({
                    translation_id: translationId,
                    rating: rating
                });
            }
        });

        if (votes.length === 0) {
            showVoteStatus('Please rate or reject at least one translation', 'error');
            return;
        }

        // Disable submit button during submission
        if (submitVotesBtn) {
            submitVotesBtn.disabled = true;
            submitVotesBtn.textContent = 'Submitting...';
        }

        // Submit votes to server
        fetch('/vote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query_id: parseInt(queryId),
                votes: votes
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showVoteStatus('Thank you for voting! Your votes have been submitted.', 'success');
                // Hide voting controls and submit button
                disableVotingControls();
                if (submitVotesBtn) {
                    submitVotesBtn.style.display = 'none';
                }
                // Show model names
                document.querySelectorAll('.model-name').forEach(el => {
                    el.classList.remove('hidden');
                });
            } else {
                showVoteStatus(data.error || 'Error submitting votes', 'error');
                // Re-enable submit button
                if (submitVotesBtn) {
                    submitVotesBtn.disabled = false;
                    submitVotesBtn.textContent = 'Submit Votes';
                }
            }
        })
        .catch(error => {
            console.error('Error submitting votes:', error);
            showVoteStatus('Error submitting votes. Please try again.', 'error');
            // Re-enable submit button
            if (submitVotesBtn) {
                submitVotesBtn.disabled = false;
                submitVotesBtn.textContent = 'Submit Votes';
            }
        });
    }

    // Show vote status message
    function showVoteStatus(message, type) {
        if (voteStatusDiv) {
            voteStatusDiv.textContent = message;
            voteStatusDiv.className = `vote-status ${type}`;
            voteStatusDiv.classList.remove('hidden');
            
            // Auto-hide success messages after 5 seconds
            if (type === 'success') {
                setTimeout(() => {
                    voteStatusDiv.classList.add('hidden');
                }, 5000);
            }
        }
    }

    // Disable voting controls after submission
    function disableVotingControls() {
        const cards = document.querySelectorAll('.translation-card');
        cards.forEach(card => {
            const stars = card.querySelectorAll('.star');
            const rejectBtn = card.querySelector('.reject-btn-new');

            // Disable all interactive elements
            if (rejectBtn) {
                rejectBtn.disabled = true;
                rejectBtn.style.cursor = 'default';
            }
            stars.forEach(star => {
                star.style.pointerEvents = 'none';
                star.style.cursor = 'default';
            });
        });
    }
});
