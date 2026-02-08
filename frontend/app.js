/**
 * WNL Athlete Video Index - Frontend Application
 */

// ── DOM Elements ──────────────────────────────────────
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const searchSpinner = document.getElementById('searchSpinner');
const resultsContainer = document.getElementById('resultsContainer');
const emptyState = document.getElementById('emptyState');
const initialState = document.getElementById('initialState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');

// Stats
const statVideos = document.getElementById('statVideos');
const statAppearances = document.getElementById('statAppearances');

// Video Index
const videoIndexToggle = document.getElementById('videoIndexToggle');
const videoIndexChevron = document.getElementById('videoIndexChevron');
const videoIndexPanel = document.getElementById('videoIndexPanel');
const videoIndexList = document.getElementById('videoIndexList');
const videoFilterInput = document.getElementById('videoFilterInput');
const sortButtons = document.querySelectorAll('.sort-btn');

// ── State ─────────────────────────────────────────────
let cachedVideos = [];
let currentSort = 'title';
let sortAsc = true;
let filterDebounceTimer = null;

// ── UI State Management ───────────────────────────────

function showState(state) {
    resultsContainer.classList.add('hidden');
    emptyState.classList.add('hidden');
    initialState.classList.add('hidden');
    errorState.classList.add('hidden');

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

function setLoading(loading) {
    searchButton.disabled = loading;
    searchSpinner.classList.toggle('hidden', !loading);
}

function showError(message) {
    errorMessage.textContent = message;
    showState('error');
}

// ── Helpers ───────────────────────────────────────────

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimestamp(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Stats Bar ─────────────────────────────────────────

function animateCounter(el, target) {
    const duration = 600;
    const start = performance.now();
    const from = 0;

    function tick(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // ease-out quad
        const eased = 1 - (1 - progress) * (1 - progress);
        el.textContent = Math.round(from + (target - from) * eased);
        if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
}

function updateStats(videos) {
    const totalVideos = videos.length;
    const totalAppearances = videos.reduce((sum, v) => sum + (v.athlete_count || 0), 0);
    animateCounter(statVideos, totalVideos);
    animateCounter(statAppearances, totalAppearances);
}

// ── Video Index ───────────────────────────────────────

async function loadVideos() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/videos`);
        if (!res.ok) throw new Error(res.statusText);
        cachedVideos = await res.json();
        updateStats(cachedVideos);
        renderVideoIndex();
    } catch (err) {
        console.error('Failed to load videos:', err);
        videoIndexList.innerHTML =
            '<li class="text-center py-8 text-body text-sm">Unable to load video index.</li>';
        statVideos.textContent = '—';
        statAppearances.textContent = '—';
    }
}

function renderVideoIndex() {
    const filter = (videoFilterInput.value || '').toLowerCase();
    let videos = cachedVideos;

    // Filter
    if (filter) {
        videos = videos.filter(v => {
            const title = (v.title || '').toLowerCase();
            const event = (v.event_name || '').toLowerCase();
            return title.includes(filter) || event.includes(filter);
        });
    }

    // Sort
    videos = [...videos].sort((a, b) => {
        let cmp = 0;
        switch (currentSort) {
            case 'title':
                cmp = (a.title || '').localeCompare(b.title || '');
                break;
            case 'date':
                cmp = (a.processed_at || '').localeCompare(b.processed_at || '');
                break;
            case 'athletes':
                cmp = (a.athlete_count || 0) - (b.athlete_count || 0);
                break;
        }
        return sortAsc ? cmp : -cmp;
    });

    // Render
    if (videos.length === 0) {
        videoIndexList.innerHTML =
            '<li class="text-center py-8 text-body text-sm">No videos match your filter.</li>';
        return;
    }

    videoIndexList.innerHTML = '';
    for (const video of videos) {
        videoIndexList.appendChild(createVideoIndexItem(video));
    }
}

function createVideoIndexItem(video) {
    const li = document.createElement('li');
    li.className = 'px-2 py-3 hover:bg-primary-light/40 transition-colors rounded-lg';

    const watchUrl = `https://www.youtube.com/watch?v=${encodeURIComponent(video.youtube_id)}`;

    li.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="flex-1 min-w-0">
                <p class="font-heading font-semibold text-heading text-sm truncate">
                    ${escapeHtml(video.title || 'Untitled Video')}
                </p>
                <p class="text-xs text-body mt-0.5">
                    ${video.event_name ? escapeHtml(video.event_name) + ' &middot; ' : ''}
                    <span class="text-accent font-semibold">${video.athlete_count || 0}</span> athlete${(video.athlete_count || 0) !== 1 ? 's' : ''}
                    ${video.processed_at ? ' &middot; ' + escapeHtml(formatDate(video.processed_at)) : ''}
                </p>
            </div>
            <a href="${escapeHtml(watchUrl)}"
               target="_blank" rel="noopener noreferrer"
               class="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-yt text-white text-xs font-semibold hover:bg-red-700 transition-colors">
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
                </svg>
                Watch
            </a>
        </div>
    `;
    return li;
}

// Toggle expand / collapse
videoIndexToggle.addEventListener('click', () => {
    const expanded = videoIndexPanel.classList.toggle('expanded');
    videoIndexChevron.classList.toggle('rotated', expanded);
    videoIndexToggle.setAttribute('aria-expanded', expanded);
});

// Sort buttons
sortButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const sortKey = btn.dataset.sort;
        if (currentSort === sortKey) {
            sortAsc = !sortAsc;
        } else {
            currentSort = sortKey;
            sortAsc = true;
        }
        // Update active class
        sortButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderVideoIndex();
    });
});

// Filter input with debounce
videoFilterInput.addEventListener('input', () => {
    clearTimeout(filterDebounceTimer);
    filterDebounceTimer = setTimeout(renderVideoIndex, 250);
});

// ── Confidence Badge ──────────────────────────────────

function getConfidenceBadgeClass(confidence) {
    if (confidence >= 0.9) return 'bg-green-100 text-green-700';
    if (confidence >= 0.7) return 'bg-accent/15 text-accent-dark';
    return 'bg-gray-100 text-gray-600';
}

// ── Athlete Card ──────────────────────────────────────

function createAthleteCard(athlete, index) {
    const card = document.createElement('div');
    card.className =
        'bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden card-animate border-t-4 border-t-primary';
    card.style.animationDelay = `${index * 80}ms`;
    card.style.opacity = '0';

    // Header
    const header = document.createElement('div');
    header.className = 'px-6 py-4 flex items-center justify-between';
    header.innerHTML = `
        <div>
            <h2 class="font-heading text-xl font-bold uppercase text-heading tracking-wide">
                ${escapeHtml(athlete.display_name)}
            </h2>
        </div>
        <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-accent/15 text-accent-dark text-sm font-semibold">
            ${athlete.appearances.length}
            <span class="text-xs font-normal">appearance${athlete.appearances.length !== 1 ? 's' : ''}</span>
        </span>
    `;
    card.appendChild(header);

    // Appearances
    if (athlete.appearances.length > 0) {
        const list = document.createElement('ul');
        list.className = 'divide-y divide-gray-100';

        for (const appearance of athlete.appearances) {
            const item = document.createElement('li');
            item.className = 'px-6 py-3.5 hover:bg-primary-light/30 transition-colors';

            const confidenceClass = getConfidenceBadgeClass(appearance.confidence_score);
            const confidencePercent = Math.round(appearance.confidence_score * 100);

            item.innerHTML = `
                <div class="flex items-center justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-heading font-medium text-sm truncate">${escapeHtml(appearance.video_title || 'Untitled Video')}</p>
                        <p class="text-xs text-body mt-0.5">
                            Appears at <span class="font-semibold text-primary">${formatTimestamp(appearance.timestamp_seconds)}</span>
                        </p>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <span class="px-2.5 py-1 text-xs font-semibold rounded-full ${confidenceClass}">
                            ${confidencePercent}%
                        </span>
                        <a href="${escapeHtml(appearance.youtube_timestamp_url)}"
                           target="_blank" rel="noopener noreferrer"
                           class="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-yt text-white text-xs font-semibold hover:bg-red-700 transition-colors">
                            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
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

// ── Search ────────────────────────────────────────────

async function searchAthletes(query) {
    if (!query.trim()) {
        showState('initial');
        return;
    }

    setLoading(true);

    try {
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

        const athletePromises = searchResults.map(result =>
            fetch(`${API_BASE_URL}/api/athletes/${result.id}`).then(res => res.json())
        );

        const athletes = await Promise.all(athletePromises);

        resultsContainer.innerHTML = '';

        athletes.forEach((athlete, i) => {
            const card = createAthleteCard(athlete, i);
            resultsContainer.appendChild(card);
        });

        showState('results');
    } catch (error) {
        console.error('Search error:', error);
        showError(`Failed to search: ${error.message}. Make sure the API server is running.`);
    } finally {
        setLoading(false);
    }
}

// ── Event Listeners ───────────────────────────────────

searchButton.addEventListener('click', () => {
    searchAthletes(searchInput.value);
});

searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        searchAthletes(searchInput.value);
    }
});

// ── Initialize ────────────────────────────────────────

showState('initial');
loadVideos();
