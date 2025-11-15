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
            </div>
        `;
    }).join('') + '</div>';
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
    
    return [...matched, ...limitedAuto];
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
