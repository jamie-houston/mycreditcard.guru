// Dynamic issuer loading: 2025-07-04-v1
let spendingCategories = {}; // For slug -> ID mapping
let spendingCategoriesArray = []; // For the actual category objects
let spendingCredits = [];

// Strategy presets (from roadmaps/strategies.py via the view context)
const STRATEGY_PRESETS = (() => {
    const el = document.getElementById('strategiesData');
    if (!el) return [];
    try {
        const parsed = JSON.parse(el.textContent);
        return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
        return [];
    }
})();
let selectedStrategy = ''; // '' = no strategy (filters-only, the old behavior)

function strategyByKey(key) {
    return STRATEGY_PRESETS.find(s => s.key === key) || null;
}

// Material Symbols icon per strategy preset, purely cosmetic (Ledger redesign)
const STRATEGY_ICONS = {
    simple_cash_back: 'bolt',
    travel_points: 'flight_takeoff',
    maximizer: 'table_chart'
};
STRATEGY_PRESETS.forEach(s => {
    const iconEl = document.querySelector(`#effort-${s.key} .effort-icon`);
    if (iconEl) iconEl.textContent = STRATEGY_ICONS[s.key] || 'bolt';
});

function toggleEffortOption(key) {
    // Clicking the selected answer clears it — the question is not a gate
    setStrategy(selectedStrategy === key ? '' : key, true);
}

function toggleStrategyPicker() {
    const picker = document.getElementById('strategyPicker');
    const toggle = document.getElementById('strategyPickerToggle');
    if (picker.style.display === 'none') {
        picker.style.display = 'block';
        toggle.textContent = '▾ Advanced: pick a strategy directly';
    } else {
        picker.style.display = 'none';
        toggle.textContent = '▸ Advanced: pick a strategy directly';
    }
}

// applyDefaults: true on user action (preset sets Max Recommendations and
// releases the Reward Type filter, since the preset owns the card pool);
// false when restoring saved state on page load (saved prefs already
// reflect whatever the preset set).
function setStrategy(key, applyDefaults) {
    selectedStrategy = key || '';
    const preset = strategyByKey(selectedStrategy);

    STRATEGY_PRESETS.forEach(s => {
        const el = document.getElementById(`effort-${s.key}`);
        if (el) el.classList.toggle('selected', s.key === selectedStrategy);
    });
    const select = document.getElementById('strategySelect');
    if (select) select.value = selectedStrategy;

    const hint = document.getElementById('strategyHint');
    if (hint) {
        if (preset) {
            hint.style.display = 'block';
            hint.innerHTML = `<strong>${preset.name}</strong> strategy — card pool: ${preset.pool_label}, up to ${preset.max_recommendations} new cards. You can still adjust preferences below.`;
        } else {
            hint.style.display = 'none';
        }
    }

    if (applyDefaults) {
        const maxRecs = document.getElementById('maxRecs');
        const rewardType = document.getElementById('rewardType');
        if (preset) {
            if (maxRecs) maxRecs.value = preset.max_recommendations;
            // Preset filters OR with same-type explicit filters, so a
            // leftover reward-type pick would WIDEN the pool — clear it.
            if (rewardType) rewardType.value = '';
        } else if (maxRecs) {
            const saved = JSON.parse(localStorage.getItem('userPreferences') || '{}');
            maxRecs.value = saved.default_max_recommendations || 1;
        }
    }

    localStorage.setItem('userStrategy', selectedStrategy);
}

function setSpendingMode(mode, save = true) {
    localStorage.setItem('spending_mode', mode);
    
    const btnCategory = document.getElementById('btnModeCategory');
    const btnEasy = document.getElementById('btnModeEasy');
    const categoryGrid = document.getElementById('spendingCategories');
    const easySection = document.getElementById('easyModeSpendingSection');
    
    if (mode === 'easy') {
        btnEasy.classList.add('active');
        btnCategory.classList.remove('active');
        categoryGrid.style.display = 'none';
        easySection.style.display = 'block';
    } else {
        btnCategory.classList.add('active');
        btnEasy.classList.remove('active');
        categoryGrid.style.display = 'grid';
        easySection.style.display = 'none';
    }
    
    updateTotal();
    if (save) {
        saveCurrentData();
    }
}

function onEasySpendingChange() {
    const amount = parseFloat(document.getElementById('easySpendingAmount').value) || 0;
    const interval = document.getElementById('easySpendingInterval').value;
    localStorage.setItem('easy_spending_interval', interval);
    updateTotal();
    saveCurrentData();
}

function toggleSpendingProfile() {
    const content = document.getElementById('spendingProfileContent');
    const toggle = document.getElementById('spendingToggle');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = 'expand_less';
    } else {
        content.style.display = 'none';
        toggle.textContent = 'expand_more';
    }
}

function toggleUpcomingExpense() {
    const content = document.getElementById('expenseContent');
    const toggle = document.getElementById('expenseToggle');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = 'expand_less';
    } else {
        content.style.display = 'none';
        toggle.textContent = 'expand_more';
    }
}

function togglePreferences() {
    const content = document.getElementById('preferencesContent');
    const toggle = document.getElementById('preferencesToggle');

    if (content.style.display === 'none') {
        content.style.display = 'grid';
        toggle.textContent = 'expand_less';
    } else {
        content.style.display = 'none';
        toggle.textContent = 'expand_more';
    }
}

// Toggles the whole page between "Your Roadmap" (results-first, the
// default once a Current Roadmap exists) and "Create a Roadmap"
// (the builder form). Driven by loadCurrentRoadmap() on page load and
// by getRecommendations() after a fresh generation; toggleRoadmapBuilder()
// is the manual "Update roadmap" / collapse-again entry point.
function setRoadmapViewMode(mode) {
    const builder = document.getElementById('roadmapBuilder');
    const builderToggle = document.getElementById('builderToggle');
    const heading = document.getElementById('pageHeading');
    const subtitle = document.getElementById('pageSubtitle');
    const showBuilder = mode === 'builder';

    builder.style.display = showBuilder ? 'block' : 'none';
    if (builderToggle) builderToggle.textContent = showBuilder ? 'expand_less' : 'expand_more';
    if (heading) {
        heading.innerHTML = `<span class="ico" style="color:var(--accent);vertical-align:-3px;">route</span> ${showBuilder ? 'Create a Roadmap' : 'Your Roadmap'}`;
    }
    if (subtitle) subtitle.style.display = showBuilder ? '' : 'none';
}

