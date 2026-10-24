/* Optional browser regression/capture runner. Requires an installed Playwright module
 * and a separate test-browser executable; never uses the Trinol native output. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const modulePath = process.env.ORBIT_PLAYWRIGHT_MODULE;
const executable = process.env.ORBIT_TEST_BROWSER;
if (!modulePath || !executable)
    throw Error('Set ORBIT_PLAYWRIGHT_MODULE and ORBIT_TEST_BROWSER to installed testing tools.');
const browserPath = fs.realpathSync(executable);
if (browserPath.split(path.sep).some(p => p === 'TrinolBuild' || p === 'out'))
    throw Error('Native Trinol output is forbidden.');
const { chromium } = createRequire(path.resolve(modulePath))('playwright');
const review = path.resolve(__dirname, '../review');
const captures = process.argv.includes('--capture');
const results = [], errors = [], remote = [];
let browser;
(async () => {
    browser = await chromium.launch({ headless: true, chromiumSandbox: true, executablePath: browserPath });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (new URL(r.url()).hostname !== '127.0.0.1')
        remote.push(r.url()); });
    const check = async (name, fn) => { await fn(); results.push(name); };
    const fresh = async () => page.goto('http://127.0.0.1:4173/prototype/');
    const capture = async (name) => { if (captures) {
        await page.locator('.toast.visible').waitFor({ state: 'hidden' });
        await page.screenshot({ path: path.join(review, name + '.png') });
    } };
    const click = name => page.getByRole('button', { name, exact: true }).first().click();
    const dismiss = async () => { if (await page.locator('dialog').evaluate(e => e.open))
        await page.keyboard.press('Escape'); };
    await fresh();
    await check('initial shell and demo labeling', async () => { assert.equal(await page.getByRole('tab').count(), 3); await page.getByRole('heading', { name: 'Where to next?' }).waitFor(); assert.match(await page.locator('footer').innerText(), /fictional/); });
    for (const [w, h] of [[1440, 900], [1920, 1080], [2560, 1440], [960, 760], [720, 800]]) {
        await page.setViewportSize({ width: w, height: h });
        await check(`layout ${w}x${h}`, async () => { assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); assert.equal(await page.locator('.page').evaluate(e => e.scrollWidth <= e.clientWidth), true); });
        await capture(`dark-${w}x${h}`);
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await click('Collapse sidebar');
    await capture('sidebar-collapsed');
    await check('compact sidebar expands again', async () => { await click('Expand sidebar'); assert.match(await page.locator('#sidebar').getAttribute('class'), /expanded/); });
    await click('Switch to light appearance');
    await capture('light-1440x900');
    await click('Switch to dark appearance');
    await check('new tab and close', async () => { await click('New tab'); assert.equal(await page.getByRole('tab').count(), 4); await page.locator('.tab.active .tab-close').click(); assert.equal(await page.getByRole('tab').count(), 3); });
    await check('tab switching', async () => { await page.getByRole('tab', { name: 'Atlas of the everyday' }).click(); await page.getByRole('heading', { name: 'Atlas of the everyday', exact: true }).waitFor(); await page.getByRole('tab', { name: 'New tab', exact: true }).click(); });
    await page.getByRole('combobox', { name: 'Address or search' }).focus();
    await page.getByRole('combobox', { name: 'Address or search' }).fill('atlas');
    await page.keyboard.press('ArrowDown');
    await capture('omnibox-focused');
    await check('omnibox keyboard selects open tab', async () => { await page.keyboard.press('Enter'); assert.equal(await page.getByRole('tab', { name: 'Atlas of the everyday' }).getAttribute('aria-selected'), 'true'); });
    await check('address navigation, reload/stop, back/forward', async () => { await page.locator('#address').fill('https://example.com'); await page.locator('#address-form').dispatchEvent('submit'); await page.getByRole('button', { name: 'Stop loading', exact: true }).waitFor(); await click('Stop loading'); await click('Back'); await page.getByRole('heading', { name: 'Atlas of the everyday', exact: true }).waitFor(); await click('Forward'); await page.getByRole('heading', { name: 'example.com', exact: true }).waitFor(); });
    await check('bookmark session state', async () => { await click('Bookmark this demo tab'); assert.equal(await page.getByRole('button', { name: 'Bookmark this demo tab' }).getAttribute('aria-pressed'), 'true'); await click('Bookmarks'); await page.locator('dialog').getByRole('button', { name: 'example.com' }).waitFor(); await dismiss(); });
    await check('command keyboard navigation and focus return', async () => { await click('Commands ⌘ K'); await page.getByRole('combobox', { name: 'Search commands or open tabs' }).fill('appearance'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter'); assert.equal(await page.locator('html').getAttribute('data-theme'), 'light'); await click('Switch to dark appearance'); });
    await page.getByRole('tab', { name: 'New tab', exact: true }).click();
    await click('Commands ⌘ K');
    await capture('command-palette');
    await check('modal focus is contained and Escape closes', async () => { for (let i = 0; i < 4; i++)
        await page.keyboard.press('Tab'); assert.equal(await page.evaluate(() => !!document.activeElement.closest('dialog')), true); await dismiss(); assert.equal(await page.locator('dialog').evaluate(e => e.open), false); });
    await check('demo services and empty states', async () => { for (const name of ['Tab overview', 'History', 'Downloads', 'Settings', 'Demo profile', 'Demo site information']) {
        await click(name);
        assert.equal(await page.locator('dialog').evaluate(e => e.open), true);
        await dismiss();
    } });
    await check('shortcut validation and addition', async () => { await click('Add shortcut'); await page.locator('#shortcut-name').fill('Research'); await page.locator('#shortcut-url').fill('javascript:alert(1)'); await click('Add demo shortcut'); assert.match(await page.locator('#shortcut-error').innerText(), /valid/); await page.locator('#shortcut-url').fill('https://research.example'); await click('Add demo shortcut'); await page.getByRole('button', { name: 'Open Research demo' }).waitFor(); });
    await check('pinning and keyboard tab reorder', async () => { await click('Browser menu'); await page.getByRole('button', { name: /Pin or unpin current tab/ }).click(); assert.equal(await page.locator('.tab.pinned').count(), 1); await click('Browser menu'); await page.getByRole('button', { name: /Pin or unpin current tab/ }).click(); await page.locator('.tab.active [role=tab]').focus(); await page.keyboard.press('Alt+Shift+ArrowRight'); assert.match(await page.locator('#toast').innerText(), /reordered/); });
    await check('audio indicator toggles', async () => { await click('Mute demo tab'); await page.getByRole('button', { name: 'Unmute demo tab' }).waitFor(); });
    await click('Switch to vertical tabs');
    await capture('vertical-tabs');
    await check('vertical tab model shares tabs and fits narrow window', async () => { await click('Collapse sidebar'); assert.doesNotMatch(await page.locator('#sidebar').getAttribute('class'), /expanded/); await click('Expand sidebar'); assert.equal(await page.getByRole('tab').count(), 3); await page.setViewportSize({ width: 720, height: 800 }); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); await page.setViewportSize({ width: 1440, height: 900 }); await click('Switch to horizontal tabs'); });
    await check('overflow with many tabs', async () => { for (let i = 0; i < 12; i++)
        await page.locator('.titlebar .new-tab').click(); assert.equal(await page.locator('#tabs').evaluate(e => e.scrollWidth > e.clientWidth), true); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); });
    await capture('tab-overflow');
    await fresh();
    for (const [name, file] of [['Loading', 'loading'], ['Certificate warning', 'certificate-warning'], ['Invalid address', 'invalid-address'], ['HTTPS URL', 'https-url'], ['Empty address field', 'empty-omnibox']]) {
        await click('Review states');
        await page.getByRole('button', { name, exact: true }).first().click();
        await check(`review state ${name}`, async () => { if (name === 'Loading')
            await page.getByRole('button', { name: 'Stop loading', exact: true }).waitFor(); if (name === 'Certificate warning')
            await page.getByRole('heading', { name: 'Connection warning' }).waitFor(); if (name === 'Invalid address')
            await page.getByRole('heading', { name: 'This address is unavailable' }).waitFor(); });
        await capture(file);
    }
    await check('semantic text color contrast in both themes', async () => {
        for (const theme of ['dark', 'light']) {
            const ratios = await page.evaluate(theme => {
                document.documentElement.dataset.theme = theme;
                const css = getComputedStyle(document.documentElement);
                const lum = hex => { const a = hex.trim().slice(1).match(/../g).map(c => parseInt(c, 16) / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4); return a[0] * .2126 + a[1] * .7152 + a[2] * .0722; };
                return [['--text', '--canvas'], ['--text', '--surface'], ['--muted', '--frame'], ['--muted', '--raised'], ['--accent', '--accent-wash'], ['--coral', '--raised']].map(([a, b]) => { const l = lum(css.getPropertyValue(a)), r = lum(css.getPropertyValue(b)); return { pair: a + '/' + b, ratio: (Math.max(l, r) + .05) / (Math.min(l, r) + .05) }; });
            }, theme);
            for (const r of ratios)
                assert.ok(r.ratio >= 4.5, `${theme} ${r.pair}: ${r.ratio}`);
        }
    });
    await fresh();
    await check('prototype keyboard shortcuts and tab focus', async () => {
        await page.locator('body').dispatchEvent('keydown', { key: 't', metaKey: true });
        assert.equal(await page.getByRole('tab').count(), 4);
        await page.locator('body').dispatchEvent('keydown', { key: 'w', metaKey: true });
        assert.equal(await page.getByRole('tab').count(), 3);
        assert.equal(await page.evaluate(() => document.activeElement.getAttribute('role')), 'tab');
        await page.locator('body').dispatchEvent('keydown', { key: 'k', metaKey: true });
        await page.locator('#command-search').waitFor();
        await dismiss();
        await page.locator('body').dispatchEvent('keydown', { key: 'l', metaKey: true });
        assert.equal(await page.locator('#address').evaluate(e => e === document.activeElement), true);
        await page.keyboard.press('Escape');
    });
    await check('reduced motion', async () => assert.equal(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), true));
    await check('no external requests or uncaught errors', async () => { assert.deepEqual(errors, []); assert.deepEqual(remote, []); });
    if (captures)
        fs.writeFileSync(path.join(review, 'verification.json'), JSON.stringify({ browser: await browser.version(), checks: results, screenshots: fs.readdirSync(review).filter(n => n.endsWith('.png')), uncaughtErrors: errors, externalRequests: remote }, null, 2) + '\n');
    console.log(`PASS: ${results.length} browser checks; ${captures ? 'review captures written' : 'no capture files changed'}.`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); });
