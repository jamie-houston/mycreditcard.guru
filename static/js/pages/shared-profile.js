// Get the share UUID from the current URL
const pathParts = window.location.pathname.split('/');
const shareUuid = pathParts[pathParts.indexOf('shared') + 1];

// Load shared profile data (read-only)
document.addEventListener('DOMContentLoaded', function() {
    console.log('Loading shared profile data for UUID:', shareUuid);
    loadSharedProfileData();
});

async function loadSharedProfileData() {
    try {
        // Fetch the shared profile data
        const response = await fetch(`${API_BASE}/cards/profile/shared/${shareUuid}/`);
        if (!response.ok) {
            throw new Error(`Failed to fetch profile data: ${response.status}`);
        }
        
        const profileData = await response.json();
        console.log('Loaded profile data:', profileData);
        
        // Load all sections with the profile data
        await Promise.all([
            loadSharedCardCollection(profileData),
            loadSharedSpendingProfile(profileData),
            loadSharedCategoryOptimization(profileData)
        ]);
        
        // Calculate portfolio summary
        await calculateSharedPortfolioSummary(profileData);
        
    } catch (error) {
        console.error('Error loading shared profile data:', error);
        showError('Failed to load profile data. This profile may no longer be public or may not exist.');
    }
}

async function loadSharedCardCollection(profileData) {
    const cardCollectionContainer = document.getElementById('cardCollection');
    
    try {
        // Check if the profile has cards associated with the user
        if (!profileData.user) {
            cardCollectionContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No Card Information Available</h3>
                    <p>This shared profile doesn't have associated card collection data.</p>
                </div>
            `;
            return;
        }
        
        // For shared profiles, we'll show a message that card details are private
        cardCollectionContainer.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--muted);">
                <p>🔒 Card collection details are kept private in shared profiles</p>
                <p style="font-size: 14px;">Portfolio summary and optimization data are shown below</p>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading shared card collection:', error);
        cardCollectionContainer.innerHTML = `
            <div class="error">Error loading card collection data.</div>
        `;
    }
}

async function loadSharedSpendingProfile(profileData) {
    const spendingContainer = document.getElementById('spendingProfile');
    
    try {
        if (!profileData.spending_amounts || profileData.spending_amounts.length === 0) {
            spendingContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No Spending Profile Set</h3>
                    <p>This user hasn't set up their spending profile yet.</p>
                </div>
            `;
            return;
        }
        
        // Load category names for display
        const categoriesResponse = await fetch(`${API_BASE}/cards/spending-categories/`);
        const categoriesData = categoriesResponse.ok ? await categoriesResponse.json() : [];
        const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData.results || []);
        const categoryMap = {};
        categories.forEach(cat => {
            categoryMap[cat.slug] = cat.display_name || cat.name;
        });
        
        // Convert spending amounts to the expected format
        const spending = {};
        profileData.spending_amounts.forEach(amount => {
            spending[amount.category] = amount.monthly_amount;
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
        
        sortedSpending.forEach(([categorySlug, amount]) => {
            const categoryName = categoryMap[categorySlug] || categorySlug.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const monthlyAmount = parseFloat(amount);
            totalMonthly += monthlyAmount;
            
            spendingHtml += `
                <div class="spending-category-item">
                    <div class="spending-category-name">${categoryName}</div>
                    <div class="spending-category-amount">$${monthlyAmount.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})}/month</div>
                </div>
            `;
        });
        
        spendingHtml += `
            <div class="spending-total">
                <div class="spending-category-name"><strong>Total Monthly Spending</strong></div>
                <div class="spending-category-amount"><strong>$${totalMonthly.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})}/month</strong></div>
            </div>
        `;
        
        spendingContainer.innerHTML = spendingHtml;
        
    } catch (error) {
        console.error('Error loading shared spending profile:', error);
        spendingContainer.innerHTML = `
            <div class="error">Error loading spending profile data.</div>
        `;
    }
}

async function loadSharedCategoryOptimization(profileData) {
    const categoryContainer = document.getElementById('categoryOptimization');
    
    try {
        const recommendations = profileData.card_recommendations || [];
        
        if (recommendations.length === 0) {
            categoryContainer.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--muted);">
                    <p>🎯 No card recommendations available</p>
                    <p style="font-size: 14px;">This user may not have card ownership data or spending information</p>
                </div>
            `;
            return;
        }
        
        let recommendationsHtml = `
            <div style="margin-bottom: 20px;">
        `;
        
        recommendations.forEach((rec, index) => {
            recommendationsHtml += `
                <div class="card-recommendation" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; margin-bottom: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px;">
                    <div style="flex: 1;">
                        <span style="font-weight: 600; color: var(--text-strong); font-size: 15px;">${rec.category}</span>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <span style="color: var(--muted); font-size: 14px;">${rec.percentage}</span>
                    </div>
                    <div style="flex: 2; text-align: right;">
                        <span style="color: var(--accent); font-weight: 500; font-size: 14px;">
                            ${rec.recommended_card} (${rec.reward_rate})
                        </span>
                    </div>
                </div>
            `;
        });
        
        recommendationsHtml += `</div>`;
        
        categoryContainer.innerHTML = recommendationsHtml;
        
    } catch (error) {
        console.error('Error loading shared category optimization:', error);
        categoryContainer.innerHTML = `
            <div class="error">Error loading category optimization data.</div>
        `;
    }
}

async function calculateSharedPortfolioSummary(profileData) {
    try {
        let totalMonthlySpending = 0;
        
        if (profileData.spending_amounts && profileData.spending_amounts.length > 0) {
            totalMonthlySpending = profileData.spending_amounts
                .reduce((sum, amount) => sum + parseFloat(amount.monthly_amount || 0), 0);
        }
        
        // Show actual portfolio data from the enhanced API
        const portfolio = profileData.portfolio_summary || {};
        
        document.getElementById('totalCards').textContent = portfolio.total_cards || '0';
        document.getElementById('totalAnnualFees').textContent = 
            portfolio.total_annual_fees ? `$${portfolio.total_annual_fees.toLocaleString()}` : '$0';
        
        // Estimate annual rewards based on spending (rough calculation)
        const estimatedAnnualRewards = totalMonthlySpending * 12 * 0.015; // Assume 1.5% average return
        document.getElementById('totalAnnualRewards').textContent = 
            `~$${estimatedAnnualRewards.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})}`;
        
        const netValue = estimatedAnnualRewards - (portfolio.total_annual_fees || 0);
        document.getElementById('netPortfolioValue').textContent = 
            `${netValue >= 0 ? '+' : ''}$${netValue.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})}`;
        
    } catch (error) {
        console.error('Error calculating shared portfolio summary:', error);
        // Set fallback values
        document.getElementById('totalCards').textContent = 'Error';
        document.getElementById('totalAnnualFees').textContent = 'Error';
        document.getElementById('totalAnnualRewards').textContent = 'Error';
        document.getElementById('netPortfolioValue').textContent = 'Error';
    }
}