function toggleRoadmapBuilder() {
    const builder = document.getElementById('roadmapBuilder');
    const builderOpen = builder.style.display !== 'none';
    setRoadmapViewMode(builderOpen ? 'results' : 'builder');
    if (!builderOpen) {
        builder.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Roadmap Sharing — mirrors profile.html's privacy toggle
// (initializePrivacySettings/updatePrivacySetting/showShareableUrl/
// copyShareableUrl, templates/profile.html:916-1006), repointed at
// the roadmap-sharing endpoints. Unlike profile sharing, this works
// for anon (session-owned Current Roadmap) — no login required.
function toggleRoadmapSharePanel() {
    const panel = document.getElementById('roadmapSharePanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

async function initializeRoadmapSharePanel() {
    try {
        const response = await fetch(`${API_BASE}/roadmaps/current/share/`);
        if (!response.ok) return;
        const data = await response.json();

        const privacyRadio = document.querySelector(`input[name="roadmap-privacy"][value="${data.privacy_setting}"]`);
        if (privacyRadio) privacyRadio.checked = true;

        if (data.is_public && data.shareable_url) {
            showRoadmapShareableUrl(window.location.origin + data.shareable_url);
        } else {
            hideRoadmapShareableUrl();
        }
    } catch (error) {
        console.log('Could not load roadmap sharing settings', error);
    }
}

async function updateRoadmapPrivacySetting(privacySetting) {
    try {
        const response = await fetch(`${API_BASE}/roadmaps/current/share/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ privacy_setting: privacySetting })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.is_public && data.shareable_url) {
                showRoadmapShareableUrl(window.location.origin + data.shareable_url);
            } else {
                hideRoadmapShareableUrl();
            }
            showNotification(privacySetting === 'public' ?
                'Roadmap is now public and shareable!' :
                'Roadmap is now private', 'success');
        } else {
            const errorData = await response.json();
            showNotification(errorData.error || 'Failed to update roadmap sharing', 'error');
        }
    } catch (error) {
        showNotification('Error updating roadmap sharing. Please try again.', 'error');
    }
}

function showRoadmapShareableUrl(url) {
    const section = document.getElementById('roadmap-shareable-url-section');
    const input = document.getElementById('roadmap-shareable-url');
    input.value = url;
    section.style.display = 'block';
}

function hideRoadmapShareableUrl() {
    document.getElementById('roadmap-shareable-url-section').style.display = 'none';
}

function copyRoadmapShareableUrl() {
    const input = document.getElementById('roadmap-shareable-url');
    input.select();
    input.setSelectionRange(0, 99999);
    try {
        document.execCommand('copy');
        showNotification('URL copied to clipboard!', 'success');
        const copyBtn = document.getElementById('roadmap-copy-url-btn');
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '✅ Copied!';
        setTimeout(() => { copyBtn.innerHTML = originalText; }, 2000);
    } catch (err) {
        showNotification('Failed to copy URL', 'error');
    }
}

function toggleSection(sectionKey) {
    const content = document.getElementById(`content-${sectionKey}`);
    const toggle = document.getElementById(`toggle-${sectionKey}`);
    
    if (!content || !toggle) return;
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.style.transform = 'rotate(0deg)';
    } else {
        content.style.display = 'none';
        toggle.style.transform = 'rotate(-90deg)';
    }
}

async function loadData() {
    try {
        // Load spending categories
        const categoriesResponse = await fetch(`${API_BASE}/cards/spending-categories/`);
        const categoriesData = await categoriesResponse.json();
        
        // Load spending credits
        const creditsResponse = await fetch(`${API_BASE}/cards/spending-credits/`);
        const creditsData = await creditsResponse.json();
        spendingCredits = creditsData.results || creditsData;
        
        // Handle both paginated and non-paginated responses
        const categories = categoriesData.results || categoriesData;
        
        if (Array.isArray(categories)) {
            // Sort categories by sort_order
            categories.sort((a, b) => (a.sort_order || 100) - (b.sort_order || 100));
            
            // Store the categories array for parent/child logic
            spendingCategoriesArray = categories;
            
            // Build spending categories mapping
            categories.forEach(cat => {
                spendingCategories[cat.slug] = cat.id;
            });
            
            // Render spending categories in the UI
            renderSpendingCategories(categories);
            renderExpenseCategoryOptions(categories);
        } else {
            console.error('Categories response is not an array:', typeof categories);
        }
        
        // Load issuers for the dropdown
        await loadIssuers();
        
        // Load saved spending and preferences
        await loadSavedData();

        // Set up auto-save listeners after data is loaded
        setupAutoSave();

        // Set up total calculation
        setupTotalCalculation();

        // Restore the last generated roadmap, if any, so it survives a reload
        await loadCurrentRoadmap();
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('spendingCategories').innerHTML = 
            '<div class="error">Error loading spending categories. Please try again.</div>';
    }
}

async function loadIssuers() {
    try {
        const issuersResponse = await fetch(`${API_BASE}/cards/issuers/`);
        const issuersData = await issuersResponse.json();
        const issuers = issuersData.results || issuersData;
        
        const issuerSelect = document.getElementById('issuer');
        
        // Sort issuers alphabetically
        issuers.sort((a, b) => a.name.localeCompare(b.name));
        
        // Add each issuer as an option
        issuers.forEach(issuer => {
            const option = document.createElement('option');
            option.value = issuer.name;
            option.textContent = issuer.name;
            issuerSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading issuers:', error);
    }
}

// Material Symbols per category slug (Ledger redesign) — falls back to
// emoji defaultIcons below for slugs not in this curated list.
const CATEGORY_ICONS = {
    'dining': 'restaurant',
    'groceries': 'shopping_cart',
    'travel': 'flight',
    'gas': 'local_gas_station',
    'streaming': 'play_circle',
    'entertainment': 'play_circle',
    'general': 'category',
    'other': 'category',
    'shopping': 'shopping_bag',
    'online-shopping': 'shopping_bag',
    'amazon': 'shopping_bag',
    'utilities': 'bolt',
    'transportation': 'directions_car'
};

function renderSpendingCategories(categories) {
    const container = document.getElementById('spendingCategories');

    // Default icons for categories
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
    
    // Filter to only show parent categories (no parent field)
    const parentCategories = categories.filter(cat => !cat.parent);
    
    const html = parentCategories.map(category => {
        const displayName = category.display_name || category.name;
        const description = category.description || '';
        const slug = category.slug;
        
        // Handle icon - prefer a curated Material Symbol, fallback to emoji/FA/default
        let iconHtml = '';
        if (CATEGORY_ICONS[slug]) {
            iconHtml = `<span class="ico" style="font-size: 19px; margin-right: 8px; color: var(--accent);">${CATEGORY_ICONS[slug]}</span>`;
        } else if (category.icon && category.icon.includes('fa-')) {
            // Font Awesome icon
            iconHtml = `<i class="${category.icon}" style="font-size: 18px; margin-right: 8px; width: 20px; text-align: center;"></i>`;
        } else if (category.icon && !category.icon.includes('fa-')) {
            // Emoji or other text icon
            iconHtml = `<span style="font-size: 20px; margin-right: 8px;">${category.icon}</span>`;
        } else {
            // Default emoji based on slug
            const defaultIcon = defaultIcons[slug] || '💳';
            iconHtml = `<span style="font-size: 20px; margin-right: 8px;">${defaultIcon}</span>`;
        }
        
        // Create a safe HTML ID by replacing hyphens with underscores
        const htmlId = slug.replace(/-/g, '_');
        
        // Create tooltip for description
        const tooltipHtml = description ? 
            `<span class="tooltip-icon" title="${description}">❓</span>` : '';
        
        // Check if this category has subcategories
        const hasSubcategories = category.subcategories && category.subcategories.length > 0;
        
        let categoryHtml = `
            <div class="spending-item main-category-item">
                <div class="input-group">
                    <span class="input-group-text category-label" style="min-width: 160px;">
                        ${iconHtml}${displayName} ${tooltipHtml}
                    </span>
                    <span class="input-group-text" style="border-left: none;">$</span>
                    <input type="number" id="${htmlId}" data-category-slug="${slug}"
                           placeholder="0" min="0" step="10" class="form-control spending-input"
                           ${hasSubcategories ? 'readonly' : ''}>
                </div>
                ${hasSubcategories ? '<div style="font-size: 12px; color: var(--muted); margin-top: 4px; margin-left: 10px;"><em>Total calculated from subcategories below</em></div>' : ''}
            </div>
        `;
        
        // Add subcategories if they exist
        if (category.subcategories && category.subcategories.length > 0) {
            category.subcategories.forEach(subcat => {
                const subDisplayName = subcat.display_name || subcat.name;
                const subSlug = subcat.slug;
                const subHtmlId = subSlug.replace(/-/g, '_');
                const subDescription = subcat.description || '';
                const subTooltipHtml = subDescription ? 
                    `<span class="tooltip-icon" title="${subDescription}">❓</span>` : '';
                
                // Handle subcategory icon
                let subIconHtml = '';
                if (subcat.icon && subcat.icon.includes('fa-')) {
                    subIconHtml = `<i class="${subcat.icon}" style="font-size: 14px; margin-right: 8px; width: 16px; text-align: center; color: var(--muted);"></i>`;
                } else if (subcat.icon && !subcat.icon.includes('fa-')) {
                    subIconHtml = `<span style="font-size: 14px; margin-right: 8px; opacity: 0.7;">${subcat.icon}</span>`;
                } else {
                    subIconHtml = `<span style="font-size: 14px; margin-right: 8px; color: var(--muted-2);">↳</span>`;
                }

                categoryHtml += `
                    <div class="spending-item subcategory-item">
                        <div class="input-group">
                            <span class="input-group-text subcategory-label" style="min-width: 140px;">
                                ${subIconHtml}${subDisplayName} ${subTooltipHtml}
                            </span>
                            <span class="input-group-text" style="border-left: none;">$</span>
                            <input type="number" id="${subHtmlId}" data-category-slug="${subSlug}"
                                   placeholder="0" min="0" step="10" class="form-control spending-input" style="font-size: 13px;">
                        </div>
                    </div>
                `;
            });
        }
        
        // Add spending credits for this category if they exist
        const categoryCredits = spendingCredits.filter(credit => credit.category.slug === slug);
        if (categoryCredits && categoryCredits.length > 0) {
            categoryHtml += `
                <div class="spending-credits-section" style="margin-top: 10px; margin-left: 20px;">
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 8px; font-weight: 500;">
                        Credits You Use:
                    </div>
                    <div class="spending-credits-list" style="display: block !important; width: 100%;">
            `;

            categoryCredits.forEach(credit => {
                const creditDescription = credit.description ?
                    `<span class="tooltip-icon" title="${credit.description}" style="margin-left: 4px;">❓</span>` : '';
                const stackabilityHint = credit.stackable === false ?
                    `<span style="color: var(--muted); font-size: 11px; margin-left: 4px;" title="If you hold more than one card with this credit, it only counts once toward your total">(counted once across cards)</span>` : '';

                categoryHtml += `
                    <div class="spending-credit-item" style="display: flex !important; align-items: center !important; gap: 6px; font-size: 12px; width: 100% !important; margin-bottom: 8px; flex-wrap: nowrap !important;">
                        <input type="checkbox" id="credit_${credit.slug}" name="spending_credit_preferences"
                               value="${credit.slug}" onchange="handleSpendingCreditChange(this)">
                        <label for="credit_${credit.slug}" style="cursor: pointer; color: var(--text); font-weight: normal; margin: 0;">
                            ${credit.icon ? `${credit.icon} ` : ''}${credit.display_name}${creditDescription}${stackabilityHint}
                        </label>
                    </div>
                `;
            });
            
            categoryHtml += `
                    </div>
                </div>
            `;
        }
        
        return categoryHtml;
    }).join('');
    
    container.innerHTML = html;
}

// Phase N: flat parent + indented-subcategory option list for the
// "Upcoming large purchase" category picker, sharing the same
// categories payload as renderSpendingCategories() above.
function renderExpenseCategoryOptions(categories) {
    const select = document.getElementById('expenseCategory');
    if (!select) return;

    const options = ['<option value="">General / any category</option>'];
    categories.filter(cat => !cat.parent).forEach(category => {
        const displayName = category.display_name || category.name;
        options.push(`<option value="${category.id}">${displayName}</option>`);
        (category.subcategories || []).forEach(subcat => {
            const subDisplayName = subcat.display_name || subcat.name;
            options.push(`<option value="${subcat.id}">&nbsp;&nbsp;↳ ${subDisplayName}</option>`);
        });
    });
    select.innerHTML = options.join('');
}

function handleSpendingCreditChange(checkbox) {
    // Save spending credit preferences
    saveSpendingCreditPreferences();
}

function setupTotalCalculation() {
    // Update total whenever any spending input changes
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('spending-input')) {
            updateTotal();
            updateParentCategoryTotals();
        }
    });
    
    // Initial calculation
    updateTotal();
    updateParentCategoryTotals();
}

function updateTotal() {
    const mode = localStorage.getItem('spending_mode') || 'category';
    let total = 0;
    if (mode === 'easy') {
        const amount = parseFloat(document.getElementById('easySpendingAmount').value) || 0;
        const interval = document.getElementById('easySpendingInterval').value;
        total = interval === 'yearly' ? amount / 12 : amount;
    } else {
        const spendingInputs = document.querySelectorAll('.spending-input:not([readonly])');
        spendingInputs.forEach(input => {
            const value = parseFloat(input.value) || 0;
            total += value;
        });
    }
    document.getElementById('totalSpending').textContent = Math.round(total).toLocaleString();
}

function updateParentCategoryTotals() {
    // Update parent category totals based on their subcategories
    if (!spendingCategoriesArray || spendingCategoriesArray.length === 0) return;
    
    const parentCategories = spendingCategoriesArray.filter(cat => !cat.parent);
    
    parentCategories.forEach(parentCategory => {
        // Skip if this parent doesn't have subcategories
        if (!parentCategory.subcategories || parentCategory.subcategories.length === 0) {
            return;
        }
        
        // Calculate total from all subcategories
        let subcategoryTotal = 0;
        parentCategory.subcategories.forEach(subcat => {
            const subInput = document.getElementById(subcat.slug.replace(/-/g, '_'));
            if (subInput) {
                const value = parseFloat(subInput.value) || 0;
                subcategoryTotal += value;
            }
        });
        
        // Update the parent category input
        const parentInput = document.getElementById(parentCategory.slug.replace(/-/g, '_'));
        if (parentInput) {
            parentInput.value = subcategoryTotal > 0 ? subcategoryTotal : '';
        }
    });
}

function resetSpendingProfile() {
    if (confirm('Are you sure you want to reset all spending amounts and spending credit preferences? This action cannot be undone.')) {
        // Clear all spending inputs (only editable ones)
        const spendingInputs = document.querySelectorAll('.spending-input:not([readonly])');
        spendingInputs.forEach(input => {
            input.value = '';
        });
        
        // Clear readonly parent category inputs as well
        const readonlyInputs = document.querySelectorAll('.spending-input[readonly]');
        readonlyInputs.forEach(input => {
            input.value = '';
        });
        
        // Clear all spending credit preference checkboxes
        const spendingCreditCheckboxes = document.querySelectorAll('input[name="spending_credit_preferences"]');
        spendingCreditCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Clear easy mode inputs as well
        const easyAmountInput = document.getElementById('easySpendingAmount');
        if (easyAmountInput) easyAmountInput.value = '';
        
        // Update the total display
        updateTotal();
        
        // Clear saved data
        clearSavedData();
        
        // Show success message
        const totalSection = document.getElementById('totalSpending').parentElement;
        const originalBg = totalSection.style.background;
        totalSection.style.background = 'var(--accent-soft)';
        setTimeout(() => {
            totalSection.style.background = originalBg;
        }, 2000);
        
        console.log('Spending profile and credit preferences have been reset');
    }
}

async function clearSavedData() {
    try {
        // Clear spending data
        await UserDataManager.saveSpending({});

        // Persist cleared credit preferences (resetSpendingProfile
        // already unchecked the checkboxes before calling this).
        await saveSpendingCreditPreferences();

        console.log('Saved data cleared successfully');
    } catch (error) {
        console.error('Error clearing saved data:', error);
    }
}

// Phase K: auth-only household summary line, linking to the
// profile page's Household management panel. Anon users stay
// single-player, so this stays hidden for them entirely.
async function loadHouseholdSummaryLine() {
    const line = document.getElementById('householdSummaryLine');
    if (!isAuthenticated) {
        line.style.display = 'none';
        return;
    }
    try {
        const entities = await UserDataManager.getEntities();
        const players = entities.filter(e => e.kind !== 'business').length;
        const businesses = entities.filter(e => e.kind === 'business').length;
        document.getElementById('householdSummaryText').textContent =
            `Household: ${players} player${players === 1 ? '' : 's'} · ${businesses} business${businesses === 1 ? '' : 'es'}`;
        line.style.display = 'block';
    } catch (error) {
        console.error('Error loading household summary:', error);
        line.style.display = 'none';
    }
}

async function loadSavedData() {
    try {
        // Wait for user state to be initialized
        await initUserState();
        await loadHouseholdSummaryLine();

        // Load spending data
        const savedSpending = await UserDataManager.getSpending();
        Object.keys(savedSpending).forEach(categorySlug => {
            const amount = savedSpending[categorySlug];
            // Convert slug to HTML ID (replace hyphens with underscores)
            const htmlId = categorySlug.replace(/-/g, '_');
            const input = document.getElementById(htmlId);
            if (input && amount) {
                input.value = amount;
            }
        });
        
        // Determine spending mode
        let spendingMode = localStorage.getItem('spending_mode') || 'category';
        const nonZeroCategories = Object.keys(savedSpending).filter(slug => parseFloat(savedSpending[slug]) > 0);
        if (nonZeroCategories.length === 1 && nonZeroCategories[0] === 'other' && !localStorage.getItem('spending_mode')) {
            spendingMode = 'easy';
        }
        
        // Populate easy mode input if other exists
        const easyAmountInput = document.getElementById('easySpendingAmount');
        const easyIntervalSelect = document.getElementById('easySpendingInterval');
        const interval = localStorage.getItem('easy_spending_interval') || 'monthly';
        if (easyIntervalSelect) {
            easyIntervalSelect.value = interval;
        }
        if (easyAmountInput && savedSpending['other']) {
            const monthlyAmount = parseFloat(savedSpending['other']) || 0;
            easyAmountInput.value = interval === 'yearly' ? monthlyAmount * 12 : monthlyAmount;
        }

        setSpendingMode(spendingMode, false); // Initialize mode display and total
        updateParentCategoryTotals();
        
        // Load preferences
        const savedPreferences = await UserDataManager.getPreferences();
        if (savedPreferences.default_issuer_filter) {
            const issuerSelect = document.getElementById('issuer');
            if (issuerSelect) issuerSelect.value = savedPreferences.default_issuer_filter;
        }
        if (savedPreferences.default_reward_type_filter) {
            const rewardTypeSelect = document.getElementById('rewardType');
            if (rewardTypeSelect) rewardTypeSelect.value = savedPreferences.default_reward_type_filter;
        }
        if (savedPreferences.default_max_fee_filter) {
            const maxFeeInput = document.getElementById('maxFee');
            if (maxFeeInput) maxFeeInput.value = savedPreferences.default_max_fee_filter;
        }
        if (savedPreferences.default_max_recommendations) {
            const maxRecsSelect = document.getElementById('maxRecs');
            if (maxRecsSelect) maxRecsSelect.value = savedPreferences.default_max_recommendations;
        }

        // Restore strategy selection (highlight/picker only — saved
        // preferences already reflect any defaults the preset applied)
        const savedStrategy = localStorage.getItem('userStrategy') || '';
        if (savedStrategy && strategyByKey(savedStrategy)) {
            setStrategy(savedStrategy, false);
        }

        // Load spending credit preferences after a short delay to ensure they are rendered
        setTimeout(() => {
            loadSpendingCreditPreferences();
        }, 500);
    } catch (error) {
        console.error('Error loading saved data:', error);
    }
}

async function saveSpendingCreditPreferences() {
    try {
        // Send the full checkbox state (not just the checked ones) so
        // unchecking a credit persists an explicit False, not just
        // the absence of a True.
        const preferences = {};
        document.querySelectorAll('input[name="spending_credit_preferences"]').forEach(checkbox => {
            preferences[checkbox.value] = checkbox.checked;
        });

        await UserDataManager.saveCreditPreferences(preferences);
    } catch (error) {
        console.error('Error saving spending credit preferences:', error);
    }
}

async function loadSpendingCreditPreferences() {
    try {
        const preferences = await UserDataManager.getCreditPreferences();
        Object.entries(preferences).forEach(([creditSlug, valuesCredit]) => {
            const checkbox = document.querySelector(`input[name="spending_credit_preferences"][value="${creditSlug}"]`);
            if (checkbox) {
                checkbox.checked = valuesCredit;
            }
        });
    } catch (error) {
        console.error('Error loading spending credit preferences:', error);
    }
}

async function saveCurrentData() {
    try {
        const mode = localStorage.getItem('spending_mode') || 'category';
        const spendingData = {};
        
        if (mode === 'easy') {
            const amount = parseFloat(document.getElementById('easySpendingAmount').value) || 0;
            const interval = document.getElementById('easySpendingInterval').value;
            const monthlyAmount = interval === 'yearly' ? amount / 12 : amount;
            if (monthlyAmount > 0) {
                spendingData['other'] = monthlyAmount;
            }
        } else {
            // Save spending data (only from editable inputs - subcategories and standalone categories)
            const spendingInputs = document.querySelectorAll('.spending-input:not([readonly])');
            spendingInputs.forEach(input => {
                const categorySlug = input.dataset.categorySlug;
                const value = input.value;
                if (value && categorySlug) {
                    spendingData[categorySlug] = parseFloat(value) || 0;
                }
            });
        }
        
        // Save preferences
        const preferencesData = {
            default_issuer_filter: document.getElementById('issuer')?.value || '',
            default_reward_type_filter: document.getElementById('rewardType')?.value || '',
            default_max_fee_filter: parseFloat(document.getElementById('maxFee')?.value) || null,
            default_max_recommendations: parseInt(document.getElementById('maxRecs')?.value) || 1
        };

        // Use the unified data manager to save
        await UserDataManager.saveSpending(spendingData);
        
        // Save spending credit preferences
        await saveSpendingCreditPreferences();
        
        // For preferences, we need to save them separately since UserDataManager 
        // doesn't have a savePreferences method yet
        if (isAuthenticated) {
            try {
                await fetch(`${API_BASE}/users/data/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        spending: spendingData,
                        cards: await UserDataManager.getCards(),
                        preferences: preferencesData
                    })
                });
            } catch (error) {
                console.error('Error saving to server:', error);
            }
        } else {
            // Save preferences to localStorage for anonymous users
            localStorage.setItem('userPreferences', JSON.stringify(preferencesData));
        }
        
    } catch (error) {
        console.error('Error saving current data:', error);
    }
}

