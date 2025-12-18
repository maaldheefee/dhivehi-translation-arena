document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elements = {
        loadingState: document.getElementById('loading-state'),
        emptyState: document.getElementById('empty-state'),
        interface: document.getElementById('compare-interface'),
        sourceText: document.getElementById('source-text'),
        optionA: document.getElementById('option-a'),
        optionB: document.getElementById('option-b'),
        tieBtn: document.getElementById('tie-btn'),
        skipBtn: document.getElementById('skip-btn')
    };
    
    // Elements already defined above... adding new ones
    elements.toggleFiltersBtn = document.getElementById('toggle-filters-btn');
    elements.filterPanel = document.getElementById('filter-panel');
    elements.modelFiltersGrid = document.getElementById('model-filters-grid');
    elements.applyFiltersBtn = document.getElementById('apply-filters-btn');
    elements.clearFiltersBtn = document.getElementById('clear-filters-btn');
    elements.filterCountBadge = document.getElementById('filter-count-badge');
    elements.activeFilterMsg = document.getElementById('active-filter-msg');
    elements.activeFilterList = document.getElementById('active-filter-list');
    
    // State
    let currentComparison = null;
    let isSubmitting = false;
    let availableModels = {};
    let selectedModels = new Set();
    
    // Initialization
    fetchAvailableModels(); // Load models first, but don't wait for it to load comparison
    loadNextComparison();
    
    // Event Listeners
    if (elements.optionA) {
        elements.optionA.addEventListener('click', () => submitComparison('a'));
    }
    
    if (elements.optionB) {
        elements.optionB.addEventListener('click', () => submitComparison('b'));
    }
    
    if (elements.tieBtn) {
        elements.tieBtn.addEventListener('click', () => submitComparison('tie'));
    }
    
    if (elements.skipBtn) {
        elements.skipBtn.addEventListener('click', loadNextComparison);
    }

    // Filter Listeners
    if(elements.toggleFiltersBtn) {
        elements.toggleFiltersBtn.addEventListener('click', () => {
             elements.filterPanel.classList.toggle('hidden');
        });
    }

    if(elements.applyFiltersBtn) {
        elements.applyFiltersBtn.addEventListener('click', () => {
            updateSelectedModels();
            loadNextComparison();
            // Optional: Close panel on apply? keeping it open might be better if they want to tweak 
            // elements.filterPanel.classList.add('hidden'); 
        });
    }

    if(elements.clearFiltersBtn) {
        elements.clearFiltersBtn.addEventListener('click', () => {
             document.querySelectorAll('.model-filter-checkbox').forEach(cb => cb.checked = false);
             updateSelectedModels(); // Will clear the set
             loadNextComparison();
        });
    }
    
    // Functions
    async function fetchAvailableModels() {
        try {
            const res = await fetch('/get_available_models');
            const data = await res.json();
            availableModels = data.models;
            renderModelFilters();
        } catch (err) {
            console.error('Failed to load models', err);
            if (elements.modelFiltersGrid) {
                elements.modelFiltersGrid.innerHTML = '<div class="text-red-500 text-xs">Failed to load models</div>';
            }
        }
    }

    function renderModelFilters() {
        if (!elements.modelFiltersGrid) return;
        elements.modelFiltersGrid.innerHTML = '';
        
        // Sort by name
        const sortedKeys = Object.keys(availableModels).sort((a, b) => {
            return (availableModels[a].name || a).localeCompare(availableModels[b].name || b);
        });

        sortedKeys.forEach(key => {
            const model = availableModels[key];
            const div = document.createElement('div');
            // Increased gap to 3, improved dark mode hover, added padding
            div.className = 'flex items-center gap-3 text-xs p-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded transition-colors';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `filter-${key}`;
            checkbox.value = key;
            // Added dark mode border and background for checkbox to be visible
            checkbox.className = 'model-filter-checkbox rounded text-primary focus:ring-primary border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:checked:bg-primary';
            
            const label = document.createElement('label');
            label.htmlFor = `filter-${key}`;
            // Removed explicit color classes to inherit var(--text-primary) from body
            label.className = 'truncate cursor-pointer select-none flex-1 font-medium';
            label.textContent = model.name;
            label.title = model.name; 
            
            div.appendChild(checkbox);
            div.appendChild(label);
            elements.modelFiltersGrid.appendChild(div);
        });
    }

    function updateSelectedModels() {
        selectedModels.clear();
        document.querySelectorAll('.model-filter-checkbox:checked').forEach(cb => {
            selectedModels.add(cb.value);
        });
        
        // Update badge and active message
        if (selectedModels.size > 0) {
            if(elements.filterCountBadge) {
                elements.filterCountBadge.textContent = selectedModels.size;
                elements.filterCountBadge.classList.remove('hidden');
            }
            if(elements.activeFilterMsg) {
                elements.activeFilterMsg.classList.remove('hidden');
                elements.activeFilterList.textContent = Array.from(selectedModels).map(k => availableModels[k]?.name || k).join(', ');
            }
            // Highlight toggle button
            elements.toggleFiltersBtn.classList.add('text-primary');
        } else {
            if(elements.filterCountBadge) elements.filterCountBadge.classList.add('hidden');
            if(elements.activeFilterMsg) elements.activeFilterMsg.classList.add('hidden');
            elements.toggleFiltersBtn.classList.remove('text-primary');
        }
    }

    async function loadNextComparison() {
        showLoading();
        
        try {
            let url = '/compare/random';
            if (selectedModels.size > 0) {
                const modelsParam = Array.from(selectedModels).join(',');
                url += `?target_models=${encodeURIComponent(modelsParam)}`;
            }

            const res = await fetch(url);
            if (res.status === 404) {
                showEmptyState();
                return;
            }
            
            if (!res.ok) throw new Error('Failed to fetch comparison');
            
            const data = await res.json();
            renderComparison(data);
        } catch (err) {
            console.error('Error loading comparison:', err);
            // Show toast or error state
            showToast('Failed to load comparison: ' + err.message, 'error');
            
            // If it failed because of strict filter, maybe we should show empty state
            if (selectedModels.size > 0) {
                 showEmptyState();
                 // Custom message for empty state when filtering
                 const emptyMsg = elements.emptyState.querySelector('h3');
                 if(emptyMsg) emptyMsg.textContent = t('no_more_comparisons');
            }
        }
    }
    
    function renderComparison(data) {
        currentComparison = data;
        
        // Reset selections
        elements.optionA.className = 'compare-card cursor-pointer hover:border-primary transition-all duration-200';
        elements.optionB.className = 'compare-card cursor-pointer hover:border-primary transition-all duration-200';
        
        // Reset model name visibility
        elements.optionA.querySelector('.model-name').classList.add('hidden');
        elements.optionB.querySelector('.model-name').classList.add('hidden');
        
        // Update content
        elements.sourceText.textContent = data.source_text;
        
        // Option A
        const t1 = data.translations[0];
        elements.optionA.dataset.id = t1.id;
        elements.optionA.querySelector('.translation-text').textContent = t1.text;
        renderModelInfo(elements.optionA.querySelector('.model-name'), t1);
        
        // Option B
        const t2 = data.translations[1];
        elements.optionB.dataset.id = t2.id;
        elements.optionB.querySelector('.translation-text').textContent = t2.text;
        renderModelInfo(elements.optionB.querySelector('.model-name'), t2);
        
        if (data.stats) {
            renderStats(data.stats);
        }

        showInterface();
    }
    
    async function submitComparison(winner) {
        if (isSubmitting || !currentComparison) return;
        isSubmitting = true;
        
        // Visual feedback
        if (winner === 'a') {
            elements.optionA.classList.add('selected');
        } else if (winner === 'b') {
            elements.optionB.classList.add('selected');
        }

        // Reveal model names
        elements.optionA.querySelector('.model-name').classList.remove('hidden');
        elements.optionB.querySelector('.model-name').classList.remove('hidden');
        
        const payload = {
            query_id: currentComparison.query_id,
            translation_ids: [
                currentComparison.translations[0].id,
                currentComparison.translations[1].id
            ],
            winner_id: null
        };
        
        if (winner === 'a') {
            payload.winner_id = currentComparison.translations[0].id;
        } else if (winner === 'b') {
            payload.winner_id = currentComparison.translations[1].id;
        }
        // If tie, winner_id remains null
        
        try {
            const res = await fetch('/compare/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) throw new Error('Failed to submit comparison');
            
            // Success! Load next
            showToast(t('toast_votes_submitted'), 'success');
            setTimeout(() => {
                isSubmitting = false;
                loadNextComparison();
            }, 1500); // 1.5s delay to see selection and model names
            
        } catch (err) {
            console.error('Error submitting comparison:', err);
            showToast('Failed to submit comparison', 'error');
            isSubmitting = false;
        }
    }
    
    // UI Helpers
    function showLoading() {
        elements.loadingState.classList.remove('hidden');
        elements.emptyState.classList.add('hidden');
        elements.interface.classList.add('hidden');
    }
    
    function showEmptyState() {
        elements.loadingState.classList.add('hidden');
        elements.emptyState.classList.remove('hidden');
        elements.interface.classList.add('hidden');
    }
    
    function showInterface() {
        elements.loadingState.classList.add('hidden');
        elements.emptyState.classList.add('hidden');
        elements.interface.classList.remove('hidden');
    }
    
    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        const container = document.getElementById('toast-container');
        if (container) {
            container.appendChild(toast);
            setTimeout(() => {
                toast.remove();
            }, 3000);
        }
    }

    function renderModelInfo(element, translation) {
        element.innerHTML = '';
        
        const container = document.createElement('div');
        container.className = 'text-right flex flex-col items-end';
        
        const nameDiv = document.createElement('div');
        nameDiv.className = 'font-bold text-gray-900 dark:text-gray-100 text-sm';
        nameDiv.textContent = translation.base_model || translation.model;
        container.appendChild(nameDiv);
        
        if (translation.preset_name) {
            const presetDiv = document.createElement('div');
            presetDiv.className = 'text-xs text-gray-500';
            presetDiv.textContent = translation.preset_name;
            container.appendChild(presetDiv);
        }
        
        element.appendChild(container);
    }

    function renderStats(stats) {
        const container = document.getElementById('stats-container');
        if (!container || !stats) return;

        console.log("Comparison Stats:", stats);
        // "Comparisons submitted: 5 (20 remaining)"
        const remainingText = stats.pairs_remaining !== undefined ? ` (${stats.pairs_remaining} ${t('stats_remaining')})` : '';
        container.textContent = `${t('stats_submitted')}: ${stats.comparisons_done}${remainingText}`;
    }
});
