document.addEventListener('DOMContentLoaded', function () {
    // Add Category
    const addCategoryBtn = document.getElementById('add-category');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', function () {
            const container = document.getElementById('categories-container');
            const categoryCount = container.querySelectorAll('.category-row').length;
            const newRow = document.createElement('div');
            newRow.className = 'row mb-3 category-row';

            // Check if we're using selects or inputs for categories
            const useSelect = container.querySelector('select[name^="category_name_"]');

            if (useSelect) {
                // Clone the first select to get all options
                const firstSelect = container.querySelector('select[name^="category_name_"]');
                const selectHTML = firstSelect.outerHTML
                    .replace(/name="category_name_\d+"/, `name="category_name_${categoryCount}"`)
                    .replace(/selected/, ''); // Remove any selected attributes

                newRow.innerHTML = `
                    <div class="col-md-6">
                        <label class="form-label">Category</label>
                        ${selectHTML}
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Reward Percentage</label>
                        <div class="input-group">
                            <input type="number" step="0.1" min="0" class="form-control" name="category_percentage_${categoryCount}" value="0">
                            <span class="input-group-text">%</span>
                        </div>
                    </div>
                    <div class="col-md-1 d-flex align-items-end mb-2">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-category">✕</button>
                    </div>`;
            } else {
                // Use text input if selects aren't being used
                newRow.innerHTML = `
                    <div class="col-md-6">
                        <label class="form-label">Category</label>
                        <input type="text" class="form-control" name="category_name_${categoryCount}" placeholder="e.g., Gas, Groceries">
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Reward Percentage</label>
                        <div class="input-group">
                            <input type="number" step="0.1" min="0" class="form-control" name="category_percentage_${categoryCount}" value="0">
                            <span class="input-group-text">%</span>
                        </div>
                    </div>
                    <div class="col-md-1 d-flex align-items-end mb-2">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-category">✕</button>
                    </div>`;
            }

            container.appendChild(newRow);
        });
    }

    // Remove Category
    document.body.addEventListener('click', function (e) {
        if (e.target.classList.contains('remove-category')) {
            const categoryRow = e.target.closest('.category-row');
            categoryRow.remove();
        }
    });

    // Add Offer
    const addOfferBtn = document.getElementById('add-offer');
    if (addOfferBtn) {
        addOfferBtn.addEventListener('click', function () {
            const container = document.getElementById('offers-container');
            const offerCount = container.querySelectorAll('.offer-row').length;
            const newRow = document.createElement('div');
            newRow.className = 'row mb-3 offer-row';
            newRow.innerHTML = `
                <div class="col-md-4">
                    <label class="form-label">Offer Type</label>
                    <input type="text" class="form-control" name="offer_type_${offerCount}" placeholder="e.g., Travel Credit">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Amount</label>
                    <div class="input-group">
                        <span class="input-group-text">$</span>
                        <input type="number" step="0.01" min="0" class="form-control" name="offer_amount_${offerCount}" value="0">
                    </div>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Frequency</label>
                    <select class="form-select" name="offer_frequency_${offerCount}">
                        <option value="one_time">One Time</option>
                        <option value="annual">Annual</option>
                        <option value="monthly">Monthly</option>
                    </select>
                </div>
                <div class="col-md-1 d-flex align-items-end mb-2">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-offer">✕</button>
                </div>`;
            container.appendChild(newRow);
        });
    }

    // Remove Offer
    document.body.addEventListener('click', function (e) {
        if (e.target.classList.contains('remove-offer')) {
            const offerRow = e.target.closest('.offer-row');
            offerRow.remove();
        }
    });
}); 