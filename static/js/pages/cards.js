// Filter chips: convenience layer over the existing detailed <select> filters.
function toggleMoreFilters() {
    const panel = document.getElementById('moreFiltersPanel');
    const toggle = document.getElementById('moreFiltersToggle');
    const isHidden = panel.style.display === 'none';
    panel.style.display = isHidden ? 'block' : 'none';
    toggle.innerHTML = isHidden
        ? 'Fewer filters <span class="ico" style="font-size:14px;vertical-align:-2px;">expand_less</span>'
        : 'More filters <span class="ico" style="font-size:14px;vertical-align:-2px;">expand_more</span>';
}

function setActiveChip(id) {
    ['chip-all', 'chip-nofee', 'chip-travel', 'chip-issuer'].forEach(chipId => {
        document.getElementById(chipId).classList.toggle('active', chipId === id);
    });
}

function applyChipFilter(kind) {
    if (kind === 'all') {
        setActiveChip('chip-all');
        resetFilters();
        return;
    }
    if (kind === 'nofee') {
        setActiveChip('chip-nofee');
        document.getElementById('filterFee').value = '0';
        filterCards();
        return;
    }
    if (kind === 'travel') {
        setActiveChip('chip-travel');
        document.getElementById('filterRewardCategory').value = 'travel';
        filterCards();
        return;
    }
    if (kind === 'issuer') {
        setActiveChip('chip-issuer');
        document.getElementById('moreFiltersPanel').style.display = 'block';
        document.getElementById('filterIssuer').focus();
    }
}

// Fixed pagination issue: 2025-07-04-v3
let allCards = [];
let userCards = new Set();

async function loadCards() {
    try {
        // Load cards - all cards without pagination
        const cardsResponse = await fetch(`${API_BASE}/cards/cards/`, {
            cache: 'no-cache'
        });
        const cardsData = await cardsResponse.json();
        allCards = cardsData; // No pagination, so no 'results' wrapper
        
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
        
        // Load reward types for filter
        const rewardTypesResponse = await fetch(`${API_BASE}/cards/reward-types/`);
        const rewardTypesData = await rewardTypesResponse.json();
        const rewardTypes = rewardTypesData.results || rewardTypesData;
        
        const rewardTypeSelect = document.getElementById('filterRewardType');
        rewardTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.name;
            option.textContent = type.name;
            rewardTypeSelect.appendChild(option);
        });
        
        // Load spending categories for filter
        const categoriesResponse = await fetch(`${API_BASE}/cards/spending-categories/`);
        const categoriesData = await categoriesResponse.json();
        const categories = categoriesData.results || categoriesData;

        const categorySelect = document.getElementById('filterRewardCategory');
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.slug;
            option.textContent = category.display_name || category.name;
            categorySelect.appendChild(option);
        });

        // Load spending credits for filter
        const creditsResponse = await fetch(`${API_BASE}/cards/spending-credits/`);
        const creditsData = await creditsResponse.json();
        const credits = creditsData.results || creditsData;

        const creditSelect = document.getElementById('filterCredit');
        credits.forEach(credit => {
            const option = document.createElement('option');
            option.value = credit.slug;
            option.textContent = credit.display_name || credit.name;
            creditSelect.appendChild(option);
        });

        // Load user's current cards (if any)
        await loadUserCards();
        
        // Load cards with ownership data and display them
        await loadCardsWithOwnership();
        
        // Check for URL parameters to pre-select filters
        loadURLFilters();
        
    } catch (error) {
        console.error('Error loading cards:', error);
        document.getElementById('cardsContainer').innerHTML = 
            '<div class="error">Error loading cards. Please try again.</div>';
    }
}

async function loadUserCards() {
    try {
        userCards = await loadOwnedCardIds();

        // Also load detailed card information for display
        const userCardsDetails = await UserDataManager.getUserCardsDetails();
        window.userCardsDetails = userCardsDetails;
    } catch (error) {
        console.error('Error loading user cards:', error);
    }
}

async function saveUserCards() {
    try {
        await UserDataManager.saveCards([...userCards]);
    } catch (error) {
        console.error('Error saving user cards:', error);
    }
}

