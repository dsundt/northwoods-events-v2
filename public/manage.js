// GitHub API Integration
// Add this to the beginning of manage.js

// GitHub Configuration
let GITHUB_OWNER = '';
let GITHUB_REPO = '';
let GITHUB_TOKEN = '';
let GITHUB_BRANCH = 'main';

// Auto-detect repo from URL
function detectGitHubRepo() {
    const hostname = window.location.hostname;
    const pathname = window.location.pathname;
    
    if (hostname.endsWith('.github.io')) {
        const parts = hostname.split('.');
        if (parts.length >= 3) {
            GITHUB_OWNER = parts[0];
        }
        
        const pathParts = pathname.split('/').filter(p => p);
        if (pathParts.length > 0) {
            GITHUB_REPO = pathParts[0];
        }
    }
    
    // Load token from localStorage
    GITHUB_TOKEN = localStorage.getItem('github_token') || '';
    
    console.log('Detected:', GITHUB_OWNER, '/', GITHUB_REPO);
}

// Save token to localStorage
function saveGitHubToken(token) {
    GITHUB_TOKEN = token;
    localStorage.setItem('github_token', token);
    showToast('GitHub token saved');
}

// Clear token
function clearGitHubToken() {
    GITHUB_TOKEN = '';
    localStorage.removeItem('github_token');
    showToast('GitHub token cleared');
}

