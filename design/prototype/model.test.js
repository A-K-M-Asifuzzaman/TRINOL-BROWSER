import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseAddress, moveTab, nextTabAfterClose, escapeHTML } from './model.js';
test('addresses normalize HTTP(S) without fetching or accepting executable schemes', () => {
    assert.equal(parseAddress('example.com').url, 'https://example.com/');
    assert.equal(parseAddress('hello world').kind, 'search');
    assert.equal(parseAddress('javascript:alert(1)').kind, 'invalid');
    assert.equal(parseAddress('file:///private/profile').kind, 'invalid');
    assert.equal(parseAddress('https://user:secret@example.com').kind, 'invalid');
    assert.equal(parseAddress('https://').kind, 'invalid');
    assert.equal(parseAddress(''), null);
});
test('input data cannot inject markup', () => assert.equal(escapeHTML('<img src="x">'), '&lt;img src=&quot;x&quot;&gt;'));
test('reorder preserves input and pinned boundary', () => {
    const tabs = [{ id: 1, pinned: true }, { id: 2, pinned: false }, { id: 3, pinned: false }];
    assert.deepEqual(moveTab(tabs, 2, 3).map(t => t.id), [1, 3, 2]);
    assert.deepEqual(moveTab(tabs, 1, 3), tabs);
    assert.deepEqual(moveTab(tabs, 9, 3), tabs);
    assert.deepEqual(tabs.map(t => t.id), [1, 2, 3]);
});
test('closing selects a neighbor without disturbing another active tab', () => {
    const tabs = [{ id: 1 }, { id: 2 }, { id: 3 }];
    assert.equal(nextTabAfterClose(tabs, 2, 2).active, 1);
    assert.equal(nextTabAfterClose(tabs, 1, 3).active, 3);
    assert.equal(nextTabAfterClose([{ id: 1 }], 1, 1).active, undefined);
});