// Global variable definition used in click handlers
window.removeUserCard = removeUserCard;
window.saveCardOwnership = saveCardOwnership;
window.openCardOwnershipModal = openCardOwnershipModal;
window.closeCardOwnershipModal = closeCardOwnershipModal;

function loadURLFilters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Pre-select category filter if provided in URL
    const categoryParam = urlParams.get('category');
    if (categoryParam) {
        const categorySelect = document.getElementById('filterRewardCategory');
        categorySelect.value = categoryParam;
    }
    
    // Pre-select ownership filter if provided in URL
    const ownershipParam = urlParams.get('ownership');
    if (ownershipParam) {
        const ownershipSelect = document.getElementById('filterOwnership');
        if (ownershipParam === 'owned') {
            ownershipSelect.value = 'owned';
        } else if (ownershipParam === 'not_owned') {
            ownershipSelect.value = 'not_owned';
        }
    }
    
    // Pre-select card type filter if provided in URL
    const cardTypeParam = urlParams.get('card_type');
    if (cardTypeParam) {
        const cardTypeSelect = document.getElementById('filterCardType');
        cardTypeSelect.value = cardTypeParam;
    }
    
    // Pre-select issuer filter if provided in URL
    const issuerParam = urlParams.get('issuer');
    if (issuerParam) {
        const issuerSelect = document.getElementById('filterIssuer');
        issuerSelect.value = issuerParam;
    }
    
    // Pre-select minimum reward rate filter if provided in URL
    const minRewardRateParam = urlParams.get('min_reward_rate');
    if (minRewardRateParam) {
        const feeSelect = document.getElementById('filterFee');
        // Map reward rate to fee filter (this is a bit of a hack but works)
        if (minRewardRateParam === '2') {
            // For now, just show all fees when reward rate is filtered
            // You might want to add a specific reward rate filter to the cards page
        }
    }
    
    const rewardTypeParam = urlParams.get('reward_type');
    if (rewardTypeParam) {
        const rewardTypeSelect = document.getElementById('filterRewardType');
        rewardTypeSelect.value = rewardTypeParam;
    }
}

function filterCards() {
    const ownershipFilter = document.getElementById('filterOwnership').value;
    const cardTypeFilter = document.getElementById('filterCardType').value;
    const issuerFilter = document.getElementById('filterIssuer').value.toLowerCase();
    const rewardTypeFilter = document.getElementById('filterRewardType').value.toLowerCase();
    const rewardCategoryFilter = document.getElementById('filterRewardCategory').value;
    const creditFilter = document.getElementById('filterCredit').value;
    const feeFilter = document.getElementById('filterFee').value;
    const searchFilter = document.getElementById('searchCards').value.toLowerCase();

    console.log('Filtering with:', {
        issuerFilter,
        creditFilter,
        totalCards: allCards.length,
        uniqueIssuers: [...new Set(allCards.map(c => c.issuer.name.toLowerCase()))]
    });

    let filteredCards = allCards.filter(card => {
        // Ownership filter
        const hasCard = userCards.has(card.id);
        if (ownershipFilter === 'owned' && !hasCard) return false;
        if (ownershipFilter === 'not_owned' && hasCard) return false;
        // 'all' shows everything

        // Card type filter
        if (cardTypeFilter !== 'all' && card.card_type !== cardTypeFilter) {
            return false;
        }

        // Issuer filter
        if (issuerFilter && card.issuer.name.toLowerCase() !== issuerFilter) {
            return false;
        }

        // Reward type filter
        if (rewardTypeFilter && card.primary_reward_type.name.toLowerCase() !== rewardTypeFilter) {
            return false;
        }

        // Reward category filter
        if (rewardCategoryFilter && card.reward_categories) {
            const hasCategory = card.reward_categories.some(rewardCat =>
                rewardCat.category.slug === rewardCategoryFilter
            );
            if (!hasCategory) return false;
        }

        // Credit/Benefit filter
        if (creditFilter && card.credits) {
            const hasCredit = card.credits.some(credit =>
                credit.spending_credit && credit.spending_credit.slug === creditFilter
            );
            if (!hasCredit) return false;
        }

        // Fee filter
        if (feeFilter) {
            const fee = parseFloat(card.annual_fee) || 0;
            if (feeFilter === '0' && fee !== 0) return false;
            if (feeFilter === '1-95' && (fee < 1 || fee > 95)) return false;
            if (feeFilter === '96-250' && (fee < 96 || fee > 250)) return false;
            if (feeFilter === '251+' && fee < 251) return false;
        }

        // Search filter
        if (searchFilter && !cardMatchesQuery(card, searchFilter)) {
            return false;
        }

        return true;
    });
    
    displayCards(filteredCards);
}

