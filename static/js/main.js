document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const translateBtn = document.getElementById('translate-btn');
    const queryInput = document.getElementById('query-input');
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
    const modelSelectionCheckboxes = document.getElementById('model-selection-checkboxes');

    // Event Listeners
    if (translateBtn) {
        translateBtn.addEventListener('click', handleTranslate);
    }
    
    predefinedQueryButtons.forEach(button => {
        button.addEventListener('click', function() {
            queryInput.value = this.textContent.trim();
            handleTranslate();
        });
    });
    
    loadUsers();
    loadModelsForSelection();
    
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }
    
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', handleClearCache);
    }
    
    if (submitVotesBtn) {
        submitVotesBtn.addEventListener('click', handleSubmitVotes);
    }
    
    function loadUsers() {
        fetch('/get_users')
            .then(response => response.json())
            .then(data => {
                if (data.users && usernameSelect) {
                    while (usernameSelect.options.length > 1) {
                        usernameSelect.remove(1);
                    }
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

    function loadModelsForSelection() {
        fetch('/get_available_models')
            .then(response => response.json())
            .then(data => {
                if (data.models && modelSelectionCheckboxes) {
                    modelSelectionCheckboxes.innerHTML = ''; // Clear loader
                    for (const [key, displayName] of Object.entries(data.models)) {
                        const div = document.createElement('div');
                        div.className = 'checkbox-wrapper';
                        
                        const input = document.createElement('input');
                        input.type = 'checkbox';
                        input.id = `model-${key}`;
                        input.name = 'models';
                        input.value = key;
                        input.checked = true; // Default to checked

                        const label = document.createElement('label');
                        label.htmlFor = `model-${key}`;
                        label.textContent = displayName;
                        
                        div.appendChild(input);
                        div.appendChild(label);
                        modelSelectionCheckboxes.appendChild(div);
                    }
                }
            })
            .catch(error => {
                console.error('Error loading models:', error);
                if(modelSelectionCheckboxes) {
                    modelSelectionCheckboxes.innerHTML = '<div class="error">Could not load models.</div>';
                }
            });
    }

    function handleLogin() {
        const username = usernameSelect.value;
        const password = userPassword.value;
        
        if (!username || !password) {
            alert('Please select a user and enter the password.');
            return;
        }
        
        fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            if (data.success) {
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error logging in:', error);
            alert('Error logging in. Please try again.');
        });
    }
    
    function handleTranslate() {
        const query = queryInput.value.trim();
        const selectedModels = Array.from(document.querySelectorAll('#model-selection-checkboxes input:checked')).map(cb => cb.value);

        if (!query) {
            alert('Please enter text to translate');
            return;
        }

        if (selectedModels.length < 2) {
            alert('Please select at least two models to compare.');
            return;
        }

        resultsSection.classList.remove('hidden');
        translationsContainer.innerHTML = '<div class="loader">Loading translations...</div>';
        if (submitVotesBtn) submitVotesBtn.style.display = 'none';
        if (voteStatusDiv) voteStatusDiv.classList.add('hidden');

        fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                models: selectedModels
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                translationsContainer.innerHTML = `<div class="error">${data.error}</div>`;
                return;
            }
            displayTranslations(data);
        })
        .catch(error => {
            console.error('Error fetching translations:', error);
            translationsContainer.innerHTML = '<div class="error">Error fetching translations. Please try again.</div>';
        });
    }

    function displayTranslations(data) {
        translationsContainer.innerHTML = '';
        if (queryIdField) queryIdField.value = data.query_id;

        let totalCost = 0;
        data.translations.forEach(translation => {
            const card = createTranslationCard(translation);
            translationsContainer.appendChild(card);
            totalCost += translation.cost;
        });

        totalCostElement.textContent = '$' + totalCost.toFixed(6);
        
        if (submitVotesBtn) {
            submitVotesBtn.style.display = 'inline-block';
            submitVotesBtn.disabled = false;
            submitVotesBtn.textContent = 'Submit Votes';
        }
    }

    function createTranslationCard(translation) {
        const template = document.getElementById('translation-template');
        const card = document.importNode(template.content, true).querySelector('.translation-card');

        card.dataset.id = translation.id;
        card.dataset.model = translation.model || "Unknown";
        card.querySelector('.position').textContent = translation.position;
        card.querySelector('.translation-text').textContent = translation.translation;
        
        const modelElement = card.querySelector('.model');
        if (modelElement) modelElement.textContent = translation.model;
        
        const ratingInput = card.querySelector('.rating-value');
        if (ratingInput) ratingInput.name = `rating-${translation.id}`;

        setupStarRatingListeners(card);
        return card;
    }

    function handleClearCache() {
        if (!confirm('Are you sure you want to clear the translation cache?')) return;
        
        fetch('/clear_cache', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            alert(data.message || data.error);
        })
        .catch(error => {
            console.error('Error clearing cache:', error);
            alert('Error clearing cache.');
        });
    }

    function setupStarRatingListeners(card) {
        const stars = card.querySelectorAll('.star');
        const rejectBtn = card.querySelector('.reject-btn-new');
        const ratingInput = card.querySelector('.rating-value');

        stars.forEach(star => {
            star.addEventListener('click', function() {
                const value = this.dataset.value;
                ratingInput.value = value;
                stars.forEach(s => s.classList.toggle('selected', s.dataset.value <= value));
                if (rejectBtn) rejectBtn.classList.remove('selected');
            });
            star.addEventListener('mouseover', function() {
                const value = this.dataset.value;
                stars.forEach(s => s.classList.toggle('hovered', s.dataset.value <= value));
            });
            star.addEventListener('mouseout', function() {
                stars.forEach(s => s.classList.remove('hovered'));
            });
        });

        if (rejectBtn) {
            rejectBtn.addEventListener('click', function() {
                const wasSelected = this.classList.contains('selected');
                this.classList.toggle('selected', !wasSelected);
                ratingInput.value = wasSelected ? 0 : -1;
                if (!wasSelected) stars.forEach(s => s.classList.remove('selected'));
            });
        }
    }

    function handleSubmitVotes() {
        const queryId = queryIdField ? queryIdField.value : null;
        if (!queryId) {
            showVoteStatus('No query ID found', 'error');
            return;
        }

        const votes = [];
        document.querySelectorAll('.translation-card').forEach(card => {
            const ratingInput = card.querySelector('.rating-value');
            const rating = parseInt(ratingInput.value, 10);
            if (rating !== 0) {
                votes.push({
                    translation_id: parseInt(card.dataset.id, 10),
                    rating: rating
                });
            }
        });

        if (votes.length === 0) {
            showVoteStatus('Please rate or reject at least one translation', 'error');
            return;
        }

        if (submitVotesBtn) {
            submitVotesBtn.disabled = true;
            submitVotesBtn.textContent = 'Submitting...';
        }

        fetch('/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query_id: parseInt(queryId, 10), votes: votes })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showVoteStatus('Thank you for voting!', 'success');
                disableVotingControls();
                if (submitVotesBtn) submitVotesBtn.style.display = 'none';
                document.querySelectorAll('.model-name').forEach(el => el.classList.remove('hidden'));
            } else {
                showVoteStatus(data.error || 'Error submitting votes', 'error');
                if (submitVotesBtn) {
                    submitVotesBtn.disabled = false;
                    submitVotesBtn.textContent = 'Submit Votes';
                }
            }
        })
        .catch(error => {
            console.error('Error submitting votes:', error);
            showVoteStatus('Error submitting votes. Please try again.', 'error');
            if (submitVotesBtn) {
                submitVotesBtn.disabled = false;
                submitVotesBtn.textContent = 'Submit Votes';
            }
        });
    }

    function showVoteStatus(message, type) {
        if (voteStatusDiv) {
            voteStatusDiv.textContent = message;
            voteStatusDiv.className = `vote-status ${type}`;
            voteStatusDiv.classList.remove('hidden');
            if (type === 'success') {
                setTimeout(() => voteStatusDiv.classList.add('hidden'), 5000);
            }
        }
    }

    function disableVotingControls() {
        document.querySelectorAll('.translation-card').forEach(card => {
            card.querySelectorAll('.star, .reject-btn-new').forEach(el => {
                el.style.pointerEvents = 'none';
                el.style.cursor = 'default';
            });
        });
    }
});