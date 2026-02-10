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

// Theme Toggle
const themeToggle = document.getElementById('themeToggle');
const sunIcon = document.getElementById('sunIcon');
const moonIcon = document.getElementById('moonIcon');

function updateToggleIcons(isDark) {
    sunIcon.classList.toggle('hidden', !isDark);
    moonIcon.classList.toggle('hidden', isDark);
    themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
}

themeToggle.addEventListener('click', () => {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem(window.__themeUtils.STORAGE_KEY, isDark ? 'dark' : 'light');
    updateToggleIcons(isDark);
});

// Sync icons on load
updateToggleIcons(document.documentElement.classList.contains('dark'));

// Listen for OS theme changes (only when no manual preference)
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (localStorage.getItem(window.__themeUtils.STORAGE_KEY)) return;
    window.__themeUtils.applyTheme(e.matches ? 'dark' : 'light');
    updateToggleIcons(e.matches);
});

// ── State ─────────────────────────────────────────────
let cachedVideos = [];
let currentSort = 'title';
let sortAsc = true;
let filterDebounceTimer = null;
let searchDebounceTimer = null;
let suggestionIndex = -1;

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
            '<li class="text-center py-8 text-body dark:text-dk-body text-sm">Unable to load video index.</li>';
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
            const channel = (v.channel_name || '').toLowerCase();
            return title.includes(filter) || event.includes(filter) || channel.includes(filter);
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
                cmp = (a.event_date || a.processed_at || '').localeCompare(b.event_date || b.processed_at || '');
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
            '<li class="text-center py-8 text-body dark:text-dk-body text-sm">No videos match your filter.</li>';
        return;
    }

    videoIndexList.innerHTML = '';
    for (const video of videos) {
        videoIndexList.appendChild(createVideoIndexItem(video));
    }
}

