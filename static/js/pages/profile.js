// New Global State for redesign
let _activeProfileTab = 'cards';
let _profileFilterMode = 'personal';
let _expandedCards = {};
let _recommendationsMap = {};

window.switchProfileTab = function(tabId) {
    _activeProfileTab = tabId;
    
    // Update active tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById('tabBtn' + tabId.charAt(0).toUpperCase() + tabId.slice(1));
    if (activeBtn) activeBtn.classList.add('active');
    
    // Update active content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    const activeContent = document.getElementById('tabContent' + tabId.charAt(0).toUpperCase() + tabId.slice(1));
    if (activeContent) activeContent.classList.add('active');
};

window.setProfileFilterMode = function(mode) {
    _profileFilterMode = mode;
    
    // Update active button state
    document.querySelectorAll('.segment-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById('btnProfile' + mode.charAt(0).toUpperCase() + mode.slice(1));
    if (activeBtn) activeBtn.classList.add('active');
    
    // Re-render holdings list
    renderCardCollectionTable();
};

window.toggleSettingsPanel = function() {
    const panel = document.getElementById('settingsPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
};

window.toggleSpendingProfileSection = function() {
    const wrapper = document.getElementById('spendingProfileWrapper');
    const chevron = document.getElementById('spendingProfileChevron');
    if (wrapper) {
        const isHidden = wrapper.style.display === 'none';
        wrapper.style.display = isHidden ? 'block' : 'none';
        if (chevron) {
            chevron.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
        }
    }
};

window.toggleCardRowExpansion = function(cardId) {
    _expandedCards[cardId] = !_expandedCards[cardId];
    renderCardCollectionTable();
};

window.handlePrivacyRadioClick = function(value) {
    updatePrivacySetting(value);
};

window.filterCards = function() {
    loadProfileData();
};

function getIssuerStyle(issuerName) {
    const name = (issuerName || '').toLowerCase();
    if (name.includes('chase')) {
        return { initials: 'CS', bg: 'oklch(45% 0.14 260)' };
    } else if (name.includes('american express') || name.includes('amex')) {
        return { initials: 'AX', bg: 'oklch(58% 0.14 85)' };
    } else if (name.includes('citi')) {
        return { initials: 'CI', bg: 'oklch(48% 0.03 250)' };
    } else if (name.includes('capital one') || name.includes('capitol one')) {
        return { initials: 'CO', bg: 'oklch(50% 0.13 25)' };
    } else if (name.includes('discover')) {
        return { initials: 'DI', bg: 'oklch(48% 0.15 45)' };
    } else if (name.includes('bank of america') || name.includes('bofa')) {
        return { initials: 'BA', bg: 'oklch(45% 0.14 15)' };
    } else if (name.includes('wellsfargo') || name.includes('wells fargo')) {
        return { initials: 'WF', bg: 'oklch(52% 0.15 75)' };
    }
    return { initials: (issuerName || 'CG').substring(0, 2).toUpperCase(), bg: 'oklch(55% 0.12 175)' };
}

function getCardInitialsAndColor(cardName, issuerName) {
    const cName = (cardName || '').toLowerCase();
    if (cName.includes('sapphire')) return { initials: 'CS', bg: 'oklch(45% 0.14 260)' };
    if (cName.includes('freedom unlimited')) return { initials: 'FU', bg: 'oklch(45% 0.14 260)' };
    if (cName.includes('gold')) return { initials: 'AG', bg: 'oklch(58% 0.14 85)' };
    if (cName.includes('platinum')) return { initials: 'AP', bg: 'oklch(62% 0.02 250)' };
    if (cName.includes('double cash')) return { initials: 'DC', bg: 'oklch(48% 0.03 250)' };
    if (cName.includes('venture x')) return { initials: 'VX', bg: 'oklch(50% 0.13 25)' };
    
    return getIssuerStyle(issuerName);
}

window.windowEditCardDetails = async function(cardId, cardName, cardType) {
    currentModalCard = { id: cardId, name: cardName, card_type: cardType };
    await openEditCardDetailsModal();
};

window.removeCardOwnership = async function(cardId, cardName, buttonEl) {
    if (!confirm(`Are you sure you want to remove ${cardName || 'this card'}?`)) {
        return;
    }
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.textContent = '⏳ ...';
    }
    try {
        if (isAuthenticated) {
            const response = await fetch(`${API_BASE}/cards/user-cards/toggle/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ card_id: cardId, action: 'remove' })
            });
            if (!response.ok) {
                throw new Error('Failed to remove card');
            }
        } else {
            const cards = (await UserDataManager.getCards()).filter(id => id !== cardId);
            await UserDataManager.saveCards(cards);
        }
        showNotification(`Removed ${cardName || 'card'}`, 'success');
        await loadProfileData();
    } catch (error) {
        console.error('Error removing card:', error);
        showNotification('Error removing card. Please try again.', 'error');
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.textContent = 'Remove card';
        }
    }
};

document.addEventListener('DOMContentLoaded', async function() {
    await loadProfileData();
    
    // Set up card search event listeners
    const cardSearchInput = document.getElementById('cardSearch');
    if (cardSearchInput) {
        cardSearchInput.addEventListener('input', function(e) {
            searchCards(e.target.value);
        });
        
        cardSearchInput.addEventListener('focus', function(e) {
            e.target.style.borderColor = 'var(--accent)';
        });

        cardSearchInput.addEventListener('blur', function(e) {
            if (!e.target.value) {
                e.target.style.borderColor = 'var(--border)';
            }
            setTimeout(() => hideSearchResults(), 200);
        });
    }
});

async function loadProfileData() {
    try {
        // Initialize user state first
        await initUserState();
        
        // Update UI based on authentication status
        updateAddCardSection();
        
        // Load all profile data
        await Promise.all([
            loadCardCollection(),
            loadCategoryOptimization(),
            loadSpendingProfile(),
            loadCreditsProfile(),
            loadHousehold()
        ]);

        // Calculate and display portfolio summary
        calculatePortfolioSummary();
        
    } catch (error) {
        console.error('Error loading profile data:', error);
        showError('Failed to load profile data. Please try refreshing the page.');
    }
}

// Card collection table: state kept module-scoped so sorting can re-render
// without re-fetching (loadCardCollection populates these, then calls
// renderCardCollectionTable()).
let _cardCollectionGroups = null;
let _cardCollectionDetails = null;
let _cardSort = { key: null, dir: 1 };

const CARD_SORT_COLUMNS = [
    { key: 'name', label: 'Card Name', type: 'string' },
    { key: 'issuer', label: 'Issuer', type: 'string' },
    { key: 'signup_date', label: 'Signup Date', type: 'date' },
    { key: 'annual_fee', label: 'Annual Fee', type: 'number' },
    { key: 'reward_type', label: 'Reward Type', type: 'string' },
    { key: 'point_value', label: 'Point Value', type: 'number' },
    { key: 'signup_bonus', label: 'Signup Bonus', type: 'number' },
    { key: 'card_type', label: 'Card Type', type: 'string' },
    { key: 'owner', label: 'Owner', type: 'string' },
    { key: 'count', label: 'Count', type: 'number' },
    { key: 'renewal', label: 'Renews', type: 'date' },
    { key: null, label: 'Actions', type: null }
];

// Phase K: household management panel (auth-only — hidden entirely for
// anon users, whose accounts stay single-player per the locked scope).
async function loadHousehold() {
    const section = document.getElementById('householdSection');
    if (!isAuthenticated) {
        section.style.display = 'none';
        return;
    }
    section.style.display = 'block';
    try {
        const entities = await UserDataManager.getEntities(true);
        renderHouseholdList(entities);
    } catch (error) {
        console.error('Error loading household:', error);
        document.getElementById('householdList').innerHTML =
            '<p style="color:var(--muted);">Failed to load household.</p>';
    }
}

function renderHouseholdList(entities) {
    const container = document.getElementById('householdList');
    if (!entities || entities.length === 0) {
        container.innerHTML = '<p style="color:var(--muted);">No household members yet.</p>';
        return;
    }
    container.innerHTML = entities.map(entity => `
        <div style="display:flex; align-items:center; gap:10px; padding:8px 0; border-bottom:1px solid var(--border);">
            <span style="font-weight:600;">${escapeHtml(entity.name)}</span>
            ${entity.is_primary ? '<span class="chip" style="font-size:11px;">Primary</span>' : ''}
            <span style="color:var(--muted); font-size:13px; text-transform:capitalize;">${escapeHtml(entity.kind)}</span>
            <span style="color:var(--muted); font-size:13px;">${entity.active_card_count} card${entity.active_card_count === 1 ? '' : 's'}</span>
            <div style="margin-left:auto; display:flex; gap:6px;">
                <button class="table-action-btn" onclick="renameHouseholdEntity(${entity.id}, '${escapeHtml(entity.name).replace(/'/g, "\\'")}')" title="Rename">✏️</button>
                ${!entity.is_primary ? `<button class="table-action-btn" onclick="removeHouseholdEntity(${entity.id})" title="Remove">🗑️</button>` : ''}
            </div>
        </div>
    `).join('');
}

function showAddHouseholdEntityForm() {
    document.getElementById('addHouseholdEntityForm').style.display = 'block';
    document.getElementById('newEntityName').focus();
}

function hideAddHouseholdEntityForm() {
    document.getElementById('addHouseholdEntityForm').style.display = 'none';
    document.getElementById('newEntityName').value = '';
}

async function submitAddHouseholdEntity() {
    const name = document.getElementById('newEntityName').value.trim();
    const kind = document.getElementById('newEntityKind').value;
    if (!name) {
        showNotification('Enter a name first', 'error');
        return;
    }
    const result = await UserDataManager.addEntity(name, kind);
    if (result.success) {
        hideAddHouseholdEntityForm();
        await loadHousehold();
        showNotification(`Added ${name}`, 'success');
    } else {
        showNotification(result.error || 'Failed to add household member', 'error');
    }
}

async function renameHouseholdEntity(entityId, currentName) {
    const name = prompt('Rename to:', currentName);
    if (!name || !name.trim() || name.trim() === currentName) {
        return;
    }
    const result = await UserDataManager.renameEntity(entityId, name.trim());
    if (result.success) {
        await loadHousehold();
    } else {
        showNotification(result.error || 'Failed to rename', 'error');
    }
}

async function removeHouseholdEntity(entityId) {
    if (!confirm('Remove this household member?')) {
        return;
    }
    const result = await UserDataManager.removeEntity(entityId);
    if (result.success) {
        await loadHousehold();
    } else {
        showNotification(result.error || "Failed to remove — reassign or remove their cards first", 'error');
    }
}

// Next annual-fee renewal: the upcoming anniversary (this year if it hasn't
// passed yet, otherwise next year) of the card's opened_date.
function nextAnniversary(openedDateStr) {
    if (!openedDateStr) return null;
    const opened = new Date(openedDateStr);
    const todayMidnight = new Date();
    todayMidnight.setHours(0, 0, 0, 0);
    const anniversary = new Date(todayMidnight.getFullYear(), opened.getMonth(), opened.getDate());
    if (anniversary < todayMidnight) {
        anniversary.setFullYear(anniversary.getFullYear() + 1);
    }
    return anniversary;
}

function cardSortValue(key, group, cardInfo) {
    switch (key) {
        case 'name': return cardInfo.name || '';
        case 'issuer': return cardInfo.issuer?.name || '';
        case 'signup_date': {
            const dates = group.instances.filter(i => i.opened_date).map(i => new Date(i.opened_date).getTime());
            return dates.length > 0 ? Math.min(...dates) : Infinity; // no date sorts last (ascending)
        }
        case 'annual_fee': return parseFloat(cardInfo.annual_fee || 0);
        case 'reward_type': return cardInfo.primary_reward_type?.name || '';
        case 'point_value': return cardInfo.metadata?.reward_value_multiplier || 0.01;
        case 'signup_bonus': return cardInfo.signup_bonus_amount || 0;
        case 'card_type': return cardInfo.card_type || '';
        case 'owner': {
            const names = group.instances.map(i => i.owner_name || '').filter(Boolean).sort();
            return names[0] || '';
        }
        case 'count': return group.instances.length;
        case 'renewal': {
            const anniversaries = group.instances
                .filter(i => i.opened_date)
                .map(i => nextAnniversary(i.opened_date).getTime());
            return anniversaries.length > 0 ? Math.min(...anniversaries) : Infinity;
        }
        default: return '';
    }
}

function sortCardCollection(key) {
    if (!key) return;
    if (_cardSort.key === key) {
        _cardSort.dir *= -1;
    } else {
        _cardSort = { key, dir: 1 };
    }
    renderCardCollectionTable();
}

function buildCardRow(cardId, group, cardInfo) {
    const instances = group.instances;
    const hasMultiple = instances.length > 1;

    // Calculate annual fee
    const annualFee = parseFloat(cardInfo.annual_fee || 0);
    const feeClass = annualFee === 0 ? 'fee-zero' : 'fee-paid';
    const feeText = annualFee === 0 ? 'No Fee' : `$${annualFee}/year`;

    // Get reward type and value
    const rewardType = cardInfo.primary_reward_type?.name || 'Unknown';
    const rewardMultiplier = cardInfo.metadata?.reward_value_multiplier || 0.01;
    const pointValue = `${(rewardMultiplier * 100).toFixed(1)}¢`;

    // Get signup bonus
    const signupBonus = cardInfo.signup_bonus_amount ?
        `${cardInfo.signup_bonus_amount.toLocaleString()} ${rewardType}` : 'None';

    // Create nicknames display for table
    let nicknamesDisplay = '';
    if (hasMultiple) {
        const nicknames = instances.filter(i => i.nickname).map(i => i.nickname);
        nicknamesDisplay = nicknames.length > 0 ?
            `<small class="card-nicknames">${nicknames.join(', ')}</small>` : '';
    } else {
        const instance = instances[0];
        nicknamesDisplay = instance.nickname ?
            `<small class="card-nicknames">${instance.nickname}</small>` : '';
    }

    // Signup date display (plain — the "renews soon" highlight lives on
    // the Renews column below, computed from the anniversary, not this).
    let signupDateDisplay = '';
    if (hasMultiple) {
        const dates = instances
            .filter(i => i.opened_date)
            .map(i => new Date(i.opened_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }));
        signupDateDisplay = dates.length > 0 ? dates.map(d => `<div>${d}</div>`).join('') : '<span style="color: var(--muted-2);">-</span>';
    } else {
        const instance = instances[0];
        signupDateDisplay = instance.opened_date
            ? new Date(instance.opened_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
            : '<span style="color: var(--muted-2);">-</span>';
    }

    // Renewal date display: the next anniversary of opened_date, highlighted
    // when it's within 2 months and the card carries an annual fee.
    const today = new Date();
    const twoMonthsFromNow = new Date(today);
    twoMonthsFromNow.setMonth(twoMonthsFromNow.getMonth() + 2);

    let renewalDateDisplay = '';
    if (hasMultiple) {
        const renewals = instances
            .filter(i => i.opened_date)
            .map(i => {
                const anniversary = nextAnniversary(i.opened_date);
                const formattedDate = anniversary.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                const shouldHighlight = annualFee > 0 && anniversary <= twoMonthsFromNow;
                const style = shouldHighlight ? 'color: var(--color-warning); font-weight: 600;' : '';
                return `<div style="${style}">${formattedDate}</div>`;
            });
        renewalDateDisplay = renewals.length > 0 ? renewals.join('') : '<span style="color: var(--muted-2);">-</span>';
    } else {
        const instance = instances[0];
        if (instance.opened_date) {
            const anniversary = nextAnniversary(instance.opened_date);
            const formattedDate = anniversary.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            const shouldHighlight = annualFee > 0 && anniversary <= twoMonthsFromNow;
            const style = shouldHighlight ? 'color: var(--color-warning); font-weight: 600;' : '';
            renewalDateDisplay = `<span style="${style}">${formattedDate}</span>`;
        } else {
            renewalDateDisplay = '<span style="color: var(--muted-2);">-</span>';
        }
    }

    // Owner display (Phase K): one name per instance, stacked like the
    // signup-date/renewal columns above — this is exactly the "two owners,
    // same card" shape the multi-instance stacking already supports.
    let ownerDisplay;
    if (hasMultiple) {
        const names = instances.map(i => i.owner_name).filter(Boolean);
        ownerDisplay = names.length > 0
            ? names.map(n => `<div>${escapeHtml(n)}</div>`).join('')
            : '<span style="color: var(--muted-2);">-</span>';
    } else {
        ownerDisplay = instances[0].owner_name
            ? escapeHtml(instances[0].owner_name)
            : '<span style="color: var(--muted-2);">-</span>';
    }

    return `
        <tr class="card-row modal-card-clickable" onclick="openCardModal(${cardId})" title="Click to view details">
            <td class="card-name-cell">
                <div class="card-name-wrapper">
                    <strong>${cardInfo.name}</strong>
                    ${nicknamesDisplay ? `<br>${nicknamesDisplay}` : ''}
                </div>
            </td>
            <td>${cardInfo.issuer?.name || 'Unknown'}</td>
            <td>${signupDateDisplay}</td>
            <td><span class="${feeClass}">${feeText}</span></td>
            <td>${rewardType}</td>
            <td>${pointValue}</td>
            <td>${signupBonus}</td>
            <td>${cardInfo.card_type ? cardInfo.card_type.charAt(0).toUpperCase() + cardInfo.card_type.slice(1) : 'Personal'}</td>
            <td>${ownerDisplay}</td>
            <td class="card-count-cell">
                <span class="card-count">${instances.length}</span>
                ${hasMultiple ? ' <span class="multiple-indicator" title="Multiple cards">📚</span>' : ''}
            </td>
            <td>${renewalDateDisplay}</td>
            <td class="actions-cell">
                <button class="table-action-btn" onclick="event.stopPropagation(); openCardModal(${cardId})" title="View Details">
                    👁️
                </button>
            </td>
        </tr>
    `;
}

function renderCardCollectionTable() {
    const cardCollectionContainer = document.getElementById('cardCollection');
    const cardGroups = _cardCollectionGroups || {};
    const cardDetails = _cardCollectionDetails || {};

    // Only rows with fetched details are sortable/renderable
    let rows = Object.entries(cardGroups)
        .filter(([cardId]) => cardDetails[cardId])
        .map(([cardId, group]) => ({ cardId, group, cardInfo: cardDetails[cardId] }));

    // Filter by personal vs business mode
    rows = rows.filter(({ cardInfo }) => {
        const cardType = (cardInfo.card_type || 'personal').toLowerCase();
        return cardType === _profileFilterMode;
    });

    if (rows.length === 0) {
        cardCollectionContainer.innerHTML = `
            <div style="text-align:center; padding: 40px; color: var(--muted); border: 1px dashed var(--border); border-radius: 12px; background: white;">
                No ${_profileFilterMode} cards in your collection yet.
            </div>
        `;
        return;
    }

    // Sort by name or open date if sorted
    if (_cardSort.key) {
        rows.sort((a, b) => {
            const va = cardSortValue(_cardSort.key, a.group, a.cardInfo);
            const vb = cardSortValue(_cardSort.key, b.group, b.cardInfo);
            let cmp;
            if (typeof va === 'string') {
                cmp = va.localeCompare(vb);
            } else {
                cmp = va - vb;
            }
            return cmp * _cardSort.dir;
        });
    }

    const rowsHtml = rows.map(({ cardId, group, cardInfo }) => {
        const instances = group.instances;
        const hasMultiple = instances.length > 1;
        const isExpanded = !!_expandedCards[cardId];
        
        // Calculate annual fee
        const annualFee = parseFloat(cardInfo.annual_fee || 0);
        const feeText = annualFee === 0 ? '$0' : `$${annualFee}`;
        
        // Get recommendation and status
        const rec = _recommendationsMap[cardId];
        let status = 'keep';
        let reason = 'Holds ongoing rewards value or has no annual fee.';
        let estValue = '$0/yr';
        let bestFor = 'General spend';
        
        if (rec) {
            status = rec.action || 'keep';
            reason = rec.reason || reason;
            estValue = rec.estimated_rewards ? `$${rec.estimated_rewards.toFixed(0)}/yr` : estValue;
            
            // Get best category from breakdown
            if (rec.rewards_breakdown && rec.rewards_breakdown.length > 0) {
                const categories = rec.rewards_breakdown
                    .filter(item => item.type !== 'credit' && item.type !== 'info' && item.type !== 'bonus_shift' && item.category_rewards > 0)
                    .map(item => item.category_name);
                if (categories.length > 0) {
                    bestFor = categories.slice(0, 2).join(', ');
                }
            }
        } else {
            if (annualFee === 0) {
                reason = 'No annual fee. Safe to keep to maintain credit history length.';
            } else {
                reason = 'Review annual fee vs ongoing rewards category value.';
                status = 'review';
            }
        }
        
        const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
        const cardStyle = getCardInitialsAndColor(cardInfo.name, cardInfo.issuer?.name);
        
        // Formatted dates/instances
        let openedDateDisplay = '';
        if (instances.length > 0 && instances[0].opened_date) {
            openedDateDisplay = new Date(instances[0].opened_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        } else {
            openedDateDisplay = 'unknown date';
        }
        
        const rewardType = cardInfo.primary_reward_type?.name || 'Points';

        // Details drawer content
        let detailsHtml = '';
        if (isExpanded) {
            const instancesHtml = instances.map(inst => {
                const nicknameStr = inst.nickname ? `"${inst.nickname}" · ` : '';
                const ownerStr = inst.owner_name ? `Held by ${escapeHtml(inst.owner_name)}` : '';
                const renewsStr = inst.opened_date ? ` · Renews ${nextAnniversary(inst.opened_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}` : '';
                return `<div style="font-size:13px; color:var(--muted); margin-bottom:4px;">${nicknameStr}${ownerStr}${renewsStr}</div>`;
            }).join('');
            
            detailsHtml = `
                <div class="card-row-expanded">
                    <div class="card-expanded-grid">
                        <div class="card-expanded-grid-item">
                            <span class="card-expanded-grid-label">Reward type</span>
                            <span class="card-expanded-grid-value">${rewardType}</span>
                        </div>
                        <div class="card-expanded-grid-item">
                            <span class="card-expanded-grid-label">Est. annual value</span>
                            <span class="card-expanded-grid-value">${estValue}</span>
                        </div>
                        <div class="card-expanded-grid-item">
                            <span class="card-expanded-grid-label">Best for</span>
                            <span class="card-expanded-grid-value">${bestFor}</span>
                        </div>
                    </div>
                    ${instancesHtml ? `<div style="margin-top: 6px;">${instancesHtml}</div>` : ''}
                    <div class="card-expanded-reason-box" style="margin-top: 8px;">
                        <strong>Why ${statusLabel.toLowerCase()}:</strong> ${reason}
                    </div>
                    <div class="card-expanded-actions" style="margin-top: 10px;">
                        <button onclick="event.stopPropagation(); windowEditCardDetails(${cardId}, '${cardInfo.name.replace(/'/g, "\\'")}', '${cardInfo.card_type || 'personal'}')" class="card-action-btn-outline">Edit details</button>
                        <button onclick="event.stopPropagation(); removeCardOwnership(${cardId}, '${cardInfo.name.replace(/'/g, "\\'")}', this)" class="card-action-btn-outline remove-btn">Remove card</button>
                    </div>
                </div>
            `;
        }

        return `
            <div class="card-row-box" id="cardRowBox_${cardId}">
                <button onclick="toggleCardRowExpansion(${cardId})" class="card-row-header-btn">
                    <div class="issuer-initials-badge" style="background: ${cardStyle.bg};">${cardStyle.initials}</div>
                    <div class="card-row-info">
                        <div class="card-row-name">${cardInfo.name}</div>
                        <div class="card-row-meta">${cardInfo.issuer?.name || 'Unknown'} · Opened ${openedDateDisplay}</div>
                    </div>
                    <div class="card-row-fee-block">
                        <div class="card-row-fee-label">Annual fee</div>
                        <div class="card-row-fee-value">${feeText}</div>
                    </div>
                    <div class="status-pill ${status.toLowerCase()}">${statusLabel}</div>
                    <div class="card-row-chevron">${isExpanded ? '▲' : '▼'}</div>
                </button>
                ${detailsHtml}
            </div>
        `;
    }).join('');

    cardCollectionContainer.innerHTML = rowsHtml;
}

async function loadCardCollection() {
    try {
        let userCardsDetails;
        const cardCollectionContainer = document.getElementById('cardCollection');
        
        if (!isAuthenticated) {
            // For unauthenticated users, get cards from local storage
            const localCardIds = LocalStorage.getCards();
            const localCardDetails = LocalStorage.getCardDetails();
            
            if (localCardIds.length === 0) {
                cardCollectionContainer.innerHTML = `
                    <div class="empty-state">
                        <h3>No Cards Added Yet</h3>
                        <p>Start building your credit card portfolio by adding your cards using the search above. Your cards will be saved locally, and you can sync them to your account when you log in.</p>
                        <a href="/cards/">Browse All Credit Cards</a>
                    </div>
                `;
                return;
            }
            
            // Convert local storage data to match expected format
            userCardsDetails = [];
            for (const cardId of localCardIds) {
                try {
                    const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                    if (response.ok) {
                        const cardData = await response.json();
                        const details = localCardDetails[cardId] || {};
                        userCardsDetails.push({
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
        } else {
            // For authenticated users, get from server
            userCardsDetails = await UserDataManager.getUserCardsDetails();
        }
        
        if (!userCardsDetails || userCardsDetails.length === 0) {
            cardCollectionContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No Cards Added Yet</h3>
                    <p>Start building your credit card portfolio by adding your cards using the search above.</p>
                    <a href="/cards/">Browse All Credit Cards</a>
                </div>
            `;
            return;
        }
        
        // Group cards by card ID and count duplicates
        const cardGroups = {};
        for (const userCard of userCardsDetails) {
            const cardId = userCard.card.id;
            if (!cardGroups[cardId]) {
                cardGroups[cardId] = {
                    card: userCard.card,
                    instances: []
                };
            }
            cardGroups[cardId].instances.push(userCard);
        }
        
        // Fetch detailed card information
        const cardIds = Object.keys(cardGroups);
        const cardDetails = {};

        for (const cardId of cardIds) {
            try {
                const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                if (response.ok) {
                    cardDetails[cardId] = await response.json();
                }
            } catch (error) {
                console.error(`Error fetching details for card ${cardId}:`, error);
            }
        }

        // Stash for re-render on sort (avoids re-fetching)
        _cardCollectionGroups = cardGroups;
        _cardCollectionDetails = cardDetails;

        renderCardCollectionTable();

    } catch (error) {
        console.error('Error loading card collection:', error);
        document.getElementById('cardCollection').innerHTML = `
            <div class="error">Error loading card collection. Please try refreshing the page.</div>
        `;
    }
}