// Commit file to GitHub
async function commitFileToGitHub(path, content, message) {
    if (!GITHUB_TOKEN) {
        throw new Error('GitHub token not configured');
    }
    
    if (!GITHUB_OWNER || !GITHUB_REPO) {
        throw new Error('Could not detect GitHub repository');
    }
    
    const apiBase = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}`;
    
    // Get current file SHA (if it exists)
    let sha = null;
    try {
        const getResponse = await fetch(`${apiBase}/contents/${path}`, {
            headers: {
                'Authorization': `Bearer ${GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });
        
        if (getResponse.ok) {
            const data = await getResponse.json();
            sha = data.sha;
        }
    } catch (error) {
        // File doesn't exist yet, that's okay
        console.log('File does not exist yet, will create new');
    }
    
    // Create or update file
    const body = {
        message: message,
        content: btoa(unescape(encodeURIComponent(content))), // Base64 encode with UTF-8
        branch: GITHUB_BRANCH
    };
    
    if (sha) {
        body.sha = sha;
    }
    
    const response = await fetch(`${apiBase}/contents/${path}`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${GITHUB_TOKEN}`,
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to commit file');
    }
    
    return await response.json();
}

// Trigger GitHub Actions workflow
async function triggerWorkflow() {
    if (!GITHUB_TOKEN) {
        throw new Error('GitHub token not configured');
    }
    
    if (!GITHUB_OWNER || !GITHUB_REPO) {
        throw new Error('Could not detect GitHub repository');
    }
    
    const apiBase = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}`;
    
    const response = await fetch(`${apiBase}/actions/workflows/build-ics-and-deploy.yml/dispatches`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${GITHUB_TOKEN}`,
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            ref: GITHUB_BRANCH
        })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to trigger workflow');
    }
    
    return true;
}

// Save feeds to GitHub
async function saveToGitHub(autoTrigger = false) {
    try {
        const yaml = generateYAML(curatedFeeds);
        
        await commitFileToGitHub(
            'config/curated.yaml',
            yaml,
            'Update curated feeds configuration via web interface'
        );
        
        showToast('Configuration saved to GitHub!', 'success');
        
        if (autoTrigger) {
            showToast('Triggering workflow...', 'info');
            await triggerWorkflow();
            showToast('Workflow triggered! Check Actions tab for progress.', 'success');
        }
        
        return true;
    } catch (error) {
        console.error('Error saving to GitHub:', error);
        showToast('Error: ' + error.message, 'danger');
        return false;
    }
}

// Check if GitHub token is configured
function isGitHubConfigured() {
    return GITHUB_TOKEN && GITHUB_OWNER && GITHUB_REPO;
}
// Northwoods Events - Curated Feeds Manager (GitHub Pages Edition)
// This runs entirely client-side using localStorage

// State
let allEvents = [];
let allSources = [];
let filteredEvents = [];
let selectedEventUIDs = new Set();
let curatedFeeds = [];
let currentEditingFeedId = null;

// Editor state
let editorSelectedUIDs = [];
let editorKeywords = [];
let editorExcludeKeywords = [];
let editorLocations = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    detectGitHubRepo();
    loadData();
    loadFeedsFromStorage();
    showView('feeds');
    updateGitHubStatus();
});

// Load data from report.json
async function loadData() {
    try {
        const response = await fetch('report.json');
        const data = await response.json();
        
        allEvents = data.normalized_events || [];
        allSources = data.source_logs || [];
        
        console.log(`Loaded ${allEvents.length} events from ${allSources.length} sources`);
        
        populateSourceFilter();
        renderFeeds();
        filterEvents();
    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Failed to load event data. Make sure report.json exists.', 'warning');
    }
}

// localStorage management
function loadFeedsFromStorage() {
    const stored = localStorage.getItem('northwoods_curated_feeds');
    if (stored) {
        try {
            curatedFeeds = JSON.parse(stored);
        } catch (e) {
            curatedFeeds = getDefaultFeeds();
        }
    } else {
        curatedFeeds = getDefaultFeeds();
    }
}

function saveFeedsToStorage() {
    localStorage.setItem('northwoods_curated_feeds', JSON.stringify(curatedFeeds));
}

function getDefaultFeeds() {
    return [
        {
            id: 'family-events',
            name: 'Family-Friendly Northwoods Events',
            enabled: true,
            selected_events: [],
            preferences: {
                include_sources: ['boulder-junction-tec', 'eagle-river-chamber-tec', 'vilas-county-tourism-tec'],
                exclude_sources: [],
                locations: ['Boulder Junction', 'Eagle River'],
                keywords: ['family', 'kids', 'children', 'festival', 'parade'],
                exclude_keywords: ['21+', 'adults only', 'bar crawl'],
                max_auto_events: 50,
                days_ahead: 90
            }
        }
    ];
}

// View management
function showView(view, param) {
    // Update nav
    document.querySelectorAll('nav button').forEach(btn => btn.classList.remove('active'));
    
    // Hide all views
    document.getElementById('view-feeds').style.display = 'none';
    document.getElementById('view-browse').style.display = 'none';
    document.getElementById('view-editor').style.display = 'none';
    
    // Show selected view
    if (view === 'feeds') {
        document.getElementById('nav-feeds').classList.add('active');
        document.getElementById('view-feeds').style.display = 'block';
        renderFeeds();
    } else if (view === 'browse') {
        document.getElementById('nav-browse').classList.add('active');
        document.getElementById('view-browse').style.display = 'block';
        filterEvents();
    } else if (view === 'editor') {
        document.getElementById('nav-create').classList.add('active');
        document.getElementById('view-editor').style.display = 'block';
        if (param === 'new') {
            initEditorNew();
        } else {
            initEditorEdit(param);
        }
    }
}

// Feeds view
function renderFeeds() {
    const container = document.getElementById('feeds-list');
    
    if (curatedFeeds.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Curated Feeds Yet</h3>
                <p>Create your first curated feed to get started!</p>
                <button onclick="showView('editor', 'new')" class="btn btn-primary">Create Your First Feed</button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '<div class="grid grid-2">' + curatedFeeds.map(feed => {
        const matchedEvents = simulateFeedGeneration(feed);
        const manualCount = feed.selected_events ? feed.selected_events.length : 0;
        const autoCount = matchedEvents.length - manualCount;
        
        return `
            <div class="feed-card" style="cursor: default;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                    <div>
                        <h3 class="feed-title">${escapeHtml(feed.name)}</h3>
                        <span class="badge ${feed.enabled ? 'badge-success' : 'badge-secondary'}">
                            ${feed.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                    </div>
                    <div class="feed-actions">
                        <button onclick="editFeed('${feed.id}')" class="btn btn-sm btn-secondary">
                            ✏️ Edit
                        </button>
                        <button onclick="toggleFeed('${feed.id}')" class="btn btn-sm ${feed.enabled ? 'btn-secondary' : 'btn-success'}">
                            ${feed.enabled ? '⏸️' : '▶️'}
                        </button>
                        <button onclick="deleteFeed('${feed.id}')" class="btn btn-sm btn-danger">
                            🗑️
                        </button>
                    </div>
                </div>
                <div style="margin: 0.5rem 0; color: var(--text-muted); font-size: 0.9rem;">
                    <strong>ID:</strong> ${feed.id}
                </div>
                <div class="feed-stats">
                    <div class="stat">
                        <div class="stat-value">${matchedEvents.length}</div>
                        <div class="stat-label">Total Events</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${manualCount}</div>
                        <div class="stat-label">Manual</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${autoCount}</div>
                        <div class="stat-label">Auto</div>
                    </div>
                </div>
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
                    <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.9rem;">📥 ICS Feed URL:</div>
                    <div id="ics-section-${feed.id}">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <input type="text" readonly value="${getICSUrl(feed.id)}" 
                                   style="flex: 1; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 4px; font-size: 0.85rem; font-family: monospace;">
                            <button onclick="copyToClipboard('${getICSUrl(feed.id)}', '${feed.id}')" class="btn btn-sm btn-secondary" title="Copy URL">
                                📋 Copy
                            </button>
                            <button onclick="window.open('${getICSUrl(feed.id)}', '_blank')" class="btn btn-sm btn-secondary" title="Test URL">
                                🔗 Test
                            </button>
                        </div>
                        <div style="margin-top: 0.5rem;">
                            <button onclick="generateAndSaveFeed('${feed.id}')" class="btn btn-sm btn-primary">
                                ⚡ Regenerate Feed
                            </button>
                            <button onclick="previewFeed('${feed.id}')" class="btn btn-sm btn-secondary" style="margin-left: 0.5rem;">
                                👁️ Preview Events
                            </button>
                            <small style="color: var(--text-muted); margin-left: 0.5rem;">
                                Commits config & triggers workflow
                            </small>
                        </div>
                    </div>
                </div>
                <div id="preview-${feed.id}" style="display: none; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
                    <!-- Preview content will be inserted here -->
                </div>
            </div>
        `;
    }).join('') + '</div>';
}

function normalizeTitleForDuplicateCheck(title, startUtc) {
    // Normalize title: lowercase, remove special chars, collapse whitespace
    const normalizedTitle = title
        .toLowerCase()
        .replace(/[^\w\s]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
    
    // Normalize date to just the date part (ignore time)
    let dateKey = '';
    try {
        const dt = new Date(startUtc);
        dateKey = dt.toISOString().split('T')[0]; // YYYY-MM-DD
    } catch (e) {
        dateKey = String(startUtc).substring(0, 10);
    }
    
    return `${normalizedTitle}|${dateKey}`;
}

function removeDuplicateEvents(events) {
    const seenKeys = new Set();
    const unique = [];
    
    for (const event of events) {
        const title = event.title || '';
        const startUtc = event.start_utc;
        
        if (!title || !startUtc) {
            unique.push(event);
            continue;
        }
        
        const key = normalizeTitleForDuplicateCheck(title, startUtc);
        
        if (!seenKeys.has(key)) {
            seenKeys.add(key);
            unique.push(event);
        }
    }
    
    return unique;
}

function simulateFeedGeneration(feed) {
    const now = new Date();
    let matched = [];
    
    // Add manually selected events (future only)
    if (feed.selected_events) {
        matched = allEvents.filter(e => 
            feed.selected_events.includes(e.uid) && 
            new Date(e.start_utc) >= now
        );
    }
    
    const matchedUIDs = new Set(matched.map(e => e.uid));
    
    // Add auto-selected events
    const prefs = feed.preferences || {};
    const daysAhead = prefs.days_ahead || 180;
    const maxDate = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);
    
    const autoEvents = allEvents.filter(event => {
        if (matchedUIDs.has(event.uid)) return false;
        
        const eventDate = new Date(event.start_utc);
        if (eventDate < now || eventDate > maxDate) return false;
        
        // Source filters
        if (prefs.include_sources && prefs.include_sources.length > 0) {
            const matchesSource = prefs.include_sources.some(src => 
                (event.source || '').toLowerCase().includes(src.toLowerCase())
            );
            if (!matchesSource) return false;
        }
        
        if (prefs.exclude_sources && prefs.exclude_sources.length > 0) {
            const matchesExclude = prefs.exclude_sources.some(src => 
                (event.source || '').toLowerCase().includes(src.toLowerCase())
            );
            if (matchesExclude) return false;
        }
        
        // Location filters
        if (prefs.locations && prefs.locations.length > 0) {
            const matchesLocation = prefs.locations.some(loc => 
                (event.location || '').toLowerCase().includes(loc.toLowerCase())
            );
            if (!matchesLocation) return false;
        }
        
        // Exclude keywords (takes precedence)
        if (prefs.exclude_keywords && prefs.exclude_keywords.length > 0) {
            const text = `${event.title} ${event.location}`.toLowerCase();
            const matchesExclude = prefs.exclude_keywords.some(kw => 
                text.includes(kw.toLowerCase())
            );
            if (matchesExclude) return false;
        }
        
        // Include keywords
        if (prefs.keywords && prefs.keywords.length > 0) {
            const text = `${event.title} ${event.location}`.toLowerCase();
            const matchesKeyword = prefs.keywords.some(kw => 
                text.includes(kw.toLowerCase())
            );
            if (!matchesKeyword) return false;
        }
        
        return true;
    });
    
    const maxAuto = prefs.max_auto_events || 0;
    const limitedAuto = maxAuto > 0 ? autoEvents.slice(0, maxAuto) : autoEvents;
    
    // Combine and remove duplicates
    const combined = [...matched, ...limitedAuto];
    const unique = removeDuplicateEvents(combined);
    
    // Sort by start date (chronological order)
    unique.sort((a, b) => new Date(a.start_utc) - new Date(b.start_utc));
    
    return unique;
}

function editFeed(feedId) {
    showView('editor', feedId);
}

function toggleFeed(feedId) {
    const feed = curatedFeeds.find(f => f.id === feedId);
    if (feed) {
        feed.enabled = !feed.enabled;
        saveFeedsToStorage();
        renderFeeds();
        showToast(`Feed ${feed.enabled ? 'enabled' : 'disabled'}`);
    }
}

function deleteFeed(feedId) {
    if (!confirm('Are you sure you want to delete this feed?')) return;
    
    curatedFeeds = curatedFeeds.filter(f => f.id !== feedId);
    saveFeedsToStorage();
    renderFeeds();
    showToast('Feed deleted');
}

// Browse events view
function populateSourceFilter() {
    const select = document.getElementById('source-filter');
    const uniqueSources = [...new Set(allEvents.map(e => e.source).filter(Boolean))];
    
    select.innerHTML = '<option value="">All Sources</option>' +
        uniqueSources.map(source => `<option value="${escapeHtml(source)}">${escapeHtml(source)}</option>`).join('');
}

function filterEvents() {
    const keyword = (document.getElementById('keyword-filter')?.value || '').toLowerCase();
    const source = (document.getElementById('source-filter')?.value || '').toLowerCase();
    const location = (document.getElementById('location-filter')?.value || '').toLowerCase();
    
    filteredEvents = allEvents.filter(event => {
        const matchesKeyword = !keyword || 
            (event.title || '').toLowerCase().includes(keyword) ||
            (event.location || '').toLowerCase().includes(keyword);
        
        const matchesSource = !source || 
            (event.source || '').toLowerCase().includes(source);
        
        const matchesLocation = !location ||
            (event.location || '').toLowerCase().includes(location);
        
        return matchesKeyword && matchesSource && matchesLocation;
    });
    
    renderEvents();
}

function renderEvents() {
    const container = document.getElementById('events-grid');
    const countEl = document.getElementById('event-count');
    
    if (!container || !countEl) return;
    
    countEl.textContent = `Showing ${filteredEvents.length} of ${allEvents.length} events`;
    
    if (filteredEvents.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No events found</p></div>';
        return;
    }
    
    container.innerHTML = filteredEvents.map(event => {
        const isSelected = selectedEventUIDs.has(event.uid);
        return `
            <div class="event-card ${isSelected ? 'selected' : ''}" 
                 onclick="toggleEventSelection('${event.uid}')">
                <h4 class="event-title">${escapeHtml(event.title || 'Untitled')}</h4>
                <div class="event-meta">
                    <div>📅 ${formatDate(event.start_utc)}</div>
                    ${event.location ? `<div>📍 ${escapeHtml(event.location)}</div>` : ''}
                    <div>🏢 ${escapeHtml(event.source || 'Unknown')}</div>
                    ${event.uid ? `<div style="font-size: 0.75rem;">UID: ${event.uid}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    updateSelectionPanel();
}

function toggleEventSelection(uid) {
    if (selectedEventUIDs.has(uid)) {
        selectedEventUIDs.delete(uid);
    } else {
        selectedEventUIDs.add(uid);
    }
    renderEvents();
}

function updateSelectionPanel() {
    const panel = document.getElementById('selection-panel');
    const countEl = document.getElementById('selected-count');
    
    if (!panel || !countEl) return;
    
    if (selectedEventUIDs.size === 0) {
        panel.style.display = 'none';
        countEl.textContent = '';
    } else {
        panel.style.display = 'block';
        countEl.textContent = `${selectedEventUIDs.size} selected`;
    }
}

function clearSelection() {
    selectedEventUIDs.clear();
    renderEvents();
}

function showAddToFeedDialog() {
    const feedId = prompt('Enter feed ID to add events to (or leave empty to cancel):');
    if (!feedId) return;
    
    const feed = curatedFeeds.find(f => f.id === feedId);
    if (!feed) {
        showToast('Feed not found', 'warning');
        return;
    }
    
    const existingUIDs = feed.selected_events || [];
    const newUIDs = [...new Set([...existingUIDs, ...Array.from(selectedEventUIDs)])];
    feed.selected_events = newUIDs;
    
    saveFeedsToStorage();
    showToast(`Added ${selectedEventUIDs.size} events to ${feed.name}`);
    clearSelection();
}

// Editor view
function initEditorNew() {
    currentEditingFeedId = null;
    document.getElementById('editor-title').textContent = 'Create New Feed';
    document.getElementById('feed-id').readOnly = false;
    
    // Reset form
    document.getElementById('feed-id').value = '';
    document.getElementById('feed-name').value = '';
    document.getElementById('feed-enabled').checked = true;
    
    editorSelectedUIDs = [];
    editorKeywords = [];
    editorExcludeKeywords = [];
    editorLocations = [];
    
    document.getElementById('max-auto-events').value = '0';
    document.getElementById('days-ahead').value = '180';
    
    renderEditorLists();
}

function initEditorEdit(feedId) {
    currentEditingFeedId = feedId;
    const feed = curatedFeeds.find(f => f.id === feedId);
    
    if (!feed) {
        showToast('Feed not found', 'warning');
        showView('feeds');
    updateGitHubStatus();
        return;
    }
    
    document.getElementById('editor-title').textContent = `Edit Feed: ${feed.name}`;
    document.getElementById('feed-id').value = feed.id;
    document.getElementById('feed-id').readOnly = true;
    document.getElementById('feed-name').value = feed.name;
    document.getElementById('feed-enabled').checked = feed.enabled !== false;
    
    editorSelectedUIDs = feed.selected_events || [];
    
    const prefs = feed.preferences || {};
    editorKeywords = prefs.keywords || [];
    editorExcludeKeywords = prefs.exclude_keywords || [];
    editorLocations = prefs.locations || [];
    
    document.getElementById('max-auto-events').value = prefs.max_auto_events || 0;
    document.getElementById('days-ahead').value = prefs.days_ahead || 180;
    
    renderEditorLists();
}

function renderEditorLists() {
    // Render selected UIDs
    const uidsContainer = document.getElementById('selected-uids-display');
    if (editorSelectedUIDs.length === 0) {
        uidsContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">No events selected</div>';
    } else {
        uidsContainer.innerHTML = '<div class="tags">' + editorSelectedUIDs.map(uid => 
            `<span class="tag">${escapeHtml(uid)} <span class="tag-remove" onclick="removeEditorUID('${uid}')">×</span></span>`
        ).join('') + '</div>';
    }
    
    // Render keywords
    const keywordsContainer = document.getElementById('keywords-display');
    if (editorKeywords.length === 0) {
        keywordsContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">No keywords</div>';
    } else {
        keywordsContainer.innerHTML = '<div class="tags">' + editorKeywords.map(kw => 
            `<span class="tag">${escapeHtml(kw)} <span class="tag-remove" onclick="removeEditorKeyword('${kw}')">×</span></span>`
        ).join('') + '</div>';
    }
    
    // Render exclude keywords
    const excludeContainer = document.getElementById('exclude-keywords-display');
    if (editorExcludeKeywords.length === 0) {
        excludeContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">No excluded keywords</div>';
    } else {
        excludeContainer.innerHTML = '<div class="tags">' + editorExcludeKeywords.map(kw => 
            `<span class="tag">${escapeHtml(kw)} <span class="tag-remove" onclick="removeEditorExcludeKeyword('${kw}')">×</span></span>`
        ).join('') + '</div>';
    }
    
    // Render locations
    const locationsContainer = document.getElementById('locations-display');
    if (editorLocations.length === 0) {
        locationsContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">All locations</div>';
    } else {
        locationsContainer.innerHTML = '<div class="tags">' + editorLocations.map(loc => 
            `<span class="tag">${escapeHtml(loc)} <span class="tag-remove" onclick="removeEditorLocation('${loc}')">×</span></span>`
        ).join('') + '</div>';
    }
}

function addUID() {
    const input = document.getElementById('uid-input');
    const uid = input.value.trim();
    if (uid && !editorSelectedUIDs.includes(uid)) {
        editorSelectedUIDs.push(uid);
        renderEditorLists();
        input.value = '';
    }
}

function removeEditorUID(uid) {
    editorSelectedUIDs = editorSelectedUIDs.filter(u => u !== uid);
    renderEditorLists();
}

function addKeyword() {
    const input = document.getElementById('keyword-input');
    const keyword = input.value.trim();
    if (keyword && !editorKeywords.includes(keyword)) {
        editorKeywords.push(keyword);
        renderEditorLists();
        input.value = '';
    }
}

function removeEditorKeyword(keyword) {
    editorKeywords = editorKeywords.filter(k => k !== keyword);
    renderEditorLists();
}

function addExcludeKeyword() {
    const input = document.getElementById('exclude-keyword-input');
    const keyword = input.value.trim();
    if (keyword && !editorExcludeKeywords.includes(keyword)) {
        editorExcludeKeywords.push(keyword);
        renderEditorLists();
        input.value = '';
    }
}

function removeEditorExcludeKeyword(keyword) {
    editorExcludeKeywords = editorExcludeKeywords.filter(k => k !== keyword);
    renderEditorLists();
}

function addLocation() {
    const input = document.getElementById('location-input');
    const location = input.value.trim();
    if (location && !editorLocations.includes(location)) {
        editorLocations.push(location);
        renderEditorLists();
        input.value = '';
    }
}

function removeEditorLocation(location) {
    editorLocations = editorLocations.filter(l => l !== location);
    renderEditorLists();
}

function saveFeed(event) {
    event.preventDefault();
    
    const feedId = document.getElementById('feed-id').value.trim();
    const feedName = document.getElementById('feed-name').value.trim();
    const enabled = document.getElementById('feed-enabled').checked;
    
    const feed = {
        id: feedId,
        name: feedName,
        enabled: enabled,
        selected_events: editorSelectedUIDs,
        preferences: {
            include_sources: [],
            exclude_sources: [],
            locations: editorLocations,
            keywords: editorKeywords,
            exclude_keywords: editorExcludeKeywords,
            max_auto_events: parseInt(document.getElementById('max-auto-events').value) || 0,
            days_ahead: parseInt(document.getElementById('days-ahead').value) || 180
        }
    };
    
    if (currentEditingFeedId === null) {
        // New feed
        if (curatedFeeds.some(f => f.id === feedId)) {
            showToast('Feed ID already exists', 'warning');
            return;
        }
        curatedFeeds.push(feed);
        showToast('Feed created successfully');
    } else {
        // Edit existing
        const index = curatedFeeds.findIndex(f => f.id === currentEditingFeedId);
        if (index >= 0) {
            curatedFeeds[index] = feed;
            showToast('Feed updated successfully');
        }
    }
    
    saveFeedsToStorage();
    showView('feeds');
    updateGitHubStatus();
}

// Export configuration
function exportConfig() {
    const yaml = generateYAML(curatedFeeds);
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'curated.yaml';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Configuration downloaded. Commit this to your repository and trigger the GitHub Actions workflow.');
}

function generateYAML(feeds) {
    let yaml = '# User-Curated Feeds Configuration\n';
    yaml += '# Generated by Northwoods Events Manager\n\n';
    
    feeds.forEach(feed => {
        yaml += `- id: ${feed.id}\n`;
        yaml += `  name: "${feed.name}"\n`;
        yaml += `  enabled: ${feed.enabled}\n`;
        yaml += `  \n`;
        yaml += `  selected_events:\n`;
        if (feed.selected_events && feed.selected_events.length > 0) {
            feed.selected_events.forEach(uid => {
                yaml += `    - "${uid}"\n`;
            });
        } else {
            yaml += `    []\n`;
        }
        yaml += `  \n`;
        yaml += `  preferences:\n`;
        
        const p = feed.preferences || {};
        
        yaml += `    include_sources:\n`;
        if (p.include_sources && p.include_sources.length > 0) {
            p.include_sources.forEach(src => yaml += `      - ${src}\n`);
        } else {
            yaml += `      []\n`;
        }
        
        yaml += `    \n`;
        yaml += `    exclude_sources:\n`;
        if (p.exclude_sources && p.exclude_sources.length > 0) {
            p.exclude_sources.forEach(src => yaml += `      - ${src}\n`);
        } else {
            yaml += `      []\n`;
        }
        
        yaml += `    \n`;
        yaml += `    locations:\n`;
        if (p.locations && p.locations.length > 0) {
            p.locations.forEach(loc => yaml += `      - "${loc}"\n`);
        } else {
            yaml += `      []\n`;
        }
        
        yaml += `    \n`;
        yaml += `    keywords:\n`;
        if (p.keywords && p.keywords.length > 0) {
            p.keywords.forEach(kw => yaml += `      - "${kw}"\n`);
        } else {
            yaml += `      []\n`;
        }
        
        yaml += `    \n`;
        yaml += `    exclude_keywords:\n`;
        if (p.exclude_keywords && p.exclude_keywords.length > 0) {
            p.exclude_keywords.forEach(kw => yaml += `      - "${kw}"\n`);
        } else {
            yaml += `      []\n`;
        }
        
        yaml += `    \n`;
        yaml += `    max_auto_events: ${p.max_auto_events || 0}\n`;
        yaml += `    days_ahead: ${p.days_ahead || 180}\n`;
        yaml += `\n`;
    });
    
    return yaml;
}

// Utilities
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return dateStr;
    }
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '1000';
    toast.style.minWidth = '300px';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Update GitHub status indicator
function updateGitHubStatus() {
    const statusEl = document.getElementById('github-status');
    if (!statusEl) return;
    
    if (isGitHubConfigured()) {
        statusEl.innerHTML = `
            <span style="color: var(--success-color);">✓ GitHub Connected</span>
            <span style="color: var(--text-muted); margin-left: 1rem;">${GITHUB_OWNER}/${GITHUB_REPO}</span>
        `;
    } else {
        statusEl.innerHTML = `
            <span style="color: var(--danger-color);">⚠ GitHub Token Required</span>
        `;
    }
}

// Check if ICS file exists for a feed
async function checkICSFileExists(feedId) {
    try {
        const baseUrl = window.location.origin + window.location.pathname.replace('/manage.html', '');
        const icsUrl = `${baseUrl}/curated/${feedId}.ics`;
        const response = await fetch(icsUrl, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Slugify function matching Python backend
function slugify(text) {
    if (!text) return 'item';
    return text
        .toString()
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9\s-]/g, '')  // Keep only letters, numbers, spaces, hyphens
        .replace(/[\s_]+/g, '-')        // Replace spaces and underscores with hyphens
        .replace(/-+/g, '-')            // Replace multiple hyphens with single hyphen
        .replace(/^-+|-+$/g, '');       // Remove leading/trailing hyphens
}

// Generate ICS URL for a feed
function getICSUrl(feedId) {
    const baseUrl = window.location.origin + window.location.pathname.replace('/manage.html', '');
    const slug = slugify(feedId);
    return `${baseUrl}/curated/${slug}.ics`;
}

// Copy URL to clipboard
function copyToClipboard(text, feedId) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('URL copied to clipboard!');
    }).catch(err => {
        showToast('Failed to copy URL', 'danger');
    });
}

// Generate a specific feed and save to GitHub
async function generateAndSaveFeed(feedId) {
    if (!isGitHubConfigured()) {
        showToast('Please configure GitHub token first', 'warning');
        showGitHubTokenDialog();
        return;
    }
    
    try {
        // Save current config to GitHub
        await saveToGitHub(true); // true = trigger workflow
        
        showToast(`Feed generation started! Check back in 2-3 minutes.`, 'info');
        
        // Wait a bit then refresh the page
        setTimeout(() => {
            showToast('Refreshing feed status...', 'info');
            renderFeeds();
        }, 5000);
        
    } catch (error) {
        showToast('Failed to generate feed: ' + error.message, 'danger');
    }
}

// Preview feed events
function previewFeed(feedId) {
    const previewDiv = document.getElementById(`preview-${feedId}`);
    
    if (previewDiv.style.display === 'block') {
        // Hide if already showing
        previewDiv.style.display = 'none';
        return;
    }
    
    // Get the feed
    const feed = curatedFeeds.find(f => f.id === feedId);
    if (!feed) {
        showToast('Feed not found', 'danger');
        return;
    }
    
    // Get events that would be in this feed
    const matchedEvents = simulateFeedGeneration(feed);
    
    if (matchedEvents.length === 0) {
        previewDiv.innerHTML = `
            <div style="padding: 1rem; text-align: center; color: var(--text-muted);">
                <p>No events match this feed's criteria.</p>
            </div>
        `;
        previewDiv.style.display = 'block';
        return;
    }
    
    // Generate preview HTML
    const eventsHTML = matchedEvents.map((event, index) => {
        const startDate = new Date(event.start_utc);
        const dateStr = startDate.toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        });
        const timeStr = startDate.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit'
        });
        
        const location = event.location || 'Location TBA';
        const description = event.description || '';
        const url = event.url || '';
        const source = event.calendar_slug || event.source || 'Unknown';
        
        // Truncate description
        const maxDescLength = 200;
        let displayDesc = description;
        if (description.length > maxDescLength) {
            displayDesc = description.substring(0, maxDescLength) + '...';
        }
        
        return `
            <div style="padding: 1rem; border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 0.75rem; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <div style="flex: 1;">
                        <h4 style="margin: 0 0 0.25rem 0; color: var(--primary-color);">
                            ${url ? `<a href="${escapeHtml(url)}" target="_blank" style="color: var(--primary-color); text-decoration: none;">${escapeHtml(event.title)}</a>` : escapeHtml(event.title)}
                        </h4>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            <span style="margin-right: 1rem;">📅 ${dateStr} at ${timeStr}</span>
                            <span style="margin-right: 1rem;">📍 ${escapeHtml(location)}</span>
                            <span class="badge badge-secondary" style="font-size: 0.75rem;">${escapeHtml(source)}</span>
                        </div>
                    </div>
                </div>
                ${displayDesc ? `
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: var(--text-color); line-height: 1.4;">
                        ${escapeHtml(displayDesc)}
                    </p>
                ` : ''}
                <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    ${url ? `
                        <a href="${escapeHtml(url)}" target="_blank" class="btn btn-sm btn-primary" style="text-decoration: none; display: inline-block;">
                            🔗 View Details
                        </a>
                    ` : ''}
                    <button onclick='generateInstagramImage(${JSON.stringify(event).replace(/'/g, "\\'")})'  class="btn btn-sm btn-success">
                        🎨 Generate Image
                    </button>
                    <button onclick='generateInstagramReel(${JSON.stringify(event).replace(/'/g, "\\'")})'  class="btn btn-sm" style="background: #E1306C; color: white;">
                        🎥 Generate Reel
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    previewDiv.innerHTML = `
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; font-size: 1.1rem;">
                    📋 Preview: ${matchedEvents.length} Event${matchedEvents.length !== 1 ? 's' : ''}
                </h3>
                <button onclick="previewFeed('${feedId}')" class="btn btn-sm btn-secondary">
                    ✖ Close Preview
                </button>
            </div>
            <div style="max-height: 600px; overflow-y: auto;">
                ${eventsHTML}
            </div>
        </div>
    `;
    
    previewDiv.style.display = 'block';
    
    // Scroll to preview
    setTimeout(() => {
        previewDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

// ==================== INSTAGRAM IMAGE GENERATION ====================

// OpenAI API configuration
let OPENAI_API_KEY = localStorage.getItem('openai_api_key') || '';

function configureOpenAIKey() {
    const currentKey = OPENAI_API_KEY ? '••••••' + OPENAI_API_KEY.slice(-4) : 'Not configured';
    
    const dialog = document.createElement('div');
    dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
    
    dialog.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 500px; width: 90%;">
            <h2 style="margin-top: 0;">Configure OpenAI API Key</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Required for AI image generation. Get your key from: 
                <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI Platform</a>
            </p>
            <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">
                Current key: <code>${currentKey}</code>
            </p>
            <input type="password" id="openai-key-input" placeholder="sk-..." 
                   style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 1rem; font-family: monospace;">
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button onclick="this.closest('[style*=fixed]').remove()" class="btn btn-secondary">Cancel</button>
                <button onclick="saveOpenAIKey()" class="btn btn-primary">Save Key</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    document.getElementById('openai-key-input').focus();
}

function saveOpenAIKey() {
    const input = document.getElementById('openai-key-input');
    const key = input.value.trim();
    
    if (!key) {
        showToast('Please enter an API key', 'danger');
        return;
    }
    
    if (!key.startsWith('sk-')) {
        showToast('Invalid API key format. Should start with "sk-"', 'warning');
        return;
    }
    
    OPENAI_API_KEY = key;
    localStorage.setItem('openai_api_key', key);
    
    document.querySelector('[style*="fixed"]').remove();
    showToast('OpenAI API key saved!', 'success');
}

async function generateInstagramImage(event) {
    if (!OPENAI_API_KEY) {
        showToast('Please configure OpenAI API key first', 'warning');
        configureOpenAIKey();
        return;
    }
    
    // Show generation dialog
    showImageGenerationDialog(event);
}

function showImageGenerationDialog(event) {
    const eventDate = new Date(event.start_utc);
    const dateStr = eventDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        month: 'long', 
        day: 'numeric',
        year: 'numeric'
    });
    
    const defaultPrompt = `Create a beautiful, vibrant Instagram post image for "${event.title}". 

SETTING: Northern Wisconsin / Northwoods region
- Dense pine and deciduous forests
- Crystal-clear lakes with gentle shorelines
- Rolling hills (NO mountains - this is Wisconsin!)
- Rustic log cabins and lakeside lodges
- Charming small-town Main Streets
- Natural Wisconsin landscapes

STYLE: Professional tourism photography, warm and inviting, captures the natural beauty and recreational spirit of the Northwoods.

ELEMENTS TO INCLUDE:
- Towering pine trees and mixed forests
- Pristine blue lakes or rivers
- Rustic wooden structures (cabins, docks, lodges)
- Outdoor recreation vibes (canoeing, hiking, fishing)
- Seasonal appropriate (consider the event date)
- Wisconsin charm and natural beauty

IMPORTANT: 
- NO mountains or mountain ranges
- NO desert landscapes
- Focus on forests, lakes, and gentle Wisconsin terrain
- Do not include any text in the image (text will be added separately)

Create an image that makes people want to visit Northern Wisconsin!`;
    
    const dialog = document.createElement('div');
    dialog.id = 'instagram-dialog';
    dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000; overflow-y: auto;';
    
    dialog.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 700px; width: 90%; max-height: 90vh; overflow-y: auto; margin: 2rem;">
            <h2 style="margin-top: 0;">🎨 Generate Instagram Image</h2>
            
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1rem;">${escapeHtml(event.title)}</h3>
                <div style="font-size: 0.9rem; color: var(--text-muted);">
                    📅 ${dateStr}
                    ${event.location ? `<br>📍 ${escapeHtml(event.location)}` : ''}
                </div>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; font-weight: 600; margin-bottom: 0.5rem;">AI Image Prompt:</label>
                <textarea id="image-prompt" rows="6" 
                          style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 4px; font-family: inherit; resize: vertical;">${defaultPrompt}</textarea>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem;">
                    💡 Tip: Be specific about style, colors, and mood. Avoid requesting text in the image.
                </div>
            </div>
            
            <div id="generation-status" style="margin-bottom: 1rem;"></div>
            <div id="image-preview" style="margin-bottom: 1rem;"></div>
            
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; flex-wrap: wrap;">
                <button onclick="document.getElementById('instagram-dialog').remove()" class="btn btn-secondary">Close</button>
                <button onclick="configureOpenAIKey()" class="btn btn-secondary">⚙️ API Key</button>
                <button onclick="startImageGeneration(${JSON.stringify(event).replace(/"/g, '&quot;')})" class="btn btn-primary" id="generate-btn">
                    ✨ Generate Image ($0.04)
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
}

