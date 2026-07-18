// Plain-Node smoke test for the pure, DOM-free helpers in
// static/js/roadmap-results.js (Phase E timing display + summary math).
// No framework by design (see docs/README_TESTING.md) — just `assert` and
// `node`. Run with: node scripts/test_roadmap_results.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(
    path.join(__dirname, '..', 'static', 'js', 'roadmap-results.js'), 'utf8');

// The file also defines renderRoadmapResults(), which touches `document` —
// harmless to load into the sandbox since we never call it here.
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const { _roadmapTimingLabel, _roadmapFormatSigned, _roadmapBenefitsValue,
        _roadmapRewardsValue } = sandbox;

function test(name, fn) {
    try {
        fn();
        console.log(`ok - ${name}`);
    } catch (e) {
        console.error(`FAIL - ${name}`);
        console.error(e);
        process.exitCode = 1;
    }
}

// Construct dates from local y/m/d components (not an ISO string) so
// setMonth()/toLocaleString() — both local-time — behave the same
// regardless of the machine's timezone offset from UTC.
test('_roadmapTimingLabel: null/0 month is "Apply now"', () => {
    const base = new Date(2026, 6, 15); // Jul 15 2026
    assert.strictEqual(_roadmapTimingLabel(0, base), 'Apply now');
    assert.strictEqual(_roadmapTimingLabel(null, base), 'Apply now');
    assert.strictEqual(_roadmapTimingLabel(undefined, base), 'Apply now');
});

test('_roadmapTimingLabel: singular vs plural month wording', () => {
    const base = new Date(2026, 6, 15); // Jul 15 2026
    assert.strictEqual(_roadmapTimingLabel(1, base), 'Apply in ~1 month (Aug 2026)');
    assert.strictEqual(_roadmapTimingLabel(4, base), 'Apply in ~4 months (Nov 2026)');
});

test('_roadmapTimingLabel: month offset rolls the calendar year over', () => {
    const base = new Date(2026, 10, 1); // Nov 1 2026
    assert.strictEqual(_roadmapTimingLabel(3, base), 'Apply in ~3 months (Feb 2027)');
});

test('_roadmapFormatSigned: negative values use the minus-sign glyph', () => {
    assert.strictEqual(_roadmapFormatSigned(100), '$100');
    assert.strictEqual(_roadmapFormatSigned(-50), '−$50');
    assert.strictEqual(_roadmapFormatSigned(0), '$0');
});

test('_roadmapBenefitsValue / _roadmapRewardsValue partition rewards_breakdown', () => {
    const rec = {
        rewards_breakdown: [
            { type: 'category', category_rewards: 100 },
            { type: 'credit', category_rewards: 50 },
            { type: 'bonus_shift', category_rewards: -20 },
            { type: 'info', category_rewards: 0 },
        ]
    };
    assert.strictEqual(_roadmapBenefitsValue(rec), 50);
    assert.strictEqual(_roadmapRewardsValue(rec), 80); // 100 + (-20), info excluded
});

if (process.exitCode) {
    console.error('\nOne or more tests failed.');
} else {
    console.log('\nAll roadmap-results.js smoke tests passed.');
}
