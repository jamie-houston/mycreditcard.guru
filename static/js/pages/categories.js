let allCategories = [];
let userCards = new Set();
let allCards = []; // Cache cards data to avoid repeated API calls

async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/cards/categories-with-rewards/`);
        const categories = await response.json();
        
        if (categories.error) {
            throw new Error(categories.error);
        }
        
        allCategories = categories;
        
        // Load cards data once for filtering
        const cardsResponse = await fetch(`${API_BASE}/cards/cards/`);
        const cardsData = await cardsResponse.json();
        allCards = cardsData.results || cardsData;
        
        // Load issuers for filter
        const issuersResponse = await fetch(`${API_BASE}/cards/issuers/`);
        const issuersData = await issuersResponse.json();
        const issuers = issuersData.results || issuersData;
        
        const issuerSelect = document.getElementById('filterIssuer');
        issuers.forEach(issuer => {
            const option = document.createElement('option');
            option.value = issuer.name;
            option.textContent = issuer.name;
            issuerSelect.appendChild(option);
        });
        
        // Load user's current cards (if any)
        await loadUserCards();
        
        await filterCategories();
        
    } catch (error) {
        console.error('Error loading categories:', error);
        document.getElementById('categoriesContainer').innerHTML = 
            '<div class="error">Error loading categories. Please try again.</div>';
    }
}

async function loadUserCards() {
    try {
        userCards = await loadOwnedCardIds();
    } catch (error) {
        console.error('Error loading user cards:', error);
    }
}

async function filterCategories() {
    // Ensure user cards are loaded first
    await loadUserCards();
    
    const ownershipFilter = document.getElementById('filterOwnership').value;
    const cardTypeFilter = document.getElementById('filterCardType').value;
    const issuerFilter = document.getElementById('filterIssuer').value;
    const rewardRateFilter = document.getElementById('filterRewardRate').value;
    const searchFilter = document.getElementById('searchCategories').value.toLowerCase();
    
    // Build category to cards mapping and user category IDs
    let userCategoryIds = new Set();
    let notOwnedCategoryIds = new Set();
    let categoryCardData = new Map(); // category.id -> array of cards
    
    allCards.forEach(card => {
        if (card.reward_categories) {
            card.reward_categories.forEach(rewardCat => {
                if (rewardCat.category && rewardCat.category.id) {
                    const categoryId = rewardCat.category.id;
                    if (!categoryCardData.has(categoryId)) {
                        categoryCardData.set(categoryId, []);
                    }
                    categoryCardData.get(categoryId).push(card);
                    
                    // For ownership filtering
                    if (userCards.has(card.id) || userCards.has(String(card.id)) || userCards.has(Number(card.id))) {
                        userCategoryIds.add(categoryId);
                    } else {
                        notOwnedCategoryIds.add(categoryId);
                    }
                }
            });
        }
    });
    
    let filteredCategories = allCategories.filter(category => {
        // Ownership filter
        if (ownershipFilter === 'owned' && !userCategoryIds.has(category.id)) {
            return false;
        }
        if (ownershipFilter === 'not_owned' && !notOwnedCategoryIds.has(category.id)) {
            return false;
        }
        
        // Card type filter
        if (cardTypeFilter) {
            const categoryCards = categoryCardData.get(category.id) || [];
            const hasCardType = categoryCards.some(card => card.card_type === cardTypeFilter);
            if (!hasCardType) {
                return false;
            }
        }
        
        // Issuer filter
        if (issuerFilter) {
            const categoryCards = categoryCardData.get(category.id) || [];
            const hasIssuer = categoryCards.some(card => card.issuer.name === issuerFilter);
            if (!hasIssuer) {
                return false;
            }
        }
        
        // Reward rate filter
        if (rewardRateFilter) {
            const minRate = parseFloat(rewardRateFilter);
            if (category.top_reward_rate < minRate) {
                return false;
            }
        }
        
        // Search filter
        if (searchFilter && !category.display_name.toLowerCase().includes(searchFilter)) {
            return false;
        }
        
        return true;
    });
    
    displayCategories(filteredCategories, categoryCardData, ownershipFilter, cardTypeFilter, issuerFilter, rewardRateFilter);
}

async function resetFilters() {
    document.getElementById('filterOwnership').value = 'all';
    document.getElementById('filterCardType').value = '';
    document.getElementById('filterIssuer').value = '';
    document.getElementById('filterRewardRate').value = '';
    document.getElementById('searchCategories').value = '';
    await filterCategories();
}

function displayCategories(categories, categoryCardData, ownershipFilter, cardTypeFilter, issuerFilter, rewardRateFilter) {
    const container = document.getElementById('categoriesContainer');
    
    if (categories.length === 0) {
        container.innerHTML = '<div class="error">No categories found.</div>';
        return;
    }
    
    const html = categories.map(category => {
        // Calculate filtered card count for this category
        const categoryCards = categoryCardData.get(category.id) || [];
        
        // Apply all filters to get the correct card count for this category
        const filteredCards = categoryCards.filter(card => {
            // Ownership filter
            const isOwned = userCards.has(card.id) || userCards.has(String(card.id)) || userCards.has(Number(card.id));
            if (ownershipFilter === 'owned' && !isOwned) return false;
            if (ownershipFilter === 'not_owned' && isOwned) return false;
            
            // Card type filter
            if (cardTypeFilter && card.card_type !== cardTypeFilter) return false;
            
            // Issuer filter
            if (issuerFilter && card.issuer.name !== issuerFilter) return false;
            
            // Reward rate filter
            if (rewardRateFilter) {
                const minRate = parseFloat(rewardRateFilter);
                const cardRewardRate = card.reward_categories.find(rc => rc.category.id === category.id)?.reward_rate || 0;
                if (parseFloat(cardRewardRate) < minRate) return false;
            }
            
            return true;
        });
        
        const filteredCardCount = filteredCards.length;
        
        // Calculate the top reward rate from filtered cards
        let topRewardRate = 0;
        if (filteredCards.length > 0) {
            topRewardRate = Math.max(...filteredCards.map(card => {
                const cardRewardCategory = card.reward_categories.find(rc => rc.category.id === category.id);
                return parseFloat(cardRewardCategory?.reward_rate || 0);
            }));
        }
        
        // Handle icon display
        let iconHtml = '';
        if (category.icon && category.icon.includes('fa-')) {
            iconHtml = `<i class="${category.icon}" style="font-size: 24px; color: #2563eb;"></i>`;
        } else if (category.icon) {
            iconHtml = `<span style="font-size: 24px;">${category.icon}</span>`;
        } else {
            // Default emoji icons
            const defaultIcons = {
                'groceries': '🛒',
                'dining': '🍽️',
                'travel': '✈️',
                'gas': '⛽',
                'online-shopping': '📦',
                'general': '💳',
                'entertainment': '🎬',
                'transportation': '🚗',
                'utilities': '⚡',
                'drugstores': '💊',
                'streaming': '📺',
                'home_improvement': '🔨',
                'office_supplies': '📄',
                'telecommunications': '📱',
                'shopping': '🛍️',
                'amazon': '📦',
                'other': '💰'
            };
            const defaultIcon = defaultIcons[category.slug] || '💳';
            iconHtml = `<span style="font-size: 24px;">${defaultIcon}</span>`;
        }
        
        return `
            <div class="category-box">
                <div class="category-icon">${iconHtml}</div>
                <div class="category-name">${category.display_name}</div>
                <div class="category-reward-info">
                    ${filteredCardCount > 0 ? 
                        `<div class="category-reward-rate">${topRewardRate}x</div>` : 
                        `<div class="category-reward-rate" style="color: #9ca3af;">No cards</div>`
                    }
                    <div class="category-card-count">${filteredCardCount} cards</div>
                </div>
                ${filteredCardCount > 0 ? 
                    `<a href="${buildCardsUrl(category.slug)}" class="category-link">View Cards</a>` :
                    `<div class="category-no-cards">No cards</div>`
                }
            </div>
        `;
    }).join('');
    
    container.innerHTML = `<div class="categories-grid">${html}</div>`;
}

function buildCardsUrl(categorySlug) {
    const ownershipFilter = document.getElementById('filterOwnership').value;
    const cardTypeFilter = document.getElementById('filterCardType').value;
    const issuerFilter = document.getElementById('filterIssuer').value;
    const rewardRateFilter = document.getElementById('filterRewardRate').value;
    
    const params = new URLSearchParams();
    params.set('category', categorySlug);
    
    // Add current filters to the URL
    if (ownershipFilter && ownershipFilter !== 'all') {
        params.set('ownership', ownershipFilter);
    }
    if (cardTypeFilter) {
        params.set('card_type', cardTypeFilter);
    }
    if (issuerFilter) {
        params.set('issuer', issuerFilter);
    }
    if (rewardRateFilter) {
        params.set('min_reward_rate', rewardRateFilter);
    }
    
    return `/cards/?${params.toString()}`;
}

// Add event listeners for filter changes
function setupFilterEventListeners() {
    document.getElementById('filterOwnership').addEventListener('change', () => {
        console.log('Ownership filter changed to:', document.getElementById('filterOwnership').value);
        filterCategories();
    });
    
    document.getElementById('filterCardType').addEventListener('change', () => {
        console.log('Card type filter changed to:', document.getElementById('filterCardType').value);
        filterCategories();
    });
    
    document.getElementById('filterIssuer').addEventListener('change', () => {
        console.log('Issuer filter changed to:', document.getElementById('filterIssuer').value);
        filterCategories();
    });
    
    document.getElementById('filterRewardRate').addEventListener('change', () => {
        console.log('Reward rate filter changed to:', document.getElementById('filterRewardRate').value);
        filterCategories();
    });
    
    document.getElementById('searchCategories').addEventListener('input', () => {
        console.log('Search filter changed to:', document.getElementById('searchCategories').value);
        filterCategories();
    });
}

// Load categories when page loads
loadCategories().then(() => {
    // Setup event listeners after page loads
    setupFilterEventListeners();
});

// Test function to manually add a card for testing
window.testAddCard = function(cardId) {
    console.log('Adding card', cardId, 'to user cards for testing');
    userCards.add(cardId);
    userCards.add(String(cardId));
    userCards.add(Number(cardId));
    console.log('User cards after adding:', [...userCards]);
    filterCategories();
};

// Test function to clear all cards
window.testClearCards = function() {
    console.log('Clearing all user cards');
    userCards.clear();
    filterCategories();
};

// Test function to add some sample cards for testing
window.testAddSampleCards = function() {
    console.log('Adding sample cards for testing...');
    // Add some common card IDs (these would be actual card IDs from your system)
    const sampleCardIds = [1, 2, 3, 4, 5, 10, 15, 20]; // You can adjust these
    sampleCardIds.forEach(id => {
        userCards.add(id);
        userCards.add(String(id));
        userCards.add(Number(id));
    });
    console.log('Sample cards added:', [...userCards]);
    filterCategories();
};

// Test function to show current filter state
window.testShowState = function() {
    console.log('=== CURRENT STATE ===');
    console.log('All categories:', allCategories.length);
    console.log('All cards:', allCards.length);
    console.log('User cards:', [...userCards]);
    console.log('Ownership filter:', document.getElementById('filterOwnership').value);
    filterCategories();
};

// Test function to manually set ownership filter to "owned"
window.testOwnedFilter = function() {
    console.log('Setting ownership filter to "owned"');
    document.getElementById('filterOwnership').value = 'owned';
    filterCategories();
};

// Test function to manually set ownership filter to "not_owned"
window.testNotOwnedFilter = function() {
    console.log('Setting ownership filter to "not_owned"');
    document.getElementById('filterOwnership').value = 'not_owned';
    filterCategories();
};