async function loadCurrentRoadmap() {
    try {
        const response = await fetch(`${API_BASE}/roadmaps/current/`);
        if (!response.ok) {
            // 404 = nothing generated yet: first-time-user path, builder
            // open, nothing to "update" yet.
            setRoadmapViewMode('builder');
            document.getElementById('resultsHeader').style.display = 'none';
            return;
        }
        const data = await response.json();
        const generatedAt = data.generated_at ? new Date(data.generated_at) : null;
        const banner = generatedAt
            ? `Generated on ${generatedAt.toLocaleDateString()} — inputs may have changed`
            : '';
        renderRoadmapResults(data, {
            container: document.getElementById('results'),
            banner,
            noScroll: true
        });
        setRoadmapViewMode('results');
        document.getElementById('resultsHeader').style.display = 'block';
        initializeRoadmapSharePanel();
    } catch (error) {
        console.error('Error loading current roadmap:', error);
    }
}

async function getRecommendations() {
    // Collapse preferences section
    const preferencesContent = document.getElementById('preferencesContent');
    const preferencesToggle = document.getElementById('preferencesToggle');
    if (preferencesContent.style.display !== 'none') {
        preferencesContent.style.display = 'none';
        preferencesToggle.textContent = '▼ Click to expand';
    }
    
    // Save current data before getting recommendations
    await saveCurrentData();
    
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">🔄 Analyzing your profile and generating recommendations...</div>';
    
    // Scroll to loading message so user sees immediate feedback
    setTimeout(() => {
        resultsDiv.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }, 100);

    try {
        // Build spending amounts object
        const spendingAmounts = {};
        const mode = localStorage.getItem('spending_mode') || 'category';
        
        if (mode === 'category') {
            // Build spending amounts from dynamic inputs (only editable ones - subcategories and standalone categories)
            const spendingInputs = document.querySelectorAll('.spending-input:not([readonly])');
            spendingInputs.forEach(input => {
                const categorySlug = input.dataset.categorySlug;
                const amount = input.value;
                const categoryId = spendingCategories[categorySlug];
                
                if (amount && amount > 0 && categoryId) {
                    spendingAmounts[categoryId] = parseFloat(amount);
                }
            });
        }

        // Build user cards array from saved data. Authenticated users
        // already have their real UserCard rows in the DB (just
        // persisted by saveCurrentData() above) — the engine reads
        // those directly, so sending this placeholder payload would
        // make the scratch rewrite (roadmaps/serializers.py) flatten
        // real opened dates, bonus overrides, and owners back to
        // defaults. Anonymous users have no DB rows, so they still
        // need to send their session/localStorage card list.
        let userCards;
        if (!isAuthenticated) {
            const userCardIds = await UserDataManager.getCards();
            userCards = userCardIds.map(cardId => ({
                card_id: cardId,
                opened_date: '2023-01-01', // Default date
                nickname: '',
                is_active: true
            }));
        }

        // Build filters array
        const filters = [];
        const cardType = document.getElementById('cardType').value;
        const issuer = document.getElementById('issuer').value;
        const rewardType = document.getElementById('rewardType').value;
        const maxFee = document.getElementById('maxFee').value;

        if (cardType && cardType !== 'all') {
            filters.push({
                name: 'Card Type Filter',
                filter_type: 'card_type',
                value: cardType
            });
        }
        if (issuer) {
            filters.push({
                name: 'Issuer Filter',
                filter_type: 'issuer',
                value: issuer
            });
        }
        if (rewardType) {
            filters.push({
                name: 'Reward Type Filter',
                filter_type: 'reward_type',
                value: rewardType
            });
        }
        if (maxFee) {
            filters.push({
                name: 'Annual Fee Filter',
                filter_type: 'annual_fee',
                value: `0-${maxFee}`
            });
        }

        // Get selected spending credit preferences
        const selectedSpendingCredits = [];
        const spendingCreditCheckboxes = document.querySelectorAll('input[name="spending_credit_preferences"]:checked');
        spendingCreditCheckboxes.forEach(checkbox => {
            selectedSpendingCredits.push(checkbox.value);
        });

        const requestData = {
            user_cards: userCards,
            filters: filters,
            max_recommendations: parseInt(document.getElementById('maxRecs').value) || 1,
            spending_credit_preferences: selectedSpendingCredits,
            strategy: selectedStrategy
        };

        if (mode === 'easy') {
            const amount = parseFloat(document.getElementById('easySpendingAmount').value) || 0;
            const interval = document.getElementById('easySpendingInterval').value;
            requestData.easy_mode_spending = {
                amount: amount,
                interval: interval
            };
            requestData.spending_amounts = {};
        } else {
            requestData.spending_amounts = spendingAmounts;
        }

        // Phase N: optional one-off upcoming expense — omitted
        // entirely (not sent as 0/null) when the amount is blank,
        // so the response's expense_recommendation panel only
        // appears when the user actually asked for one.
        const expenseAmountValue = parseFloat(document.getElementById('expenseAmount').value);
        if (expenseAmountValue > 0) {
            const expenseCategoryId = document.getElementById('expenseCategory').value;
            requestData.expense = {
                amount: expenseAmountValue,
                category_id: expenseCategoryId ? parseInt(expenseCategoryId) : null
            };
        }

        const response = await fetch(`${API_BASE}/roadmaps/quick-recommendation/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (data.error) {
            resultsDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
            return;
        }

        // Display recommendations
        const activePreset = strategyByKey(selectedStrategy);
        renderRoadmapResults(data, {
            container: resultsDiv,
            strategyLabel: activePreset ? activePreset.name : '',
            poolLabel: activePreset ? activePreset.pool_label : ''
        });
        // Settle into results mode — matches what a reload will show now
        // that this roadmap is persisted as the Current Roadmap.
        setRoadmapViewMode('results');
        document.getElementById('resultsHeader').style.display = 'block';
        initializeRoadmapSharePanel();

    } catch (error) {
        resultsDiv.innerHTML = '<div class="error">Error generating recommendations. Please try again.</div>';
        console.error('Error:', error);
        
        // Scroll to results even on error so user can see the error message
        setTimeout(() => {
            const resultsElement = document.getElementById('results');
            if (resultsElement) {
                resultsElement.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }
        }, 100);
    }
}

// Helper functions for data extraction
function getSpendingData() {
    const spendingData = {};
    document.querySelectorAll('input[data-category-slug]').forEach(input => {
        const category = input.getAttribute('data-category-slug');
        const value = parseFloat(input.value) || 0;
        if (value > 0) {
            spendingData[category] = value;
        }
    });
    return spendingData;
}

async function getSelectedCards() {
    const selectedCards = {
        owned: [],
        available: []
    };
    
    try {
        // Get owned cards from UserDataManager
        const userCardIds = await UserDataManager.getCards();
        
        // Convert card IDs to names if we have access to the cards data
        // For now, just return the IDs - the backend can resolve them
        selectedCards.owned = userCardIds.map(cardId => ({ 
            id: cardId,
            name: `Card ID: ${cardId}` // Placeholder - backend will resolve
        }));
        
    } catch (error) {
        console.error('Error getting selected cards:', error);
    }
    
    return selectedCards;
}

function getFilters() {
    return {
        cardType: document.getElementById('cardType')?.value || 'personal',
        issuer: document.getElementById('issuer')?.value || null,
        rewardType: document.getElementById('rewardType')?.value || 'Points',
        maxFee: parseFloat(document.getElementById('maxFee')?.value) || null,
        maxRecommendations: parseInt(document.getElementById('maxRecommendations')?.value) || 1
    };
}

function getSelectedSpendingCredits() {
    const selectedCredits = [];
    document.querySelectorAll('.credit-checkbox-item input[type="checkbox"]:checked').forEach(checkbox => {
        const creditId = checkbox.getAttribute('data-credit-id');
        const creditName = checkbox.closest('.spending-credit-item')?.querySelector('label')?.textContent?.trim();
        if (creditId) {
            selectedCredits.push({
                id: parseInt(creditId),
                name: creditName || 'Unknown Credit'
            });
        }
    });
    return selectedCredits;
}

async function exportToScenario() {
    const spendingData = getSpendingData();
    const selectedCards = await getSelectedCards();
    const filters = getFilters();
    const selectedSpendingCredits = getSelectedSpendingCredits();
    
    // Calculate total monthly spending for scaling
    const totalMonthlySpending = Object.values(spendingData)
        .reduce((sum, amount) => sum + parseFloat(amount || 0), 0);
    
    // Build the test scenario object
    const scenario = {
        name: `Custom Scenario - ${new Date().toLocaleDateString()}`,
        description: `Test scenario exported from user input on ${new Date().toLocaleDateString()}`,
        ...(selectedStrategy ? { strategy: selectedStrategy } : {}),
        user_profile: {
            spending: spendingData,
            monthly_spending_total: totalMonthlySpending
        },
        scenario: {
            owned_cards: selectedCards.owned.map(card => card.name),
            available_cards: [], // Will be populated with generic cards
            filters: {
                max_annual_fee: filters.maxFee || null,
                card_type: filters.cardType || 'personal',
                preferred_reward_type: filters.rewardType || 'Points',
                issuer: filters.issuer || null,
                max_recommendations: filters.maxRecommendations || 1
            },
            spending_credit_preferences: selectedSpendingCredits
        },
        expected_recommendations: {
            actions: ["apply", "keep"],
            min_cards: 1,
            max_cards: filters.maxRecommendations || 1,
            reasoning_must_contain: ["spending", "rewards", "portfolio"],
            test_conditions: [
                "Validates user input scenario",
                "Checks spending pattern optimization",
                "Verifies credit preferences integration"
            ]
        }
    };
    
    try {
        // First, send to API for processing and validation
        const response = await fetch(`${API_BASE}/roadmaps/export-scenario/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(scenario)
        });
        
        const apiResult = await response.json();
        
        if (apiResult.error) {
            alert(`❌ Export failed: ${apiResult.error}`);
            return;
        }
        
        // Create downloadable JSON file with the processed scenario
        const processedScenario = apiResult.scenario || scenario;
        const jsonString = JSON.stringify(processedScenario, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Create download link
        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.download = `test-scenario-${new Date().toISOString().split('T')[0]}.json`;
        
        // Trigger download
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        
        // Clean up the URL object
        URL.revokeObjectURL(url);
        
        // Show success message with debug info
        console.log('Exported scenario:', processedScenario);
        alert(`✅ Test scenario exported successfully!\n\nThe JSON file contains your current spending profile, cards, and preferences.\n\nYou can add this to data/tests/scenarios.json for testing and debugging.\n\nCheck the browser console for the full scenario data.`);
        
    } catch (error) {
        console.error('Export error:', error);
        
        // Fallback: still create the file even if API fails
        const jsonString = JSON.stringify(scenario, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.download = `test-scenario-${new Date().toISOString().split('T')[0]}.json`;
        
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        
        URL.revokeObjectURL(url);
        
        alert(`✅ Test scenario exported (offline mode)\n\nAPI was unavailable, but the scenario file was still created.\nError: ${error.message}`);
    }
}

// Apply mobile-specific classes based on screen size
function applyMobileClasses() {
    const isMobile = window.innerWidth <= 480;
    const preferencesSection = document.querySelector('.preferences-section');
    const spendingSection = document.querySelector('.spending-section');
    const actionButton = document.querySelector('.action-button');
    const resultsSection = document.querySelector('.results');
    
    if (isMobile) {
        preferencesSection?.classList.add('preferences-mobile');
        spendingSection?.classList.add('spending-mobile');
        actionButton?.classList.add('action-button-mobile');
        resultsSection?.classList.add('results-mobile');
    } else {
        preferencesSection?.classList.remove('preferences-mobile');
        spendingSection?.classList.remove('spending-mobile');
        actionButton?.classList.remove('action-button-mobile');
        resultsSection?.classList.remove('results-mobile');
    }
}

// Apply mobile classes on load and resize
window.addEventListener('load', applyMobileClasses);
window.addEventListener('resize', applyMobileClasses);

// Load initial data when page loads
loadData();

// Auto-save when user navigates away
window.addEventListener('beforeunload', function(e) {
    // Save data synchronously (limited time available)
    try {
        const spendingData = {};
        const spendingInputs = document.querySelectorAll('.spending-input:not([readonly])');
        spendingInputs.forEach(input => {
            const categorySlug = input.dataset.categorySlug;
            const value = input.value;
            if (value && categorySlug) {
                spendingData[categorySlug] = parseFloat(value) || 0;
            }
        });
        
        const preferencesData = {
            default_issuer_filter: document.getElementById('issuer')?.value || '',
            default_reward_type_filter: document.getElementById('rewardType')?.value || '',
            default_max_fee_filter: parseFloat(document.getElementById('maxFee')?.value) || null,
            default_max_recommendations: parseInt(document.getElementById('maxRecs')?.value) || 1
        };

        // Use localStorage for immediate saving (works in beforeunload)
        localStorage.setItem('userSpending', JSON.stringify(spendingData));
        localStorage.setItem('userPreferences', JSON.stringify(preferencesData));
        
        // If authenticated, try to save to server (may not complete)
        if (isAuthenticated) {
            navigator.sendBeacon(`${API_BASE}/users/data/`, JSON.stringify({
                spending: spendingData,
                cards: JSON.parse(localStorage.getItem('userCards') || '[]'),
                preferences: preferencesData
            }));
        }
    } catch (error) {
        console.error('Error in beforeunload save:', error);
    }
});

// Auto-save on form changes (debounced)
let saveTimeout;
function debouncedSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveCurrentData, 1000); // Save 1 second after last change
}

