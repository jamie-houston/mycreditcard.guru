// Shared alias-aware card search used by the profile add-card autocomplete,
// the cards list, and category detail pages.
//
// Matching is token-AND: every word the user types must match somewhere in
// "card name + issuer name", either literally or via an alias expansion.
// So "amex gold" matches "American Express Gold Card" and "csr" matches
// "Chase Sapphire Reserve".

const CARD_SEARCH_ALIASES = {
    // Issuers
    'amex': 'american express',
    'boa': 'bank of america',
    'bofa': 'bank of america',
    'wf': 'wells fargo',
    'cap1': 'capital one',
    'capone': 'capital one',
    'c1': 'capital one',
    'usb': 'us bank',
    // Common card shorthand (churner vocabulary)
    'csr': 'sapphire reserve',
    'csp': 'sapphire preferred',
    'cfu': 'freedom unlimited',
    'cff': 'freedom flex',
    'cic': 'ink business cash',
    'ciu': 'ink business unlimited',
    'cip': 'ink business preferred',
    'bcp': 'blue cash preferred',
    'bce': 'blue cash everyday',
    'bbp': 'blue business plus',
    'bbc': 'blue business cash',
    'vx': 'venture x',
    'swa': 'southwest',
    'woh': 'world of hyatt',
};

function cardMatchesQuery(card, query) {
    const haystack = (card.name + ' ' + ((card.issuer && card.issuer.name) || '')).toLowerCase();
    const tokens = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    return tokens.every(token => {
        if (haystack.includes(token)) return true;
        const expanded = CARD_SEARCH_ALIASES[token];
        return Boolean(expanded && haystack.includes(expanded));
    });
}
