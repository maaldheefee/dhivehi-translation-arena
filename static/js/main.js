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
    const submitVotesBtn = document.getElementById('submit-votes-btn');
    const queryIdField = document.getElementById('query-id');
    const voteStatusDiv = document.getElementById('vote-status');
    const modelSelectionCheckboxes = document.getElementById('model-selection-checkboxes');

    let eventSource = null;
    let totalCost = 0;

    // Event Listeners
    if (translateBtn) translateBtn.addEventListener('click', handleTranslate);
    
    predefinedQueryButtons.forEach(button => {
        button.addEventListener('click', () => {
            queryInput.value = button.textContent.trim();
            handleTranslate();
        });
    });
    
    loadUsers();
    loadModelsForSelection();
    
    if (loginBtn) loginBtn.addEventListener('click', handleLogin);
    if (submitVotesBtn) submitVotesBtn.addEventListener('click', handleSubmitVotes);

    function loadUsers() {
        fetch('/get_users')
            .then(response => response.json())
            .then(data => {
                if (!data.users || !usernameSelect) return;
                while (usernameSelect.options.length > 1) usernameSelect.remove(1);
                data.users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.username;
                    option.textContent = user.username;
                    usernameSelect.appendChild(option);
                });
            }).catch(error => console.error('Error loading users:', error));
    }

    function loadModelsForSelection() {
        fetch('/get_available_models')
            .then(response => response.json())
            .then(data => {
                if (!data.models || !modelSelectionCheckboxes) return;
                modelSelectionCheckboxes.innerHTML = '';
                Object.entries(data.models).forEach(([key, displayName]) => {
                    const div = document.createElement('div');
                    div.className = 'checkbox-wrapper';
                    const input = document.createElement('input');
                    input.type = 'checkbox';
                    input.id = `model-${key}`;
                    input.name = 'models';
                    input.value = key;
                    input.checked = true;
                    const label = document.createElement('label');
                    label.htmlFor = `model-${key}`;
                    label.textContent = displayName;
                    div.append(input, label);
                    modelSelectionCheckboxes.appendChild(div);
                });
            }).catch(error => {
                console.error('Error loading models:', error);
                if (modelSelectionCheckboxes) modelSelectionCheckboxes.innerHTML = '<div class="error">Could not load models.</div>';
            });
    }

    function handleLogin() {
        if (!usernameSelect.value || !userPassword.value) {
            alert('Please select a user and enter the password.');
            return;
        }
        fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameSelect.value, password: userPassword.value })
        }).then(response => response.json()).then(data => {
            if (data.error) return alert(data.error);
            if (data.success) window.location.reload();
        }).catch(error => console.error('Error logging in:', error));
    }
    
    function handleTranslate() {
        const query = queryInput.value.trim();
        const selectedModels = Array.from(document.querySelectorAll('#model-selection-checkboxes input:checked')).map(cb => cb.value);

        if (!query) return alert('Please enter text to translate');
        if (selectedModels.length < 2) return alert('Please select at least two models to compare.');

        if (eventSource) eventSource.close();
        
        resultsSection.classList.remove('hidden');
        translationsContainer.innerHTML = '';
        if (submitVotesBtn) submitVotesBtn.style.display = 'none';
        if (voteStatusDiv) voteStatusDiv.classList.add('hidden');
        totalCost = 0;
        totalCostElement.textContent = '$0.000000';

        selectedModels.forEach((modelKey, index) => {
            const placeholder = createPlaceholderCard(modelKey, index + 1);
            translationsContainer.appendChild(placeholder);
        });

        const params = new URLSearchParams({ query: query });
        selectedModels.forEach(model => params.append('models', model));
        
        eventSource = new EventSource(`/stream-translate?${params.toString()}`);
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.error) {
                console.error(`Error for model ${data.model}: ${data.error}`);
                updateCardWithError(data.model, data.error);
                return;
            }
            updateCardWithTranslation(data);
        };

        eventSource.addEventListener('end', function(event) {
            eventSource.close();
            eventSource = null;
            if (submitVotesBtn) submitVotesBtn.style.display = 'inline-block';
            console.log('Stream finished.');
        });

        eventSource.onerror = function(err) {
            console.error('EventSource failed:', err);
            translationsContainer.innerHTML = `<div class="error">A network error occurred. Please try again.</div>`;
            if(eventSource) eventSource.close();
        };
    }

    function createPlaceholderCard(modelKey, position) {
        const template = document.getElementById('translation-placeholder-template');
        const card = template.content.cloneNode(true).querySelector('.translation-card');
        card.dataset.modelKey = modelKey;
        card.querySelector('.position').textContent = position;
        return card;
    }

    function updateCardWithTranslation(data) {
        const card = document.querySelector(`.translation-card[data-model-key="${data.model}"]`);
        if (!card) return;

        card.classList.remove('placeholder');
        card.dataset.id = data.id;
        if (queryIdField && !queryIdField.value) queryIdField.value = data.query_id;

        const contentTemplate = document.getElementById('translation-card-content-template');
        const content = contentTemplate.content.cloneNode(true);

        const modelNameDiv = content.querySelector('.model-name');
        modelNameDiv.querySelector('.model').textContent = data.model;
        card.querySelector('.card-header').appendChild(modelNameDiv);
        
        content.querySelector('.translation-text').textContent = data.translation;
        card.querySelector('.card-body').innerHTML = '';
        card.querySelector('.card-body').appendChild(content.querySelector('.card-body-content'));
        
        card.querySelector('.card-footer').innerHTML = '';
        card.querySelector('.card-footer').appendChild(content.querySelector('.card-footer-content'));
        
        setupStarRatingListeners(card);

        totalCost += data.cost;
        totalCostElement.textContent = '$' + totalCost.toFixed(6);
    }
    
    function updateCardWithError(modelKey, errorMsg) {
        const card = document.querySelector(`.translation-card[data-model-key="${modelKey}"]`);
        if (!card) return;
        card.classList.add('error-card');
        card.querySelector('.card-body').innerHTML = `<div class="error-message"><strong>Error:</strong> ${errorMsg}</div>`;
        
        const retryTemplate = document.getElementById('retry-button-template');
        if (retryTemplate) {
            const retryButton = retryTemplate.content.cloneNode(true).querySelector('button');
            retryButton.addEventListener('click', () => {
                const query = queryInput.value.trim();
                retrySingleTranslation(query, modelKey);
            });
            const footer = card.querySelector('.card-footer');
            footer.innerHTML = '';
            footer.appendChild(retryButton);
        }
    }
    
    function retrySingleTranslation(query, modelKey) {
        if (!query || !modelKey) return;

        const card = document.querySelector(`.translation-card[data-model-key="${modelKey}"]`);
        if (!card) return;

        card.classList.remove('error-card');
        card.querySelector('.card-body').innerHTML = '<div class="spinner"></div>';
        card.querySelector('.card-footer').innerHTML = '';

        const params = new URLSearchParams({ query: query, models: modelKey });
        const singleEventSource = new EventSource(`/stream-translate?${params.toString()}`);

        singleEventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.error) {
                console.error(`Retry error for model ${data.model}: ${data.error}`);
                updateCardWithError(data.model, data.error);
            } else {
                updateCardWithTranslation(data);
            }
        };

        singleEventSource.addEventListener('end', function(event) {
            singleEventSource.close();
            console.log(`Retry stream for ${modelKey} finished.`);
        });

        singleEventSource.onerror = function(err) {
            console.error('Single EventSource failed:', err);
            updateCardWithError(modelKey, 'A network error occurred during retry.');
            singleEventSource.close();
        };
    }

    function setupStarRatingListeners(card) {
        const stars = card.querySelectorAll('.star');
        const rejectBtn = card.querySelector('.reject-btn-new');
        const ratingInput = card.querySelector('.rating-value');
        if (!ratingInput) return;

        stars.forEach(star => {
            star.addEventListener('click', () => {
                const value = star.dataset.value;
                ratingInput.value = value;
                stars.forEach(s => s.classList.toggle('selected', s.dataset.value <= value));
                if (rejectBtn) rejectBtn.classList.remove('selected');
            });
            star.addEventListener('mouseover', () => {
                const value = star.dataset.value;
                stars.forEach(s => s.classList.toggle('hovered', s.dataset.value <= value));
            });
            star.addEventListener('mouseout', () => stars.forEach(s => s.classList.remove('hovered')));
        });

        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => {
                const wasSelected = rejectBtn.classList.contains('selected');
                rejectBtn.classList.toggle('selected', !wasSelected);
                ratingInput.value = wasSelected ? 0 : -1;
                if (!wasSelected) stars.forEach(s => s.classList.remove('selected'));
            });
        }
    }

    function handleSubmitVotes() {
        const queryId = queryIdField ? queryIdField.value : null;
        if (!queryId) return showVoteStatus('No query ID found', 'error');

        const votes = [];
        document.querySelectorAll('.translation-card:not(.placeholder):not(.error-card)').forEach(card => {
            const ratingInput = card.querySelector('.rating-value');
            if (ratingInput && ratingInput.value != 0) {
                votes.push({
                    translation_id: parseInt(card.dataset.id, 10),
                    rating: parseInt(ratingInput.value, 10)
                });
            }
        });

        if (votes.length === 0) return showVoteStatus('Please rate or reject at least one translation', 'error');

        if (submitVotesBtn) {
            submitVotesBtn.disabled = true;
            submitVotesBtn.textContent = 'Submitting...';
        }

        fetch('/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query_id: parseInt(queryId, 10), votes: votes })
        }).then(response => response.json()).then(data => {
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
        }).catch(error => {
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
            if (type === 'success') setTimeout(() => voteStatusDiv.classList.add('hidden'), 5000);
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