function setupAutoSave() {
    // Add listeners to all spending inputs (dynamic)
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('spending-input')) {
            debouncedSave();
        }
    });
    
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('spending-input')) {
            debouncedSave();
        }
    });
    
    // Add listeners to preference inputs
    const preferenceInputs = ['issuer', 'rewardType', 'maxFee', 'maxRecs'];
    preferenceInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('change', debouncedSave);
        }
    });
}

// Card Ownership Modal Functions (copied from cards_list.html)
async function openCardOwnershipModal(cardId, existingUserCard = null, cardType = 'personal') {
    const modal = document.getElementById('cardOwnershipModal');
    const form = document.getElementById('cardOwnershipForm');
    const modalTitle = document.getElementById('modalTitle');

    // Set modal title and add auth status indicator
    if (isAuthenticated) {
        modalTitle.textContent = existingUserCard ? 'Edit Card Details' : 'Add Card to Collection';
    } else {
        modalTitle.innerHTML = existingUserCard ?
            'Edit Card Details <span style="background: #5C6675; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; margin-left: 8px;">Local Mode</span>' :
            'Add Card to Collection <span style="background: #5C6675; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; margin-left: 8px;">Local Mode</span>';
    }

    // Store card ID in form
    form.dataset.cardId = cardId;
    form.dataset.userCardId = existingUserCard ? existingUserCard.id : '';

    // Pre-fill form if editing existing card
    if (existingUserCard) {
        form.nickname.value = existingUserCard.nickname || '';
        form.opened_date.value = existingUserCard.opened_date || '';
        form.closed_date.value = existingUserCard.closed_date || '';
        form.notes.value = existingUserCard.notes || '';
    } else {
        form.reset();
    }

    // Phase K: owner selector — mirrors base.html's edit-card modal.
    // Only shown for authed households with more than one entity of
    // THIS card's own kind; otherwise the backend auto-assigns by
    // card_type on add (see _resolve_owner_entity), so there's
    // nothing to pick.
    const ownerGroup = document.getElementById('cardOwnershipOwnerGroup');
    const ownerSelect = document.getElementById('ownershipOwner');
    const entities = await UserDataManager.getEntities();
    const isBusinessCard = cardType === 'business';
    const candidates = entities.filter(e => (e.kind === 'business') === isBusinessCard);
    if (isAuthenticated && candidates.length > 1) {
        ownerSelect.innerHTML = candidates.map(e =>
            `<option value="${e.id}">${escapeHtml(e.name)}${e.is_primary ? ' (Primary)' : ''}</option>`
        ).join('');
        const defaultId = candidates.find(e => e.is_primary)?.id || candidates[0].id;
        ownerSelect.value = (existingUserCard && existingUserCard.owner) ?? defaultId;
        ownerGroup.style.display = 'block';
    } else {
        ownerGroup.style.display = 'none';
    }

    // Show/hide local storage notice
    const localNotice = document.getElementById('localStorageNotice');
    if (localNotice) {
        localNotice.style.display = isAuthenticated ? 'none' : 'block';
    }

    modal.style.display = 'flex';
}

