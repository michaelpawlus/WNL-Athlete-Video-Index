/**
 * WNL Athlete Video Index - Frontend Application
 */

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const searchSpinner = document.getElementById('searchSpinner');
const resultsContainer = document.getElementById('resultsContainer');
const emptyState = document.getElementById('emptyState');
const initialState = document.getElementById('initialState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');

/**
 * Show/hide UI states
 */
function showState(state) {
    // Hide all states
    resultsContainer.classList.add('hidden');
    emptyState.classList.add('hidden');
    initialState.classList.add('hidden');
    errorState.classList.add('hidden');

    // Show requested state
    switch (state) {
        case 'results':
            resultsContainer.classList.remove('hidden');
            break;
        case 'empty':
            emptyState.classList.remove('hidden');
            break;
        case 'initial':
            initialState.classList.remove('hidden');
            break;
        case 'error':
            errorState.classList.remove('hidden');
            break;
    }
}

/**
 * Show loading state
 */
function setLoading(loading) {
    if (loading) {
        searchButton.disabled = true;
        searchSpinner.classList.remove('hidden');
    } else {
        searchButton.disabled = false;
        searchSpinner.classList.add('hidden');
    }
}

/**
 * Show error message
 */
function showError(message) {
    errorMessage.textContent = message;
    showState('error');
}

/**
 * Format timestamp as MM:SS
 */
function formatTimestamp(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Get confidence badge color
 */
function getConfidenceBadgeClass(confidence) {
    if (confidence >= 0.9) return 'bg-green-100 text-green-800';
    if (confidence >= 0.7) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
}

/**
 * Create HTML for an athlete result card
 */
function createAthleteCard(athlete) {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-lg shadow-md overflow-hidden';

    // Header
    const header = document.createElement('div');
    header.className = 'px-6 py-4 border-b border-gray-200';
    header.innerHTML = `
        <h2 class="text-xl font-semibold text-gray-800">${escapeHtml(athlete.display_name)}</h2>
        <p class="text-sm text-gray-500">${athlete.appearances.length} video appearance${athlete.appearances.length !== 1 ? 's' : ''}</p>
    `;
    card.appendChild(header);

    // Appearances list
    if (athlete.appearances.length > 0) {
        const list = document.createElement('ul');
        list.className = 'divide-y divide-gray-200';

        for (const appearance of athlete.appearances) {
            const item = document.createElement('li');
            item.className = 'px-6 py-4 hover:bg-gray-50';

            const confidenceClass = getConfidenceBadgeClass(appearance.confidence_score);
            const confidencePercent = Math.round(appearance.confidence_score * 100);

            item.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <p class="text-gray-800 font-medium">${escapeHtml(appearance.video_title || 'Untitled Video')}</p>
                        <p class="text-sm text-gray-500">
                            Appears at ${formatTimestamp(appearance.timestamp_seconds)}
                        </p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-2 py-1 text-xs font-medium rounded-full ${confidenceClass}">
                            ${confidencePercent}% confidence
                        </span>
                        <a
                            href="${escapeHtml(appearance.youtube_timestamp_url)}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="inline-flex items-center px-3 py-1.5 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 transition-colors"
                        >
                            <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
                            </svg>
                            Watch
                        </a>
                    </div>
                </div>
            `;
            list.appendChild(item);
        }

        card.appendChild(list);
    }

    return card;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Search for athletes by name
 */
async function searchAthletes(query) {
    if (!query.trim()) {
        showState('initial');
        return;
    }

    setLoading(true);

    try {
        // First, search for athletes
        const searchResponse = await fetch(
            `${API_BASE_URL}/api/athletes/search?q=${encodeURIComponent(query)}`
        );

        if (!searchResponse.ok) {
            throw new Error(`Search failed: ${searchResponse.statusText}`);
        }

        const searchResults = await searchResponse.json();

        if (searchResults.length === 0) {
            showState('empty');
            return;
        }

        // Fetch full details for each athlete (with appearances)
        const athletePromises = searchResults.map(result =>
            fetch(`${API_BASE_URL}/api/athletes/${result.id}`).then(res => res.json())
        );

        const athletes = await Promise.all(athletePromises);

        // Clear previous results
        resultsContainer.innerHTML = '';

        // Create cards for each athlete
        for (const athlete of athletes) {
            const card = createAthleteCard(athlete);
            resultsContainer.appendChild(card);
        }

        showState('results');

    } catch (error) {
        console.error('Search error:', error);
        showError(`Failed to search: ${error.message}. Make sure the API server is running.`);
    } finally {
        setLoading(false);
    }
}

/**
 * Event Listeners
 */

// Search button click
searchButton.addEventListener('click', () => {
    searchAthletes(searchInput.value);
});

// Enter key in search input
searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        searchAthletes(searchInput.value);
    }
});

// Initialize
showState('initial');
