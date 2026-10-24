import { icon, mark } from './icons.js';
import { parseAddress, moveTab, nextTabAfterClose, escapeHTML as esc } from './model.js';
const $ = s => document.querySelector(s);
const shell = $('#shell'), page = $('#page'), panel = $('#panel'), address = $('#address');
let serial = 3, active = 1, expanded = true, vertical = false, workspace = 'Personal';
let tabs = [
    { id: 1, title: 'New tab', url: 'trinol://newtab', kind: 'newtab', pinned: false },
    { id: 2, title: 'Field notes — the art of paying attention', url: 'https://fieldnotes.example/journal', kind: 'https', audio: true, pinned: false },
    { id: 3, title: 'Atlas of the everyday', url: 'https://atlas.example/collections', kind: 'https', pinned: false },
];
for (const tab of tabs) {
    tab.history = [{ title: tab.title, url: tab.url, kind: tab.kind }];
    tab.position = 0;
}
let toastTimer, returnFocus, commandIndex = 0, visibleCommands = [], suggestionIndex = 0;
let lastDrag = null;
const loaders = new Map();
let shortcuts = [
    ['Notebook', 'N', 'https://notebook.example'], ['Atlas', 'A', 'https://atlas.example'],
    ['Are.na', 'a', 'https://arena.example'], ['GitHub', 'G', 'https://github.example'], ['Figma', 'F', 'https://figma.example'],
];
const recents = [
    ['A quieter kind of internet', 'Field notes', '12 min ago', 'https://fieldnotes.example/journal'],
    ['Objects worth keeping', 'Atlas', 'Yesterday', 'https://atlas.example/collections'],
    ['The shape of a good idea', 'Notebook', 'Yesterday', 'https://notebook.example/ideas'],
    ['A place for the unfinished', 'Studio notes', '2 days ago', 'https://studio.example/notes'],
];
const current = () => tabs.find(t => t.id === active);
const button = (action, label, glyph, extra = '') => `<button class="nav-row ${extra}" data-action="${action}" aria-label="${label}" title="${label}">${icon(glyph)}<span class="nav-label">${label}</span></button>`;
function notify(text) { clearTimeout(toastTimer); $('#toast').textContent = text; $('#toast').classList.add('visible'); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 2800); }
function tabHTML(t) {
    return `<div class="tab ${t.id === active ? 'active' : ''} ${t.pinned ? 'pinned' : ''} ${t.audio ? 'audio' : ''}" draggable="true" data-tab="${t.id}">
    <button class="tab-select" role="tab" aria-selected="${t.id === active}" tabindex="${t.id === active ? 0 : -1}" aria-controls="page" id="tab-${t.id}" data-select="${t.id}" title="${esc(t.title)}${t.pinned ? ' (pinned)' : ''}">
    <span class="favicon">${t.loading ? '<span class="loading-ring"></span>' : t.kind === 'newtab' ? mark : esc(t.title[0].toUpperCase())}</span><span class="tab-title" ${t.pinned && !vertical ? 'hidden' : ''}>${esc(t.title)}</span></button>
    ${t.pinned ? '' : `<button class="tab-close" data-close="${t.id}" aria-label="Close ${esc(t.title)}">${icon('close')}</button>`}
    ${t.audio ? `<button class="audio-toggle" data-audio="${t.id}" aria-label="${t.muted ? 'Unmute' : 'Mute'} demo tab" aria-pressed="${!!t.muted}" title="Demo audio indicator">${icon(t.muted ? 'close' : 'audio')}</button>` : ''}</div>`;
}
function renderTabs() {
    $('#tabs').innerHTML = tabs.map(tabHTML).join('');
    $('#tabs').setAttribute('aria-orientation', 'horizontal');
    if (vertical)
        $('#vertical-tabs').innerHTML = tabs.map(tabHTML).join('');
    page.setAttribute('aria-labelledby', `tab-${active}`);
    // Only the visible tablist owns IDs and panel relationships.
    if (vertical)
        $('#tabs').innerHTML = '';
}
function renderSidebar() {
    $('#sidebar').className = `sidebar ${expanded ? 'expanded' : ''}`;
    $('#sidebar').innerHTML = `<div class="sidebar-head">${mark}${expanded || vertical ? '<span class="brand-name">trinol</span>' : ''}</div>
    ${vertical ? '<div id="vertical-tabs" class="tabs" role="tablist" aria-orientation="vertical" aria-label="Open demo tabs"></div>' + button('new', 'New tab', 'plus') : button('new', 'New tab', 'plus', current().kind === 'newtab' ? 'selected' : '')}
    ${button('tabs', 'Tab overview', 'tabs')}${button('bookmarks', 'Bookmarks', 'star')}${button('history', 'History', 'history')}${button('downloads', 'Downloads', 'download')}
    <div class="sidebar-rule"></div>${expanded || vertical ? '<div class="sidebar-label">Spaces <span class="badge">· Concept</span></div>' : ''}
    <button class="nav-row ${workspace === 'Personal' ? 'selected' : ''}" data-space="Personal" title="Personal demo space" aria-label="Personal demo space"><span class="workspace-dot"></span><span class="nav-label">Personal</span>${expanded || vertical ? '<span class="badge">⌥1</span>' : ''}</button>
    <button class="nav-row ${workspace === 'Studio' ? 'selected' : ''}" data-space="Studio" title="Studio demo space" aria-label="Studio demo space"><span class="workspace-dot coral"></span><span class="nav-label">Studio</span></button>
    <div class="sidebar-spacer"></div>${button('settings', 'Settings', 'settings')}${button('sidebar', expanded ? 'Collapse sidebar' : 'Expand sidebar', 'sidebar', 'collapse-button')}`;
}
function newTabHTML() {
    return `<section class="newtab"><div class="page-top"><span class="space-pill"><span class="workspace-dot ${workspace === 'Studio' ? 'coral' : ''}"></span>${workspace} space</span><button class="text-button" data-action="commands">${icon('command')}Quick command <kbd>⌘ K</kbd></button></div>
    <div class="newtab-center"><svg class="orbit-art" viewBox="0 0 400 400" aria-hidden="true"><ellipse cx="200" cy="200" rx="174" ry="75" transform="rotate(-42 200 200)"/><ellipse cx="200" cy="200" rx="174" ry="113" transform="rotate(-42 200 200)"/><path d="M52 307 261 27l83 279"/><circle cx="316" cy="97" r="5"/><circle cx="68" cy="253" r="3"/></svg>
    <div class="wordmark">${mark}<span>trinol</span></div><h1>Where to next?</h1>
    <form class="newtab-search" id="start-search" role="search" aria-label="New tab search">${icon('search')}<input aria-label="Search the web or enter a URL" placeholder="Search the web or enter a URL" autocomplete="off"><kbd>↵</kbd></form>
    <div class="shortcuts" aria-label="Demo pinned shortcuts">${shortcuts.map(([name, letter, url]) => `<button class="shortcut" data-url="${esc(url)}" aria-label="Open ${esc(name)} demo"><span class="shortcut-icon">${esc(letter)}</span><span>${esc(name)}</span></button>`).join('')}<button class="shortcut add" data-action="add-shortcut"><span class="shortcut-icon">${icon('plus')}</span><span>Add shortcut</span></button></div>
    <section class="threads"><div class="section-title"><h2>Pick up a thread</h2><span>Demo history</span></div><div class="thread-list">${recents.map(([title, site, when, url]) => `<button class="thread" data-url="${url}"><span class="favicon">${esc(site[0])}</span><span class="thread-text"><strong>${title}</strong><small>${site} · ${when}</small></span>${icon('arrow')}</button>`).join('')}</div></section></div>
    <div class="newtab-bottom"><span>${icon('globe')}A little more room for your next idea.</span><button class="text-button" data-action="appearance">${icon('settings')}Make it yours</button></div></section>`;
}
function contentHTML(t) {
    if (t.kind === 'newtab')
        return newTabHTML();
    const warning = t.kind === 'warning', invalid = t.kind === 'invalid';
    return `${t.loading ? '<div class="loading-strip" aria-label="Demo page loading"></div>' : ''}<section class="preview-content"><span class="demo-banner">${icon(warning || invalid ? 'warning' : 'globe')}Simulated page · No network request</span>
    <h1>${warning ? 'Connection warning' : invalid ? 'This address is unavailable' : t.kind === 'search' ? 'A direction to explore.' : esc(t.title)}</h1>
    <p>${warning ? 'This is a certificate-warning design example. In the native browser, Chromium owns certificate validation and interstitial decisions.' : invalid ? 'Use an HTTP or HTTPS address, or enter a search. This prototype does not run scripts or open local files from the address field.' : t.kind === 'search' ? `Demo search for “${esc(t.title)}”. A native integration will use the configured search provider.` : 'A reading surface for reviewing the browser around it. This fictional page demonstrates tab navigation, loading, history and bookmarks without contacting a website.'}</p>
    ${!warning && !invalid ? '<div class="article-demo"><div>Room for the work.</div><div>Less in the way.</div></div><div class="article-rule"></div><p>Every control has a place. Every page has room to breathe.</p>' : ''}
    <button class="action" data-action="${warning || invalid ? 'focus-address' : 'new'}">${icon(warning || invalid ? 'search' : 'plus')}${warning || invalid ? 'Edit address' : 'Open a new tab'}</button></section>`;
}
function render() {
    const t = current();
    shell.classList.toggle('vertical', vertical);
    renderSidebar();
    renderTabs();
    page.innerHTML = contentHTML(t);
    address.value = t.kind === 'newtab' ? '' : t.url;
    $('#address-form').classList.toggle('warning', t.kind === 'warning' || t.kind === 'invalid');
    $('[data-action="back"]').disabled = t.position === 0;
    $('[data-action="forward"]').disabled = t.position === t.history.length - 1;
    $('[data-action="reload"]').innerHTML = icon(t.loading ? 'stop' : 'reload');
    $('[data-action="reload"]').setAttribute('aria-label', t.loading ? 'Stop loading' : 'Reload');
    $('[data-action="site"]').innerHTML = icon(t.kind === 'warning' || t.kind === 'invalid' ? 'warning' : 'site');
    $('[data-action="site"]').style.color = t.kind === 'warning' || t.kind === 'invalid' ? 'var(--coral)' : '';
    $('[data-action="bookmark"]').innerHTML = icon('star');
    $('[data-action="bookmark"]').setAttribute('aria-pressed', !!t.bookmarked);
    $('[data-action="bookmark"]').style.color = t.bookmarked ? 'var(--accent)' : '';
    $('[data-action="layout"]').innerHTML = icon(vertical ? 'tabs' : 'sidebar');
    $('[data-action="layout"]').setAttribute('aria-label', vertical ? 'Switch to horizontal tabs' : 'Switch to vertical tabs');
    $('[data-action="theme"]').innerHTML = icon(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon');
    $('[data-action="theme"]').setAttribute('aria-label', document.documentElement.dataset.theme === 'dark' ? 'Switch to light appearance' : 'Switch to dark appearance');
    $('[data-action="new"]').innerHTML = icon('plus');
    for (const action of ['back', 'forward', 'downloads', 'menu'])
        $(`.navigation [data-action="${action}"]`).innerHTML = icon(action === 'downloads' ? 'download' : action);
}
function addTab() { const t = { id: ++serial, title: 'New tab', url: 'trinol://newtab', kind: 'newtab', pinned: false, history: [{ title: 'New tab', url: 'trinol://newtab', kind: 'newtab' }], position: 0 }; tabs.push(t); active = t.id; hideSuggestions(); render(); address.focus(); }
function selectTab(id) { active = id; hideSuggestions(); render(); }
function closeTab(id) { clearTimeout(loaders.get(id)); const next = nextTabAfterClose(tabs, id, active); tabs = next.tabs; active = next.active; if (!tabs.length)
    addTab();
else {
    render();
    $(`#tab-${active}`).focus();
} }
function navigate(value) {
    const entry = parseAddress(value);
    if (!entry)
        return;
    const t = current();
    clearTimeout(loaders.get(t.id));
    t.history = t.history.slice(0, t.position + 1);
    t.history.push(entry);
    t.position++;
    Object.assign(t, entry);
    t.loading = entry.kind !== 'invalid' && entry.kind !== 'newtab';
    hideSuggestions();
    render();
    page.focus();
    if (t.loading)
        loaders.set(t.id, setTimeout(() => { t.loading = false; if (t.id === active)
            render(); }, 1200));
}
function historyStep(delta) { const t = current(); const next = t.position + delta; if (next < 0 || next >= t.history.length)
    return; clearTimeout(loaders.get(t.id)); t.position = next; Object.assign(t, t.history[next], { loading: false }); render(); }
function toggleTheme() { document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; render(); }
function closePanel() { panel.close(); if (returnFocus?.isConnected)
    returnFocus.focus();
else
    $('[data-action="commands"]').focus(); }
function openPanel(title, body) { hideSuggestions(); returnFocus = document.activeElement; panel.innerHTML = `<div class="dialog-header"><h2 id="panel-title">${title}</h2><button class="icon-button" data-action="dismiss" aria-label="Close dialog">${icon('close')}</button></div><div class="dialog-body">${body}</div>`; panel.showModal(); }
const row = (label, description, action, glyph = 'chevron') => `<button class="dialog-row" data-action="${action}">${icon(glyph)}<span>${label}${description ? `<small>${description}</small>` : ''}</span></button>`;
function openService(service) {
    if (service === 'tabs')
        return openPanel('Your open tabs', `<p>Demo session · ${tabs.length} tabs</p>${tabs.map(t => `<button class="dialog-row" data-go-tab="${t.id}"><span class="favicon">${esc(t.title[0])}</span><span>${esc(t.title)}<small>${esc(t.url)}</small></span>${t.id === active ? icon('check') : ''}</button>`).join('')}`);
    if (service === 'bookmarks')
        return openPanel('Bookmarks', `<p>Stored in this preview session only.</p>${tabs.filter(t => t.bookmarked).map(t => `<button class="dialog-row" data-go-tab="${t.id}">${icon('star')}<span>${esc(t.title)}</span></button>`).join('') || '<p class="empty-state">No bookmarks yet. Use the star in the address bar to save a demo tab.</p>'}`);
    if (service === 'history')
        return openPanel('History', `<p>Fictional entries for design review.</p>${recents.map(([title, site, when, url]) => `<button class="dialog-row" data-url="${url}">${icon('history')}<span>${title}<small>${site} · ${when}</small></span></button>`).join('')}`);
    if (service === 'downloads')
        return openPanel('Downloads', `<p>No files have been downloaded. This preview never downloads or accesses your files.</p><div class="empty-state">${icon('download')} Downloads will appear here in the native browser.</div>`);
    if (service === 'profile')
        return openPanel('Personal profile', `<p>Local design persona. No account or personal profile is connected.</p>${row('Personal', 'Active demo space', 'space-personal', 'globe')}${row('Studio', 'Explore a second demo space', 'space-studio', 'folder')}`);
    if (service === 'site')
        return openPanel('Demo site information', `<p>${current().kind === 'warning' ? 'Certificate warning example.' : current().url.startsWith('https:') ? 'HTTPS URL example.' : 'Internal or non-HTTPS page example.'} This prototype does not validate a connection, certificate or permissions.</p><p>Native site information and security decisions will remain owned by Chromium.</p>`);
    if (service === 'appearance' || service === 'settings')
        return openPanel(service === 'settings' ? 'Settings preview' : 'Make it yours', `<p>Appearance changes apply only to this design preview.</p>${row('Switch appearance', document.documentElement.dataset.theme === 'dark' ? 'Currently dark' : 'Currently light', 'theme', 'sun')}${row(vertical ? 'Use horizontal tabs' : 'Explore vertical tabs', 'Alternative layout for design review', 'layout', 'tabs')}${row(expanded ? 'Collapse sidebar' : 'Expand sidebar', 'Compact and expanded navigation', 'sidebar', 'sidebar')}${row('Add a shortcut', 'Fictional shortcut, stored for this session', 'add-shortcut', 'plus')}`);
    if (service === 'menu')
        return openPanel('Trinol menu', `${row('New tab', '⌘T', 'new', 'plus')}${row('Pin or unpin current tab', 'Keep it at the leading edge', 'pin', 'pin')}${row('Tab overview', 'Switch between open demo tabs', 'tabs', 'tabs')}${row('Appearance', 'Theme and tab layout', 'appearance', 'sun')}${row('Command palette', '⌘K', 'commands', 'command')}`);
}
function openShortcut() { openPanel('Add a shortcut', '<form id="shortcut-form"><label for="shortcut-name">Name</label><input class="dialog-input" id="shortcut-name" required maxlength="20" placeholder="My notebook"><label for="shortcut-url">Web address</label><input class="dialog-input" id="shortcut-url" required placeholder="https://notebook.example"><p id="shortcut-error" role="alert"></p><button class="action dialog-row" type="submit">Add demo shortcut</button></form>'); $('#shortcut-name').focus(); }
const commands = [['New tab', 'new', 'plus', '⌘T'], ['Search open tabs', 'tabs', 'tabs', ''], ['Open downloads', 'downloads', 'download', ''], ['Open settings', 'settings', 'settings', ''], ['Search history', 'history', 'history', ''], ['Toggle sidebar', 'sidebar', 'sidebar', ''], ['Switch appearance', 'theme', 'sun', ''], ['Explore tab layout', 'layout', 'tabs', '']];
function openCommands() { hideSuggestions(); returnFocus = document.activeElement; commandIndex = 0; panel.innerHTML = `<h2 id="panel-title" hidden>Quick commands</h2><div class="command-search">${icon('search')}<input id="command-search" role="combobox" aria-label="Search commands or open tabs" aria-controls="command-results" aria-expanded="true" aria-autocomplete="list" placeholder="What would you like to do?" autocomplete="off"><kbd>esc</kbd></div><div id="command-results" class="command-list" role="listbox" aria-label="Commands"></div><div class="command-footer"><span>↑ ↓ to move · ↵ to select</span><span>Trinol Orbit</span></div>`; panel.showModal(); renderCommands(''); $('#command-search').focus(); }
function renderCommands(query) { const q = query.toLowerCase().trim(); visibleCommands = commands.filter(c => c[0].toLowerCase().includes(q)).map(c => ({ label: c[0], action: c[1], glyph: c[2], key: c[3] })); if (q)
    visibleCommands.push(...tabs.filter(t => t.title.toLowerCase().includes(q)).map(t => ({ label: `Switch to ${t.title}`, tab: t.id, glyph: 'tabs', key: '' }))); commandIndex = Math.min(commandIndex, Math.max(0, visibleCommands.length - 1)); $('#command-results').innerHTML = visibleCommands.map((c, i) => `<div class="command-option" role="option" id="command-${i}" aria-selected="${i === commandIndex}" data-command="${i}">${icon(c.glyph)}<span>${esc(c.label)}</span>${c.key ? `<kbd>${c.key}</kbd>` : ''}</div>`).join('') || '<div class="empty-state">No matching commands. Try “tab” or “settings”.</div>'; if (visibleCommands.length)
    $('#command-search').setAttribute('aria-activedescendant', `command-${commandIndex}`);
else
    $('#command-search').removeAttribute('aria-activedescendant'); }
function runCommand(index) { const c = visibleCommands[index]; if (!c)
    return; closePanel(); if (c.tab)
    selectTab(c.tab);
else
    action(c.action); }
function suggestionData() { const q = address.value.trim(); return [{ label: q ? `Search for “${q}”` : 'Search the web', detail: 'Demo search · No network request', value: q || 'a quieter web', glyph: 'search' }, ...tabs.filter(t => t.id !== active && (!q || t.title.toLowerCase().includes(q.toLowerCase()))).slice(0, 3).map(t => ({ label: t.title, detail: 'Switch to open tab', tab: t.id, glyph: 'tabs' })), { label: q.includes('.') ? q : 'fieldnotes.example', detail: 'Open a simulated page', value: q.includes('.') ? q : 'https://fieldnotes.example', glyph: 'globe' }]; }
function showSuggestions() { const data = suggestionData(); suggestionIndex = Math.min(suggestionIndex, data.length - 1); $('#suggestions').innerHTML = '<div class="suggestions-label">In this preview</div>' + data.map((s, i) => `<div role="option" class="suggestion" id="suggestion-${i}" aria-selected="${i === suggestionIndex}" data-suggestion="${i}">${icon(s.glyph)}<span><strong>${esc(s.label)}</strong><small>${esc(s.detail)}</small></span></div>`).join(''); $('#suggestions').hidden = false; address.setAttribute('aria-expanded', 'true'); address.setAttribute('aria-activedescendant', `suggestion-${suggestionIndex}`); }
function hideSuggestions() { $('#suggestions').hidden = true; address.setAttribute('aria-expanded', 'false'); address.removeAttribute('aria-activedescendant'); }
function chooseSuggestion(index) { const item = suggestionData()[index]; hideSuggestions(); if (item.tab)
    selectTab(item.tab);
else
    navigate(item.value); }
function action(name) {
    if (name === 'dismiss')
        return closePanel();
    if (name === 'new')
        return addTab();
    if (name === 'focus-address') {
        address.focus();
        address.select();
        return;
    }
    if (name === 'back' || name === 'forward')
        return historyStep(name === 'back' ? -1 : 1);
    if (name === 'reload') {
        const t = current();
        clearTimeout(loaders.get(t.id));
        t.loading = !t.loading;
        render();
        if (t.loading)
            loaders.set(t.id, setTimeout(() => { t.loading = false; if (active === t.id)
                render(); }, 1200));
        return;
    }
    if (name === 'bookmark') {
        current().bookmarked = !current().bookmarked;
        render();
        notify(current().bookmarked ? 'Demo bookmark saved' : 'Demo bookmark removed');
        return;
    }
    if (name === 'sidebar') {
        expanded = !expanded;
        render();
        return;
    }
    if (name === 'theme')
        return toggleTheme();
    if (name === 'layout') {
        vertical = !vertical;
        render();
        return;
    }
    if (name === 'commands')
        return openCommands();
    if (name === 'pin') {
        const t = current();
        t.pinned = !t.pinned;
        tabs.sort((a, b) => Number(b.pinned) - Number(a.pinned));
        render();
        notify(t.pinned ? 'Demo tab pinned' : 'Demo tab unpinned');
        return;
    }
    if (name === 'add-shortcut')
        return openShortcut();
    if (name.startsWith('space-')) {
        workspace = name === 'space-studio' ? 'Studio' : 'Personal';
        render();
        return;
    }
    if (name === 'scenarios')
        return openPanel('Review visual states', `<p>Simulated states only. No certificate checks or network requests occur.</p><div class="state-grid">${['newtab', 'loading', 'https', 'warning', 'invalid', 'empty'].map(s => `<button data-scenario="${s}">${({ newtab: 'New Tab', loading: 'Loading', https: 'HTTPS URL', warning: 'Certificate warning', invalid: 'Invalid address', empty: 'Empty address field' })[s]}</button>`).join('')}</div>`);
    openService(name);
}
function scenario(name) { closePanel(); if (name === 'newtab')
    return addTab(); if (name === 'empty') {
    address.value = '';
    address.focus();
    return;
} if (name === 'loading') {
    navigate('https://atlas.example/collections');
    clearTimeout(loaders.get(active));
    return;
} if (name === 'https')
    return navigate('https://example.com'); if (name === 'invalid')
    return navigate('javascript:alert(1)'); Object.assign(current(), { title: 'Certificate warning', url: 'https://certificate-warning.example', kind: 'warning', loading: false }); render(); }
document.addEventListener('click', e => {
    const b = e.target.closest('button,[data-suggestion],[data-command]');
    if (!b)
        return;
    if (b.dataset.action) {
        if (panel.open && !['dismiss'].includes(b.dataset.action))
            closePanel();
        action(b.dataset.action);
    }
    else if (b.dataset.select)
        selectTab(Number(b.dataset.select));
    else if (b.dataset.close)
        closeTab(Number(b.dataset.close));
    else if (b.dataset.audio) {
        const t = tabs.find(t => t.id === Number(b.dataset.audio));
        t.muted = !t.muted;
        renderTabs();
        notify(t.muted ? 'Demo audio muted' : 'Demo audio unmuted');
    }
    else if (b.dataset.url) {
        if (panel.open)
            closePanel();
        navigate(b.dataset.url);
    }
    else if (b.dataset.goTab) {
        closePanel();
        selectTab(Number(b.dataset.goTab));
    }
    else if (b.dataset.space) {
        workspace = b.dataset.space;
        render();
        notify(`${workspace} demo space selected`);
    }
    else if (b.dataset.command !== undefined)
        runCommand(Number(b.dataset.command));
    else if (b.dataset.suggestion !== undefined)
        chooseSuggestion(Number(b.dataset.suggestion));
    else if (b.dataset.scenario)
        scenario(b.dataset.scenario);
});
document.addEventListener('submit', e => { e.preventDefault(); if (e.target.id === 'address-form')
    navigate(address.value); if (e.target.id === 'start-search')
    navigate(e.target.querySelector('input').value); if (e.target.id === 'shortcut-form') {
    const entry = parseAddress($('#shortcut-url').value);
    if (!entry || !['https', 'http'].includes(entry.kind)) {
        $('#shortcut-error').textContent = 'Enter a valid HTTP or HTTPS address.';
        return;
    }
    if (shortcuts.length >= 7) {
        $('#shortcut-error').textContent = 'This layout supports up to seven demo shortcuts.';
        return;
    }
    const name = $('#shortcut-name').value.trim();
    if (!name) {
        $('#shortcut-error').textContent = 'Enter a shortcut name.';
        return;
    }
    shortcuts.push([name, name[0].toUpperCase(), entry.url]);
    closePanel();
    render();
    notify('Demo shortcut added');
} });
address.addEventListener('focus', () => { suggestionIndex = 0; showSuggestions(); });
address.addEventListener('input', () => { suggestionIndex = 0; showSuggestions(); });
document.addEventListener('input', e => { if (e.target.id === 'command-search') {
    commandIndex = 0;
    renderCommands(e.target.value);
} });
document.addEventListener('pointerdown', e => { if (!e.target.closest('#address-form'))
    hideSuggestions(); });
panel.addEventListener('cancel', e => { e.preventDefault(); closePanel(); });
panel.addEventListener('click', e => { if (e.target === panel) {
    const r = panel.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)
        closePanel();
} });
document.addEventListener('keydown', e => {
    const key = e.key.toLowerCase(), mod = e.metaKey || e.ctrlKey;
    if (panel.open) {
        if (e.target.id === 'command-search') {
            if (['arrowdown', 'arrowup'].includes(key)) {
                e.preventDefault();
                commandIndex = (commandIndex + (key === 'arrowdown' ? 1 : -1) + Math.max(visibleCommands.length, 1)) % Math.max(visibleCommands.length, 1);
                renderCommands(e.target.value);
            }
            if (key === 'enter') {
                e.preventDefault();
                runCommand(commandIndex);
            }
        }
        return;
    }
    if (mod && ['k', 'l', 't', 'w', 'b'].includes(key)) {
        e.preventDefault();
        if (key === 'k')
            openCommands();
        if (key === 'l') {
            address.focus();
            address.select();
        }
        if (key === 't')
            addTab();
        if (key === 'w')
            closeTab(active);
        if (key === 'b')
            action('sidebar');
        return;
    }
    if (e.altKey && key === '1') {
        e.preventDefault();
        workspace = 'Personal';
        render();
    }
    if (e.target === address && !$('#suggestions').hidden) {
        if (['arrowdown', 'arrowup'].includes(key)) {
            e.preventDefault();
            suggestionIndex = (suggestionIndex + (key === 'arrowdown' ? 1 : -1) + suggestionData().length) % suggestionData().length;
            showSuggestions();
        }
        if (key === 'enter') {
            e.preventDefault();
            chooseSuggestion(suggestionIndex);
        }
        if (key === 'escape') {
            e.preventDefault();
            hideSuggestions();
            address.blur();
        }
        return;
    }
    const tab = e.target.closest('[role="tab"]');
    if (tab && ['arrowright', 'arrowleft', 'arrowup', 'arrowdown', 'home', 'end'].includes(key)) {
        e.preventDefault();
        const index = tabs.findIndex(t => t.id === Number(tab.dataset.select));
        const next = key === 'home' ? 0 : key === 'end' ? tabs.length - 1 : (index + (['arrowright', 'arrowdown'].includes(key) ? 1 : -1) + tabs.length) % tabs.length;
        if (e.altKey && e.shiftKey) {
            tabs = moveTab(tabs, tabs[index].id, tabs[next].id);
            renderTabs();
            notify('Demo tab reordered');
            $(`#tab-${active}`).focus();
        }
        else {
            selectTab(tabs[next].id);
            $(`#tab-${active}`).focus();
        }
    }
});
document.addEventListener('dragstart', e => { const tab = e.target.closest('[data-tab]'); if (tab) {
    lastDrag = Number(tab.dataset.tab);
    e.dataTransfer.setData('text/plain', String(lastDrag));
} });
document.addEventListener('dragover', e => { const tab = e.target.closest('[data-tab]'); if (tab) {
    e.preventDefault();
    tab.classList.add('drag-over');
} });
document.addEventListener('dragleave', e => e.target.closest('[data-tab]')?.classList.remove('drag-over'));
document.addEventListener('drop', e => { const tab = e.target.closest('[data-tab]'); if (tab && lastDrag) {
    e.preventDefault();
    tabs = moveTab(tabs, lastDrag, Number(tab.dataset.tab));
    lastDrag = null;
    renderTabs();
} });
render();
