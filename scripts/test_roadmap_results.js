// Plain-Node smoke test for the pure, DOM-free helpers in
// static/js/roadmap-results.js (Phase E timing display + summary math).
// No framework by design (see docs/README_TESTING.md) — just `assert` and
// `node`. Run with: node scripts/test_roadmap_results.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const utilsSource = fs.readFileSync(
    path.join(__dirname, '..', 'static', 'js', 'utils.js'), 'utf8');
const source = fs.readFileSync(
    path.join(__dirname, '..', 'static', 'js', 'roadmap-results.js'), 'utf8');

// The file also defines renderRoadmapResults(), which touches `document` —
// harmless to load into the sandbox since we never call it here. utils.js
// is loaded first since roadmap-results.js depends on its escapeHtml().
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(utilsSource, sandbox);
vm.runInContext(source, sandbox);

const { _roadmapTimingLabel, _roadmapFormatSigned, _roadmapBenefitsValue,
        _roadmapRewardsValue, _roadmapBonusShiftAggregate,
        _roadmapApplyAsLabel, escapeHtml,
        _roadmapCategoryMatrix, _roadmapCategoryMatrixHtml,
        _roadmapValueOverTime, _roadmapValueOverTimeHtml,
        _roadmapRedemptionHtml, _roadmapExpenseLineText,
        _roadmapExpensePanelHtml } = sandbox;

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

test('_roadmapBonusShiftAggregate: no shifts renders nothing', () => {
    assert.strictEqual(_roadmapBonusShiftAggregate([]), null);
    assert.strictEqual(_roadmapBonusShiftAggregate(undefined), null);
});

test('_roadmapBonusShiftAggregate: net-zero shifts render nothing', () => {
    const shifts = [
        { name: 'Groceries from Card A', value: 22, calculation: '22 earned' },
        { name: 'Gas from Card B', value: -22, calculation: '22 forgone' },
    ];
    assert.strictEqual(_roadmapBonusShiftAggregate(shifts), null);
});

test('_roadmapBonusShiftAggregate: non-zero shifts produce one aggregated row', () => {
    const shifts = [
        { name: 'Groceries from Card A', value: -4.65, calculation: 'calc A' },
        { name: 'Gas from Card B', value: -33.85, calculation: 'calc B' },
    ];
    const result = _roadmapBonusShiftAggregate(shifts);
    assert.ok(result);
    assert.strictEqual(Math.round(result.total), -38);
    assert.strictEqual(result.title, 'calc A\ncalc B');
});

test('_roadmapApplyAsLabel: absent apply_as renders nothing', () => {
    assert.strictEqual(_roadmapApplyAsLabel({}), '');
    assert.strictEqual(_roadmapApplyAsLabel({ apply_as: null }), '');
});

test('_roadmapApplyAsLabel: present apply_as renders "as {name}"', () => {
    const rec = { apply_as: { entity_id: 2, name: 'Sam', kind: 'personal' } };
    assert.strictEqual(_roadmapApplyAsLabel(rec), ' · as Sam');
});

test('_roadmapApplyAsLabel: entity name is HTML-escaped', () => {
    const rec = { apply_as: { entity_id: 3, name: '<script>alert(1)</script>', kind: 'personal' } };
    assert.strictEqual(
        _roadmapApplyAsLabel(rec),
        ' · as &lt;script&gt;alert(1)&lt;/script&gt;');
});

test('escapeHtml: escapes the standard HTML-sensitive characters', () => {
    assert.strictEqual(
        escapeHtml(`<a href="x">it's & "fun"</a>`),
        '&lt;a href=&quot;x&quot;&gt;it&#39;s &amp; &quot;fun&quot;&lt;/a&gt;');
    assert.strictEqual(escapeHtml(null), '');
    assert.strictEqual(escapeHtml(undefined), '');
});