function closeCardOwnershipModal() {
    document.getElementById('cardOwnershipModal').style.display = 'none';
}

async function saveCardOwnership(event) {
    event.preventDefault();
    
    const form = event.target;
    const cardId = form.dataset.cardId;
    const userCardId = form.dataset.userCardId;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    const ownerGroupVisible = document.getElementById('cardOwnershipOwnerGroup').style.display !== 'none';
    const formData = {
        card_id: parseInt(cardId),
        nickname: form.nickname.value,
        opened_date: form.opened_date.value || null,
        closed_date: form.closed_date.value || null,
        notes: form.notes.value
    };
    if (ownerGroupVisible) {
        formData.owner = form.owner.value;
    }

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';

        if (isAuthenticated) {
            // For authenticated users, save to server
            let response;
            if (userCardId) {
                // Update existing card
                response = await fetch(`${API_BASE}/cards/user-cards/${userCardId}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(formData)
                });
            } else {
                // Add new card
                response = await fetch(`${API_BASE}/cards/user-cards/add/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(formData)
                });
            }
            
            if (response.ok) {
                const data = await response.json();
                closeCardOwnershipModal();
                showNotification(data.message || 'Card saved successfully!', 'success');
            } else {
                const errorData = await response.json();
                showNotification(errorData.error || 'Failed to save card', 'error');
            }
        } else {
            // For unauthenticated users, save to local storage
            const localCards = LocalStorage.getCards();
            const localCardDetails = LocalStorage.getCardDetails();
            
            if (userCardId && userCardId.toString().startsWith('local_')) {
                // Update existing local card
                const realCardId = parseInt(cardId);
                localCardDetails[realCardId] = {
                    nickname: formData.nickname,
                    opened_date: formData.opened_date,
                    notes: formData.notes
                };
                LocalStorage.setCardDetails(localCardDetails);
                
                showNotification('Card details updated in your local collection!', 'success');
            } else {
                // Add new card to local storage
                const realCardId = parseInt(cardId);
                if (!localCards.includes(realCardId)) {
                    localCards.push(realCardId);
                    LocalStorage.setCards(localCards);
                }
                
                localCardDetails[realCardId] = {
                    nickname: formData.nickname,
                    opened_date: formData.opened_date,
                    notes: formData.notes
                };
                LocalStorage.setCardDetails(localCardDetails);
                
                showNotification('Card added to your local collection! Log in to sync with your account.', 'success');
            }
            
            closeCardOwnershipModal();
        }
        
    } catch (error) {
        console.error('Error saving card:', error);
        showNotification('Error saving card. Please try again.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = userCardId ? 'Update Card' : 'Add Card';
    }
}
