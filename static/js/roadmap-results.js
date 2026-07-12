// Shared roadmap results renderer. Used by index.html (live generate +
// "Current Roadmap" restore on page load) and the public shared-roadmap
// page (readOnly: true — no ownership/apply actions).
//
// Depends on globals defined in base.html: API_BASE, isAuthenticated,
// getCookie(), showNotification(), UserDataManager, LocalStorage. Depends
// on CATEGORY_ICONS, toggleSection(), openCardModal(), openCardOwnershipModal()
// being defined on the page that calls renderRoadmapResults() (index.html).

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

const ROADMAP_ACTION_LABELS = { apply: 'Apply', keep: 'Keep', cancel: 'Cancel', upgrade: 'Upgrade', downgrade: 'Downgrade' };
const ROADMAP_ACTION_DANGER = { cancel: true };

function _roadmapSummaryTableHtml(recommendations) {
    const order = ['apply', 'keep', 'cancel', 'upgrade', 'downgrade'];
    const rows = order
        .flatMap(action => recommendations.filter(rec => rec.action === action))
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

async function removeCardOwnership(cardId, cardName, buttonEl) {
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.textContent = '...';
    }
    try {
        if (isAuthenticated) {
            const response = await fetch(`${API_BASE}/users/cards/toggle/`, {
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

function renderRoadmapResults(data, opts = {}) {
    const container = opts.container || document.getElementById('results');
    const readOnly = !!opts.readOnly;
    const recommendations = data.recommendations || [];
    const portfolioSummary = data.portfolio_summary || {};

    let html = `
        <div class="results" style="background:transparent;border:none;padding:0;">
            <h2 id="roadmapResults">${readOnly ? 'Shared roadmap' : 'Your roadmap'}</h2>
            ${opts.banner ? `<p style="text-align: center; color: var(--muted); margin: -10px 0 20px 0;">${opts.banner}</p>` : ''}
            ${opts.strategyLabel ? `<p style="text-align: center; color: var(--muted); margin: -10px 0 20px 0;">Strategy: <strong style="color:var(--text);">${opts.strategyLabel}</strong>${opts.poolLabel ? ` — ${opts.poolLabel}` : ''}</p>` : ''}
    `;

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
                ${(portfolioSummary.bonus_capacity && portfolioSummary.bonus_capacity.deferred_applies && portfolioSummary.bonus_capacity.deferred_applies.length > 0) ? `
                    <div style="background: var(--bg); border: 1px solid var(--border); padding: 12px 15px; border-radius: var(--radius-sm); margin-top: 15px; font-size: 13px; color: var(--muted);">
                        At ~$${(portfolioSummary.bonus_capacity.total_monthly_spending || 0).toLocaleString()}/mo of spending, the recommended signup bonuses take
                        ~${portfolioSummary.bonus_capacity.months_committed} of the year's ${portfolioSummary.bonus_capacity.capacity_months} months to earn.
                        Deferred until next year: ${portfolioSummary.bonus_capacity.deferred_applies.join(', ')}.
                    </div>
                ` : ''}
            </div>
        `;

        html += _roadmapSummaryTableHtml(recommendations);

        if (categoryOptimizationEntries.length > 0) {
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
    }

    if (recommendations.length === 0) {
        html += '<p style="text-align:center;color:var(--muted);">No recommendations found with your current criteria. Try adjusting your filters.</p>';
    } else {
        // Group recommendations by action type
        const groupedRecs = {
            keep: recommendations.filter(rec => rec.action === 'keep'),
            cancel: recommendations.filter(rec => rec.action === 'cancel'),
            apply: recommendations.filter(rec => rec.action === 'apply'),
            upgrade: recommendations.filter(rec => rec.action === 'upgrade'),
            downgrade: recommendations.filter(rec => rec.action === 'downgrade')
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

                        bonusShifts.forEach(item => {
                            const cls = item.value >= 0 ? 'positive' : 'negative';
                            const sign = item.value >= 0 ? '+' : '-';
                            breakdownHtml += `
                                <div class="breakdown-item ${cls}" title="${item.calculation}" style="font-size: 0.85em;">
                                    <span class="item-name">🔁 ${item.name}</span>
                                    <span class="item-value">${sign}$${Math.abs(item.value).toFixed(0)}</span>
                                </div>`;
                        });

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
                                        <div class="apply-card-reason">${reasonLabel}</div>
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
                                </div>
                                ${eligibilityHtml}
                                ${breakdownHtml}
                                ${!readOnly ? `
                                <div style="display:flex; gap:8px; margin-top:12px;">
                                    <button onclick="event.stopPropagation(); openCardOwnershipModal(${rec.card.id})" class="secondary" style="flex:1; padding:8px; font-size:12px;">I have this card</button>
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
                                        <div class="grouped-row-reason">${reasonLabel}</div>
                                    </div>
                                    <span class="grouped-row-value${section.danger ? ' danger' : ''}">${_roadmapFormatSigned(estimatedValue)}</span>
                                </div>
                                ${eligibilityHtml}
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
