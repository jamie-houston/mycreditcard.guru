// Shared roadmap results renderer. Used by index.html (live generate +
// "Current Roadmap" restore on page load) and the public shared-roadmap
// page (readOnly: true — no ownership/apply actions).
//
// Depends on globals defined in base.html: API_BASE, isAuthenticated,
// getCookie(), showNotification(), escapeHtml(), UserDataManager, LocalStorage.
// Depends on CATEGORY_ICONS, toggleSection(), openCardModal(),
// openCardOwnershipModal() being defined on the page that calls
// renderRoadmapResults() (index.html).

function _roadmapTopCategoriesLabel(rec) {
    const items = (rec.rewards_breakdown || []).filter(b =>
        b.type !== 'credit' && b.type !== 'info' && b.type !== 'bonus_shift' && (b.category_rewards || 0) > 0);
    items.sort((a, b) => (b.category_rewards || 0) - (a.category_rewards || 0));
    const top = items.slice(0, 2).map(b => b.category_name).filter(Boolean);
    return top.length ? `Best for ${top.join(' & ')}` : (rec.reasoning || '');
}

function _roadmapFormatSigned(value) {
    const v = parseFloat(value) || 0;
    return v < 0 ? `−$${Math.abs(v).toFixed(0)}` : `$${v.toFixed(0)}`;
}

// Phase K3: "as {name}" suffix for apply recommendations attributed to a
// specific household entity (rec.apply_as, set by the engine only when the
// profile has >1 entity — see roadmaps/recommendation_engine.py). Absent
// on old/anon payloads and single-entity households, so this returns ''.
function _roadmapApplyAsLabel(rec) {
    if (!rec.apply_as || !rec.apply_as.name) {
        return '';
    }
    return ` · as ${escapeHtml(rec.apply_as.name)}`;
}

// Phase E timing label. `recommendedMonth` is the engine's month offset
// (0/null = no bonus window to wait on — "apply now"); `baseDate` is the
// roadmap's generated_at (or "now" as a fallback for older persisted data).
function _roadmapTimingLabel(recommendedMonth, baseDate) {
    if (!recommendedMonth) {
        return 'Apply now';
    }
    const target = new Date(baseDate.getTime());
    target.setMonth(target.getMonth() + recommendedMonth);
    const monthYear = target.toLocaleString('en-US', { month: 'short', year: 'numeric' });
    return `Apply in ~${recommendedMonth} month${recommendedMonth === 1 ? '' : 's'} (${monthYear})`;
}

function _roadmapBenefitsValue(rec) {
    return (rec.rewards_breakdown || [])
        .filter(b => b.type === 'credit')
        .reduce((sum, b) => sum + (parseFloat(b.category_rewards) || 0), 0);
}

// Everything that isn't a credit — category rewards plus bonus-shift
// opportunity-cost adjustments. Together with benefits, signup bonus and
// fee this reconciles exactly to estimated_rewards (see recommendation_engine's
// reconciliation guard), so the summary table's columns add up to Value/yr.
function _roadmapRewardsValue(rec) {
    return (rec.rewards_breakdown || [])
        .filter(b => b.type !== 'credit')
        .reduce((sum, b) => sum + (parseFloat(b.category_rewards) || 0), 0);
}

// F4: collapse the (possibly several) bonus_shift breakdown items — one per
// spending source moved to meet a signup bonus — into a single display row.
// Returns null when there's nothing to show (no shifts, or they net to $0),
// otherwise {total, title} where title is the per-source detail for a tooltip.
function _roadmapBonusShiftAggregate(bonusShifts) {
    if (!bonusShifts || bonusShifts.length === 0) {
        return null;
    }
    const total = bonusShifts.reduce((sum, item) => sum + item.value, 0);
    if (Math.round(total) === 0) {
        return null;
    }
    const title = bonusShifts
        .map(item => item.calculation || item.name)
        .filter(Boolean)
        .join('\n');
    return { total, title };
}

// Phase I: groups the engine's per-category -> per-card allocation
// (roadmaps/recommendation_engine.py _calculate_portfolio_allocation, via
// portfolio_summary.category_allocation) into one row group per spending
// category — the full "who actually earns this spend" list, cap rollover
// and uncovered spend included. Entries arrive already ordered
// primary-earner-first per category (then uncovered last, if any) — this
// only groups, it doesn't re-sort.
function _roadmapCategoryMatrix(categoryAllocation) {
    const groups = [];
    const bySlug = {};
    (categoryAllocation || []).forEach(entry => {
        let group = bySlug[entry.category_slug];
        if (!group) {
            group = { slug: entry.category_slug, category_name: entry.category_name, rows: [], total_rewards: 0 };
            bySlug[entry.category_slug] = group;
            groups.push(group);
        }
        group.rows.push({
            card_id: entry.card_id,
            card_name: entry.card_name,
            rate: entry.rate,
            annual_spend: entry.annual_spend,
            annual_rewards: entry.annual_rewards,
            uncovered: !!entry.uncovered,
        });
        group.total_rewards += entry.annual_rewards || 0;
    });
    return groups;
}