async function startImageGeneration(event) {
    const promptInput = document.getElementById('image-prompt');
    const statusDiv = document.getElementById('generation-status');
    const generateBtn = document.getElementById('generate-btn');
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showToast('Please enter a prompt', 'warning');
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating...';
    
    statusDiv.innerHTML = `
        <div style="background: #e7f3ff; border: 1px solid #b3d9ff; padding: 1rem; border-radius: 4px;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 20px; height: 20px; border: 3px solid #0066cc; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <span>Generating image with DALL-E 3... This may take 10-30 seconds.</span>
            </div>
        </div>
        <style>
            @keyframes spin { to { transform: rotate(360deg); } }
        </style>
    `;
    
    try {
        // Call OpenAI DALL-E API - request base64 to avoid CORS issues
        const response = await fetch('https://api.openai.com/v1/images/generations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${OPENAI_API_KEY}`
            },
            body: JSON.stringify({
                model: 'dall-e-3',
                prompt: prompt,
                n: 1,
                size: '1024x1024',
                quality: 'standard',
                response_format: 'b64_json'  // Request base64 instead of URL to avoid CORS
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Failed to generate image');
        }
        
        const data = await response.json();
        const imageBase64 = data.data[0].b64_json;
        
        // Convert base64 to data URL
        const imageDataUrl = `data:image/png;base64,${imageBase64}`;
        
        // Download and process the image
        await processGeneratedImage(imageDataUrl, event);
        
    } catch (error) {
        console.error('Image generation error:', error);
        statusDiv.innerHTML = `
            <div style="background: #ffe7e7; border: 1px solid #ffb3b3; padding: 1rem; border-radius: 4px; color: #cc0000;">
                <strong>Error:</strong> ${escapeHtml(error.message)}
            </div>
        `;
        generateBtn.disabled = false;
        generateBtn.textContent = '✨ Generate Image ($0.04)';
    }
}

async function processGeneratedImage(imageUrl, event) {
    const statusDiv = document.getElementById('generation-status');
    const previewDiv = document.getElementById('image-preview');
    const generateBtn = document.getElementById('generate-btn');
    
    statusDiv.innerHTML = `
        <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1rem; border-radius: 4px;">
            ⚙️ Processing image (adding text overlay and logo)...
        </div>
    `;
    
    try {
        console.log('Starting image processing...');
        console.log('Image data received (base64 length):', imageUrl.length);
        
        // Create canvas for Instagram size (1080x1080)
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 1080;
        canvas.height = 1080;
        
        console.log('Loading AI-generated image...');
        statusDiv.innerHTML = `
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1rem; border-radius: 4px;">
                ⚙️ Step 1/3: Loading AI image...
            </div>
        `;
        
        // Load the base64 image directly (no CORS issues!)
        const aiImage = await loadImageFromBlob(imageUrl);
        
        statusDiv.innerHTML = `
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1rem; border-radius: 4px;">
                ⚙️ Step 2/3: Adding branding...
            </div>
        `;
        
        ctx.drawImage(aiImage, 0, 0, 1080, 1080);
        console.log('AI image drawn to canvas');
        
        // Add semi-transparent overlay at bottom for text readability
        const gradient = ctx.createLinearGradient(0, 880, 0, 1080);
        gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0.7)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 880, 1080, 200);
        
        // Add event title
        ctx.fillStyle = 'white';
        ctx.font = 'bold 48px Arial, sans-serif';
        ctx.textAlign = 'left';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 10;
        
        // Wrap text if needed
        const titleLines = wrapText(ctx, event.title, 1020, 48);
        let titleY = 950;
        if (titleLines.length > 1) titleY = 920;
        
        titleLines.forEach((line, i) => {
            ctx.fillText(line, 30, titleY + (i * 52));
        });
        
        // Add date and location
        ctx.font = '32px Arial, sans-serif';
        ctx.shadowBlur = 8;
        const eventDate = new Date(event.start_utc);
        const dateStr = eventDate.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        });
        const locationStr = event.location || '';
        const detailsText = locationStr ? `${dateStr} • ${locationStr}` : dateStr;
        ctx.fillText(detailsText, 30, 1040);
        
        // Add Red Canoe logo with 30% opacity
        console.log('Adding logo overlay...');
        statusDiv.innerHTML = `
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1rem; border-radius: 4px;">
                ⚙️ Step 3/3: Adding logo and finalizing...
            </div>
        `;
        
        try {
            const logoPath = window.location.pathname.includes('/manage.html') 
                ? window.location.pathname.replace('/manage.html', '/assets/red-canoe-logo.png')
                : '/northwoods-events-v2/assets/red-canoe-logo.png';
            console.log('Loading logo from:', logoPath);
            const logo = await loadImageFromBlob(logoPath);
            ctx.globalAlpha = 0.3;
            const logoSize = 120;
            ctx.drawImage(logo, 1080 - logoSize - 20, 1080 - logoSize - 20, logoSize, logoSize);
            ctx.globalAlpha = 1.0;
            console.log('Logo added successfully');
        } catch (err) {
            console.warn('Logo not found, skipping overlay:', err);
        }
        
        // Convert to blob
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.95));
        const finalImageUrl = URL.createObjectURL(blob);
        
        // Show preview
        statusDiv.innerHTML = `
            <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 1rem; border-radius: 4px; color: #155724;">
                ✅ Image generated successfully!
            </div>
        `;
        
        previewDiv.innerHTML = `
            <div style="border: 1px solid var(--border-color); border-radius: 4px; padding: 1rem;">
                <h3 style="margin-top: 0; font-size: 1rem;">Preview:</h3>
                <img src="${finalImageUrl}" style="width: 100%; max-width: 400px; border-radius: 4px; display: block; margin: 0 auto;">
                <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap;">
                    <a href="${finalImageUrl}" download="instagram-${slugify(event.title)}.jpg" class="btn btn-primary">
                        💾 Download Image
                    </a>
                    <button onclick="saveImageToGitHub('${finalImageUrl}', ${JSON.stringify(event).replace(/"/g, '&quot;')})" class="btn btn-success">
                        ☁️ Save to Repository
                    </button>
                    <a href="instagram-gallery.html" target="_blank" class="btn btn-secondary">
                        📸 View All Images
                    </a>
                </div>
            </div>
        `;
        
        generateBtn.disabled = false;
        generateBtn.textContent = '🔄 Regenerate Image';
        
    } catch (error) {
        console.error('Image processing error:', error);
        console.error('Error stack:', error.stack);
        statusDiv.innerHTML = `
            <div style="background: #ffe7e7; border: 1px solid #ffb3b3; padding: 1rem; border-radius: 4px; color: #cc0000;">
                <strong>Error processing image:</strong> ${escapeHtml(error.message)}
                <br><br>
                <details style="margin-top: 0.5rem;">
                    <summary style="cursor: pointer; font-weight: bold;">Technical Details (click to expand)</summary>
                    <pre style="margin-top: 0.5rem; padding: 0.5rem; background: #fff; border: 1px solid #ddd; overflow-x: auto; font-size: 0.85rem;">${escapeHtml(error.stack || error.toString())}</pre>
                </details>
                <br>
                <strong>💡 Troubleshooting:</strong>
                <ul style="margin: 0.5rem 0; padding-left: 1.5rem; font-size: 0.9rem;">
                    <li>Check browser console (F12) for detailed errors</li>
                    <li>Verify OpenAI API key is correct</li>
                    <li>Try regenerating the image</li>
                    <li>If logo error: Upload logo to /public/assets/red-canoe-logo.png</li>
                </ul>
            </div>
        `;
        generateBtn.disabled = false;
        generateBtn.textContent = '✨ Generate Image ($0.04)';
    }
}

