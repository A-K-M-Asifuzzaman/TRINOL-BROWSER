// Original 20 × 20 line icons; consistent 1.6-unit stroke, no third-party assets.
const paths = {
    plus: 'M10 4v12M4 10h12', close: 'm5 5 10 10M15 5 5 15', back: 'm11 4-6 6 6 6M5 10h11',
    forward: 'm9 4 6 6-6 6M15 10H4', reload: 'M15.5 6a6 6 0 1 0 .5 7M16 3v4h-4',
    stop: 'M5 5h10v10H5z', search: 'M9 3a6 6 0 1 0 0 12A6 6 0 0 0 9 3Zm4.5 10.5L18 18',
    site: 'M4 6h12M4 14h12M8 4v4M12 12v4', star: 'm10 2 2.5 5.2 5.5.8-4 4 .9 5.5-4.9-2.6-4.9 2.6L6 12 2 8l5.5-.8z',
    download: 'M10 2v10m-4-4 4 4 4-4M4 13v4h12v-4', menu: 'M4 5h12M4 10h12M4 15h12',
    sidebar: 'M3 3h14v14H3zM7 3v14', tabs: 'M6 3h11v11M3 6h11v11H3z',
    history: 'M3 9a7 7 0 1 1 1 5M3 4v5h5M10 6v5l3 2', settings: 'm10 2 2 2 3 .5.5 3 2 2-2 2-.5 3-3 .5-2 2-2-2-3-.5-.5-3-2-2 2-2 .5-3 3-.5zM10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
    chevron: 'm7 5 5 5-5 5', sun: 'M10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8M10 1v2M10 17v2M1 10h2M17 10h2M3 3l2 2M15 15l2 2M3 17l2-2M15 5l2-2',
    moon: 'M16 12A7 7 0 0 1 8 3a7 7 0 1 0 8 9Z', command: 'M6 6h8v8H6zM6 6H4a2 2 0 1 1 2-2v2Zm8 0V4a2 2 0 1 1 2 2h-2Zm0 8h2a2 2 0 1 1-2 2v-2Zm-8 0v2a2 2 0 1 1-2-2h2Z',
    pin: 'm7 3 6 0-1 5 3 3H5l3-3-1-5ZM10 11v7', audio: 'm3 8 4 0 4-4v12l-4-4H3zM14 7a4 4 0 0 1 0 6',
    globe: 'M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16ZM2 10h16M10 2c-5 5-5 11 0 16 5-5 5-11 0-16',
    arrow: 'M4 10h12m-5-5 5 5-5 5', check: 'm4 10 4 4 8-8', warning: 'm10 3 8 14H2zM10 7v4M10 14v.5',
    grid: 'M3 3h5v5H3zM12 3h5v5h-5zM3 12h5v5H3zM12 12h5v5h-5z', folder: 'M2 5h6l2 2h8v10H2z',
};
export function icon(name) { return `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.globe}"/></svg>`; }
export const mark = '<svg class="orbit-mark" viewBox="0 0 64 64" fill="none" aria-hidden="true"><path d="M14 44 31 10l19 35M22 31h20M10 45c11 7 34 2 43-10M13 48c13 8 36 1 42-11" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="52" cy="32" r="3.5" fill="var(--cyan)"/></svg>';