// Phase I: portfolio-level first-year vs ongoing summary. Only 'keep'/
// 'apply' recs count toward the portfolio (matches _calculate_portfolio_summary's
// own card set — cancel/upgrade/downgrade recs aren't part of it). Per-card
// first_year_value/ongoing_value already reconcile to estimated_rewards, so
// this is just a sum — one headline for "this year" vs "every year after"
// instead of requiring the user to open each card's breakdown.
function _roadmapValueOverTime(recommendations) {
    const portfolioRecs = (recommendations || []).filter(rec => rec.action === 'keep' || rec.action === 'apply');
    const firstYear = portfolioRecs.reduce((sum, rec) => sum + (parseFloat(rec.first_year_value) || 0), 0);
    const ongoing = portfolioRecs.reduce((sum, rec) => sum + (parseFloat(rec.ongoing_value) || 0), 0);
    return { first_year: firstYear, ongoing, first_year_extras: firstYear - ongoing };
}

const ROADMAP_ACTION_LABELS = { apply: 'Apply', keep: 'Keep', cancel: 'Cancel', upgrade: 'Upgrade', downgrade: 'Downgrade' };
const ROADMAP_ACTION_DANGER = { cancel: true };

function _roadmapSummaryTableHtml(recommendations) {
    const order = ['apply', 'keep', 'cancel', 'upgrade', 'downgrade'];
    const rows = order
        .flatMap(action => {
            const group = recommendations.filter(rec => rec.action === action);
            if (renderRoadmapResults.state && renderRoadmapResults.state.sortMode === 'selffunding') {
                group.sort((a, b) => {
                    const aSelf = a.pays_for_itself ? 1 : 0;
                    const bSelf = b.pays_for_itself ? 1 : 0;
                    return bSelf - aSelf;
                });
            } else if (action === 'apply') {
                group.sort((a, b) => (a.recommended_month || 0) - (b.recommended_month || 0) || a.priority - b.priority);
            }
            return group;
        })
        .map(rec => {
            const danger = !!ROADMAP_ACTION_DANGER[rec.action];
            const annualFee = parseFloat(rec.card.effective_annual_fee || 0);
            const feeWaived = rec.card.annual_fee_waived_first_year && rec.action === 'apply';
            const feeLabel = annualFee > 0 ? (feeWaived ? '$0*' : `−$${annualFee.toFixed(0)}`) : '$0';
            const rewardsValue = _roadmapRewardsValue(rec);
            const rewardsLabel = _roadmapFormatSigned(rewardsValue);
            const signupBonusValue = rec.action === 'apply' ? (parseFloat(rec.signup_bonus_value) || 0) : 0;
            const signupBonusLabel = signupBonusValue > 0 ? `+$${signupBonusValue.toFixed(0)}` : '—';
            const benefitsValue = _roadmapBenefitsValue(rec);
            const benefitsLabel = benefitsValue > 0 ? `+$${benefitsValue.toFixed(0)}` : '—';
            const estimatedValue = parseFloat(rec.estimated_rewards) || 0;

            return `
                <tr class="roadmap-summary-row" onclick="openCardModal(${rec.card.id})">
                    <td class="roadmap-summary-card">${rec.card.name}</td>
                    <td><span class="roadmap-summary-action${danger ? ' danger' : ''}">${ROADMAP_ACTION_LABELS[rec.action] || rec.action}</span></td>
                    <td class="roadmap-summary-num">${rewardsLabel}</td>
                    <td class="roadmap-summary-num">${signupBonusLabel}</td>
                    <td class="roadmap-summary-num">${benefitsLabel}</td>
                    <td class="roadmap-summary-num">${feeLabel}</td>
                    <td class="roadmap-summary-num roadmap-summary-value${danger ? ' danger' : ''}">${_roadmapFormatSigned(estimatedValue)}</td>
                </tr>
            `;
        }).join('');

    return `
        <div class="result-section-header"><span class="ico">table_view</span><span class="result-section-header-title">Card summary</span></div>
        <div class="roadmap-summary-table-wrap">
            <table class="roadmap-summary-table">
                <thead>
                    <tr>
                        <th>Card</th>
                        <th>Action</th>
                        <th class="roadmap-summary-num">Rewards</th>
                        <th class="roadmap-summary-num">Signup Bonus</th>
                        <th class="roadmap-summary-num">Benefits</th>
                        <th class="roadmap-summary-num">Fee</th>
                        <th class="roadmap-summary-num">Value/yr</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

// Phase I: the full Cards x categories allocation matrix (see
// _roadmapCategoryMatrix). Falls back to the older single-winner
// "Best card per category" block (portfolioSummary.category_optimization)
// when category_allocation isn't in the payload — Current Roadmaps and
// shared roadmaps persisted before this field existed only carry the old
// shape.
function _roadmapCategoryMatrixHtml(matrix) {
    if (!matrix || matrix.length === 0) {
        return '';
    }
    const rows = matrix.map(group => `
        <tr class="roadmap-summary-row">
            <td class="roadmap-summary-card">
                <span class="ico" style="font-size:16px; vertical-align:-3px; color:var(--accent);">${(typeof CATEGORY_ICONS !== 'undefined' && CATEGORY_ICONS[group.slug]) || 'category'}</span>
                ${escapeHtml(group.category_name)}
            </td>
            <td>${group.rows.map(r => r.uncovered
                ? `<div style="color:var(--muted);">Uncovered — no portfolio card rates this</div>`
                : `<div>${escapeHtml(r.card_name)} <span style="color:var(--muted);">(${r.rate.toFixed(1)}x)</span></div>`
            ).join('')}</td>
            <td class="roadmap-summary-num">${group.rows.map(r => `$${r.annual_spend.toFixed(0)}`).join('<br>')}</td>
            <td class="roadmap-summary-num">$${group.total_rewards.toFixed(0)}</td>
        </tr>
    `).join('');

    return `
        <div class="result-section-header"><span class="ico">grid_view</span><span class="result-section-header-title">Cards by category</span></div>
        <div class="roadmap-summary-table-wrap">
            <table class="roadmap-summary-table">
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Earning card</th>
                        <th class="roadmap-summary-num">Annual spend</th>
                        <th class="roadmap-summary-num">Annual rewards</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

// Phase I: portfolio-level first-year vs ongoing panel (see
// _roadmapValueOverTime). Skips itself when the two figures are
// effectively equal — nothing extra to call out.
function _roadmapValueOverTimeHtml(split) {
    if (Math.abs(split.first_year_extras) < 1) {
        return '';
    }
    const extrasLabel = split.first_year_extras > 0
        ? `Includes ${_roadmapFormatSigned(split.first_year_extras)} in signup bonuses & waived first-year fees`
        : `First year runs ${_roadmapFormatSigned(Math.abs(split.first_year_extras))} below ongoing (first-year fees outweigh any bonuses)`;
    return `
        <div class="result-section-header"><span class="ico">timeline</span><span class="result-section-header-title">This year vs. every year after</span></div>
        <div class="grouped-card"><div class="category-card-body" style="padding:12px 14px;">
            <div class="result-hero-stats" style="margin-top:0;">
                <div class="tile"><div class="tile-figure">${_roadmapFormatSigned(split.first_year)}</div><div class="tile-label">This year</div></div>
                <div class="tile"><div class="tile-figure">${_roadmapFormatSigned(split.ongoing)}</div><div class="tile-label">Every year after</div></div>
            </div>
            <div style="text-align:center; color:var(--muted); font-size:12px; margin-top:10px;">${extrasLabel}</div>
        </div></div>
    `;
}

// Phase I: minimal curated redemption guidance (roadmaps/redemption.py).
// rec.card.redemption is always present with the same shape once the
// payload carries it — absent entirely on older persisted/shared payloads
// generated before this field existed, so this returns '' rather than
// throwing on missing keys.
function _roadmapRedemptionHtml(rec) {
    const redemption = rec.card && rec.card.redemption;
    if (!redemption || !redemption.note) {
        return '';
    }
    const headlineParts = [];
    if (redemption.program_label) {
        headlineParts.push(escapeHtml(redemption.program_label));
    }
    if (redemption.value_per_point) {
        headlineParts.push(`~${(redemption.value_per_point * 100).toFixed(1)}¢/pt`);
    }
    const headline = headlineParts.length ? `${headlineParts.join(' · ')} — ` : '';
    const partners = (redemption.transfer_partners && redemption.transfer_partners.length)
        ? `<div style="margin-top:2px;">Transfer partners: ${redemption.transfer_partners.map(escapeHtml).join(', ')}</div>`
        : '';
    const link = redemption.portal_url
        ? ` <a href="${escapeHtml(redemption.portal_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation();">Redeem &rarr;</a>`
        : '';
    return `
        <div class="breakdown-item" style="opacity: 0.85; font-size: 0.8em; display:block;">
            <span class="item-name">\u{1F4B3} ${headline}${escapeHtml(redemption.note)}${link}</span>
            ${partners}
        </div>
    `;
}

// Phase N: per-card line for the one-off expense panel below. Pure — the
// three terms always sum to value_for_expense by construction (see
// roadmaps/engine/calculators/expense.py), so this never diverges from the
// number it's explaining.
function _roadmapExpenseLineText(item) {
    const segments = [];
    if (item.signup_bonus_value > 0) segments.push(`bonus $${item.signup_bonus_value.toFixed(0)}`);
    segments.push(`rewards $${(item.category_rewards || 0).toFixed(0)}`);
    let text = segments.join(' + ');
    if (item.effective_annual_fee > 0) {
        text += ` − $${item.effective_annual_fee.toFixed(0)} fee`;
    }
    return `${text} = ${_roadmapFormatSigned(item.value_for_expense)}`;
}

// Phase N: "Best card for your purchase" panel from
// data.expense_recommendation (see roadmaps/engine/calculators/expense.py
// and GenerateRoadmapSerializer's 'expense' field). A parallel computation
// to the portfolio roadmap — present only when the user posted an
// 'expense', so this returns '' on every payload from before this feature
// existed and on any generation where the field was left blank.
function _roadmapExpensePanelHtml(expenseReco) {
    if (!expenseReco) {
        return '';
    }
    const amountLabel = `$${(expenseReco.amount || 0).toLocaleString()}`;
    const categoryLabel = expenseReco.category_name && expenseReco.category_name !== 'General purchase'
        ? ` on ${escapeHtml(expenseReco.category_name)}`
        : '';

    const applyRows = (expenseReco.apply || []).map((item, idx) => `
        <div class="grouped-card" style="margin-bottom:8px;">
            <div class="category-card-body" style="padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:10px; cursor:pointer;" onclick="openCardModal(${item.card.id})">
                <div>
                    <div style="font-weight:600;">${idx + 1}. ${escapeHtml(item.card.name)}</div>
                    <div style="font-size:12px; color:var(--muted);">${_roadmapExpenseLineText(item)}</div>
                    ${item.bonus_note ? `<div style="font-size:11px; color:var(--muted); margin-top:2px;">${escapeHtml(item.bonus_note)}</div>` : ''}
                </div>
                <div class="apply-card-value" style="font-weight:700; white-space:nowrap;">${_roadmapFormatSigned(item.value_for_expense)}</div>
            </div>
        </div>
    `).join('');

    const ownedHtml = expenseReco.best_owned ? `
        <div class="result-section-header" style="margin-top:14px;"><span class="ico">wallet</span><span class="result-section-header-title">Or use a card you already have</span></div>
        <div class="grouped-card">
            <div class="category-card-body" style="padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:10px; cursor:pointer;" onclick="openCardModal(${expenseReco.best_owned.card.id})">
                <div>
                    <div style="font-weight:600;">${escapeHtml(expenseReco.best_owned.card.name)}</div>
                    <div style="font-size:12px; color:var(--muted);">${_roadmapExpenseLineText(expenseReco.best_owned)}</div>
                </div>
                <div class="apply-card-value" style="font-weight:700; white-space:nowrap;">${_roadmapFormatSigned(expenseReco.best_owned.value_for_expense)}</div>
            </div>
        </div>
    ` : '';

    const applySection = applyRows
        ? `<div class="result-section-header"><span class="ico">shopping_cart</span><span class="result-section-header-title">Best card to apply for</span></div>${applyRows}`
        : `<div style="color:var(--muted); font-size:13px;">No eligible new-card matches found for this purchase.</div>`;

    return `
        <div class="result-section-header"><span class="ico">payments</span><span class="result-section-header-title">Best card for your ${amountLabel}${categoryLabel} purchase</span></div>
        <div style="margin-bottom:14px;">
            ${applySection}
            ${ownedHtml}
        </div>
    `;
}

async function removeCardOwnership(cardId, cardName, buttonEl) {
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.textContent = '...';
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
        showNotification(`Removed ${cardName || 'card'} from your cards — regenerate for updated math`, 'success');
        if (buttonEl) {
            buttonEl.textContent = 'Removed';
        }
    } catch (error) {
        console.error('Error removing card:', error);
        showNotification('Error removing card. Please try again.', 'error');
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.textContent = 'Remove from my cards';
        }
    }
}