test('_roadmapCategoryMatrix: groups allocation entries by category, sums rewards', () => {
    const allocation = [
        { category_slug: 'dining', category_name: 'Dining', card_id: 1, card_name: 'Card A', rate: 3.0, annual_spend: 6000, annual_rewards: 180, is_base_rate: false, uncovered: false },
        { category_slug: 'dining', category_name: 'Dining', card_id: 2, card_name: 'Card B', rate: 1.0, annual_spend: 500, annual_rewards: 5, is_base_rate: true, uncovered: false },
        { category_slug: 'travel', category_name: 'Travel', card_id: null, card_name: null, rate: 0.0, annual_spend: 1000, annual_rewards: 0, is_base_rate: false, uncovered: true },
    ];
    const matrix = _roadmapCategoryMatrix(allocation);
    assert.strictEqual(matrix.length, 2);
    assert.strictEqual(matrix[0].slug, 'dining');
    assert.strictEqual(matrix[0].rows.length, 2);
    assert.strictEqual(matrix[0].total_rewards, 185);
    assert.strictEqual(matrix[1].slug, 'travel');
    assert.strictEqual(matrix[1].rows[0].uncovered, true);
    assert.strictEqual(matrix[1].total_rewards, 0);
});

test('_roadmapCategoryMatrix: empty/missing allocation renders no groups', () => {
    assert.strictEqual(_roadmapCategoryMatrix([]).length, 0);
    assert.strictEqual(_roadmapCategoryMatrix(undefined).length, 0);
});

test('_roadmapCategoryMatrixHtml: empty matrix renders nothing', () => {
    assert.strictEqual(_roadmapCategoryMatrixHtml([]), '');
});

test('_roadmapCategoryMatrixHtml: non-empty matrix renders the section + card name', () => {
    const matrix = _roadmapCategoryMatrix([
        { category_slug: 'dining', category_name: 'Dining', card_id: 1, card_name: 'Card A', rate: 3.0, annual_spend: 6000, annual_rewards: 180, is_base_rate: false, uncovered: false },
    ]);
    const html = _roadmapCategoryMatrixHtml(matrix);
    assert.ok(html.includes('Cards by category'));
    assert.ok(html.includes('Card A'));
    assert.ok(html.includes('Dining'));
});

test('_roadmapValueOverTime: sums only keep/apply recs, excludes cancel', () => {
    const recs = [
        { action: 'apply', first_year_value: 300, ongoing_value: 100 },
        { action: 'keep', first_year_value: 80, ongoing_value: 80 },
        { action: 'cancel', first_year_value: -95, ongoing_value: -95 },
    ];
    const split = _roadmapValueOverTime(recs);
    assert.strictEqual(split.first_year, 380);
    assert.strictEqual(split.ongoing, 180);
    assert.strictEqual(split.first_year_extras, 200);
});

test('_roadmapValueOverTimeHtml: near-equal first-year/ongoing renders nothing', () => {
    assert.strictEqual(_roadmapValueOverTimeHtml({ first_year: 100, ongoing: 100, first_year_extras: 0 }), '');
    assert.strictEqual(_roadmapValueOverTimeHtml({ first_year: 100.4, ongoing: 100, first_year_extras: 0.4 }), '');
});

test('_roadmapValueOverTimeHtml: a real gap renders the this-year/ongoing panel', () => {
    const html = _roadmapValueOverTimeHtml({ first_year: 380, ongoing: 180, first_year_extras: 200 });
    assert.ok(html.includes('This year'));
    assert.ok(html.includes('Every year after'));
    assert.ok(html.includes('$380'));
    assert.ok(html.includes('$180'));
});

test('_roadmapRedemptionHtml: missing redemption data renders nothing', () => {
    assert.strictEqual(_roadmapRedemptionHtml({ card: {} }), '');
    assert.strictEqual(_roadmapRedemptionHtml({ card: { redemption: null } }), '');
    assert.strictEqual(_roadmapRedemptionHtml({}), '');
});