function resetFilters() {
    document.getElementById('filterOwnership').value = 'all';
    document.getElementById('filterCardType').value = 'all';
    document.getElementById('filterIssuer').value = '';
    document.getElementById('filterRewardType').value = '';
    document.getElementById('filterRewardCategory').value = '';
    document.getElementById('filterCredit').value = '';
    document.getElementById('filterFee').value = '';
    document.getElementById('searchCards').value = '';
    if (typeof setActiveChip === 'function') setActiveChip('chip-all');
    filterCards();
}

// Issuer -> card-art gradient (per the Ledger redesign's 5 sample gradients),
// generic grey fallback for issuers outside that curated set.
const ISSUER_GRADIENTS = {
    'american express': 'linear-gradient(135deg,#D9B24B,#8A6A1F)',
    'amex': 'linear-gradient(135deg,#D9B24B,#8A6A1F)',
    'chase': 'linear-gradient(135deg,#3A5BA0,#1E2C4F)',
    'wells fargo': 'linear-gradient(135deg,#C0392B,#7A2018)',
    'capital one': 'linear-gradient(135deg,#2B2B2E,#0E0E10)',
    'citi': 'linear-gradient(135deg,#3A5BA0,#1E2C4F)',
    'citibank': 'linear-gradient(135deg,#3A5BA0,#1E2C4F)'
};
function issuerGradient(issuerName) {
    return ISSUER_GRADIENTS[(issuerName || '').toLowerCase()] || 'linear-gradient(135deg,#6E7B8B,#3A424D)';
}

// Network -> stylized inline SVG mark (not the real trademarked logos, just a
// recognizable color+wordmark stand-in). Falls back to the issuer gradient
// thumb when the network is missing or unrecognized.
const NETWORK_MARKS = {
    'visa': `
        <svg viewBox="0 0 46 30" xmlns="http://www.w3.org/2000/svg">
            <rect width="46" height="30" fill="#1A1F71"/>
            <text x="23" y="20" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-style="italic" font-size="13" fill="#ffffff">VISA</text>
        </svg>`,
    'mastercard': `
        <svg viewBox="0 0 46 30" xmlns="http://www.w3.org/2000/svg">
            <rect width="46" height="30" fill="#1B1B1B"/>
            <circle cx="19" cy="15" r="9" fill="#EB001B"/>
            <circle cx="27" cy="15" r="9" fill="#F79E1B" fill-opacity="0.9"/>
        </svg>`,
    'american express': `
        <svg viewBox="0 0 46 30" xmlns="http://www.w3.org/2000/svg">
            <rect width="46" height="30" fill="#006FCF"/>
            <text x="23" y="19" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="10.5" fill="#ffffff">AMEX</text>
        </svg>`,
    'amex': `
        <svg viewBox="0 0 46 30" xmlns="http://www.w3.org/2000/svg">
            <rect width="46" height="30" fill="#006FCF"/>
            <text x="23" y="19" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="10.5" fill="#ffffff">AMEX</text>
        </svg>`,
    'discover': `
        <svg viewBox="0 0 46 30" xmlns="http://www.w3.org/2000/svg">
            <rect width="46" height="30" fill="#1B1B1B"/>
            <circle cx="36" cy="21" r="10" fill="#FF6000"/>
            <text x="20" y="18" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="8" fill="#ffffff">DISC</text>
        </svg>`
};
function networkMark(networkName) {
    return NETWORK_MARKS[(networkName || '').toLowerCase()] || null;
}