function createVideoIndexItem(video) {
    const li = document.createElement('li');
    li.className = 'px-2 py-3 hover:bg-primary-light/40 dark:hover:bg-dk-hover transition-colors rounded-lg';

    const watchUrl = `https://www.youtube.com/watch?v=${encodeURIComponent(video.youtube_id)}`;
    const thumbUrl = `https://i.ytimg.com/vi/${encodeURIComponent(video.youtube_id)}/mqdefault.jpg`;
    const displayDate = video.event_date || video.processed_at;
    const channelHtml = video.channel_name
        ? escapeHtml(video.channel_name) + ' &middot; '
        : '';

    li.innerHTML = `
        <div class="flex items-center gap-3">
            <a href="${escapeHtml(watchUrl)}" target="_blank" rel="noopener noreferrer" class="shrink-0">
                <img src="${escapeHtml(thumbUrl)}" alt="" width="96" height="54"
                     class="rounded object-cover" style="width:96px;height:54px;" loading="lazy">
            </a>
            <div class="flex-1 min-w-0">
                <p class="font-heading font-semibold text-heading dark:text-dk-heading text-sm truncate">
                    ${escapeHtml(video.title || 'Untitled Video')}
                </p>
                <p class="text-xs text-body dark:text-dk-body mt-0.5">
                    ${channelHtml}
                    ${video.event_name ? escapeHtml(video.event_name) + ' &middot; ' : ''}
                    <span class="text-accent font-semibold">${video.athlete_count || 0}</span> athlete${(video.athlete_count || 0) !== 1 ? 's' : ''}
                    ${displayDate ? ' &middot; ' + escapeHtml(formatDate(displayDate)) : ''}
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
    if (confidence >= 0.9) return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    if (confidence >= 0.7) return 'bg-accent/15 text-accent-dark dark:bg-accent/10 dark:text-accent';
    return 'bg-gray-100 text-gray-600 dark:bg-dk-border dark:text-dk-body';
}

// ── Score Badge ───────────────────────────────────────

function getScoreBadgeClass(score) {
    if (score >= 80) return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    if (score >= 60) return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
    return 'bg-gray-100 text-gray-600 dark:bg-dk-border dark:text-dk-body';
}

// ── Suggestion Dropdown ───────────────────────────────

function getSuggestionDropdown() {
    let dropdown = document.getElementById('suggestionDropdown');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'suggestionDropdown';
        dropdown.className =
            'absolute left-0 right-0 top-full mt-1 bg-white dark:bg-dk-surface border border-gray-200 dark:border-dk-border rounded-xl shadow-lg dark:shadow-none z-50 overflow-hidden hidden';
        // Insert into the search wrapper
        const wrapper = searchInput.closest('.search-wrapper');
        wrapper.appendChild(dropdown);
    }
    return dropdown;
}

function renderSuggestions(results) {
    const dropdown = getSuggestionDropdown();
    suggestionIndex = -1;

    if (!results || results.length === 0) {
        dropdown.classList.add('hidden');
        return;
    }

    const list = document.createElement('ul');
    list.className = 'suggestion-list max-h-72 overflow-y-auto py-1';

    results.forEach((result, idx) => {
        const li = document.createElement('li');
        li.className =
            'suggestion-item flex items-center justify-between gap-3 px-4 py-3 cursor-pointer hover:bg-primary-light/40 dark:hover:bg-dk-hover transition-colors';
        li.dataset.index = idx;

        const scoreClass = getScoreBadgeClass(result.similarity_score);
        const score = Math.round(result.similarity_score);

        const matchedNote = result.matched_on && result.matched_on !== result.display_name
            ? `<span class="text-xs text-body dark:text-dk-body">matched: ${escapeHtml(result.matched_on)}</span>`
            : '';

        const videoCount = result.id !== null
            ? `<span class="text-xs text-body dark:text-dk-body">${result.appearance_count} video${result.appearance_count !== 1 ? 's' : ''}</span>`
            : `<span class="text-xs italic text-body dark:text-dk-body">roster only</span>`;

        const sourceTag = result.source === 'known' && result.id === null
            ? '<span class="ml-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-primary-light text-primary dark:bg-primary/20 dark:text-primary">WNL</span>'
            : '';

        li.innerHTML = `
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                    <span class="font-heading font-semibold text-heading dark:text-dk-heading text-sm truncate">${escapeHtml(result.display_name)}</span>
                    ${sourceTag}
                </div>
                <div class="flex items-center gap-2 mt-0.5">
                    ${videoCount}
                    ${matchedNote}
                </div>
            </div>
            <span class="shrink-0 px-2.5 py-1 text-xs font-semibold rounded-full ${scoreClass}">
                ${score}%
            </span>
        `;

        li.addEventListener('click', () => selectSuggestion(result));
        list.appendChild(li);
    });

    dropdown.innerHTML = '';
    dropdown.appendChild(list);
    dropdown.classList.remove('hidden');
}

function closeSuggestions() {
    const dropdown = document.getElementById('suggestionDropdown');
    if (dropdown) dropdown.classList.add('hidden');
    suggestionIndex = -1;
}

function highlightSuggestion(newIndex) {
    const items = document.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;

    // Clamp index
    if (newIndex < 0) newIndex = items.length - 1;
    if (newIndex >= items.length) newIndex = 0;

    items.forEach(item => item.classList.remove('bg-primary-light/60', 'dark:bg-dk-hover'));
    items[newIndex].classList.add('bg-primary-light/60', 'dark:bg-dk-hover');
    items[newIndex].scrollIntoView({ block: 'nearest' });
    suggestionIndex = newIndex;
}

function selectSuggestion(result) {
    closeSuggestions();

    if (result.id === null) {
        // Known-only athlete with no DB record
        resultsContainer.innerHTML = '';
        const msg = document.createElement('div');
        msg.className = 'bg-primary-light dark:bg-primary/10 border border-primary/30 text-primary-dark dark:text-primary px-5 py-4 rounded-xl text-center';
        msg.innerHTML = `
            <p class="font-heading font-semibold text-lg uppercase mb-1">${escapeHtml(result.display_name)}</p>
            <p class="text-sm text-body dark:text-dk-body">This athlete is in the WNL roster but has no indexed video appearances yet.</p>
        `;
        resultsContainer.innerHTML = '';
        resultsContainer.appendChild(msg);
        showState('results');
        return;
    }

    loadAthleteCard(result.id);
}

// ── Load Athlete Card ─────────────────────────────────

async function loadAthleteCard(athleteId) {
    setLoading(true);
    try {
        const res = await fetch(`${API_BASE_URL}/api/athletes/${athleteId}`);
        if (!res.ok) throw new Error(`Failed to load athlete: ${res.statusText}`);
        const athlete = await res.json();

        resultsContainer.innerHTML = '';
        const card = createAthleteCard(athlete, 0);
        resultsContainer.appendChild(card);
        showState('results');
    } catch (error) {
        console.error('Load athlete error:', error);
        showError(`Failed to load athlete: ${error.message}. Make sure the API server is running.`);
    } finally {
        setLoading(false);
    }
}

// ── Athlete Card ──────────────────────────────────────

function createAthleteCard(athlete, index) {
    const card = document.createElement('div');
    card.className =
        'bg-white dark:bg-dk-surface rounded-xl shadow-sm dark:shadow-none border border-gray-100 dark:border-dk-border overflow-hidden card-animate border-t-4 border-t-primary transition-colors duration-300';
    card.style.animationDelay = `${index * 80}ms`;
    card.style.opacity = '0';

    // Header
    const header = document.createElement('div');
    header.className = 'px-6 py-4 flex items-center justify-between';
    header.innerHTML = `
        <div>
            <h2 class="font-heading text-xl font-bold uppercase text-heading dark:text-dk-heading tracking-wide">
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
        list.className = 'divide-y divide-gray-100 dark:divide-dk-border';

        for (const appearance of athlete.appearances) {
            const item = document.createElement('li');
            item.className = 'px-6 py-3.5 hover:bg-primary-light/30 dark:hover:bg-dk-hover transition-colors';

            const confidenceClass = getConfidenceBadgeClass(appearance.confidence_score);
            const confidencePercent = Math.round(appearance.confidence_score * 100);

            item.innerHTML = `
                <div class="flex items-center justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-heading dark:text-dk-heading font-medium text-sm truncate">${escapeHtml(appearance.video_title || 'Untitled Video')}</p>
                        <p class="text-xs text-body dark:text-dk-body mt-0.5">
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
        closeSuggestions();
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
            closeSuggestions();
            showState('empty');
            return;
        }

        renderSuggestions(searchResults);
    } catch (error) {
        console.error('Search error:', error);
        closeSuggestions();
        showError(`Failed to search: ${error.message}. Make sure the API server is running.`);
    } finally {
        setLoading(false);
    }
}

// ── Event Listeners ───────────────────────────────────

searchButton.addEventListener('click', () => {
    searchAthletes(searchInput.value);
});

searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounceTimer);
    const query = searchInput.value.trim();
    if (query.length >= 2) {
        searchDebounceTimer = setTimeout(() => searchAthletes(query), 300);
    } else {
        closeSuggestions();
    }
});

searchInput.addEventListener('keydown', (event) => {
    const dropdown = document.getElementById('suggestionDropdown');
    const isOpen = dropdown && !dropdown.classList.contains('hidden');

    if (event.key === 'ArrowDown' && isOpen) {
        event.preventDefault();
        highlightSuggestion(suggestionIndex + 1);
    } else if (event.key === 'ArrowUp' && isOpen) {
        event.preventDefault();
        highlightSuggestion(suggestionIndex - 1);
    } else if (event.key === 'Enter') {
        if (isOpen && suggestionIndex >= 0) {
            event.preventDefault();
            const items = document.querySelectorAll('.suggestion-item');
            items[suggestionIndex]?.click();
        } else {
            searchAthletes(searchInput.value);
        }
    } else if (event.key === 'Escape') {
        closeSuggestions();
    }
});

// Click outside to close suggestions
document.addEventListener('click', (e) => {
    const wrapper = searchInput.closest('.search-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        closeSuggestions();
    }
});

// ── Initialize ────────────────────────────────────────

showState('initial');
loadVideos();