test('_roadmapRedemptionHtml: curated program renders portal link, rate, and partners', () => {
    const rec = {
        card: {
            redemption: {
                program_label: 'Chase Ultimate Rewards',
                portal_url: 'https://www.chase.com/personal/credit-cards/ultimate-rewards',
                value_per_point: 0.015,
                transfer_partners: ['United MileagePlus', 'World of Hyatt'],
                note: 'Best value transferring to airline/hotel partners.',
            },
        },
    };
    const html = _roadmapRedemptionHtml(rec);
    assert.ok(html.includes('Chase Ultimate Rewards'));
    assert.ok(html.includes('1.5¢/pt'));
    assert.ok(html.includes('United MileagePlus'));
    assert.ok(html.includes('https://www.chase.com/personal/credit-cards/ultimate-rewards'));
});

test('_roadmapRedemptionHtml: generic fallback has no program label or partners', () => {
    const rec = { card: { redemption: { program_label: null, portal_url: null, value_per_point: null, transfer_partners: [], note: 'Redeem as a statement credit or direct deposit.' } } };
    const html = _roadmapRedemptionHtml(rec);
    assert.ok(html.includes('Redeem as a statement credit or direct deposit.'));
    assert.ok(!html.includes('Transfer partners'));
});

test('_roadmapRedemptionHtml: issuer-supplied note text is HTML-escaped', () => {
    const rec = { card: { redemption: { program_label: null, portal_url: null, value_per_point: null, transfer_partners: [], note: '<script>alert(1)</script>' } } };
    const html = _roadmapRedemptionHtml(rec);
    assert.ok(!html.includes('<script>alert(1)</script>'));
    assert.ok(html.includes('&lt;script&gt;'));
});

test('_roadmapExpenseLineText: sums bonus + rewards − fee to the shown total', () => {
    const item = { signup_bonus_value: 900, category_rewards: 200, effective_annual_fee: 95, value_for_expense: 1005 };
    assert.strictEqual(_roadmapExpenseLineText(item), 'bonus $900 + rewards $200 − $95 fee = $1005');
});

test('_roadmapExpenseLineText: no bonus and no fee omits both segments', () => {
    const item = { signup_bonus_value: 0, category_rewards: 40, effective_annual_fee: 0, value_for_expense: 40 };
    assert.strictEqual(_roadmapExpenseLineText(item), 'rewards $40 = $40');
});

test('_roadmapExpensePanelHtml: absent expense_recommendation renders nothing', () => {
    assert.strictEqual(_roadmapExpensePanelHtml(null), '');
    assert.strictEqual(_roadmapExpensePanelHtml(undefined), '');
});

test('_roadmapExpensePanelHtml: renders amount, category, apply list and best-owned card', () => {
    const expenseReco = {
        amount: 10000,
        category_slug: 'travel',
        category_name: 'Travel',
        apply: [
            { card: { id: 1, name: 'Travel Card' }, action: 'apply',
              signup_bonus_value: 900, category_rewards: 200, effective_annual_fee: 95,
              value_for_expense: 1005, reward_rate: 3, bonus_note: 'Your $10,000 purchase covers the $4,000 minimum spend in 3 months' },
        ],
        best_owned: { card: { id: 2, name: 'Existing Card' }, action: 'keep',
              signup_bonus_value: 0, category_rewards: 150, effective_annual_fee: 0,
              value_for_expense: 150, reward_rate: 1.5, bonus_note: '' },
    };
    const html = _roadmapExpensePanelHtml(expenseReco);
    assert.ok(html.includes('$10,000'));
    assert.ok(html.includes('Travel'));
    assert.ok(html.includes('Travel Card'));
    assert.ok(html.includes('minimum spend'));
    assert.ok(html.includes('Existing Card'));
    assert.ok(html.includes('Or use a card you already have'));
});

test('_roadmapExpensePanelHtml: no owned card omits the "already have" section', () => {
    const html = _roadmapExpensePanelHtml({
        amount: 500, category_slug: null, category_name: 'General purchase',
        apply: [], best_owned: null,
    });
    assert.ok(!html.includes('Or use a card you already have'));
    assert.ok(html.includes('No eligible new-card matches'));
});

if (process.exitCode) {
    console.error('\nOne or more tests failed.');
} else {
    console.log('\nAll roadmap-results.js smoke tests passed.');
}