function displayCards(cards) {
    const container = document.getElementById('cardsContainer');

    if (cards.length === 0) {
        container.innerHTML = '<div class="error">No cards found matching your criteria.</div>';
        return;
    }

    const html = cards.map(card => {
        const hasCard = card.hasCard || false;
        const signupBonus = card.signup_bonus_amount || 0;
        let rewardMultiplier = card.metadata?.reward_value_multiplier || 0.01;
        if (rewardMultiplier >= 0.5) rewardMultiplier /= 100.0;

        // Store card data globally for modal access (avoid JSON.stringify in HTML)
        window[`cardData_${card.id}`] = card.user_card || null;

        // Get user's nickname for this card if they own it
        let displayName = card.name;
        if (hasCard && card.user_card && card.user_card.nickname) {
            displayName = `${card.name} (${card.user_card.nickname})`;
        }

        // Get top reward categories for display
        const topCategories = card.reward_categories && card.reward_categories.length > 0 ?
            card.reward_categories
                .filter(cat => cat.is_active)
                .sort((a, b) => parseFloat(b.reward_rate) - parseFloat(a.reward_rate))
                .slice(0, 2)
                .map(cat => {
                    const categoryName = (cat.category && cat.category.display_name) ||
                                       (cat.category && cat.category.name) ||
                                       'Unknown';
                    const rate = parseFloat(cat.reward_rate || 0);
                    return `${rate}x ${categoryName}`;
                })
                .join(', ') : 'General rewards';

        const mark = networkMark(card.metadata?.network);
        const thumbHtml = mark
            ? `<div class="card-box-thumb network">${mark}</div>`
            : `<div class="card-box-thumb" style="background: ${issuerGradient(card.issuer.name)};"></div>`;

        return `
            <div class="card-box ${hasCard ? 'owned' : ''}">
                <div style="display:flex; align-items:center; gap:12px; cursor:pointer;" onclick="openCardModal(${card.id})">
                    ${thumbHtml}
                    <div class="card-box-body">
                        <div class="card-issuer">${card.issuer.name} · ${topCategories}</div>
                        <div class="card-name">${displayName}</div>
                    </div>
                    <div class="card-box-side">
                        <div class="card-box-fee">$${card.annual_fee}</div>
                        ${hasCard ? '<div class="card-box-owned-chip">OWNED</div>' : ''}
                    </div>
                </div>

                <div class="card-details-expandable" style="display:block;">
                    <div class="card-key-info">
                        <div class="card-annual-fee">
                            <strong>Annual Fee:</strong> $${card.annual_fee}
                        </div>

                        ${signupBonus ?
                            `<div class="card-signup-bonus">
                                <strong>Bonus:</strong> ${signupBonus.toLocaleString()} ${card.signup_bonus_type ? card.signup_bonus_type.name : 'points'}
                            </div>` :
                            '<div class="card-signup-bonus">No signup bonus</div>'
                        }

                        <div class="card-reward-type">
                            <span class="badge ${card.primary_reward_type.name.toLowerCase()}">${card.primary_reward_type.name}</span>
                        </div>

                        <div class="card-reward-highlight">
                            ${(rewardMultiplier * 100).toFixed(1)}¢ per point
                        </div>
                    </div>

                    <div class="card-actions">
                        ${hasCard ? `
                            <button
                                onclick="event.stopPropagation(); openCardOwnershipModal(${card.id}, window.cardData_${card.id}, '${card.card_type}')"
                                class="secondary"
                            >
                                Edit card details
                            </button>
                            <button
                                onclick="event.stopPropagation(); removeUserCard('${card.user_card ? card.user_card.id : 'null'}', ${card.id})"
                                class="danger"
                            >
                                Remove from my cards
                            </button>
                        ` : `
                            <button
                                onclick="event.stopPropagation(); openCardOwnershipModal(${card.id}, null, '${card.card_type}')"
                                class="success"
                            >
                                I have this card
                            </button>
                        `}
                        ${card.apply_url ? `
                            <button
                                onclick="event.stopPropagation(); window.open('${card.apply_url}', '_blank')"
                                class="apply-btn"
                            >
                                Apply Now
                            </button>
                        ` : ''}
                        <button
                            onclick="event.stopPropagation(); openCardModal(${card.id})"
                            class="primary"
                        >
                            View Details
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `<div class="cards-grid">${html}</div>`;
}



async function removeUserCard(userCardId, cardId = null) {
    if (!userCardId || userCardId === 'null') {
        showNotification('Invalid card ID', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to remove this card from your collection?')) {
        return;
    }
    
    try {
        // Handle local storage cards (userCardId like 'local_6')
        if (userCardId.toString().startsWith('local_') || !isAuthenticated) {
            // Remove from local storage
            const localCards = LocalStorage.getCards();
            const localCardDetails = LocalStorage.getCardDetails();
            
            // Extract the real card ID from the userCardId or use provided cardId
            let realCardId = cardId;
            if (!realCardId && userCardId.toString().startsWith('local_')) {
                // Try to find the card ID by matching with the local storage
                const cardElements = document.querySelectorAll('[data-card-id]');
                for (const element of cardElements) {
                    const elementCardId = element.getAttribute('data-card-id');
                    const elementUserCardId = element.getAttribute('data-user-card-id');
                    if (elementUserCardId === userCardId.toString()) {
                        realCardId = parseInt(elementCardId);
                        break;
                    }
                }
            }
            
            if (realCardId) {
                // Remove from local storage arrays
                const updatedCards = localCards.filter(id => id !== parseInt(realCardId));
                LocalStorage.setCards(updatedCards);
                
                // Remove from local details
                delete localCardDetails[realCardId];
                LocalStorage.setCardDetails(localCardDetails);
                
                showNotification('Card removed from your local collection!', 'success');
                loadCardsWithOwnership();
                return;
            }
        }
        
        // Handle server-side cards for authenticated users
        if (isAuthenticated) {
            const response = await fetch(`${API_BASE}/cards/user-cards/${userCardId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                showNotification(data.message || 'Card removed successfully', 'success');
                
                // Reload cards to reflect changes
                loadCardsWithOwnership();
            } else {
                const errorData = await response.json();
                showNotification(errorData.error || 'Failed to remove card', 'error');
            }
        } else {
            showNotification('Please log in to remove cards from your account', 'error');
        }
        
    } catch (error) {
        console.error('Error removing card:', error);
        showNotification('Error removing card. Please try again.', 'error');
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('cardOwnershipModal');
    if (event.target === modal) {
        closeCardOwnershipModal();
    }
}

// Load cards with ownership data
async function loadCardsWithOwnership() {
    try {
        // Fetch all cards
        const cardsResponse = await fetch(`${API_BASE}/cards/cards/`);
        const cards = await cardsResponse.json();
        
        // Fetch user's owned cards if authenticated
        let userCards = [];
        if (isAuthenticated) {
            try {
                const userCardsResponse = await fetch(`${API_BASE}/cards/user-cards/`);
                if (userCardsResponse.ok) {
                    userCards = await userCardsResponse.json();
                }
            } catch (error) {
                console.log('Error loading user cards:', error);
            }
        } else {
            // For unauthenticated users, try to get cards from local storage
            try {
                const localCardIds = LocalStorage.getCards();
                const localCardDetails = LocalStorage.getCardDetails();
                
                // Convert local storage data to match expected format
                for (const cardId of localCardIds) {
                    try {
                        const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                        if (response.ok) {
                            const cardData = await response.json();
                            const details = localCardDetails[cardId] || {};
                            userCards.push({
                                id: `local_${cardId}`,
                                card: cardData,
                                nickname: details.nickname || '',
                                opened_date: details.opened_date || null,
                                closed_date: null,
                                notes: details.notes || '',
                                is_local: true
                            });
                        }
                    } catch (error) {
                        console.error(`Error fetching card ${cardId}:`, error);
                    }
                }
            } catch (error) {
                console.log('Error loading local cards:', error);
            }
        }
        
        // Create a map of owned cards by card ID
        const ownedCardsMap = {};
        userCards.forEach(userCard => {
            ownedCardsMap[userCard.card.id] = userCard;
        });
        
        // Add ownership data to cards
        const cardsWithOwnership = cards.map(card => ({
            ...card,
            user_card: ownedCardsMap[card.id] || null,
            hasCard: !!ownedCardsMap[card.id]
        }));
        
        // Update allCards for filtering
        allCards = cardsWithOwnership;

        // Render cards, respecting any active filters
        filterCards();
        
    } catch (error) {
        console.error('Error loading cards:', error);
        showNotification('Error loading cards. Please refresh the page.', 'error');
    }
}

// Load cards when page loads
loadCards();