function loadImageFromBlob(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = (err) => {
            console.error('Image load error:', err);
            reject(new Error(`Failed to load image from ${url}`));
        };
        img.src = url;
    });
}

function wrapText(ctx, text, maxWidth, fontSize) {
    const words = text.split(' ');
    const lines = [];
    let currentLine = words[0];
    
    for (let i = 1; i < words.length; i++) {
        const testLine = currentLine + ' ' + words[i];
        const metrics = ctx.measureText(testLine);
        
        if (metrics.width > maxWidth) {
            lines.push(currentLine);
            currentLine = words[i];
        } else {
            currentLine = testLine;
        }
    }
    lines.push(currentLine);
    
    return lines.slice(0, 2); // Max 2 lines
}

async function saveImageToGitHub(imageUrl, event) {
    if (!isGitHubConfigured()) {
        showToast('Please configure GitHub token first', 'warning');
        showGitHubTokenDialog();
        return;
    }
    
    try {
        showToast('Uploading image to repository...', 'info');
        
        // Convert blob URL to base64
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        const reader = new FileReader();
        
        const base64 = await new Promise((resolve, reject) => {
            reader.onloadend = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
        
        // Generate filename
        const eventDate = new Date(event.start_utc);
        const dateStr = eventDate.toISOString().split('T')[0]; // YYYY-MM-DD
        const eventSlug = slugify(event.title);
        const filename = `${dateStr}-${eventSlug}.jpg`;
        const path = `public/instagram/${filename}`;
        
        // Commit to GitHub
        const apiBase = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}`;
        
        const commitResponse = await fetch(`${apiBase}/contents/${path}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: `Add Instagram image for: ${event.title}`,
                content: base64,
                branch: GITHUB_BRANCH
            })
        });
        
        if (!commitResponse.ok) {
            const error = await commitResponse.json();
            throw new Error(error.message || 'Failed to upload image');
        }
        
        const commitData = await commitResponse.json();
        const imageGitHubUrl = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/blob/${GITHUB_BRANCH}/${path}`;
        
        showToast('Image saved to repository!', 'success');
        
        // Update preview with GitHub link
        const previewDiv = document.getElementById('image-preview');
        const downloadSection = previewDiv.querySelector('[style*="margin-top"]');
        if (downloadSection) {
            downloadSection.innerHTML += `
                <div style="margin-top: 1rem; padding: 1rem; background: #d4edda; border-radius: 4px;">
                    ✅ Saved to repository!<br>
                    <a href="${imageGitHubUrl}" target="_blank" style="font-size: 0.9rem;">View on GitHub →</a>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Failed to save image: ' + error.message, 'danger');
    }
}


