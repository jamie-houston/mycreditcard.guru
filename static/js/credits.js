// Shared owned-card credit aggregation. Loaded in base.html's <head>, after
// utils.js — used by both profile.js (Benefits tab) and roadmap.js (builder)
// so the two views can't drift on the reconciling credit math.

async function fetchOwnedCardDetails(cardIds) {
    const cardDetails = {};
    for (const cardId of cardIds) {
        try {
            const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
            if (response.ok) {
                cardDetails[cardId] = await response.json();
            }
        } catch (error) {
            console.error(`Error fetching card ${cardId}:`, error);
        }
    }
    return cardDetails;
}

// Aggregates every credit carried by the given owned cards into one entry
// per catalog slug, resolving stackability the same way the engine's
// allocate_portfolio_credits does: stackable credits sum across cards,
// non-stackable credits count only once (whichever card carries the most
// value). effectiveAmount is 0 unless the user has opted into the credit
// via `preferences`.
function aggregateOwnedCredits(cardDetails, preferences) {
    const allCredits = {};

    Object.entries(cardDetails).forEach(([cardId, card]) => {
        if (!card.credits || card.credits.length === 0) return;
        card.credits.forEach(credit => {
            const creditType = credit.spending_credit;
            if (!creditType) return;
            const creditKey = creditType.slug;
            if (!allCredits[creditKey]) {
                allCredits[creditKey] = {
                    name: creditType.display_name || creditType.name,
                    slug: creditType.slug,
                    stackable: creditType.stackable !== false,
                    cards: []
                };
            }
            const annualValue = credit.annual_value || (parseFloat(credit.value || 0) * (credit.times_per_year || 1));
            allCredits[creditKey].cards.push({
                creditId: credit.id,
                cardId: cardId,
                name: card.name,
                value: credit.value,
                annualValue: annualValue,
                timesPerYear: credit.times_per_year,
                description: credit.description
            });
        });
    });

    return Object.fromEntries(Object.values(allCredits).map(credit => {
        const isUsed = preferences[credit.slug] === true;
        let winnerCardId = null;
        let rawAmount = 0;

        if (credit.stackable) {
            rawAmount = credit.cards.reduce((sum, c) => sum + c.annualValue, 0);
        } else {
            const winner = credit.cards.reduce(
                (best, c) => (c.annualValue > best.annualValue ? c : best), credit.cards[0]);
            winnerCardId = winner.cardId;
            rawAmount = winner.annualValue;
        }

        return [credit.slug, {
            ...credit,
            isUsed,
            winnerCardId,
            rawAmount,
            effectiveAmount: isUsed ? rawAmount : 0
        }];
    }));
}
