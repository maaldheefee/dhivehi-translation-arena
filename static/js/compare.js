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
    
    // State
    let currentComparison = null;
    let isSubmitting = false;
    
    // Initialization
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
    
    // Functions
    async function loadNextComparison() {
        showLoading();
        
        try {
            const res = await fetch('/compare/random');
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
            showToast('Failed to load comparison', 'error');
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
            showToast('Comparison recorded', 'success');
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
});