// ==================== INSTAGRAM REEL GENERATION ====================

// Runway ML API configuration
let RUNWAY_API_KEY = localStorage.getItem('runway_api_key') || '';

// Beatoven.ai API for music
let BEATOVEN_API_KEY = localStorage.getItem('beatoven_api_key') || '';

function configureRunwayKey() {
    const currentKey = RUNWAY_API_KEY ? '••••••' + RUNWAY_API_KEY.slice(-4) : 'Not configured';
    
    const dialog = document.createElement('div');
    dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
    
    dialog.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 500px; width: 90%;">
            <h2 style="margin-top: 0;">Configure Runway ML API Key</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Required for AI video generation. Get your key from: 
                <a href="https://app.runwayml.com/" target="_blank">Runway ML</a>
            </p>
            <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">
                <strong>Cost:</strong> ~$0.05-0.15 per second (~$2-4 per reel)<br>
                <strong>Generation time:</strong> 2-5 minutes per reel<br>
                Current key: <code>${currentKey}</code>
            </p>
            <input type="password" id="runway-key-input" placeholder="Enter Runway ML API key..." 
                   style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 1rem; font-family: monospace;">
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button onclick="this.closest('[style*=fixed]').remove()" class="btn btn-secondary">Cancel</button>
                <button onclick="saveRunwayKey()" class="btn btn-primary">Save Key</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    document.getElementById('runway-key-input').focus();
}

