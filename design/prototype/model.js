// Prototype state only. Native integration will use Chromium models and services.
export function parseAddress(value) {
    const text = value.trim();
    if (!text)
        return null;
    if (text === 'trinol://newtab')
        return { title: 'New tab', url: text, kind: 'newtab' };
    if (/^[a-z][\w+.-]*:/i.test(text) && !/^https?:\/\//i.test(text))
        return { title: 'Address unavailable', url: text, kind: 'invalid' };
    if (!/^https?:\/\//i.test(text) && (/\s/.test(text) || !text.includes('.')))
        return { title: text, url: `https://search.example/?q=${encodeURIComponent(text)}`, kind: 'search' };
    try {
        const url = new URL(/^https?:\/\//i.test(text) ? text : `https://${text}`);
        if (!url.hostname || url.username || url.password)
            throw new Error('Invalid address');
        return { title: url.hostname, url: url.href, kind: url.protocol === 'https:' ? 'https' : 'http' };
    }
    catch {
        return { title: 'Address unavailable', url: text, kind: 'invalid' };
    }
}
export function moveTab(tabs, from, to) {
    const copy = [...tabs];
    const start = copy.findIndex(t => t.id === from), end = copy.findIndex(t => t.id === to);
    if (start < 0 || end < 0 || start === end)
        return copy;
    if (copy[start].pinned !== copy[end].pinned)
        return copy;
    copy.splice(end, 0, copy.splice(start, 1)[0]);
    return copy;
}
export function nextTabAfterClose(tabs, id, active) {
    const index = tabs.findIndex(t => t.id === id);
    const remaining = tabs.filter(t => t.id !== id);
    return { tabs: remaining, active: id === active ? remaining[Math.max(0, index - 1)]?.id : active };
}
export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