function formatRewardRate(rateValue, rewardTypeName) {
    const rType = (rewardTypeName || '').toLowerCase();
    if (rType.includes('cash')) {
        return `${parseFloat(rateValue).toFixed(1).replace('.0', '')}% cash back`;
    } else if (rType.includes('mile')) {
        return `${parseFloat(rateValue).toFixed(0)}x miles`;
    } else {
        return `${parseFloat(rateValue).toFixed(0)}x points`;
    }
}

async function loadCategoryOptimization() {
    try {
        const userCards = await UserDataManager.getCards();
        const categoryContainer = document.getElementById('categoryOptimization');
        
        if (!userCards || userCards.length === 0) {
            categoryContainer.innerHTML = `
                <div class="empty-state">
                    <h3>Add Cards to See Categories</h3>
                    <p>Add your credit cards using the search box below to see which card to use for each spending category.</p>
                </div>
            `;
            return;
        }
        
        // Get detailed card information for all user cards
        const cardDetails = {};
        for (const cardId of userCards) {
            try {
                const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                if (response.ok) {
                    cardDetails[cardId] = await response.json();
                }
            } catch (error) {
                console.error(`Error fetching card ${cardId}:`, error);
            }
        }
        
        // Load category names for display
        let categoriesResponse;
        try {
            categoriesResponse = await fetch(`${API_BASE}/cards/spending-categories/`);
            if (!categoriesResponse.ok) throw new Error('Failed to fetch categories');
        } catch (error) {
            console.error('Error fetching categories:', error);
            categoriesResponse = null;
        }
        
        const categoriesData = categoriesResponse ? await categoriesResponse.json() : [];
        // Handle both paginated (results array) and direct array responses
        const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData.results || []);
        const categoryMap = {};
        categories.forEach(cat => {
            categoryMap[cat.slug] = cat.display_name || cat.name;
        });
        
        // Build a map of all reward categories from user's cards
        const categoryRewards = {};
        
        for (const cardId of userCards) {
            const card = cardDetails[cardId];
            if (!card || !card.reward_categories) continue;
            
            const rewardType = card.primary_reward_type?.name || 'Points';
            
            for (const rewardCategory of card.reward_categories) {
                if (!rewardCategory.is_active) continue;
                
                const categorySlug = rewardCategory.category.slug;
                const categoryName = categoryMap[categorySlug] || rewardCategory.category.display_name || rewardCategory.category.name;
                const rewardRate = parseFloat(rewardCategory.reward_rate);
                const cardName = card.name;
                
                // Track the best rate for each category
                if (!categoryRewards[categorySlug] || rewardRate > categoryRewards[categorySlug].rate) {
                    categoryRewards[categorySlug] = {
                        categoryName: categoryName,
                        rate: rewardRate,
                        cardName: cardName,
                        rewardType: rewardType,
                        card: card,
                        maxSpend: rewardCategory.max_annual_spend
                    };
                }
            }
        }
        
        if (Object.keys(categoryRewards).length === 0) {
            categoryContainer.innerHTML = `
                <div class="no-data">
                    Your cards don't have specific reward categories. They may earn a flat rate on all purchases.
                </div>
            `;
            return;
        }
        
        // Sort categories alphabetically for consistent display
        const sortedCategories = Object.entries(categoryRewards)
            .sort((a, b) => a[1].categoryName.localeCompare(b[1].categoryName));
        
        let optimizationHtml = '';
        
        for (const [categorySlug, categoryData] of sortedCategories) {
            const { categoryName, rate, cardName, rewardType, card, maxSpend } = categoryData;
            
            // Skip general/catch-all categories at 1x rate
            if (rate <= 1.0 && ['other', 'general', 'everything-else'].includes(categorySlug)) {
                continue;
            }
            
            const cardStyle = getCardInitialsAndColor(cardName, card.issuer?.name);
            const formattedRate = formatRewardRate(rate, rewardType);
            
            optimizationHtml += `
                <div class="category-card-cell">
                    <div class="category-cell-name">${categoryName}</div>
                    <div class="category-cell-body">
                        <div class="category-cell-badge" style="background: ${cardStyle.bg};">${cardStyle.initials}</div>
                        <div class="category-cell-info">
                            <div class="category-cell-cardname">${cardName}</div>
                            <div class="category-cell-rate">${formattedRate}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (optimizationHtml === '') {
            categoryContainer.innerHTML = `
                <div class="no-data">
                    Your cards appear to have only general earning rates (1x). Consider adding cards with bonus categories for better optimization.
                </div>
            `;
        } else {
            categoryContainer.innerHTML = optimizationHtml;
        }
        
    } catch (error) {
        console.error('Error loading category optimization:', error);
        document.getElementById('categoryOptimization').innerHTML = `
            <div class="error">Error loading category optimization. Please try refreshing the page.</div>
        `;
    }
}

async function loadSpendingProfile() {
    try {
        const spending = await UserDataManager.getSpending();
        const spendingContainer = document.getElementById('spendingProfile');
        
        if (!spending || Object.keys(spending).length === 0) {
            spendingContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No Spending Profile Set</h3>
                    <p>Set up your spending profile to see detailed analysis and recommendations.</p>
                    <a href="/">Set Up Spending Profile</a>
                </div>
            `;
            return;
        }
        
        // Load category names
        let categoriesResponse;
        try {
            categoriesResponse = await fetch(`${API_BASE}/cards/spending-categories/`);
            if (!categoriesResponse.ok) throw new Error('Failed to fetch categories');
        } catch (error) {
            console.error('Error fetching categories:', error);
            categoriesResponse = null;
        }
        
        const categoriesData = categoriesResponse ? await categoriesResponse.json() : [];
        // Handle both paginated (results array) and direct array responses
        const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData.results || []);
        const categoryMap = {};
        categories.forEach(cat => {
            categoryMap[cat.slug] = cat.display_name || cat.name;
        });
        
        // Sort spending by amount (highest first)
        const sortedSpending = Object.entries(spending)
            .filter(([, amount]) => parseFloat(amount) > 0)
            .sort((a, b) => parseFloat(b[1]) - parseFloat(a[1]));
        
        if (sortedSpending.length === 0) {
            spendingContainer.innerHTML = `
                <div class="no-data">
                    No spending categories with positive amounts found.
                </div>
            `;
            return;
        }
        
        let spendingHtml = '';
        let totalMonthly = 0;
        
        for (const [categorySlug, monthlyAmount] of sortedSpending) {
            const amount = parseFloat(monthlyAmount);
            const annualAmount = amount * 12;
            totalMonthly += amount;
            
            const categoryName = categoryMap[categorySlug] || categorySlug.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            
            spendingHtml += `
                <div class="spending-item">
                    <div class="spending-category">${categoryName}</div>
                    <div class="spending-amounts">
                        <div class="monthly-amount">$${amount.toLocaleString('en-US', { maximumFractionDigits: 0 })}/mo</div>
                        <div class="annual-amount">$${annualAmount.toLocaleString('en-US', { maximumFractionDigits: 0 })}/year</div>
                    </div>
                </div>
            `;
        }
        
        // Add total
        spendingHtml += `
            <div class="spending-item" style="border-top: 2px solid var(--border); margin-top: 15px; padding-top: 15px; background: var(--accent-soft);">
                <div class="spending-category" style="font-weight: 700; color: var(--accent);">Total Monthly Spending</div>
                <div class="spending-amounts">
                    <div class="monthly-amount" style="color: var(--accent);">$${totalMonthly.toLocaleString('en-US', { maximumFractionDigits: 0 })}/mo</div>
                    <div class="annual-amount">$${(totalMonthly * 12).toLocaleString('en-US', { maximumFractionDigits: 0 })}/year</div>
                </div>
            </div>
        `;
        
        spendingContainer.innerHTML = spendingHtml;
 
    } catch (error) {
        console.error('Error loading spending profile:', error);
        document.getElementById('spendingProfile').innerHTML = `
            <div class="error">Error loading spending profile. Please try refreshing the page.</div>
        `;
    }
}