function saveRunwayKey() {
    const input = document.getElementById('runway-key-input');
    const key = input.value.trim();
    
    if (!key) {
        showToast('Please enter an API key', 'danger');
        return;
    }
    
    RUNWAY_API_KEY = key;
    localStorage.setItem('runway_api_key', key);
    
    document.querySelector('[style*="fixed"]').remove();
    showToast('Runway ML API key saved!', 'success');
}

function configureBeatovenKey() {
    const currentKey = BEATOVEN_API_KEY ? '••••••' + BEATOVEN_API_KEY.slice(-4) : 'Not configured';
    
    const dialog = document.createElement('div');
    dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
    
    dialog.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 500px; width: 90%;">
            <h2 style="margin-top: 0;">Configure Beatoven.ai API Key</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Optional for AI-generated background music. Get your key from: 
                <a href="https://www.beatoven.ai/" target="_blank">Beatoven.ai</a>
            </p>
            <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">
                <strong>Cost:</strong> Free tier available, Pro $20/month<br>
                <strong>Quality:</strong> High-quality, emotion-based AI music<br>
                <strong>Alternative:</strong> Add music in Instagram app (FREE!)<br>
                Current key: <code>${currentKey}</code>
            </p>
            <input type="password" id="beatoven-key-input" placeholder="Enter Beatoven.ai API key..." 
                   style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 1rem; font-family: monospace;">
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button onclick="this.closest('[style*=fixed]').remove()" class="btn btn-secondary">Cancel</button>
                <button onclick="saveBeatovenKey()" class="btn btn-primary">Save Key</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    document.getElementById('beatoven-key-input').focus();
}