// Register global control change handler for filtering/sorting
if (typeof window !== 'undefined' && typeof window._onRoadmapControlChange === 'undefined') {
    window._onRoadmapControlChange = function() {
        const filterCheckbox = document.getElementById('filterSelfFunding');
        const sortSelect = document.getElementById('sortRecommendations');
        if (filterCheckbox) {
            renderRoadmapResults.state.filterSelfFunding = filterCheckbox.checked;
        }
        if (sortSelect) {
            renderRoadmapResults.state.sortMode = sortSelect.value;
        }
        if (renderRoadmapResults.lastData) {
            renderRoadmapResults(renderRoadmapResults.lastData, {
                ...renderRoadmapResults.lastOpts,
                noScroll: true
            });
        }
    };
}

function renderRoadmapResults(data, opts = {}) {
    // Cache inputs for client-side filtering/sorting re-renders
    renderRoadmapResults.lastData = data;
    renderRoadmapResults.lastOpts = opts;

    if (!renderRoadmapResults.state) {
        renderRoadmapResults.state = {
            filterSelfFunding: false,
            sortMode: 'default'
        };
    }

    const container = opts.container || document.getElementById('results');
    const readOnly = !!opts.readOnly;
    const recommendations = data.recommendations || [];
    const portfolioSummary = data.portfolio_summary || {};
    const baseDate = data.generated_at ? new Date(data.generated_at) : new Date();

    const filterSelfFunding = renderRoadmapResults.state.filterSelfFunding;
    const sortMode = renderRoadmapResults.state.sortMode;

    let filteredRecs = [...recommendations];
    if (filterSelfFunding) {
        filteredRecs = filteredRecs.filter(rec => rec.pays_for_itself);
    }

    let html = `
        <div class="results" style="background:transparent;border:none;padding:0;">
            <h2 id="roadmapResults">${readOnly ? 'Shared roadmap' : 'Your roadmap'}</h2>
            ${opts.banner ? `<p style="text-align: center; color: var(--muted); margin: -10px 0 20px 0;">${opts.banner}</p>` : ''}
            ${opts.strategyLabel ? `<p style="text-align: center; color: var(--muted); margin: -10px 0 20px 0;">Strategy: <strong style="color:var(--text);">${opts.strategyLabel}</strong>${opts.poolLabel ? ` — ${opts.poolLabel}` : ''}</p>` : ''}
    `;

    // Phase N: independent of the portfolio recommendations below — renders
    // whenever the request posted an 'expense', even if there are no
    // apply/keep/cancel recommendations to show otherwise.
    html += _roadmapExpensePanelHtml(data.expense_recommendation);

    // Render client-side controls bar
    if (recommendations.length > 0) {
        html += `
            <div class="roadmap-controls" style="display:flex; justify-content:space-between; align-items:center; margin: 15px 4px 20px; gap: 10px; flex-wrap: wrap; padding: 10px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md);">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size: 13px; color: var(--muted); font-weight: 500;">Filter:</span>
                    <label style="display:inline-flex; align-items:center; gap:6px; font-size:13px; color:var(--text); cursor:pointer; margin:0; user-select:none;">
                        <input type="checkbox" id="filterSelfFunding" ${filterSelfFunding ? 'checked' : ''} onchange="window._onRoadmapControlChange()" style="margin:0; width:16px; height:16px; cursor:pointer;">
                        Self-funding cards only
                    </label>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size: 13px; color: var(--muted); font-weight: 500;">Sort:</span>
                    <select id="sortRecommendations" onchange="window._onRoadmapControlChange()" style="padding: 4px 8px; font-size: 13px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg); color: var(--text); cursor:pointer;">
                        <option value="default" ${sortMode === 'default' ? 'selected' : ''}>Recommended order</option>
                        <option value="selffunding" ${sortMode === 'selffunding' ? 'selected' : ''}>Self-funding first</option>
                    </select>
                </div>
            </div>
        `;
    }

    // Add portfolio summary if we have recommendations
    if (recommendations.length > 0 && portfolioSummary.card_count > 0) {
        const categoryOptimization = portfolioSummary.category_optimization || {};
        const categoryOptimizationEntries = Object.entries(categoryOptimization);
        const netValue = portfolioSummary.net_portfolio_value || 0;
        const keepCount = recommendations.filter(r => r.action === 'keep').length;
        const applyCount = recommendations.filter(r => r.action === 'apply').length;
        const cancelCount = recommendations.filter(r => r.action === 'cancel').length;

        html += `
            <div class="result-hero">
                <div class="result-hero-label">Estimated rewards / year</div>
                <div class="result-hero-figure-row">
                    <span class="result-hero-figure">${_roadmapFormatSigned(netValue)}</span>
                </div>
                <div class="result-hero-sub">$${(portfolioSummary.total_portfolio_rewards || 0).toFixed(0)} rewards − $${(portfolioSummary.total_annual_fees || 0).toFixed(0)} fees · $${(portfolioSummary.total_annual_spending || 0).toLocaleString()}/yr tracked</div>
                <div class="result-hero-stats">
                    <div class="tile"><div class="tile-figure">${keepCount}</div><div class="tile-label">Keep</div></div>
                    <div class="tile"><div class="tile-figure">${applyCount}</div><div class="tile-label">Apply</div></div>
                    <div class="tile"><div class="tile-figure">${cancelCount}</div><div class="tile-label">Cancel</div></div>
                </div>
                ${(portfolioSummary.bonus_capacity && portfolioSummary.bonus_capacity.months_committed > 0) ? `
                    <div style="background: var(--bg); border: 1px solid var(--border); padding: 12px 15px; border-radius: var(--radius-sm); margin-top: 15px; font-size: 13px; color: var(--muted);">
                        At ~$${(portfolioSummary.bonus_capacity.total_monthly_spending || 0).toLocaleString()}/mo of spending, the recommended signup bonuses take
                        ~${portfolioSummary.bonus_capacity.months_committed} of the year's ${portfolioSummary.bonus_capacity.capacity_months} months to earn:
                        ${(portfolioSummary.bonus_capacity.timeline || []).filter(t => t.bonus_counted).map(t =>
                            `${t.card_name} ${t.recommended_month ? `in ~${t.recommended_month} mo` : 'now'}`).join(', ')}.
                        ${portfolioSummary.bonus_capacity.deferred_applies && portfolioSummary.bonus_capacity.deferred_applies.length > 0 ? `
                            Deferred until next year: ${portfolioSummary.bonus_capacity.deferred_applies.join(', ')}.
                        ` : ''}
                        ${portfolioSummary.bonus_capacity.bonus_less_applies && portfolioSummary.bonus_capacity.bonus_less_applies.length > 0 ? `
                            ${portfolioSummary.bonus_capacity.bonus_less_applies.join(', ')} ${portfolioSummary.bonus_capacity.bonus_less_applies.length === 1 ? 'is' : 'are'}
                            recommended on ongoing value alone — ${portfolioSummary.bonus_capacity.bonus_less_applies.length === 1 ? 'its' : 'their'} bonus doesn't fit this year's spending.
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;

        html += _roadmapSummaryTableHtml(filteredRecs);

        // Phase I: the full allocation matrix supersedes the older
        // single-winner "Best card per category" block — but fall back to
        // the old block for payloads persisted/shared before
        // category_allocation existed.
        const categoryAllocation = portfolioSummary.category_allocation || [];
        if (categoryAllocation.length > 0) {
            html += _roadmapCategoryMatrixHtml(_roadmapCategoryMatrix(categoryAllocation));
        } else if (categoryOptimizationEntries.length > 0) {
            html += `
                <div class="result-section-header"><span class="ico">grid_view</span><span class="result-section-header-title">Best card per category</span></div>
                <div class="grouped-card"><div class="category-card-body">
                    ${categoryOptimizationEntries.map(([slug, catData]) => `
                        <div class="category-row">
                            <span class="ico">${(typeof CATEGORY_ICONS !== 'undefined' && CATEGORY_ICONS[slug]) || 'category'}</span>
                            <span class="category-row-name">${catData.category_name}</span>
                            <span class="category-row-card">${catData.best_card}</span>
                            <span class="category-row-rate">${catData.best_rate}x</span>
                        </div>
                    `).join('')}
                </div></div>
            `;
        }

        html += _roadmapValueOverTimeHtml(_roadmapValueOverTime(recommendations));
    }

    if (recommendations.length === 0) {
        html += '<p style="text-align:center;color:var(--muted);">No recommendations found with your current criteria. Try adjusting your filters.</p>';
    } else if (filteredRecs.length === 0) {
        html += '<p style="text-align:center;color:var(--muted);margin-top:20px;margin-bottom:20px;">No self-funding cards found in this roadmap. Try clearing the filter.</p>';
    } else {
        // Group recommendations by action type with sort mode applied
        const groupedRecs = {
            keep: filteredRecs.filter(rec => rec.action === 'keep')
                .sort((a, b) => {
                    if (sortMode === 'selffunding') {
                        const aSelf = a.pays_for_itself ? 1 : 0;
                        const bSelf = b.pays_for_itself ? 1 : 0;
                        if (aSelf !== bSelf) return bSelf - aSelf;
                    }
                    return 0;
                }),
            cancel: filteredRecs.filter(rec => rec.action === 'cancel')
                .sort((a, b) => {
                    if (sortMode === 'selffunding') {
                        const aSelf = a.pays_for_itself ? 1 : 0;
                        const bSelf = b.pays_for_itself ? 1 : 0;
                        if (aSelf !== bSelf) return bSelf - aSelf;
                    }
                    return 0;
                }),
            apply: filteredRecs.filter(rec => rec.action === 'apply')
                .sort((a, b) => {
                    if (sortMode === 'selffunding') {
                        const aSelf = a.pays_for_itself ? 1 : 0;
                        const bSelf = b.pays_for_itself ? 1 : 0;
                        if (aSelf !== bSelf) return bSelf - aSelf;
                    }
                    return (a.recommended_month || 0) - (b.recommended_month || 0) || a.priority - b.priority;
                }),
            upgrade: filteredRecs.filter(rec => rec.action === 'upgrade')
                .sort((a, b) => {
                    if (sortMode === 'selffunding') {
                        const aSelf = a.pays_for_itself ? 1 : 0;
                        const bSelf = b.pays_for_itself ? 1 : 0;
                        if (aSelf !== bSelf) return bSelf - aSelf;
                    }
                    return 0;
                }),
            downgrade: filteredRecs.filter(rec => rec.action === 'downgrade')
                .sort((a, b) => {
                    if (sortMode === 'selffunding') {
                        const aSelf = a.pays_for_itself ? 1 : 0;
                        const bSelf = b.pays_for_itself ? 1 : 0;
                        if (aSelf !== bSelf) return bSelf - aSelf;
                    }
                    return 0;
                })
        };

        // Section metadata (order: Apply, Keep, Cancel, then any Upgrade/Downgrade)
        const sections = [
            { key: 'apply', title: 'Apply for these', icon: 'add_circle', danger: false },
            { key: 'keep', title: 'Keep', icon: 'check_circle', danger: false },
            { key: 'cancel', title: 'Cancel', icon: 'cancel', danger: true },
            { key: 'upgrade', title: 'Upgrade options', icon: 'trending_up', danger: false },
            { key: 'downgrade', title: 'Downgrade options', icon: 'trending_down', danger: false }
        ];

        sections.forEach(section => {
            const sectionRecs = groupedRecs[section.key];
            if (sectionRecs && sectionRecs.length > 0) {
                const isApply = section.key === 'apply';
                const canRemove = !readOnly && (section.key === 'keep' || section.key === 'cancel');
                html += `
                    <div class="result-section-header${section.danger ? ' danger' : ''}" onclick="toggleSection('${section.key}')" style="cursor:pointer;">
                        <span class="ico">${section.icon}</span>
                        <span class="result-section-header-title">${section.title}</span>
                        <span class="result-section-header-count">${sectionRecs.length}</span>
                        <span class="ico" id="toggle-${section.key}" style="margin-left:auto; font-size:20px; color:var(--muted); transition: transform 0.2s ease;">expand_more</span>
                    </div>
                    <div id="content-${section.key}" class="${isApply ? '' : 'grouped-card' + (section.danger ? ' danger' : '')}">
                `;

                sectionRecs.forEach(rec => {
                    // Generate detailed value breakdown HTML
                    let breakdownHtml = '';

                    if (rec.rewards_breakdown && Array.isArray(rec.rewards_breakdown) && rec.rewards_breakdown.length > 0) {
                        let breakdownItems = [];

                        rec.rewards_breakdown.forEach(breakdown => {
                            breakdownItems.push({
                                name: breakdown.category_name || 'Unknown Category',
                                value: parseFloat(breakdown.category_rewards || 0),
                                type: breakdown.type || 'reward_category',
                                calculation: breakdown.calculation || ''
                            });
                        });

                        let signupBonusValue = 0;
                        if (rec.action === 'apply' && rec.signup_bonus_value) {
                            signupBonusValue = parseFloat(rec.signup_bonus_value);
                        }

                        const annualFeeForBreakdown = parseFloat(rec.card.effective_annual_fee || 0);

                        breakdownHtml = `
                            <div class="value-breakdown">
                                <div class="breakdown-header">
                                    <strong>💰 Value Breakdown</strong>
                                    <span class="breakdown-total">Total: $${rec.estimated_rewards.toFixed(0)}</span>
                                </div>
                                <div class="breakdown-items">`;

                        const rewardCategories = breakdownItems.filter(item =>
                            item.type !== 'credit' && item.type !== 'info' && item.type !== 'bonus_shift');
                        const credits = breakdownItems.filter(item => item.type === 'credit');
                        const bonusShifts = breakdownItems.filter(item => item.type === 'bonus_shift');
                        const infoNotes = breakdownItems.filter(item => item.type === 'info');

                        rewardCategories.forEach(item => {
                            if (item.value > 0) {
                                breakdownHtml += `
                                    <div class="breakdown-item positive" title="${item.calculation}">
                                        <span class="item-name">🏆 ${item.name}</span>
                                        <span class="item-value">+$${item.value.toFixed(0)}</span>
                                    </div>`;
                            }
                        });

                        const shiftAggregate = _roadmapBonusShiftAggregate(bonusShifts);
                        if (shiftAggregate) {
                            const cls = shiftAggregate.total >= 0 ? 'positive' : 'negative';
                            const sign = shiftAggregate.total >= 0 ? '+' : '-';
                            breakdownHtml += `
                                <div class="breakdown-item ${cls}" title="${shiftAggregate.title}" style="font-size: 0.85em;">
                                    <span class="item-name">🔁 Bonus-window opportunity cost</span>
                                    <span class="item-value">${sign}$${Math.abs(shiftAggregate.total).toFixed(0)}</span>
                                </div>`;
                        }

                        credits.forEach(item => {
                            if (item.value > 0) {
                                breakdownHtml += `
                                    <div class="breakdown-item positive">
                                        <span class="item-name">🎁 ${item.name}</span>
                                        <span class="item-value">+$${item.value.toFixed(0)}</span>
                                    </div>`;
                            }
                        });

                        if (rec.action === 'apply' && signupBonusValue > 0) {
                            breakdownHtml += `
                                <div class="breakdown-item positive">
                                    <span class="item-name">🎁 Signup Bonus</span>
                                    <span class="item-value">+$${signupBonusValue.toFixed(0)}</span>
                                </div>`;
                        }

                        if (annualFeeForBreakdown > 0) {
                            const feeLabel = rec.card.annual_fee_waived_first_year && rec.action === 'apply'
                                ? 'Annual Fee (waived Year 1)'
                                : 'Annual Fee';
                            const feeValue = rec.card.annual_fee_waived_first_year && rec.action === 'apply' ? 0 : annualFeeForBreakdown;

                            if (feeValue > 0) {
                                breakdownHtml += `
                                    <div class="breakdown-item negative">
                                        <span class="item-name">${feeLabel}</span>
                                        <span class="item-value">-$${feeValue.toFixed(0)}</span>
                                    </div>`;
                            }
                        }

                        infoNotes.forEach(item => {
                            breakdownHtml += `
                                <div class="breakdown-item" style="opacity: 0.85; font-size: 0.85em;">
                                    <span class="item-name">⚠️ ${item.name}: ${item.calculation}</span>
                                </div>`;
                        });

                        if (rec.valuation_note) {
                            breakdownHtml += `
                                <div class="breakdown-item" style="opacity: 0.7; font-size: 0.8em;">
                                    <span class="item-name">${rec.valuation_note}</span>
                                </div>`;
                        }
                        if (rec.first_year_value !== undefined && rec.ongoing_value !== undefined
                            && Math.abs(rec.first_year_value - rec.ongoing_value) >= 1) {
                            breakdownHtml += `
                                <div class="breakdown-item" style="font-size: 0.85em;">
                                    <span class="item-name">First year: $${rec.first_year_value.toFixed(0)} · Ongoing: $${rec.ongoing_value.toFixed(0)}/yr</span>
                                </div>`;
                        }

                        breakdownHtml += _roadmapRedemptionHtml(rec);

                        breakdownHtml += `
                                </div>
                            </div>`;
                    }

                    const estimatedValue = parseFloat(rec.estimated_rewards) || 0;
                    const annualFee = parseFloat(rec.card.effective_annual_fee || 0);
                    const reasonLabel = _roadmapTopCategoriesLabel(rec);
                    const eligibilityHtml = rec.eligibility_note ? `
                        <div class="chip" style="margin-top: 10px;">${rec.eligibility_note}</div>
                    ` : '';
                    const paysForItselfHtml = rec.pays_for_itself ? `
                        <div class="chip accent" style="margin-top: 10px;"><span class="ico" style="font-size: 14px;">savings</span> Pays for itself via credits</div>
                    ` : '';
                    const removeHtml = canRemove ? `
                        <div style="margin-top:8px;">
                            <button onclick="event.stopPropagation(); removeCardOwnership(${rec.card.id}, '${(rec.card.name || '').replace(/'/g, "\\'")}', this)" class="secondary" style="padding:6px 10px; font-size:12px;">Remove from my cards</button>
                        </div>
                    ` : '';

                    if (isApply) {
                        html += `
                            <div class="apply-card" onclick="openCardModal(${rec.card.id})">
                                <div class="apply-card-top">
                                    <div>
                                        <div class="apply-card-name">${rec.card.name}</div>
                                        <div class="apply-card-reason">${reasonLabel}${_roadmapApplyAsLabel(rec)}</div>
                                    </div>
                                    <span class="apply-card-value">${_roadmapFormatSigned(estimatedValue)}</span>
                                </div>
                                <div class="apply-card-stats">
                                    ${rec.card.signup_bonus_amount ? `
                                        <div><div class="apply-card-stat-label">BONUS</div><div class="apply-card-stat-value">${rec.card.signup_bonus_amount.toLocaleString()}</div></div>
                                    ` : ''}
                                    <div><div class="apply-card-stat-label">FEE</div><div class="apply-card-stat-value">$${annualFee.toFixed(0)}${rec.card.annual_fee_waived_first_year ? '*' : ''}</div></div>
                                    ${rec.card.signup_spending_requirement ? `
                                        <div><div class="apply-card-stat-label">SPEND</div><div class="apply-card-stat-value">$${(rec.card.signup_spending_requirement / 1000).toFixed(0)}k/${rec.card.signup_time_limit_months || 3}mo</div></div>
                                    ` : ''}
                                    <div><div class="apply-card-stat-label">WHEN</div><div class="apply-card-stat-value">${_roadmapTimingLabel(rec.recommended_month, baseDate)}</div></div>
                                </div>
                                ${eligibilityHtml}
                                ${paysForItselfHtml}
                                ${breakdownHtml}
                                ${!readOnly ? `
                                <div style="display:flex; gap:8px; margin-top:12px;">
                                    <button onclick="event.stopPropagation(); openCardOwnershipModal(${rec.card.id}, null, '${rec.card.card_type || 'personal'}')" class="secondary" style="flex:1; padding:8px; font-size:12px;">I have this card</button>
                                    ${rec.card.apply_url ? `<button onclick="event.stopPropagation(); window.open('${rec.card.apply_url}', '_blank')" style="flex:1; padding:8px; font-size:12px;">Apply Now</button>` : ''}
                                </div>
                                ` : ''}
                            </div>
                        `;
                    } else {
                        html += `
                            <div class="grouped-item">
                                <div class="grouped-row" onclick="openCardModal(${rec.card.id})">
                                    <div>
                                        <div class="grouped-row-name">${rec.card.name}</div>
                                        <div class="grouped-row-reason">${reasonLabel}${_roadmapApplyAsLabel(rec)}</div>
                                    </div>
                                    <span class="grouped-row-value${section.danger ? ' danger' : ''}">${_roadmapFormatSigned(estimatedValue)}</span>
                                </div>
                                ${eligibilityHtml}
                                ${paysForItselfHtml}
                                ${breakdownHtml}
                                ${removeHtml}
                            </div>
                        `;
                    }
                });

                html += `</div>`;
            }
        });
    }

    html += '</div>';
    container.innerHTML = html;

    if (typeof applyMobileClasses === 'function') {
        applyMobileClasses();
    }

    if (!opts.noScroll) {
        setTimeout(() => {
            const roadmapElement = document.getElementById('roadmapResults');
            if (roadmapElement) {
                roadmapElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    }
}