async function loadCreditsProfile() {
    try {
        const userCards = await UserDataManager.getCards();
        const creditsContainer = document.getElementById('creditsProfile');

        if (!userCards || userCards.length === 0) {
            creditsContainer.innerHTML = `
                <div class="info-box">
                    <h3>📱 No Cards Added Yet</h3>
                    <p>Add your credit cards above to see all the benefits and credits you're earning!</p>
                </div>
            `;
            return;
        }

        // Fetch detailed card information to get credits, and which credits
        // this user actually values (server-persisted, same source the
        // engine reads — a credit only counts if explicitly opted in).
        const cardDetails = {};
        const allCredits = {};
        const [_, preferences, usages] = await Promise.all([
            (async () => {
                for (const cardId of userCards) {
                    try {
                        const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                        if (response.ok) {
                            const card = await response.json();
                            cardDetails[cardId] = card;

                            // Collect all credits from this card
                            if (card.credits && card.credits.length > 0) {
                                card.credits.forEach(credit => {
                                    const creditType = credit.spending_credit;
                                    if (creditType) {
                                        const creditKey = creditType.slug;
                                        if (!allCredits[creditKey]) {
                                            allCredits[creditKey] = {
                                                name: creditType.display_name || creditType.name,
                                                slug: creditType.slug,
                                                stackable: creditType.stackable !== false,
                                                cards: []
                                            };
                                        }
                                        // Use annual_value if available, otherwise calculate
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
                                    }
                                });
                            }
                        }
                    } catch (error) {
                        console.error(`Error fetching card ${cardId}:`, error);
                    }
                }
            })(),
            UserDataManager.getCreditPreferences(),
            UserDataManager.getCreditUsages()
        ]);

        // Resolve stackability: a non-stackable credit only counts once,
        // on whichever card carries it for the most value — mirrors the
        // engine's _allocate_portfolio_credits dedup rule. An opted-out
        // credit (or one never opted into) counts $0, same as the engine.
        const creditEntries = Object.values(allCredits).map(credit => {
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

            return {
                ...credit,
                isUsed,
                winnerCardId,
                effectiveAmount: isUsed ? rawAmount : 0
            };
        });

        if (creditEntries.length === 0) {
            creditsContainer.innerHTML = `
                <div class="info-box">
                    <h3>ℹ️ No Card Benefits Found</h3>
                    <p>Your current cards don't have any tracked benefits or credits. Consider adding cards with travel credits, statement credits, or other perks!</p>
                </div>
            `;
            return;
        }

        // Compile trackable credit instances
        const trackableCredits = [];
        creditEntries.forEach(entry => {
            if (entry.isUsed) {
                entry.cards.forEach(cardCredit => {
                    trackableCredits.push({
                        creditId: cardCredit.creditId,
                        cardName: cardCredit.name,
                        benefitName: entry.name,
                        description: cardCredit.description,
                        value: cardCredit.value,
                        timesPerYear: cardCredit.timesPerYear,
                        isUsedThisPeriod: usages[cardCredit.creditId] === true
                    });
                });
            }
        });

        let creditsHtml = '';
        
        // Total summary box at the top of the tab
        const totalCreditsValue = creditEntries.reduce((sum, credit) => sum + credit.effectiveAmount, 0);
        creditsHtml += `
            <div style="background: oklch(95% 0.008 250); border: 1px solid var(--border); color: var(--text); padding: 16px 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="font-size: 13px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em;">Total Annual Benefits</div>
                    <div style="font-size: 12px; color: var(--muted); margin-top: 2px;">Based on benefits you use across ${Object.keys(cardDetails).length} card${Object.keys(cardDetails).length !== 1 ? 's' : ''}</div>
                </div>
                <div style="font-size: 30px; font-weight: 800; color: var(--accent-dark); font-family: var(--font-ui);">$${totalCreditsValue.toFixed(0)}<span style="font-size:14px; font-weight: 500; color: var(--muted);">/yr</span></div>
            </div>
        `;
        
        if (trackableCredits.length > 0) {
            creditsHtml += `
                <div style="margin-bottom: 24px;">
                    <h3 style="font-family: var(--font-ui); font-size: 15px; font-weight: 700; color: var(--text-strong); margin-bottom: 6px;">📅 Track Benefits for This Period</h3>
                    <p style="font-size: 13.5px; color: var(--muted); margin-top: 0; margin-bottom: 14px;">Toggle benefits to mark them as used. Helps track monthly or annual credits.</p>
                    <div class="benefits-list-container">
            `;
            
            trackableCredits.forEach(c => {
                const formattedValue = parseFloat(c.value) > 0 ? `$${parseFloat(c.value).toFixed(0)}` : 'Benefit';
                const freqLabel = c.timesPerYear === 12 ? '/mo' : c.timesPerYear === 4 ? '/qtr' : c.timesPerYear === 2 ? '/half' : '/yr';
                const statusClass = c.isUsedThisPeriod ? 'used' : 'unused';
                const statusText = c.isUsedThisPeriod ? 'Used' : 'Unused';
                
                creditsHtml += `
                    <div class="benefit-row-card" onclick="toggleCreditUsagePeriod(${c.creditId}, ${!c.isUsedThisPeriod})" style="cursor: pointer; user-select: none;">
                        <div class="benefit-row-info">
                            <div class="benefit-row-name">${c.benefitName}</div>
                            <div class="benefit-row-meta">${c.cardName} · worth ${formattedValue}${freqLabel}</div>
                        </div>
                        <div class="benefit-status-pill ${statusClass}">${statusText}</div>
                    </div>
                `;
            });
            
            creditsHtml += `</div></div>`;
        }

        // Add the global opted-in manage checklist at the bottom of the tab
        creditsHtml += `
            <div style="margin-top: 30px; border-top: 1px solid var(--border); padding-top: 20px;">
                <h3 style="font-family: var(--font-ui); font-size: 15px; font-weight: 700; color: var(--text-strong); margin-bottom: 6px;">Manage Opted-In Benefits</h3>
                <p style="font-size: 13.5px; color: var(--muted); margin-top: 0; margin-bottom: 16px;">Only check benefits you realistically expect to use. The math will automatically adjust to reflect these values.</p>
                <div class="credits-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
        `;
        
        // Sort by effective amount, highest first
        creditEntries.sort((a, b) => b.effectiveAmount - a.effectiveAmount);

        creditEntries.forEach(credit => {
            const notStacking = !credit.stackable && credit.cards.length > 1;
            const winnerName = credit.cards.find(c => c.cardId === credit.winnerCardId)?.name;

            creditsHtml += `
                <div style="background: white; border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 12px; padding: 14px 16px; ${credit.isUsed ? '' : 'opacity: 0.65;'}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="checkbox" id="creditUse_${credit.slug}" ${credit.isUsed ? 'checked' : ''}
                                   onchange="toggleCreditUsage('${credit.slug}', this.checked)"
                                   title="I use this benefit" style="cursor: pointer; width:16px; height:16px;">
                            <label for="creditUse_${credit.slug}" style="cursor: pointer; margin: 0; font-weight: 600; font-size: 14.5px; color: var(--text-strong);">
                                ${credit.name}
                            </label>
                        </div>
                        <span style="background: var(--accent-soft); color: var(--accent-dark); padding: 4px 8px; border-radius: 8px; font-size: 12.5px; font-weight: 700; white-space: nowrap; font-family: var(--font-ui);">
                             +$${credit.effectiveAmount.toFixed(0)}/yr
                        </span>
                    </div>
                    ${notStacking ? `<div style="font-size: 11.5px; color: var(--muted); margin-bottom: 6px; line-height:1.35;">Doesn't stack across cards — counted once, on ${winnerName}</div>` : ''}
                    <div style="margin-top: 10px; display:flex; flex-direction:column; gap:6px;">
                        ${credit.cards.map(card => {
                            const isWinner = credit.stackable || card.cardId === credit.winnerCardId;
                            const amountLabel = !credit.isUsed
                                ? '$0/year'
                                : (isWinner
                                    ? `$${parseFloat(card.annualValue).toFixed(0)}/year${card.timesPerYear > 1 ? ` ($${parseFloat(card.value).toFixed(0)} × ${card.timesPerYear})` : ''}`
                                    : `counted once — on ${winnerName}`);
                            return `
                                <div style="background: oklch(98% 0.005 250); padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border-light); font-size: 12.5px; display:flex; justify-content:space-between; align-items:center;">
                                    <div style="font-weight: 500; color: var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:160px;">${card.name}</div>
                                    <div style="color: ${isWinner ? 'var(--accent-dark)' : 'var(--muted)'}; font-weight: 700; font-size: 12px; font-family: var(--font-ui);">${amountLabel}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });
        
        creditsHtml += `</div></div>`;
        creditsContainer.innerHTML = creditsHtml;

    } catch (error) {
        console.error('Error loading credits profile:', error);
        document.getElementById('creditsProfile').innerHTML = `
            <div class="error">Error loading benefits. Please try refreshing the page.</div>
        `;
    }
}

async function toggleCreditUsage(slug, checked) {
    try {
        await UserDataManager.saveCreditPreferences({ [slug]: checked });
        await loadCreditsProfile();
    } catch (error) {
        console.error('Error updating credit preference:', error);
    }
}

async function toggleCreditUsagePeriod(creditId, checked) {
    try {
        await UserDataManager.saveCreditUsages({ [creditId]: checked });
        await loadCreditsProfile();
    } catch (error) {
        console.error('Error updating credit usage period:', error);
    }
}

async function calculatePortfolioSummary() {
    try {
        const userCards = await UserDataManager.getCards();
        const spending = await UserDataManager.getSpending();
        
        // Initialize default values
        let totalCards = 0;
        let totalAnnualFees = 0;
        let totalAnnualRewards = 0;
        let netPortfolioValue = 0;
        
        if (userCards && userCards.length > 0) {
            // Get detailed card information and calculate fees
            const cardDetails = {};
            for (const cardId of userCards) {
                try {
                    const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                    if (response.ok) {
                        const card = await response.json();
                        cardDetails[cardId] = card;
                        totalAnnualFees += parseFloat(card.annual_fee || 0);
                    }
                } catch (error) {
                    console.error(`Error fetching card ${cardId}:`, error);
                }
            }
            
            totalCards = userCards.length;
            
            // If we have spending data, calculate optimized rewards
            if (spending && Object.keys(spending).length > 0) {
                try {
                    const requestData = {
                        spending: spending,
                        cards: userCards,
                        preferences: await UserDataManager.getPreferences(),
                        max_recommendations: 10
                    };
                    
                    const response = await fetch(`${API_BASE}/roadmaps/quick-recommendation/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify(requestData)
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        const portfolioSummary = data.portfolio_summary;
                        
                        _recommendationsMap = {};
                        if (data.recommendations && Array.isArray(data.recommendations)) {
                            for (const rec of data.recommendations) {
                                if (rec.card && rec.card.id) {
                                    _recommendationsMap[rec.card.id] = rec;
                                }
                            }
                        }
                        
                        if (portfolioSummary) {
                            totalAnnualRewards = portfolioSummary.total_portfolio_rewards || 0;
                            netPortfolioValue = portfolioSummary.net_portfolio_value || 0;
                            // Use the optimized fees from the portfolio summary if available
                            if (portfolioSummary.total_annual_fees !== undefined) {
                                totalAnnualFees = portfolioSummary.total_annual_fees;
                            }
                        }
                        
                        // Re-render to show keep/cancel statuses and live reasoning
                        renderCardCollectionTable();
                    }
                } catch (error) {
                    console.error('Error calculating portfolio optimization:', error);
                    // Fall back to simple calculation
                    netPortfolioValue = Math.max(0, totalAnnualRewards - totalAnnualFees);
                }
            } else {
                // No spending data, so no rewards
                netPortfolioValue = -totalAnnualFees;
            }
        }
        
        // Update the display
        document.getElementById('totalCards').textContent = totalCards.toString();
        document.getElementById('totalAnnualFees').textContent = `$${totalAnnualFees.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
        document.getElementById('totalAnnualRewards').textContent = `$${totalAnnualRewards.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
        
        // Color code the net value
        const netValueElement = document.getElementById('netPortfolioValue');
        netValueElement.textContent = `$${netPortfolioValue.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
        
        if (netPortfolioValue > 0) {
            netValueElement.style.color = '#3FCF8E'; // Green for positive
        } else if (netPortfolioValue < 0) {
            netValueElement.style.color = '#F87171'; // Red for negative
        } else {
            netValueElement.style.color = '#8B95A4'; // Gray for zero
        }
        
    } catch (error) {
        console.error('Error calculating portfolio summary:', error);
        // Show error state
        document.getElementById('totalCards').textContent = 'Error';
        document.getElementById('totalAnnualFees').textContent = 'Error';
        document.getElementById('totalAnnualRewards').textContent = 'Error';
        document.getElementById('netPortfolioValue').textContent = 'Error';
    }
}

// Profile Privacy and Sharing Functionality
async function initializePrivacySettings() {
    try {
        const response = await fetch('/api/cards/profile/privacy/');
        if (response.ok) {
            const data = await response.json();
            
            // Set the current privacy setting
            const privacyRadio = document.querySelector(`input[name="privacy"][value="${data.privacy_setting}"]`);
            if (privacyRadio) {
                privacyRadio.checked = true;
            }
            
            // Show shareable URL if public
            if (data.is_public && data.shareable_url) {
                showShareableUrl(data.shareable_url);
            }
        }
    } catch (error) {
        console.log('Could not load privacy settings (user may not be logged in)');
    }
}

async function updatePrivacySetting(privacySetting) {
    try {
        const response = await fetch('/api/cards/profile/privacy/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                privacy_setting: privacySetting
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.is_public && data.shareable_url) {
                showShareableUrl(window.location.origin + data.shareable_url);
            } else {
                hideShareableUrl();
            }
            
            // Show success message
            showNotification(privacySetting === 'public' ? 
                'Profile is now public and shareable!' : 
                'Profile is now private', 'success');
        } else {
            const errorData = await response.json();
            showNotification(errorData.error || 'Failed to update privacy setting', 'error');
        }
    } catch (error) {
        showNotification('Error updating privacy setting. Please try again.', 'error');
    }
}

function showShareableUrl(url) {
    const shareableUrlSection = document.getElementById('shareable-url-section');
    const shareableUrlInput = document.getElementById('shareable-url');
    
    shareableUrlInput.value = url;
    shareableUrlSection.style.display = 'block';
}

function hideShareableUrl() {
    const shareableUrlSection = document.getElementById('shareable-url-section');
    shareableUrlSection.style.display = 'none';
}

function copyShareableUrl() {
    const shareableUrlInput = document.getElementById('shareable-url');
    shareableUrlInput.select();
    shareableUrlInput.setSelectionRange(0, 99999); // For mobile devices
    
    try {
        document.execCommand('copy');
        showNotification('URL copied to clipboard!', 'success');
        
        // Change button text briefly
        const copyBtn = document.getElementById('copy-url-btn');
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '✅ Copied!';
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
        }, 2000);
    } catch (err) {
        showNotification('Failed to copy URL', 'error');
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize privacy settings on page load
    initializePrivacySettings();
    
    // Add event listeners for privacy toggle
    const privacyRadios = document.querySelectorAll('input[name="privacy"]');
    privacyRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                updatePrivacySetting(this.value);
            }
        });
    });
});

// Card Search Functionality
let allCards = [];
let selectedCard = null;
let searchTimeout = null;

// Load all cards for search
async function loadAllCards() {
    try {
        const response = await fetch('/api/cards/cards/');
        allCards = await response.json();
    } catch (error) {
        console.error('Error loading cards:', error);
    }
}

// Search cards as user types
function searchCards(query) {
    const resultsDiv = document.getElementById('cardSearchResults');
    const addButton = document.getElementById('addSelectedCard');
    
    // Clear previous timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    // Reset selected card
    selectedCard = null;
    if (addButton) {
        addButton.disabled = true;
        addButton.style.opacity = '0.5';
    }
    
    if (!query || query.length < 2) {
        resultsDiv.style.display = 'none';
        return;
    }
    
    // Debounce search
    searchTimeout = setTimeout(() => {
        const filtered = allCards.filter(card =>
            cardMatchesQuery(card, query)
        ).slice(0, 8); // Limit to 8 results
        
        displaySearchResults(filtered);
    }, 300);
}

// Display search results
function displaySearchResults(cards) {
    let resultsDiv = document.getElementById('cardSearchResults');
    
    // Move dropdown to body to escape all stacking contexts
    if (resultsDiv.parentNode !== document.body) {
        document.body.appendChild(resultsDiv);
    }
    
    // Position dropdown relative to search input
    const searchInput = document.getElementById('cardSearch');
    const inputRect = searchInput.getBoundingClientRect();
    
    // Style the dropdown as a portal
    resultsDiv.style.position = 'fixed';
    resultsDiv.style.top = (inputRect.bottom + 2) + 'px';
    resultsDiv.style.left = inputRect.left + 'px';
    resultsDiv.style.width = inputRect.width + 'px';
    resultsDiv.style.zIndex = '10000';
    resultsDiv.style.background = 'var(--surface)';
    resultsDiv.style.border = '1px solid var(--border)';
    resultsDiv.style.borderTop = 'none';
    resultsDiv.style.borderRadius = '0 0 var(--radius-sm) var(--radius-sm)';
    resultsDiv.style.maxHeight = '300px';
    resultsDiv.style.overflowY = 'auto';
    resultsDiv.style.boxShadow = 'var(--shadow-md)';

    if (cards.length === 0) {
        resultsDiv.innerHTML = '<div style="padding: 12px; color: var(--muted); text-align: center;">No cards found</div>';
        resultsDiv.style.display = 'block';
        return;
    }

    const html = cards.map(card => `
        <div
            class="search-result-item"
            onclick="selectCard(${card.id}, '${card.name.replace(/'/g, '\\\'')}')"
            style="padding: 12px; cursor: pointer; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; transition: background-color 0.2s;"
            onmouseover="this.style.backgroundColor='var(--bg)'"
            onmouseout="this.style.backgroundColor='transparent'"
        >
            <div>
                <div style="font-weight: 600; color: var(--text-strong);">${card.name}</div>
                <div style="font-size: 12px; color: var(--muted);">${card.issuer.name} • Annual Fee: $${card.annual_fee}</div>
            </div>
            <div style="color: var(--accent); font-size: 12px; font-weight: 600;">Select →</div>
        </div>
    `).join('');
    
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

// Hide search results dropdown
function hideSearchResults() {
    const resultsDiv = document.getElementById('cardSearchResults');
    if (resultsDiv) {
        resultsDiv.style.display = 'none';
    }
}

// Select a card from search results
async function selectCard(cardId, cardName) {
    selectedCard = cardId;
    
    // Update input value
    document.getElementById('cardSearch').value = cardName;
    
    // Hide results and clean up positioning
    const resultsDiv = document.getElementById('cardSearchResults');
    resultsDiv.style.display = 'none';
    
    // Since there's no button, automatically add the card
    await addSelectedCardToCollection();
}

// Add selected card to collection
async function addSelectedCardToCollection() {
    if (!selectedCard) {
        showNotification('Please select a card first', 'error');
        return;
    }
    
    const addButton = document.getElementById('addSelectedCard');
    let originalText = '';
    if (addButton) {
        originalText = addButton.innerHTML;
        addButton.innerHTML = '⏳ Adding...';
        addButton.disabled = true;
    }
    
    try {
        if (isAuthenticated) {
            // For authenticated users, save to server
            const response = await fetch('/api/cards/user-cards/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    card_id: selectedCard
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                showNotification(data.message || 'Card added successfully!', 'success');
                
                // Reload the page data to show the new card
                loadProfileData();
            } else {
                const errorData = await response.json();
                showNotification(errorData.error || 'Failed to add card', 'error');
                return;
            }
        } else {
            // For unauthenticated users, save to local storage
            const currentCards = LocalStorage.getCards();
            if (!currentCards.includes(selectedCard)) {
                currentCards.push(selectedCard);
                LocalStorage.setCards(currentCards);
                
                showNotification('Card added to your local collection! Log in to sync with your account.', 'success');
                
                // Reload the page data to show the new card
                loadProfileData();
            } else {
                showNotification('Card is already in your collection', 'info');
            }
        }
        
        // Clear search
        document.getElementById('cardSearch').value = '';
        selectedCard = null;
        if (addButton) {
            addButton.disabled = true;
            addButton.style.opacity = '0.5';
        }
        
    } catch (error) {
        console.error('Error adding card:', error);
        showNotification('Error adding card. Please try again.', 'error');
    } finally {
        if (addButton) {
            addButton.innerHTML = originalText;
            addButton.disabled = selectedCard === null;
        }
    }
}

// Hide search results when clicking outside
document.addEventListener('click', function(event) {
    const searchInput = document.getElementById('cardSearch');
    const resultsDiv = document.getElementById('cardSearchResults');
    
    if (!searchInput.contains(event.target) && !resultsDiv.contains(event.target)) {
        resultsDiv.style.display = 'none';
    }
});

// Load cards when page loads
loadAllCards();

// Update add card section based on authentication status
function updateAddCardSection() {
    const searchInput = document.getElementById('cardSearch');
    const addButton = document.getElementById('addSelectedCard');
    
    // Enable for both authenticated and unauthenticated users
    if (searchInput) {
        searchInput.disabled = false;
        searchInput.style.opacity = '1';
        if (isAuthenticated) {
            searchInput.placeholder = "Type card name (e.g., 'Chase Sapphire', 'Blue Cash')...";
        } else {
            searchInput.placeholder = "Type card name (e.g., 'Chase Sapphire', 'Blue Cash')... (saves locally)";
        }
    }
    
    // Button functionality removed - cards are now added automatically on selection
    
    // Add visual indicator for local storage mode
    if (!isAuthenticated) {
        const addCardSection = document.querySelector('.section h2');
        if (addCardSection && addCardSection.textContent.includes('➕ Add Credit Cards')) {
            const existingBadge = addCardSection.querySelector('.local-mode-badge');
            if (!existingBadge) {
                const badge = document.createElement('span');
                badge.className = 'local-mode-badge';
                badge.innerHTML = ' <span style="background: #5C6675; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;">Local Mode</span>';
                addCardSection.appendChild(badge);
            }
        }
    } else {
        // Remove local mode badge for authenticated users
        const badge = document.querySelector('.local-mode-badge');
        if (badge) {
            badge.remove();
        }
    }
}