function saveBeatovenKey() {
    const input = document.getElementById('beatoven-key-input');
    const key = input.value.trim();
    
    if (!key) {
        showToast('Please enter an API key', 'danger');
        return;
    }
    
    BEATOVEN_API_KEY = key;
    localStorage.setItem('beatoven_api_key', key);
    
    document.querySelector('[style*="fixed"]').remove();
    showToast('Beatoven.ai API key saved!', 'success');
}

async function generateInstagramReel(event) {
    if (!RUNWAY_API_KEY) {
        showToast('Please configure Runway ML API key first', 'warning');
        configureRunwayKey();
        return;
    }
    
    // Show generation dialog
    showReelGenerationDialog(event);
}

function showReelGenerationDialog(event) {
    const eventDate = new Date(event.start_utc);
    const dateStr = eventDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        month: 'long', 
        day: 'numeric',
        year: 'numeric'
    });
    
    const defaultPrompt = `Create a vibrant vertical video (9:16 VERTICAL aspect ratio - 1080x1920px) for "${event.title}" in Northern Wisconsin.

SETTING: Northwoods of Wisconsin
- Dense pine forests and pristine lakes
- Rustic cabins and charming small towns
- Rolling hills (NO mountains)
- Natural Wisconsin beauty

VIDEO STYLE: 
- Cinematic, professional tourism videography
- Smooth camera movements (pans, slow zooms)
- Golden hour or vibrant daylight
- Inviting and energetic

SCENES TO INCLUDE:
- Sweeping forest views with tall pines
- Beautiful lake with gentle waves
- Rustic wooden structures or town scenes
- Outdoor recreation atmosphere
- Seasonal appropriate (${dateStr.split(',')[0]})

MOOD: Exciting, inviting, captures the spirit of the event and Northern Wisconsin's natural beauty.

Duration: 8 seconds (automatically set)
Format: VERTICAL 9:16 (1080x1920px - Instagram Reel format)
NO mountains, NO deserts - Wisconsin landscape only!`;
    
    const dialog = document.createElement('div');
    dialog.id = 'reel-dialog';
    dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000; overflow-y: auto;';
    
    dialog.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 700px; width: 90%; max-height: 90vh; overflow-y: auto; margin: 2rem;">
            <h2 style="margin-top: 0;">🎥 Generate Instagram Reel</h2>
            
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1rem;">${escapeHtml(event.title)}</h3>
                <div style="font-size: 0.9rem; color: var(--text-muted);">
                    📅 ${dateStr}
                    ${event.location ? `<br>📍 ${escapeHtml(event.location)}` : ''}
                </div>
            </div>
            
            <div style="background: #e7f3ff; border: 1px solid #2196F3; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
                <strong>📱 Video Format:</strong> 9:16 Vertical (1080x1920px) - Perfect for Instagram Reels!
            </div>
            
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
                <strong>⚠️ Video Generation:</strong> Takes 2-5 minutes and costs ~$2-4 per reel. 
                Please be patient during generation.
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; font-weight: 600; margin-bottom: 0.5rem;">AI Video Prompt:</label>
                <textarea id="reel-prompt" rows="12" 
                          style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 4px; font-family: inherit; resize: vertical; font-size: 0.9rem;">${defaultPrompt}</textarea>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem;">
                    💡 Tip: Describe camera movements, scenery, and mood. Video will be 15-25 seconds.
                </div>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; font-weight: 600; margin-bottom: 0.5rem;">
                    <input type="checkbox" id="add-music" style="margin-right: 0.5rem;">
                    Add Background Music (Beatoven.ai)
                </label>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-left: 1.5rem;">
                    Generate AI music matched to event mood and genre<br>
                    <strong>Recommended:</strong> Generate without music, add in Instagram app (FREE!)
                </div>
            </div>
            
            <div id="reel-generation-status" style="margin-bottom: 1rem;"></div>
            <div id="reel-preview" style="margin-bottom: 1rem;"></div>
            
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; flex-wrap: wrap;">
                <button onclick="document.getElementById('reel-dialog').remove()" class="btn btn-secondary">Close</button>
                <button onclick="configureRunwayKey()" class="btn btn-secondary">⚙️ API Key</button>
                <button onclick="startReelGeneration(${JSON.stringify(event).replace(/"/g, '&quot;')})" class="btn btn-primary" id="generate-reel-btn">
                    ✨ Generate Reel ($2-4, 2-5 min)
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
}

