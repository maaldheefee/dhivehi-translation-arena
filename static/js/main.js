document.addEventListener('DOMContentLoaded', function() {
    // --- Configuration & Elements ---
    const elements = {
        themeToggle: document.getElementById('theme-toggle'),
        themeIconLight: document.querySelector('.light-icon'),
        themeIconDark: document.querySelector('.dark-icon'),
        userMenuBtn: document.getElementById('user-menu-btn'),
        userMenuDropdown: document.getElementById('user-menu-dropdown'),
        usernameSelect: document.getElementById('username-select'),
        userPassword: document.getElementById('user-password'),
        loginBtn: document.getElementById('login-btn'),
        currentUsername: document.getElementById('current-username'),
        
        translateBtn: document.getElementById('translate-btn'),
        queryInput: document.getElementById('query-input'),
        resultsSection: document.getElementById('results-section'),
        translationsContainer: document.querySelector('.translations-grid'),
        totalCost: document.getElementById('total-cost'),
        modelParams: document.getElementById('model-selection-checkboxes'),
        
        submitVotesBtn: document.getElementById('submit-votes-btn'),
        voteStatus: document.getElementById('vote-status'),
        queryId: document.getElementById('query-id'),
        
        chips: document.querySelectorAll('.chip')
    };
    
    let eventSource = null;
    let currentTotalCost = 0;
    let seenHashes = new Set();

    // --- Localization Helper ---
    function t(key, params = {}) {
        let text = window.translations && window.translations[key] ? window.translations[key] : key;
        for (const [k, v] of Object.entries(params)) {
             text = text.replace(`{${k}}`, v);
        }
        return text;
    }

    // --- Initialization ---
    initTheme();
    loadUsers();
    loadModels();
    setupEventListeners();

    // --- Theme Logic ---
    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    }

    function updateThemeIcon(theme) {
        // Clear inline styles first to let classes control visibility
        if (elements.themeIconLight) elements.themeIconLight.style.display = '';
        if (elements.themeIconDark) elements.themeIconDark.style.display = '';

        if (theme === 'dark') {
            if (elements.themeIconLight) elements.themeIconLight.classList.remove('hidden');
            if (elements.themeIconDark) elements.themeIconDark.classList.add('hidden');
        } else {
            if (elements.themeIconLight) elements.themeIconLight.classList.add('hidden');
            if (elements.themeIconDark) elements.themeIconDark.classList.remove('hidden');
        }
    }

    // --- Toast Notifications ---
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- CSRF Helper ---
    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }

    // --- API Interactions ---
    function loadUsers() {
        fetch('/auth/get_users')
            .then(res => res.json())
            .then(data => {
                 if (data.users && elements.usernameSelect) {
                    elements.usernameSelect.innerHTML = `<option value="">${t('select_user')}</option>`;
                    data.users.forEach(user => {
                        const opt = document.createElement('option');
                        opt.value = user.username;
                        opt.textContent = user.username;
                        elements.usernameSelect.appendChild(opt);
                    });
                 }
            })
            .catch(err => console.error('Failed to load users', err));
    }

    function loadModels() {
        if (!elements.modelParams) return;
        
        fetch('/get_available_models')
            .then(res => res.json())
            .then(data => {
                elements.modelParams.innerHTML = '';
                if (data.models) {
                    Object.entries(data.models).forEach(([key, modelData]) => {
                        // Container Card
                        const isSelected = modelData.selected !== undefined ? modelData.selected : true;
                        const card = document.createElement('div');
                        card.className = `model-select-card ${isSelected ? 'selected' : ''}`;
                        
                        // Hidden Checkbox (for form submission logic)
                        const input = document.createElement('input');
                        input.type = 'checkbox';
                        input.id = `model-${key}`;
                        input.value = key;
                        input.checked = isSelected;
                        input.style.display = 'none';

                        // Header (Name + Check Indicator)
                        const header = document.createElement('div');
                        header.className = 'model-select-header';
                        
                        const name = typeof modelData === 'string' ? modelData : modelData.name;
                        const nameSpan = document.createElement('span');
                        nameSpan.className = 'model-select-name';
                        nameSpan.textContent = name;
                        
                        const indicator = document.createElement('div');
                        indicator.className = 'selection-indicator';
                        
                        header.appendChild(nameSpan);
                        header.appendChild(indicator);

                        // Footer (Cost)
                        const footer = document.createElement('div');
                        footer.className = 'model-select-footer';
                        
                        if (typeof modelData !== 'string') {
                            const costPill = document.createElement('span');
                            costPill.className = 'model-cost-pill';
                            costPill.textContent = `$${modelData.output_cost}/m`;
                            costPill.title = `Input: $${modelData.input_cost}/m, Output: $${modelData.output_cost}/m`;
                            footer.appendChild(costPill);
                        }

                        // Assemble
                        card.appendChild(input);
                        card.appendChild(header);
                        card.appendChild(footer);
                        
                        // Click Handler
                        card.addEventListener('click', () => {
                            input.checked = !input.checked;
                            if (input.checked) {
                                card.classList.add('selected');
                            } else {
                                card.classList.remove('selected');
                            }
                        });

                        elements.modelParams.appendChild(card);
                    });
                }
            })
            .catch(err => {
                console.error(err);
                elements.modelParams.innerHTML = '<div class="error-msg">Failed to load models.</div>';
            });
    }

    async function handleLogin() {
        const username = elements.usernameSelect.value;
        const password = elements.userPassword.value;
        
        if (!username || !password) {
            showToast(t('toast_enter_creds'), 'error');
            return;
        }
        
        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await res.json();
            if (data.success) {
                showToast(t('toast_login_success'), 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast(data.error || t('toast_login_fail'), 'error');
            }
        } catch (err) {
            showToast(t('toast_network_error_login'), 'error');
        }
    }

    function handleTranslate() {
        const query = elements.queryInput.value.trim();
        const selectedModels = Array.from(elements.modelParams.querySelectorAll('input:checked')).map(cb => cb.value);

        if (!query) return showToast(t('toast_enter_text'), 'error');
        if (selectedModels.length < 2) return showToast(t('toast_select_models'), 'error');

        // Reset UI
        if(eventSource) eventSource.close();
        
        elements.resultsSection.classList.remove('hidden');
        elements.translationsContainer.innerHTML = '';
        currentTotalCost = 0;
        seenHashes.clear();
        elements.totalCost.textContent = '0.000000';
        elements.submitVotesBtn.classList.add('hidden');
        elements.voteStatus.classList.add('hidden');
        elements.queryId.value = '';

        setTimeout(() => {
           elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);

        // Create placeholders
        selectedModels.forEach(modelKey => {
            const tmpl = document.getElementById('translation-placeholder-template');
            const clone = tmpl.content.cloneNode(true);
            const card = clone.querySelector('.translation-card');
            card.dataset.modelKey = modelKey;
            elements.translationsContainer.appendChild(card);
        });

        // Start Stream
        const params = new URLSearchParams({ query });
        selectedModels.forEach(m => params.append('models', m));

        eventSource = new EventSource(`/stream-translate?${params.toString()}`);
        
        eventSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.error) {
                if (data.type === 'auth_error') {
                    showToast(t('Authentication required. Please login.'), 'error');
                    eventSource.close();
                    elements.submitVotesBtn.classList.add('hidden');
                    return;
                }
                renderError(data.model, data.error);
            } else {
                renderTranslation(data);
            }
        };
        
        eventSource.addEventListener('end', () => {
             eventSource.close();
             elements.submitVotesBtn.classList.remove('hidden');
             showToast(t('toast_translation_complete'), 'success');
        });
        
        eventSource.onerror = (e) => {
            console.error('Stream error', e);

            // Check for auth error
            if (e.data) {
                try {
                    const data = JSON.parse(e.data);
                    if (data.type === 'auth_error') {
                        showToast(t('Authentication required. Please login.'), 'error');
                        elements.userMenuDropdown.classList.remove('hidden'); // Open login menu
                        eventSource.close();
                        elements.submitVotesBtn.classList.add('hidden');
                        return;
                    }
                } catch (err) {
                    console.error('Error parsing stream error data', err);
                }
            }

            eventSource.close();
            showToast(t('toast_stream_interrupted'), 'error');

            // Mark pending models as failed
            const pendingCards = document.querySelectorAll('.translation-card.placeholder');
            pendingCards.forEach(card => {
                const modelKey = card.dataset.modelKey;
                if (modelKey) {
                    renderError(modelKey, 'Stream connection lost / Model failed');
                }
            });

            // Allow voting on successful results
            elements.submitVotesBtn.classList.remove('hidden');
        };
    }
    
    function renderTranslation(data) {
        const card = document.querySelector(`.translation-card[data-model-key="${data.model}"]`);
        if (!card) return;
        
        card.classList.remove('placeholder');
        card.dataset.id = data.id;
        card.innerHTML = ''; // Clear placeholder content
        
        if (!elements.queryId.value) elements.queryId.value = data.query_id;
        
        // Update cost
        currentTotalCost += data.cost;
        elements.totalCost.textContent = currentTotalCost.toFixed(6);

        // Build content
        const tmpl = document.getElementById('translation-card-content-template');
        const content = tmpl.content.cloneNode(true);
        
        const modelEl = content.querySelector('.model');
        modelEl.textContent = data.model;
        modelEl.classList.add('blur-text');
        
        if (data.response_hash) {
            if (seenHashes.has(data.response_hash)) {
                const badge = document.createElement('span');
                badge.className = 'duplicate-badge';
                badge.textContent = t('duplicate_result');
                badge.style.cssText = 'background: #ff9800; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-left: 8px; vertical-align: middle;';
                modelEl.appendChild(badge);
                
                // Add tooltip or toast?
                // showToast(`Duplicate result detected for ${data.model}`, 'info');
            } else {
                seenHashes.add(data.response_hash);
            }
        }
        
        content.querySelector('.translation-text').textContent = data.translation;
        
        // Setup ratings
        setupStarRatingListeners(content);
        
        card.appendChild(content);
    }
    
    function renderError(modelKey, errorMsg) {
        const card = document.querySelector(`.translation-card[data-model-key="${modelKey}"]`);
        if (!card) return;
        
        card.classList.remove('placeholder');
        card.innerHTML = `<div class="card-body"><div class="error-message">Error: ${errorMsg}</div></div>`;
        
        const retryTmpl = document.getElementById('retry-button-template');
        const retryBtn = retryTmpl.content.cloneNode(true);
        retryBtn.querySelector('.retry-btn').addEventListener('click', () => {
             retrySingle(elements.queryInput.value, modelKey);
        });
        
        const footer = document.createElement('div');
        footer.className = 'card-footer';
        footer.appendChild(retryBtn);
        card.appendChild(footer);
    }

    function setupStarRatingListeners(card) {
        const stars = card.querySelectorAll('.star-btn');
        const rejectBtn = card.querySelector('.reject-btn');
        const ratingInput = card.querySelector('.rating-value');
        if (!ratingInput) return;

        stars.forEach((star, index) => {
            // Update titles based on localization
            if (index === 0) star.title = t('rating_okay_title');
            if (index === 1) star.title = t('rating_good_title');
            if (index === 2) star.title = t('rating_excellent_title');

            // Click
            star.addEventListener('click', () => {
                const value = star.dataset.value;
                ratingInput.value = value;
                stars.forEach(s => s.classList.toggle('selected', s.dataset.value <= value));
                if (rejectBtn) rejectBtn.classList.remove('selected');
            });
            
            // Hover
            star.addEventListener('mouseenter', () => {
                const hoverValue = parseInt(star.dataset.value);
                stars.forEach(s => {
                    if (parseInt(s.dataset.value) <= hoverValue) {
                        s.classList.add('hover-active');
                    } else {
                        s.classList.remove('hover-active');
                    }
                });
            });
            
            star.addEventListener('mouseleave', () => {
                stars.forEach(s => s.classList.remove('hover-active'));
            });
        });

        if (rejectBtn) {
            rejectBtn.title = t('reject_translation_title');
            rejectBtn.addEventListener('click', () => {
                const isSelected = rejectBtn.classList.contains('selected');
                
                if (!isSelected) {
                    rejectBtn.classList.add('selected');
                    ratingInput.value = -1;
                    stars.forEach(s => s.classList.remove('selected'));
                } else {
                    rejectBtn.classList.remove('selected');
                    ratingInput.value = 0;
                }
            });
        }
    }

    async function submitVotes() {
        const queryId = elements.queryId.value;
        if (!queryId) return;
        
        const votes = [];
        document.querySelectorAll('.translation-card').forEach(card => {
            const input = card.querySelector('.rating-value');
            const translationId = parseInt(card.dataset.id);
            // Only include cards with valid translation IDs (skip error cards)
            if (input && input.value != 0 && !isNaN(translationId)) {
                votes.push({
                    translation_id: translationId,
                    rating: parseInt(input.value)
                });
            }
        });
        
        if (votes.length === 0) return showToast(t('toast_rate_one'), 'info');
        
        elements.submitVotesBtn.disabled = true;
        
        try {
            const res = await fetch('/vote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ query_id: queryId, votes })
            });
            
            const data = await res.json();
            if (data.status === 'success') {
                showToast(t('toast_votes_submitted'), 'success');
                elements.submitVotesBtn.classList.add('hidden');
                document.querySelectorAll('.model-name-badge').forEach(el => {
                    el.classList.remove('blur-text');
                    el.style.backgroundColor = 'transparent';
                    el.style.color = 'var(--text-secondary)';
                });
            } else {
                showToast(data.error || t('toast_vote_fail'), 'error');
                elements.submitVotesBtn.disabled = false;
            }
        } catch (err) {
            showToast(t('toast_vote_network_error'), 'error');
            elements.submitVotesBtn.disabled = false;
        }
    }

    function setupEventListeners() {
        if (elements.themeToggle) elements.themeToggle.addEventListener('click', toggleTheme);
        if (elements.userMenuBtn) {
            elements.userMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                elements.userMenuDropdown.classList.toggle('hidden');
            });
        }
        
        document.addEventListener('click', (e) => {
           if (elements.userMenuDropdown && !elements.userMenuDropdown.contains(e.target) && e.target !== elements.userMenuBtn) {
               elements.userMenuDropdown.classList.add('hidden');
           } 
        });

        if (elements.loginBtn) elements.loginBtn.addEventListener('click', handleLogin);
        if (elements.translateBtn) elements.translateBtn.addEventListener('click', handleTranslate);
        if (elements.submitVotesBtn) elements.submitVotesBtn.addEventListener('click', submitVotes);
        
        // Chip clicks
        elements.chips.forEach(chip => {
            chip.addEventListener('click', () => {
                elements.queryInput.value = chip.dataset.query;
                handleTranslate();
            });
        });
    }
    
    // Retry a single failed model translation
    async function retrySingle(query, modelKey) {
        const card = document.querySelector(`.translation-card[data-model-key="${modelKey}"]`);
        if (!card) return;
        
        // Show loading state
        card.innerHTML = `
            <div class="card-header">
                <div class="model-badge skeleton-text"></div>
            </div>
            <div class="card-body">
                <div class="skeleton-line full"></div>
                <div class="skeleton-line three-quarter"></div>
                <div class="skeleton-line half"></div>
            </div>`;
        card.classList.add('placeholder');
        
        try {
            const res = await fetch('/retry-single', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ query, model: modelKey })
            });
            
            if (res.status === 401) {
                showToast(t('Authentication required. Please login.'), 'error');
                renderError(modelKey, 'Authentication required');
                return;
            }

            const data = await res.json();
            
            if (data.error) {
                renderError(modelKey, data.error);
            } else {
                renderTranslation(data);
                showToast(t('toast_retry_success') || 'Retry successful!', 'success');
            }
        } catch (err) {
            console.error('Retry error:', err);
            renderError(modelKey, 'Network error during retry');
        }
    }
});