async function startReelGeneration(event) {
    const promptInput = document.getElementById('reel-prompt');
    const statusDiv = document.getElementById('reel-generation-status');
    const generateBtn = document.getElementById('generate-reel-btn');
    const addMusic = document.getElementById('add-music').checked;
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showToast('Please enter a prompt', 'warning');
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating...';
    
    statusDiv.innerHTML = `
        <div style="background: #e7f3ff; border: 1px solid #b3d9ff; padding: 1rem; border-radius: 4px;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 20px; height: 20px; border: 3px solid #0066cc; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <span><strong>Step 1/3:</strong> Checking backend configuration...</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
                Video generation requires a backend service. Checking setup...
            </div>
        </div>
        <style>
            @keyframes spin { to { transform: rotate(360deg); } }
        </style>
    `;
    
    try {
        const BACKEND_URL = localStorage.getItem('reel_backend_url') || '';
        
        if (!BACKEND_URL) {
            throw new Error('Backend URL not configured. Please set up your backend service first.');
        }
        
        // First, test the backend connection
        statusDiv.innerHTML = `
            <div style="background: #e7f3ff; border: 1px solid #b3d9ff; padding: 1rem; border-radius: 4px;">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <div style="width: 20px; height: 20px; border: 3px solid #0066cc; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <span><strong>Step 1/3:</strong> Testing backend connection...</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted);">
                    Connecting to: ${BACKEND_URL.substring(0, 50)}...
                </div>
            </div>
        `;
        
        // Test connection with health check
        try {
            const healthCheck = await fetch(BACKEND_URL, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            
            if (!healthCheck.ok) {
                throw new Error(`Backend returned status ${healthCheck.status}. Please verify the URL and deployment.`);
            }
            
            const healthData = await healthCheck.json();
            console.log('Backend health check:', healthData);
            
            if (!healthData.runwayConfigured) {
                throw new Error('Runway ML API key not configured on backend. Please set RUNWAY_API_KEY environment variable in Vercel.');
            }
        } catch (healthError) {
            console.error('Health check error:', healthError);
            throw new Error(`Cannot connect to backend: ${healthError.message}. Verify URL: ${BACKEND_URL}`);
        }
        
        statusDiv.innerHTML = `
            <div style="background: #e7f3ff; border: 1px solid #b3d9ff; padding: 1rem; border-radius: 4px;">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <div style="width: 20px; height: 20px; border: 3px solid #0066cc; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <span><strong>Step 2/3:</strong> Generating Video... This takes 2-5 minutes</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted);">
                    Submitting to Runway ML...<br>
                    Please keep this window open.
                </div>
            </div>
        `;
        
        const response = await fetch(BACKEND_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                event: {
                    title: event.title,
                    start_utc: event.start_utc,
                    location: event.location,
                },
                addMusic: addMusic,
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Backend error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }
        
        // Show preview and save options
        const previewDiv = document.getElementById('reel-preview');
        previewDiv.innerHTML = `
            <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
                ✅ Video generated successfully!
            </div>
            <video controls style="width: 100%; max-width: 400px; border-radius: 8px; margin-bottom: 1rem;">
                <source src="${data.videoUrl || data.video}" type="video/mp4">
                Your browser does not support video playback.
            </video>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <a href="${data.videoUrl || data.video}" download="reel-${Date.now()}.mp4" class="btn btn-success">
                    💾 Download Reel
                </a>
                <button onclick="saveReelToGitHub('${(data.videoUrl || data.video).replace(/'/g, "\\'")}', ${JSON.stringify(event).replace(/"/g, '&quot;')})" class="btn btn-primary">
                    ☁️ Save to Repository
                </button>
            </div>
        `;
        
        statusDiv.innerHTML = '';
        showToast('Reel generated successfully!', 'success');
        
    } catch (error) {
        console.error('Reel generation error:', error);
        
        if (error.message.includes('Backend URL not configured')) {
            statusDiv.innerHTML = `
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1.5rem; border-radius: 4px;">
                    <h3 style="margin-top: 0; font-size: 1rem;">🚧 Backend Service Required</h3>
                    <p style="margin-bottom: 1rem;">
                        Instagram Reel generation requires a backend service. Follow these steps:
                    </p>
                    <ol style="margin: 0 0 1rem 1.5rem; padding: 0; line-height: 1.8;">
                        <li>Deploy the backend to Vercel, Netlify, or AWS Lambda</li>
                        <li>Get your API endpoint URL</li>
                        <li>Click "⚙️ Configure Backend" below to save it</li>
                    </ol>
                    <button onclick="configureBackendUrl()" class="btn btn-primary">
                        ⚙️ Configure Backend URL
                    </button>
                    <a href="https://github.com/${GITHUB_REPO}/tree/main/backend-example" target="_blank" class="btn btn-secondary" style="margin-left: 0.5rem;">
                        📖 Deployment Guide
                    </a>
                </div>
            `;
        } else {
            statusDiv.innerHTML = `
                <div style="background: #ffe7e7; border: 1px solid #ffb3b3; padding: 1rem; border-radius: 4px; color: #cc0000;">
                    <strong>Error:</strong> ${escapeHtml(error.message)}<br>
                    <small>Check console for details (F12)</small>
                </div>
            `;
        }
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '✨ Generate Reel ($2-4, 2-5 min)';
    }
}

function configureBackendUrl() {
    const currentUrl = localStorage.getItem('reel_backend_url') || '';
    
    const dialog = document.createElement('div');
    dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
    
    dialog.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 500px; width: 90%;">
            <h2 style="margin-top: 0;">Configure Backend URL</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Enter the URL of your deployed backend service.
            </p>
            <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">
                <strong>Example:</strong><br>
                <code style="display: block; background: #f5f5f5; padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem;">
                https://your-project.vercel.app/api/generate-reel
                </code>
            </p>
            <input type="url" id="backend-url-input" placeholder="https://..." 
                   value="${currentUrl}"
                   style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 1rem; font-family: monospace;">
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button onclick="this.closest('[style*=fixed]').remove()" class="btn btn-secondary">Cancel</button>
                <button onclick="saveBackendUrl()" class="btn btn-primary">Save URL</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    document.getElementById('backend-url-input').focus();
}

async function saveBackendUrl() {
    const input = document.getElementById('backend-url-input');
    const url = input.value.trim();
    
    if (!url) {
        showToast('Please enter a URL', 'danger');
        return;
    }
    
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        showToast('URL must start with http:// or https://', 'danger');
        return;
    }
    
    // Test the URL before saving
    showToast('Testing backend connection...', 'info');
    
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`Backend returned status ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            localStorage.setItem('reel_backend_url', url);
            document.querySelector('[style*="fixed"]').remove();
            
            let message = '✅ Backend connected!';
            if (!data.runwayConfigured) {
                message += '\n⚠️ Warning: Runway ML API key not configured on backend';
            }
            if (!data.beatovenConfigured) {
                message += '\n⚠️ Music generation unavailable (Beatoven.ai not configured)';
            }
            
            showToast(message, 'success');
            console.log('Backend health:', data);
        } else {
            throw new Error('Invalid backend response');
        }
    } catch (error) {
        console.error('Backend test failed:', error);
        showToast(`❌ Cannot connect to backend: ${error.message}`, 'danger');
    }
}

async function saveReelToGitHub(videoUrl, event) {
    if (!GITHUB_TOKEN) {
        showToast('Please configure GitHub token first', 'warning');
        showGitHubTokenDialog();
        return;
    }
    
    try {
        showToast('Downloading video...', 'info');
        
        // Fetch video as blob
        const response = await fetch(videoUrl);
        if (!response.ok) {
            throw new Error('Failed to download video');
        }
        
        const blob = await response.blob();
        
        // Convert to base64
        const base64 = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result.split(',')[1]);
            reader.readAsDataURL(blob);
        });
        
        // Generate filename
        const eventDate = new Date(event.start_utc);
        const dateStr = eventDate.toISOString().split('T')[0];
        const slug = slugify(event.title);
        const filename = `${dateStr}-${slug}.mp4`;
        const path = `public/instagram-reels/${filename}`;
        
        showToast('Committing to repository...', 'info');
        
        // Commit to GitHub
        const apiUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${path}`;
        console.log('Committing to:', apiUrl);
        
        const commitResponse = await fetch(apiUrl, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: `Add Instagram Reel: ${event.title}`,
                content: base64,
                branch: GITHUB_BRANCH,
            }),
        });
        
        if (!commitResponse.ok) {
            const errorData = await commitResponse.json();
            throw new Error(errorData.message || 'Failed to commit to GitHub');
        }
        
        const commitData = await commitResponse.json();
        console.log('Video committed successfully:', commitData);
        
        showToast('✅ Reel saved to repository!', 'success');
        
        // Show success message with link
        const successDiv = document.createElement('div');
        successDiv.style.cssText = 'background: #d4edda; border: 1px solid #c3e6cb; padding: 1rem; border-radius: 4px; margin-top: 1rem;';
        successDiv.innerHTML = `
            <strong>✅ Saved!</strong> View in 
            <a href="reel-gallery.html" target="_blank">Reel Gallery</a> or on 
            <a href="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/blob/${GITHUB_BRANCH}/${path}" target="_blank">GitHub</a>
        `;
        document.getElementById('reel-preview').appendChild(successDiv);
        
    } catch (error) {
        console.error('Error saving reel:', error);
        showToast(`Failed to save: ${error.message}`, 'danger');
    }
}

